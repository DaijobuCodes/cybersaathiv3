#!/usr/bin/env python3
"""
Populate Firebase with Sample Data

This script adds sample summaries and tips to Firebase Firestore to test the web interface.
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

def populate_sample_data():
    """Add sample summaries and tips to Firebase for testing"""
    # Load environment variables
    load_dotenv()
    
    print("=== Firebase Firestore Sample Data Generator ===\n")
    
    # Import Firebase helper functions
    try:
        from firebase_helper import initialize_firebase, find, find_one, insert_one, close
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
        
        # Add sample summaries and tips to each article
        print("\nAdding sample summaries and tips...")
        
        sample_summaries_added = 0
        sample_tips_added = 0
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        for i, article in enumerate(all_articles):
            article_id = article.get("_id")
            title = article.get("title", "Unknown Title")
            
            print(f"\nProcessing article {i+1}/{len(all_articles)}: {title[:50]}...")
            
            # Check if summary already exists - ENSURE THIS GOES TO SUMMARIES COLLECTION
            existing_summary = find_one(firebase_collection_summaries, {"article_id": article_id})
            if not existing_summary:
                # Create a sample summary
                summary_text = f"This article discusses important cybersecurity topics related to {title}. "
                summary_text += "The main points include potential vulnerabilities, defensive strategies, "
                summary_text += "and implications for organizations. Security professionals should take note "
                summary_text += "of the findings and implement appropriate countermeasures."
                
                summary_doc = {
                    "_id": f"summary_{article_id}",
                    "article_id": article_id,
                    "title": title,
                    "summary": summary_text,  # Important: summary is a top-level field in summaries collection
                    "source": article.get("source", "Unknown"),
                    "date": article.get("date", "Unknown"),
                    "generated_at": current_date
                }
                
                # Insert the summary in SUMMARIES collection
                insert_one(firebase_collection_summaries, summary_doc)
                sample_summaries_added += 1
                print(f"Added sample summary for article: {title[:50]}...")
            else:
                print(f"Summary already exists for article: {title[:50]}...")
            
            # Check if tips already exist - ENSURE THIS GOES TO TIPS COLLECTION
            existing_tips = find_one(firebase_collection_tips, {"article_id": article_id})
            if not existing_tips:
                # Create sample tips with the CORRECT structure (tips as a nested object)
                tips_summary = "This security issue requires immediate attention from cybersecurity teams. "
                tips_summary += "Organizations should implement proper controls and monitoring."
                
                dos = [
                    "Implement multi-factor authentication",
                    "Keep all systems and software updated",
                    "Train employees on security awareness",
                    "Use strong, unique passwords for all accounts",
                    "Regularly backup critical data"
                ]
                
                donts = [
                    "Don't reuse passwords across different systems",
                    "Don't leave default credentials unchanged",
                    "Don't ignore security warnings and alerts",
                    "Don't share sensitive information on public platforms",
                    "Don't connect to untrusted networks without VPN"
                ]
                
                tips_doc = {
                    "_id": f"tips_{article_id}",
                    "article_id": article_id,
                    "title": title,
                    "tips": {  # Important: tips is a nested object with summary, dos, donts
                        "summary": tips_summary,
                        "dos": dos,
                        "donts": donts
                    },
                    "source": article.get("source", "Unknown"),
                    "date": article.get("date", "Unknown"),
                    "generated_at": current_date
                }
                
                # Insert the tips in TIPS collection
                insert_one(firebase_collection_tips, tips_doc)
                sample_tips_added += 1
                print(f"Added sample tips for article: {title[:50]}...")
            else:
                # Check if existing tips document has correct structure
                if "tips" not in existing_tips or not isinstance(existing_tips["tips"], dict):
                    print(f"⚠️ Warning: Tips document for '{title[:50]}...' has incorrect structure.")
                    print("  Run fix_firebase_data.py to correct data structure issues.")
                else:
                    print(f"Tips already exist for article: {title[:50]}...")
        
        print(f"\nSummary:")
        print(f"- Added {sample_summaries_added} sample summaries to '{firebase_collection_summaries}' collection")
        print(f"- Added {sample_tips_added} sample tips to '{firebase_collection_tips}' collection")
        print(f"- Total articles processed: {len(all_articles)}")
        
        print("\n✅ Sample data generation completed!")
        print("\nNext steps:")
        print("1. Run 'python check_firebase_data.py' to verify data structure")
        print("2. If issues are found, run 'python fix_firebase_data.py' to fix them")
        print("3. Start the web interface with 'python web_interface.py' to see the results")
        
        return True
    
    except Exception as e:
        print(f"Error generating sample data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close Firebase connection
        print("\nClosing Firebase connection...")
        close()

if __name__ == "__main__":
    success = populate_sample_data()
    if not success:
        print("\nSample data generation failed!")
        sys.exit(1) 