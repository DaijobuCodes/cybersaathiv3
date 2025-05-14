#!/usr/bin/env python3
"""
Fix Firebase Data Structure

This script fixes data structure issues in Firebase Firestore
for tips and summaries collections.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

def fix_firebase_data():
    """Fix data structure issues in Firebase Firestore"""
    # Load environment variables
    load_dotenv()
    
    print("=== Firebase Data Structure Fixer ===\n")
    
    # Import Firebase helper functions
    try:
        from firebase_helper import initialize_firebase, find, find_one, insert_one, delete_one, close
    except ImportError as e:
        print(f"ERROR: Could not import firebase_helper module: {str(e)}")
        print("Make sure firebase_helper.py is in the same directory.")
        return False
    
    # Get Firebase collection names
    firebase_collection_news = os.getenv("FIREBASE_COLLECTION_NEWS", "news")
    firebase_collection_tips = os.getenv("FIREBASE_COLLECTION_TIPS", "tips")
    firebase_collection_summaries = os.getenv("FIREBASE_COLLECTION_SUMMARIES", "summaries")
    
    # Initialize Firebase
    firebase = initialize_firebase()
    if firebase is None:
        print("Failed to connect to Firebase. Check your credentials.")
        return False
    
    try:
        # Get all articles from the unified news collection
        print("Fetching articles from Firebase...")
        all_articles = find(firebase_collection_news)
        
        if not all_articles:
            print("No articles found in the database. Please run the scraper first.")
            return False
        
        # Count articles by source type
        hackernews_count = sum(1 for article in all_articles if article.get("source_type") == "hackernews")
        cybernews_count = sum(1 for article in all_articles if article.get("source_type") == "cybernews")
        
        print(f"Found {len(all_articles)} articles in the database.")
        print(f"- {hackernews_count} from Hacker News")
        print(f"- {cybernews_count} from Cyber News")
        
        # Get all tips and summaries
        tips_docs = find(firebase_collection_tips)
        summaries_docs = find(firebase_collection_summaries)
        
        print(f"Found {len(tips_docs)} tips documents")
        print(f"Found {len(summaries_docs)} summaries documents")
        
        # Create maps for easier lookup
        summaries_by_article_id = {}
        for summary in summaries_docs:
            if "article_id" in summary:
                summaries_by_article_id[summary["article_id"]] = summary
        
        # Fix issues
        fixed_tips = 0
        fixed_summaries = 0
        
        print("\nChecking and fixing data issues...")
        
        # Current date for generation timestamps
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        for tip in tips_docs:
            article_id = tip.get("article_id")
            
            if not article_id:
                print(f"  ⚠️ Skipping tip without article_id: {tip.get('_id')}")
                continue
            
            # Check if tip document has incorrect structure (summary at top level)
            if "tips" not in tip or not isinstance(tip["tips"], dict):
                # This tips document has incorrect structure
                title = tip.get("title", "Unknown Title")
                print(f"  🔧 Fixing incorrect tips structure for article: {title[:50]}... (ID: {article_id})")
                
                # Check if it has a summary field (which needs to be moved to summaries collection)
                if "summary" in tip:
                    summary_text = tip.get("summary")
                    
                    # Create a proper summary document if it doesn't exist
                    if article_id not in summaries_by_article_id:
                        summary_doc = {
                            "_id": f"summary_{article_id}",
                            "article_id": article_id,
                            "title": tip.get("title", "Unknown Title"),
                            "summary": summary_text,
                            "source": tip.get("source", "Unknown"),
                            "date": tip.get("date", "Unknown"),
                            "generated_at": current_date
                        }
                        
                        # Insert the summary into summaries collection
                        insert_one(firebase_collection_summaries, summary_doc)
                        fixed_summaries += 1
                        print(f"    ✅ Moved summary to summaries collection")
                
                # Create a proper tips document with the right structure
                dos = tip.get("dos", []) if isinstance(tip.get("dos", []), list) else []
                donts = tip.get("donts", []) if isinstance(tip.get("donts", []), list) else []
                
                # Default summary for tips if none exists
                tips_summary = "This security issue requires immediate attention from cybersecurity teams. "
                tips_summary += "Organizations should implement proper controls and monitoring."
                
                # Create sample tips if no valid dos/donts are found
                if not dos:
                    dos = [
                        "Implement multi-factor authentication",
                        "Keep all systems and software updated",
                        "Train employees on security awareness",
                        "Use strong, unique passwords for all accounts",
                        "Regularly backup critical data"
                    ]
                
                if not donts:
                    donts = [
                        "Don't reuse passwords across different systems",
                        "Don't leave default credentials unchanged",
                        "Don't ignore security warnings and alerts",
                        "Don't share sensitive information on public platforms",
                        "Don't connect to untrusted networks without VPN"
                    ]
                
                # Update the tips document with correct structure
                fixed_tip_doc = {
                    "_id": tip.get("_id"),
                    "article_id": article_id,
                    "title": tip.get("title", "Unknown Title"),
                    "tips": {
                        "summary": tips_summary,
                        "dos": dos,
                        "donts": donts
                    },
                    "source": tip.get("source", "Unknown"),
                    "date": tip.get("date", "Unknown"),
                    "generated_at": current_date
                }
                
                # Delete the old document and insert the new one
                delete_one(firebase_collection_tips, {"_id": tip.get("_id")})
                insert_one(firebase_collection_tips, fixed_tip_doc)
                fixed_tips += 1
                print(f"    ✅ Fixed tips document structure")
        
        print("\n=== Summary of Fixes ===")
        print(f"Fixed {fixed_tips} tips documents")
        print(f"Moved {fixed_summaries} summaries to the summaries collection")
        
        if fixed_tips == 0 and fixed_summaries == 0:
            print("\n✅ No issues found. All data is correctly structured!")
        else:
            print("\n✅ Data structure has been fixed!")
        
        return True
    
    except Exception as e:
        print(f"Error fixing Firebase data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close Firebase connection
        print("\nClosing Firebase connection...")
        close()

if __name__ == "__main__":
    success = fix_firebase_data()
    if not success:
        print("\nFirebase data fix failed!")
        sys.exit(1) 