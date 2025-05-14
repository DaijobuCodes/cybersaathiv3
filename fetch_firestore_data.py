#!/usr/bin/env python3
"""
Fetch and Display Firestore Data

This script fetches and displays all data from the Firestore collections
for the CyberSaathi project, helping to diagnose data retrieval issues.
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

def fetch_all_data():
    """Fetch and display all data from Firestore collections"""
    # Load environment variables
    load_dotenv()
    
    print("=== CyberSaathi Firestore Data Fetch Utility ===\n")
    
    # Import Firebase helper functions
    try:
        from firebase_helper import initialize_firebase, find, count_documents, close
    except ImportError as e:
        print(f"ERROR: Could not import firebase_helper module: {str(e)}")
        print("Make sure firebase_helper.py is in the same directory.")
        return False
    
    # Initialize Firebase
    print("Initializing Firebase connection...")
    firebase = initialize_firebase()
    if not firebase:
        print("Failed to initialize Firebase. Check your service account credentials.")
        return False
    
    try:
        # Get Firebase collection names
        firebase_collection_hackernews = os.getenv("FIREBASE_COLLECTION_HACKERNEWS", "hackernews")
        firebase_collection_cybernews = os.getenv("FIREBASE_COLLECTION_CYBERNEWS", "cybernews")
        firebase_collection_tips = os.getenv("FIREBASE_COLLECTION_TIPS", "tips")
        firebase_collection_summaries = os.getenv("FIREBASE_COLLECTION_SUMMARIES", "summaries")
        
        # Fetch data from each collection
        print("\nFetching data from collections...")
        
        # Fetch articles
        hackernews_articles = find(firebase_collection_hackernews)
        cybernews_articles = find(firebase_collection_cybernews)
        
        # Fetch tips and summaries
        tips = find(firebase_collection_tips)
        summaries = find(firebase_collection_summaries)
        
        # Print counts
        print(f"\n=== Collection Counts ===")
        print(f"HackerNews articles: {len(hackernews_articles)}")
        print(f"CyberNews articles: {len(cybernews_articles)}")
        print(f"Tips documents: {len(tips)}")
        print(f"Summaries documents: {len(summaries)}")
        
        # Analyze tips and summaries
        tips_with_article_ids = sum(1 for tip in tips if "article_id" in tip)
        summaries_with_article_ids = sum(1 for summary in summaries if "article_id" in summary)
        
        print(f"\n=== Data Structure Analysis ===")
        print(f"Tips with article_id: {tips_with_article_ids} / {len(tips)}")
        print(f"Summaries with article_id: {summaries_with_article_ids} / {len(summaries)}")
        
        # Check for tips formatting
        correct_tips_format = sum(1 for tip in tips if "tips" in tip and isinstance(tip["tips"], dict))
        incorrect_tips_format = len(tips) - correct_tips_format
        
        print(f"Tips with correct format: {correct_tips_format} / {len(tips)}")
        print(f"Tips with incorrect format: {incorrect_tips_format} / {len(tips)}")
        
        # Check for articles with both tips and summaries
        article_ids = set()
        for article in hackernews_articles + cybernews_articles:
            if "_id" in article:
                article_ids.add(article["_id"])
        
        tips_article_ids = set(tip["article_id"] for tip in tips if "article_id" in tip)
        summaries_article_ids = set(summary["article_id"] for summary in summaries if "article_id" in summary)
        
        articles_with_tips = len(tips_article_ids.intersection(article_ids))
        articles_with_summaries = len(summaries_article_ids.intersection(article_ids))
        articles_with_both = len(tips_article_ids.intersection(summaries_article_ids).intersection(article_ids))
        
        print(f"\n=== Article Coverage ===")
        print(f"Total unique articles: {len(article_ids)}")
        print(f"Articles with tips: {articles_with_tips} / {len(article_ids)} ({articles_with_tips / len(article_ids):.1%})")
        print(f"Articles with summaries: {articles_with_summaries} / {len(article_ids)} ({articles_with_summaries / len(article_ids):.1%})")
        print(f"Articles with both tips and summaries: {articles_with_both} / {len(article_ids)} ({articles_with_both / len(article_ids):.1%})")
        
        # Display sample data
        if len(summaries) > 0:
            print("\n=== Sample Summary ===")
            sample_summary = summaries[0]
            print(f"ID: {sample_summary.get('_id', 'N/A')}")
            print(f"Article ID: {sample_summary.get('article_id', 'N/A')}")
            print(f"Title: {sample_summary.get('title', 'N/A')[:80]}...")
            print(f"Summary: {sample_summary.get('summary', 'N/A')[:150]}...")
        
        if len(tips) > 0:
            print("\n=== Sample Tips ===")
            sample_tip = tips[0]
            print(f"ID: {sample_tip.get('_id', 'N/A')}")
            print(f"Article ID: {sample_tip.get('article_id', 'N/A')}")
            print(f"Title: {sample_tip.get('title', 'N/A')[:80]}...")
            
            if "tips" in sample_tip and isinstance(sample_tip["tips"], dict):
                tips_data = sample_tip["tips"]
                print(f"Tips summary: {tips_data.get('summary', 'N/A')[:150]}...")
                
                if "dos" in tips_data and isinstance(tips_data["dos"], list):
                    print(f"Tips dos count: {len(tips_data['dos'])}")
                    if len(tips_data["dos"]) > 0:
                        print(f"  Sample do: {tips_data['dos'][0]}")
                
                if "donts" in tips_data and isinstance(tips_data["donts"], list):
                    print(f"Tips donts count: {len(tips_data['donts'])}")
                    if len(tips_data["donts"]) > 0:
                        print(f"  Sample don't: {tips_data['donts'][0]}")
            else:
                print("Tips data is not in the correct format")
        
        print("\n✅ Data fetch and analysis completed successfully")
        return True
        
    except Exception as e:
        print(f"Error fetching Firestore data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close Firebase connection
        print("\nClosing Firebase connection...")
        close()

if __name__ == "__main__":
    success = fetch_all_data()
    if not success:
        print("\nFirestore data fetch failed!")
        sys.exit(1) 