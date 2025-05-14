#!/usr/bin/env python3
"""
Check Firebase Data Structure

This script checks the current data structure in Firebase Firestore
for tips and summaries collections to diagnose data issues.
"""

import os
import sys
from dotenv import load_dotenv

def check_firebase_data():
    """Check the current data structure in Firebase Firestore"""
    # Load environment variables
    load_dotenv()
    
    print("=== Firebase Data Structure Checker ===\n")
    
    # Import Firebase helper functions
    try:
        from firebase_helper import initialize_firebase, find, find_one, close
        print("Successfully imported Firebase helper functions")
    except ImportError as e:
        print(f"ERROR: Could not import firebase_helper module: {str(e)}")
        print("Make sure firebase_helper.py is in the same directory.")
        return False
    
    # Get Firebase collection names
    firebase_collection_news = os.getenv("FIREBASE_COLLECTION_NEWS", "news")
    firebase_collection_tips = os.getenv("FIREBASE_COLLECTION_TIPS", "tips")
    firebase_collection_summaries = os.getenv("FIREBASE_COLLECTION_SUMMARIES", "summaries")
    
    print(f"Using collections: {firebase_collection_news}, {firebase_collection_tips}, {firebase_collection_summaries}")
    
    # Print environment variables for debugging
    firebase_service_account = os.getenv("FIREBASE_SERVICE_ACCOUNT", "Not set")
    print(f"FIREBASE_SERVICE_ACCOUNT: {firebase_service_account}")
    
    # Initialize Firebase
    print("Initializing Firebase connection...")
    firebase = initialize_firebase()
    if firebase is None:
        print("Failed to connect to Firebase. Check your credentials.")
        return False
    
    print("Firebase connection successful!")
    
    try:
        # Get sample articles to check
        print("Fetching sample articles...")
        all_articles = find(firebase_collection_news, limit=5)
        
        if not all_articles:
            print("No articles found in the database. Please run the scraper first.")
            return False
        
        print(f"Found {len(all_articles)} articles for checking.")
        
        # Count articles by source type
        hackernews_count = sum(1 for article in all_articles if article.get("source_type") == "hackernews")
        cybernews_count = sum(1 for article in all_articles if article.get("source_type") == "cybernews")
        print(f"- {hackernews_count} from Hacker News")
        print(f"- {cybernews_count} from Cyber News")
        
        # Check database structure
        for i, article in enumerate(all_articles):
            article_id = article.get("_id")
            title = article.get("title", "Unknown Title")
            source_type = article.get("source_type", "unknown")
            
            print(f"\n[Article {i+1}] {title[:50]}... (ID: {article_id}, Type: {source_type})")
            
            # Check in summaries collection
            summary_doc = find_one(firebase_collection_summaries, {"article_id": article_id})
            if summary_doc:
                print(f"  ✅ Found in summaries collection")
                if "summary" in summary_doc:
                    print(f"  - Summary: {summary_doc['summary'][:100]}...")
                else:
                    print(f"  - ⚠️ Summary document exists but has no 'summary' field")
            else:
                print(f"  ❌ Not found in summaries collection")
            
            # Check in tips collection
            tips_doc = find_one(firebase_collection_tips, {"article_id": article_id})
            if tips_doc:
                print(f"  ✅ Found in tips collection")
                
                # Check if tips document has correct structure
                if "tips" in tips_doc and isinstance(tips_doc["tips"], dict):
                    print(f"  - Tips structure: {list(tips_doc['tips'].keys())}")
                    
                    # Check if tips has summary
                    if "summary" in tips_doc["tips"]:
                        print(f"  - Tips summary: {tips_doc['tips']['summary'][:100]}...")
                    
                    # Check if tips has dos and donts
                    if "dos" in tips_doc["tips"]:
                        print(f"  - Tips dos: {len(tips_doc['tips']['dos'])} items")
                    if "donts" in tips_doc["tips"]:
                        print(f"  - Tips donts: {len(tips_doc['tips']['donts'])} items")
                else:
                    # Check if tips document has summary directly (wrong structure)
                    if "summary" in tips_doc:
                        print(f"  - ⚠️ Tips document has 'summary' field at top level (WRONG STRUCTURE)")
                        print(f"  - Summary in tips: {tips_doc['summary'][:100]}...")
            else:
                print(f"  ❌ Not found in tips collection")
        
        print("\n=== Summary ===")
        
        # Check all collections for counts
        tips_docs = find(firebase_collection_tips)
        summaries_docs = find(firebase_collection_summaries)
        all_news_articles = find(firebase_collection_news)
        
        tips_count = len(tips_docs)
        summaries_count = len(summaries_docs)
        total_articles = len(all_news_articles)
        
        # Count articles by source type
        total_hackernews = sum(1 for article in all_news_articles if article.get("source_type") == "hackernews")
        total_cybernews = sum(1 for article in all_news_articles if article.get("source_type") == "cybernews")
        
        print(f"Total articles: {total_articles}")
        print(f"- Hacker News articles: {total_hackernews}")
        print(f"- Cyber News articles: {total_cybernews}")
        print(f"Total tips documents: {tips_count}")
        print(f"Total summaries documents: {summaries_count}")
        
        # Check for structural issues
        incorrect_tips = 0
        for tip in tips_docs:
            if "tips" not in tip or not isinstance(tip["tips"], dict):
                incorrect_tips += 1
        
        if incorrect_tips > 0:
            print(f"\n⚠️ Found {incorrect_tips} tips documents with incorrect structure!")
            print("Run the fix_firebase_data.py script to correct these issues.")
        else:
            print(f"\n✅ All tips documents have correct structure.")
        
        return True
    
    except Exception as e:
        print(f"Error checking Firebase data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close Firebase connection
        print("\nClosing Firebase connection...")
        close()

if __name__ == "__main__":
    success = check_firebase_data()
    if not success:
        print("\nFirebase data check failed!")
        sys.exit(1) 