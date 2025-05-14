"""
Script to query CISO tips from MongoDB by date or article ID.
"""

import argparse
import json
from pymongo import MongoClient
from typing import Dict, Any, List, Optional
from datetime import datetime

def connect_to_mongodb(uri: str = "mongodb+srv://ayushchy012:Chahuta3011@article-db.milce.mongodb.net/") -> MongoClient:
    """Establish connection to MongoDB"""
    try:
        client = MongoClient(uri)
        # Test the connection
        client.server_info()
        print("Successfully connected to MongoDB")
        return client
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        raise

def query_tips_by_article_id(client: MongoClient, article_id: str, db_name: str = "cybersaathi") -> Optional[Dict[str, Any]]:
    """Query tips for a specific article ID across all date collections"""
    db = client[db_name]
    
    # Filter for tips collections
    collections = db.list_collection_names()
    tips_collections = [col for col in collections if col.startswith('tips_')]
    
    # Search for the article in all tips collections
    for collection_name in tips_collections:
        collection = db[collection_name]
        tip = collection.find_one({"article_id": article_id})
        if tip:
            return tip
    
    print(f"No tips found for article ID: {article_id}")
    return None

def query_tips_by_date(client: MongoClient, date: str, db_name: str = "cybersaathi") -> List[Dict[str, Any]]:
    """Query all tips for a specific date"""
    db = client[db_name]
    
    # Format the date for collection name
    formatted_date = date.replace('-', '_')
    collection_name = f"tips_{formatted_date}"
    
    # Check if collection exists
    if collection_name not in db.list_collection_names():
        print(f"No tips found for date: {date}")
        return []
    
    # Get all tips for the date
    collection = db[collection_name]
    tips = list(collection.find())
    
    if not tips:
        print(f"No tips found for date: {date}")
        return []
    
    return tips

def list_available_dates(client: MongoClient, db_name: str = "cybersaathi") -> List[str]:
    """List all available dates for tips collections"""
    db = client[db_name]
    collections = db.list_collection_names()
    
    # Get only the date-based collections
    date_collections = []
    for col in collections:
        if col.startswith('tips_'):
            parts = col[5:].split('_') # Remove 'tips_' prefix and split
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                date_collections.append(col)
    
    # Sort by date (convert to datetime objects for proper sorting)
    dates = []
    for col in date_collections:
        parts = col[5:].split('_')
        date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
        dates.append(date_str)
    
    return sorted(dates)

def list_all_tips(client: MongoClient, db_name: str = "cybersaathi") -> List[Dict[str, Any]]:
    """List all tips across all date collections"""
    db = client[db_name]
    collections = db.list_collection_names()
    
    # Filter for tips collections
    tips_collections = [col for col in collections if col.startswith('tips_')]
    
    # Get a summary of each tip in all collections
    tips_summary = []
    for collection_name in tips_collections:
        date = collection_name.replace('tips_', '').replace('_', '-')
        collection = db[collection_name]
        
        for tip in collection.find():
            tips_summary.append({
                'article_id': tip.get('article_id', 'Unknown'),
                'title': tip.get('title', 'Unknown'),
                'source': tip.get('source', 'Unknown'),
                'date': tip.get('date', 'Unknown')
            })
    
    return tips_summary

def format_tips_as_text(tips: Dict[str, Any]) -> str:
    """Format tips as readable text"""
    if not tips:
        return "No tips found."
    
    output = []
    output.append(f"Title: {tips.get('title', 'Unknown')}")
    output.append(f"Source: {tips.get('source', 'Unknown')}")
    output.append(f"Date: {tips.get('date', 'Unknown')}")
    output.append(f"Tags: {tips.get('tags', 'None')}")
    output.append(f"Article ID: {tips.get('article_id', 'Unknown')}")
    output.append("")
    
    # Summary
    if 'summary' in tips:
        output.append("KEY SECURITY ISSUE:")
        output.append(tips['summary'])
        output.append("")
    
    # DO's
    if 'dos' in tips and tips['dos']:
        output.append("DO's:")
        for i, do_item in enumerate(tips['dos']):
            output.append(f"✅ {do_item}")
        output.append("")
    
    # DON'Ts
    if 'donts' in tips and tips['donts']:
        output.append("DON'Ts:")
        for i, dont_item in enumerate(tips['donts']):
            output.append(f"❌ {dont_item}")
    
    return "\n".join(output)

def main():
    """Main function to run the query"""
    parser = argparse.ArgumentParser(description="Query CISO tips from MongoDB by date or article ID")
    parser.add_argument("--id", type=str, 
                        help="Article ID to query tips for (e.g., 'article_1')")
    parser.add_argument("--date", type=str, 
                        help="Date to query tips for (format: YYYY-MM-DD)")
    parser.add_argument("--list-dates", action="store_true",
                        help="List all available dates for tips collections")
    parser.add_argument("--list", action="store_true",
                        help="List all available tips")
    parser.add_argument("--output", type=str, 
                        help="Output file for the query results (optional)")
    parser.add_argument("--mongodb-uri", type=str, 
                        default="mongodb+srv://ayushchy012:Chahuta3011@article-db.milce.mongodb.net/",
                        help="MongoDB connection URI (default: MongoDB Atlas connection)")
    parser.add_argument("--db-name", type=str, default="cybersaathi",
                        help="MongoDB database name (default: cybersaathi)")
    
    args = parser.parse_args()
    
    # Ensure at least one action is specified
    if not args.id and not args.date and not args.list_dates and not args.list:
        parser.error("Please specify one of: --id, --date, --list-dates, or --list")
    
    try:
        # Connect to MongoDB
        client = connect_to_mongodb(args.mongodb_uri)
        
        # List all available dates
        if args.list_dates:
            dates = list_available_dates(client, args.db_name)
            if dates:
                print("\nAvailable dates for tips collections:")
                for i, date in enumerate(dates):
                    print(f"{i+1}. {date}")
            else:
                print("\nNo tips collections found in the database.")
        
        # List all tips
        if args.list:
            tips_summary = list_all_tips(client, args.db_name)
            if tips_summary:
                print("\nAvailable tips:")
                for i, summary in enumerate(tips_summary):
                    print(f"{i+1}. {summary['article_id']} - {summary['title']} ({summary['source']}, {summary['date']})")
            else:
                print("\nNo tips found in the database.")
        
        # Query tips by date
        if args.date:
            tips_list = query_tips_by_date(client, args.date, args.db_name)
            if tips_list:
                print(f"\nFound {len(tips_list)} tips for date {args.date}:")
                for i, tip in enumerate(tips_list):
                    print(f"\n{'-'*50}")
                    print(f"Tip #{i+1}:")
                    print(f"{'-'*50}")
                    formatted_tip = format_tips_as_text(tip)
                    print(formatted_tip)
                    
                    # Save to file if requested
                    if args.output:
                        with open(args.output, 'w', encoding='utf-8') as f:
                            for tip in tips_list:
                                f.write(format_tips_as_text(tip))
                                f.write("\n\n" + "="*50 + "\n\n")
                        print(f"\nTips saved to {args.output}")
        
        # Query specific article tips
        if args.id:
            tip = query_tips_by_article_id(client, args.id, args.db_name)
            if tip:
                formatted_tip = format_tips_as_text(tip)
                print("\n" + "="*50)
                print(formatted_tip)
                print("="*50)
                
                # Save to file if requested
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(formatted_tip)
                    print(f"\nTip saved to {args.output}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    main() 