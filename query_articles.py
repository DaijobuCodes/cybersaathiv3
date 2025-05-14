#!/usr/bin/env python3
"""
MongoDB Query Utility for Cybersecurity News Scraper

This script allows you to query and view articles stored in the MongoDB database,
including decrypting the encrypted titles.
"""

# Set environment variable to prevent Scraper.py from running scrapers on import
import os
os.environ['NO_AUTO_SCRAPE'] = 'True'

import argparse
import pymongo
import csv
from datetime import datetime
from Scraper import generate_encryption_key, decrypt_text

def connect_to_mongodb():
    """Connect to MongoDB and return client and database objects"""
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["scapper"]
        return client, db
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        return None, None

def list_collections(db):
    """List all collections in the database with document counts"""
    collections = db.list_collection_names()
    
    if not collections:
        print("No collections found in the database.")
        return
    
    print("Available collections:")
    for collection in collections:
        count = db[collection].count_documents({})
        print(f"  - {collection}: {count} documents")

def query_articles(db, collection_name, query=None, limit=10, decrypt=False, export_csv=None):
    """Query articles from a specific collection"""
    if collection_name not in db.list_collection_names():
        print(f"Collection '{collection_name}' does not exist.")
        return
    
    collection = db[collection_name]
    
    # Use empty query if none provided
    if query is None:
        query = {}
    
    # Get the articles
    articles = collection.find(query).limit(limit)
    articles_list = list(articles)  # Convert cursor to list for multiple use
    
    # Generate encryption key for decryption
    key = None
    if decrypt:
        key = generate_encryption_key(None)
    
    # Prepare CSV export if requested
    csv_file = None
    csv_writer = None
    if export_csv:
        filename = f"{export_csv}_{collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_file = open(filename, 'w', newline='', encoding='utf-8')
        fieldnames = ['id', 'title', 'date', 'source', 'url', 'tags', 'description']
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        csv_writer.writeheader()
    
    # Display the results
    count = 0
    for article in articles_list:
        count += 1
        print(f"\nArticle #{count}:")
        print(f"ID: {article.get('_id', 'N/A')}")
        
        # Title handling
        title = article.get('title', 'No title')
        print(f"Title: {title}")
        
        # Decrypt title if requested
        if decrypt and 'encrypted_title' in article:
            try:
                decrypted_title = decrypt_text(article['encrypted_title'], key)
                print(f"Decrypted Title: {decrypted_title}")
                
                # Verify decryption was correct
                if decrypted_title == title:
                    print("✓ Decryption verified (matches original title)")
                else:
                    print("⚠ Decryption produced a different result than stored title")
            except Exception as e:
                print(f"Error decrypting title: {str(e)}")
        
        # Display other article details
        date = article.get('date', 'N/A')
        source = article.get('source', 'N/A')
        url = article.get('url', 'N/A')
        print(f"Date: {date}")
        print(f"Source: {source}")
        print(f"URL: {url}")
        
        # Show tags if they exist
        tags = article.get('tags', 'No tags')
        if tags != "Tags not found":
            print(f"Tags: {tags}")
        
        # Show normalized title if it exists
        if 'normalized_title' in article:
            print(f"Normalized Title: {article['normalized_title']}")
        
        # Show a preview of the description
        description = article.get('description', 'No description')
        print(f"Description: {description}")
        
        # Write to CSV if exporting
        if csv_writer:
            csv_writer.writerow({
                'id': article.get('_id', ''),
                'title': title,
                'date': date,
                'source': source,
                'url': url,
                'tags': tags,
                'description': description
            })
    
    if count == 0:
        print("No articles found matching the query.")
    else:
        print(f"\nTotal: {count} articles found.")
    
    # Close CSV file if open
    if csv_file:
        csv_file.close()
        print(f"Articles exported to {filename}")

def main():
    """Main function for the script"""
    parser = argparse.ArgumentParser(description="Query and view articles from MongoDB database")
    parser.add_argument("--collection", choices=["hackernews", "cybernews", "all"], 
                        default="all", help="Collection to query")
    parser.add_argument("--limit", type=int, default=10, 
                        help="Maximum number of articles to retrieve")
    parser.add_argument("--decrypt", action="store_true", 
                        help="Decrypt encrypted titles")
    parser.add_argument("--search", type=str, 
                        help="Search for articles containing this text in the title or description")
    parser.add_argument("--list", action="store_true", 
                        help="List available collections")
    parser.add_argument("--export", type=str, 
                        help="Export results to CSV files with the provided prefix")
    
    args = parser.parse_args()
    
    # Connect to MongoDB
    client, db = connect_to_mongodb()
    if client is None or db is None:
        print("Failed to connect to MongoDB. Make sure it's running on localhost:27017")
        return
    
    try:
        # Just list collections if requested
        if args.list:
            list_collections(db)
            return
        
        # Prepare search query if specified
        query = None
        if args.search:
            # Search in both title and description (case-insensitive)
            query = {
                "$or": [
                    {"title": {"$regex": args.search, "$options": "i"}},
                    {"description": {"$regex": args.search, "$options": "i"}}
                ]
            }
        
        # Query the collection(s)
        if args.collection == "all":
            collections = db.list_collection_names()
            for collection in collections:
                print(f"\n=== Articles from {collection} ===")
                query_articles(db, collection, query, args.limit, args.decrypt, args.export)
        else:
            query_articles(db, args.collection, query, args.limit, args.decrypt, args.export)
    
    finally:
        # Close MongoDB connection
        if client:
            client.close()

if __name__ == "__main__":
    main() 