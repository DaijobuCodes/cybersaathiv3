#!/usr/bin/env python3
"""
Test Firebase Firestore Storage

This script tests the connection to Firebase Firestore and verifies
that data can be inserted, retrieved, and deleted properly.
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

def test_firebase_storage():
    """Test Firebase Firestore storage functionality"""
    # Load environment variables
    load_dotenv()
    
    print("=== Firebase Firestore Storage Test ===\n")
    
    # Import Firebase helper functions
    try:
        from firebase_helper import initialize_firebase, insert_one, find_one, find, delete_many, close
    except ImportError as e:
        print(f"ERROR: Could not import firebase_helper module: {str(e)}")
        print("Make sure firebase_helper.py is in the same directory.")
        return False
    
    # Step 1: Initialize Firebase
    print("\nStep 1: Initializing Firebase connection...")
    firebase = initialize_firebase()
    if not firebase:
        print("Failed to initialize Firebase. Check your service account credentials.")
        return False
    
    print("Success: Firebase initialized.")
    
    try:
        # Step 2: Test inserting a document
        print("\nStep 2: Testing document insertion...")
        test_collection = "test_collection"
        test_doc = {
            "_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": "Test Document",
            "description": "This is a test document to verify Firestore storage",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": ["test", "firebase", "storage"]
        }
        
        result = insert_one(test_collection, test_doc)
        if not result or "inserted_id" not in result:
            print(f"Failed to insert test document: {result}")
            return False
        
        doc_id = result["inserted_id"]
        print(f"Success: Document inserted with ID: {doc_id}")
        
        # Step 3: Test retrieving the document
        print("\nStep 3: Testing document retrieval...")
        retrieved_doc = find_one(test_collection, {"_id": doc_id})
        if not retrieved_doc:
            print(f"Failed to retrieve test document with ID: {doc_id}")
            return False
        
        print("Success: Document retrieved:")
        print(json.dumps(retrieved_doc, indent=2, default=str))
        
        # Step 4: Test finding all documents in collection
        print("\nStep 4: Testing collection query...")
        all_docs = find(test_collection)
        print(f"Found {len(all_docs)} documents in {test_collection}")
        
        # Step 5: Clean up test document
        print("\nStep 5: Cleaning up test document...")
        delete_result = delete_many(test_collection, {"_id": doc_id})
        if not delete_result or delete_result.get("deleted_count", 0) == 0:
            print(f"Warning: Failed to delete test document: {delete_result}")
        else:
            print(f"Success: Deleted {delete_result.get('deleted_count')} test documents")
        
        # Step 6: Test storing in a real collection
        print("\nStep 6: Testing storage in actual collection...")
        news_collection = os.getenv("FIREBASE_COLLECTION_HACKERNEWS", "hackernews")
        test_article = {
            "_id": f"test_article_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": "Test Cybersecurity Article",
            "description": "This is a test article to verify proper storage in the news collection",
            "url": "https://example.com/test-article",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Test Source",
            "tags": "security, test",
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        result = insert_one(news_collection, test_article)
        if not result or "inserted_id" not in result:
            print(f"Failed to insert test article: {result}")
        else:
            article_id = result["inserted_id"]
            print(f"Success: Test article inserted with ID: {article_id}")
            
            # Clean up test article
            delete_result = delete_many(news_collection, {"_id": article_id})
            if delete_result and delete_result.get("deleted_count", 0) > 0:
                print(f"Success: Test article deleted")
        
        print("\nAll tests completed successfully!")
        return True
    
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close Firebase connection
        print("\nClosing Firebase connection...")
        close()

if __name__ == "__main__":
    success = test_firebase_storage()
    if not success:
        print("\nFIREBASE STORAGE TEST FAILED!")
        sys.exit(1)
    else:
        print("\nFIREBASE STORAGE TEST PASSED!") 