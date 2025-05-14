#!/usr/bin/env python3
"""
Firebase Firestore Connection Test Script

This script tests the connection to Firebase Firestore using the service account
credentials in the .env file and displays information about available collections.
"""

import os
import sys
from dotenv import load_dotenv

def test_firestore_connection():
    """Test the Firebase Firestore connection and print database information"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Import Firebase helper functions
    try:
        from firebase_helper import initialize_firebase, get_collection, count_documents
    except ImportError:
        print("ERROR: firebase_helper.py module not found.")
        print("Make sure the firebase_helper.py file is in the same directory.")
        return False
    
    # Get Firebase service account path from environment variables
    firebase_service_account = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    
    if not firebase_service_account:
        print("ERROR: FIREBASE_SERVICE_ACCOUNT environment variable not found.")
        print("Make sure you have a .env file with the correct Firebase service account path.")
        print("Expected path: C:/Users/deevp/Downloads/cybers-b3f99-firebase-adminsdk-fbsvc-6da50d3aa3.json")
        return False
    
    try:
        print(f"Connecting to Firebase Firestore using credentials: {firebase_service_account}")
        firebase = initialize_firebase(firebase_service_account)
        
        if not firebase:
            print("❌ Firebase initialization failed.")
            return False
            
        print("✅ Firebase Firestore connection successful!")
        
        # Get database information
        db = firebase["db"]
        
        # List collections - Note: Firestore doesn't have a direct method to list all collections
        # We'll use known collection names from .env
        collection_names = [
            os.getenv("FIREBASE_COLLECTION_HACKERNEWS", "hackernews"),
            os.getenv("FIREBASE_COLLECTION_CYBERNEWS", "cybernews"),
            os.getenv("FIREBASE_COLLECTION_TIPS", "tips"),
            os.getenv("FIREBASE_COLLECTION_SUMMARIES", "summaries")
        ]
        
        print("\nFirebase Firestore Database")
        print(f"Available collections: {', '.join(collection_names)}")
        
        # Display collection stats if collections exist
        print("\nCollection stats:")
        for collection_name in collection_names:
            try:
                count = count_documents(collection_name)
                print(f"- {collection_name}: {count} documents")
            except Exception as e:
                print(f"- {collection_name}: Error getting count - {str(e)}")
        
        # Close the connection
        from firebase_helper import close
        close()
        
        return True
    
    except Exception as e:
        print(f"❌ Error connecting to Firebase Firestore: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=============================================")
    print("        CyberSaathi Firebase Test")
    print("=============================================\n")
    
    if test_firestore_connection():
        print("\n✅ All tests passed! Your Firebase Firestore connection is working correctly.")
    else:
        print("\n❌ Firebase Firestore connection test failed. Please check your .env file and connection settings.") 