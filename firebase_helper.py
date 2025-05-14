"""
Firebase Firestore Helper Module

This module provides functions to connect to and interact with Firebase Firestore,
serving as a drop-in replacement for the MongoDB functionality.
"""

import os
import json
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from colorama import Fore, Style

# Global variables to store Firestore client and db
_app = None
_db = None
_collections = {}

def initialize_firebase(service_account_path=None):
    """Initialize Firebase with service account credentials"""
    global _app, _db
    
    try:
        # If already initialized, return existing client
        if _app is not None:
            return {"client": _app, "db": _db}
        
        # Get service account path from environment variable if not provided
        if not service_account_path:
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")
            
        # If still not found, show helpful error message
        if not service_account_path:
            print(f"{Fore.RED}ERROR: Firebase service account path not found in .env file.")
            print(f"{Fore.YELLOW}Please ensure your .env file contains the FIREBASE_SERVICE_ACCOUNT variable.")
            print(f"{Fore.YELLOW}You can copy .env.template to .env and update with your Firebase credentials.{Style.RESET_ALL}")
            raise ValueError("Firebase service account credentials not found. Check your .env file.")
        
        # Check if file exists
        if not os.path.exists(service_account_path):
            print(f"{Fore.RED}ERROR: Firebase service account file not found at: {service_account_path}")
            print(f"{Fore.YELLOW}Please check that the path in your .env file is correct.{Style.RESET_ALL}")
            raise FileNotFoundError(f"Firebase credentials file not found at: {service_account_path}")
        
        # Check if file is valid JSON
        try:
            with open(service_account_path, 'r') as f:
                json_data = json.load(f)
                
            required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email"]
            for key in required_keys:
                if key not in json_data:
                    raise ValueError(f"Firebase service account file is missing required key: {key}")
                    
        except json.JSONDecodeError:
            raise ValueError("Firebase service account file is not valid JSON")
            
        print(f"{Fore.GREEN}Using Firebase service account: {service_account_path}")
        
        # Initialize Firebase app with credentials
        cred = credentials.Certificate(service_account_path)
        _app = firebase_admin.initialize_app(cred)
        
        # Get Firestore client
        _db = firestore.client()
        
        print(f"{Fore.GREEN}Firebase Firestore connection established successfully{Style.RESET_ALL}")
        
        # Print collection names for debugging
        collections = _db.collections()
        collection_names = [collection.id for collection in collections]
        print(f"{Fore.CYAN}Available collections: {', '.join(collection_names) if collection_names else 'No collections found'}{Style.RESET_ALL}")
        
        return {"client": _app, "db": _db}
    
    except Exception as e:
        print(f"{Fore.RED}Error connecting to Firebase Firestore: {str(e)}")
        print(f"{Fore.YELLOW}Please check your Firebase service account credentials and permissions.{Style.RESET_ALL}")
        return None

def get_collection(collection_name):
    """Get a reference to a Firestore collection, cached for performance"""
    global _collections
    
    # Initialize Firebase if not done already
    if _db is None:
        initialize_firebase()
    
    # Return cached collection reference if available
    if collection_name in _collections:
        return _collections[collection_name]
    
    # Get collection reference and cache it
    collection_ref = _db.collection(collection_name)
    _collections[collection_name] = collection_ref
    
    return collection_ref

def find_one(collection_name, query_dict):
    """Find a single document in a collection based on a query"""
    collection_ref = get_collection(collection_name)
    
    # Handle special case for '_id' field (MongoDB uses _id, Firestore uses document ID)
    if '_id' in query_dict:
        doc_id = query_dict['_id']
        doc = collection_ref.document(doc_id).get()
        if doc.exists:
            # Convert Firestore document to dict and add _id field
            doc_dict = doc.to_dict()
            doc_dict['_id'] = doc.id
            return doc_dict
        return None
    
    # Handle queries on other fields
    query = collection_ref
    for key, value in query_dict.items():
        query = query.where(key, "==", value)
    
    # Execute query and get the first result
    docs = query.limit(1).stream()
    for doc in docs:
        # Convert Firestore document to dict and add _id field
        doc_dict = doc.to_dict()
        doc_dict['_id'] = doc.id
        return doc_dict
    
    return None

def insert_one(collection_name, document):
    """Insert a document into a collection with a specified ID"""
    collection_ref = get_collection(collection_name)
    
    # Handle special case for '_id' field
    doc_id = None
    if '_id' in document:
        doc_id = document['_id']
        document_copy = document.copy()
        # Remove '_id' from the document as Firestore uses it as the document ID
        del document_copy['_id']
    else:
        document_copy = document
    
    # If doc_id is provided, use it as the document ID
    if doc_id:
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(document_copy)
        return {"inserted_id": doc_id}
    else:
        # Let Firestore generate a document ID
        doc_ref = collection_ref.add(document_copy)
        return {"inserted_id": doc_ref[1].id}

def update_one(collection_name, filter_dict, update_dict):
    """Update a document in a collection based on a filter"""
    collection_ref = get_collection(collection_name)
    
    # Handle special case for '_id' field
    if '_id' in filter_dict:
        doc_id = filter_dict['_id']
        doc_ref = collection_ref.document(doc_id)
        
        # Get only the update fields from $set operator if it exists
        if '$set' in update_dict:
            update_fields = update_dict['$set']
        else:
            update_fields = update_dict
        
        # Update the document
        doc_ref.update(update_fields)
        return {"modified_count": 1}
    
    # If no '_id' is provided, find the document first
    query = collection_ref
    for key, value in filter_dict.items():
        query = query.where(key, "==", value)
    
    # Execute query and update the first result
    docs = query.limit(1).stream()
    for doc in docs:
        # Get only the update fields from $set operator if it exists
        if '$set' in update_dict:
            update_fields = update_dict['$set']
        else:
            update_fields = update_dict
        
        # Update the document
        doc.reference.update(update_fields)
        return {"modified_count": 1}
    
    return {"modified_count": 0}

def delete_many(collection_name, filter_dict=None):
    """Delete documents from a collection based on a filter"""
    collection_ref = get_collection(collection_name)
    
    # If no filter is provided, get all documents in the collection
    if not filter_dict:
        docs = collection_ref.stream()
    else:
        # Build query from filter
        query = collection_ref
        for key, value in filter_dict.items():
            query = query.where(key, "==", value)
        docs = query.stream()
    
    # Delete each document
    deleted_count = 0
    for doc in docs:
        doc.reference.delete()
        deleted_count += 1
    
    return {"deleted_count": deleted_count}

def delete_one(collection_name, filter_dict):
    """Delete a single document from a collection based on a filter"""
    collection_ref = get_collection(collection_name)
    
    # Handle special case for '_id' field
    if '_id' in filter_dict:
        doc_id = filter_dict['_id']
        doc_ref = collection_ref.document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.delete()
            return {"deleted_count": 1}
        return {"deleted_count": 0}
    
    # Handle queries on other fields
    query = collection_ref
    for key, value in filter_dict.items():
        query = query.where(key, "==", value)
    
    # Execute query and delete the first result
    docs = query.limit(1).stream()
    for doc in docs:
        doc.reference.delete()
        return {"deleted_count": 1}
    
    return {"deleted_count": 0}

def count_documents(collection_name, filter_dict=None):
    """Count documents in a collection based on a filter"""
    collection_ref = get_collection(collection_name)
    
    # If no filter is provided, count all documents
    if not filter_dict:
        # Note: Firestore doesn't have a direct count method, so we need to get all documents
        # This is inefficient for large collections
        docs = list(collection_ref.stream())
        return len(docs)
    
    # Build query from filter
    query = collection_ref
    for key, value in filter_dict.items():
        query = query.where(key, "==", value)
    
    # Execute query and count results
    docs = list(query.stream())
    return len(docs)

def find(collection_name, filter_dict=None, sort=None, limit=None):
    """Find documents in a collection based on a filter, with sorting and limit"""
    collection_ref = get_collection(collection_name)
    
    # If no filter is provided, get all documents
    if not filter_dict:
        query = collection_ref
    else:
        # Build query from filter
        query = collection_ref
        for key, value in filter_dict.items():
            query = query.where(key, "==", value)
    
    # Apply sorting if provided
    if sort:
        for key, direction in sort:
            # Convert MongoDB sort direction to Firestore direction
            firestore_direction = firestore.Query.ASCENDING
            if direction == -1:
                firestore_direction = firestore.Query.DESCENDING
            query = query.order_by(key, direction=firestore_direction)
    
    # Apply limit if provided
    if limit:
        query = query.limit(limit)
    
    # Execute query and convert results to Python dictionaries
    docs = query.stream()
    results = []
    for doc in docs:
        doc_dict = doc.to_dict()
        doc_dict['_id'] = doc.id
        results.append(doc_dict)
    
    return results

def close():
    """Close the Firebase connection"""
    global _app, _db, _collections
    
    # Delete the app instance
    if _app:
        try:
            firebase_admin.delete_app(_app)
            _app = None
            _db = None
            _collections = {}
            print("Firebase connection closed")
        except Exception as e:
            print(f"Error closing Firebase connection: {str(e)}")

def create_index(collection_name, field_name):
    """Create a Firestore index (placeholder function to match MongoDB API)"""
    # Note: Firestore indexes are created in the Firebase console or using Firebase CLI
    # This function is a placeholder to maintain API compatibility
    print(f"Note: For Firestore, indexes are managed in the Firebase console or using Firebase CLI.")
    print(f"Consider adding an index for {field_name} in collection {collection_name}")
    return True 