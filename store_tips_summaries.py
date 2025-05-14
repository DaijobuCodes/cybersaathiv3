#!/usr/bin/env python3
"""
Store tips and summaries in Firebase Firestore

This script provides functions to parse markdown files containing
article summaries and CISO tips, and store them in Firebase Firestore.
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def parse_summaries_markdown(file_path: str, *source_collections: str) -> List[Dict[str, Any]]:
    """
    Parse the summaries markdown file and extract articles with summaries.
    Link them to original articles by ID.
    
    Args:
        file_path: Path to the markdown file
        *source_collections: One or more source collections to look up articles from
    """
    print(f"Reading summaries markdown file: {file_path}")
    
    # Read markdown file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into individual articles
    article_sections = re.split(r'\n## \d+\.', content)
    
    # First section contains header information
    header = article_sections[0]
    article_sections = article_sections[1:]
    
    # Extract generation date from header
    date_match = re.search(r'Generated on: (\d{4}-\d{2}-\d{2})', header)
    if not date_match:
        raise ValueError("Could not find generation date in markdown file")
    generation_date = date_match.group(1)
    
    # Process each article section
    summaries = []
    for i, section in enumerate(article_sections):
        # Clean up the section
        section = section.strip()
        if not section:
            continue
        
        # Extract title (first line is the title)
        title = section.split('\n')[0].strip()
        
        # Extract metadata including article ID
        metadata = {}
        metadata_matches = re.findall(r'\*\*(.*?):\*\* (.*?)(?:\n|$)', section, re.MULTILINE)
        for key, value in metadata_matches:
            metadata[key.lower()] = value.strip()
        
        # Extract summary
        summary_match = re.search(r'### Summary:\n\n(.*?)(?:\n\n###|\n\n---|\Z)', section, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else "No summary available"
        
        # Create summary object with source type if possible
        article_id = metadata.get('id', f"unknown_id_{i}")
        
        # Determine source type from metadata or source field
        source = metadata.get('source', 'Unknown')
        source_type = None
        
        # Try to determine source_type from source
        if source.lower() == 'the hacker news':
            source_type = 'hackernews'
        elif source.lower() == 'cyber news':
            source_type = 'cybernews'
        else:
            # Try to infer from metadata or default to unknown
            source_type = source.lower().replace(' ', '')
        
        summary_obj = {
            "article_id": article_id,
            "title": title,
            "summary": summary,
            "source": source,
            "source_type": source_type,
            "date": metadata.get('date', 'Unknown'),
            "generated_at": generation_date
        }
        
        summaries.append(summary_obj)
    
    print(f"Extracted {len(summaries)} article summaries")
    return summaries

def parse_tips_markdown(file_path: str, *source_collections: str) -> List[Dict[str, Any]]:
    """
    Parse the CISO tips markdown file and extract articles with tips.
    Link them to original articles by ID.
    
    Args:
        file_path: Path to the markdown file
        *source_collections: One or more source collections to look up articles from
    """
    print(f"Reading tips markdown file: {file_path}")
    
    # Read markdown file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into individual articles
    article_sections = re.split(r'\n## \d+\.', content)
    
    # First section contains header information
    header = article_sections[0]
    article_sections = article_sections[1:]
    
    # Extract generation date from header
    date_match = re.search(r'Generated on: (\d{4}-\d{2}-\d{2})', header)
    if not date_match:
        raise ValueError("Could not find generation date in markdown file")
    generation_date = date_match.group(1)
    
    # Process each article section
    tips_list = []
    for i, section in enumerate(article_sections):
        # Clean up the section
        section = section.strip()
        if not section:
            continue
        
        # Extract title (first line is the title)
        title = section.split('\n')[0].strip()
        
        # Extract metadata including article ID
        metadata = {}
        metadata_matches = re.findall(r'\*\*(.*?):\*\* (.*?)(?:\n|$)', section, re.MULTILINE)
        for key, value in metadata_matches:
            metadata[key.lower()] = value.strip()
        
        # Extract summary of security issue
        summary_match = re.search(r'### Key Security Issue\n\n(.*?)(?:\n\n###|\Z)', section, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""
        
        # Extract DO's
        dos_match = re.search(r"### DO's\n\n(.*?)(?:\n\n###|\Z)", section, re.DOTALL)
        dos_text = dos_match.group(1).strip() if dos_match else ""
        dos = [item.strip().lstrip('✅ ').strip() for item in dos_text.split('\n') if item.strip()]
        
        # Extract DON'Ts
        donts_match = re.search(r"### DON'Ts\n\n(.*?)(?:\n\n---|\Z)", section, re.DOTALL)
        donts_text = donts_match.group(1).strip() if donts_match else ""
        donts = [item.strip().lstrip('❌ ').strip() for item in donts_text.split('\n') if item.strip()]
        
        # Determine source type from metadata or source field
        source = metadata.get('source', 'Unknown')
        source_type = None
        
        # Try to determine source_type from source
        if source.lower() == 'the hacker news':
            source_type = 'hackernews'
        elif source.lower() == 'cyber news':
            source_type = 'cybernews'
        else:
            # Try to infer from metadata or default to unknown
            source_type = source.lower().replace(' ', '')
        
        # Create tips object
        article_id = metadata.get('id', f"unknown_id_{i}")
        tips_obj = {
            "article_id": article_id,
            "title": title,
            "tips": {
                "summary": summary,
                "dos": dos,
                "donts": donts
            },
            "source": source,
            "source_type": source_type,
            "date": metadata.get('date', 'Unknown'),
            "generated_at": generation_date
        }
        
        tips_list.append(tips_obj)
    
    print(f"Extracted {len(tips_list)} article tips")
    return tips_list

def store_in_firestore(collection_name: str, documents: List[Dict[str, Any]]) -> int:
    """
    Store documents in Firebase Firestore collection.
    Returns the number of documents stored.
    """
    try:
        # Import Firebase helper functions
        from firebase_helper import insert_one
        
        stored_count = 0
        for doc in documents:
            # Create a document with the article ID
            article_id = doc.get("article_id")
            if not article_id:
                print(f"Warning: Document missing article_id: {doc.get('title', 'Unknown title')}")
                continue
            
            # Set document ID
            doc["_id"] = article_id
            
            # Store the document
            try:
                result = insert_one(collection_name, doc)
                if result and "inserted_id" in result:
                    stored_count += 1
            except Exception as e:
                print(f"Error storing document for article {article_id}: {str(e)}")
        
        return stored_count
    
    except Exception as e:
        print(f"Error in store_in_firestore: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """Main function for manual testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Store tips and summaries in Firebase Firestore")
    parser.add_argument("--tips", type=str, help="Path to tips markdown file")
    parser.add_argument("--summaries", type=str, help="Path to summaries markdown file")
    parser.add_argument("--tips-collection", type=str, default="tips", 
                        help="Firestore collection for storing tips")
    parser.add_argument("--summaries-collection", type=str, default="summaries", 
                        help="Firestore collection for storing summaries")
    parser.add_argument("--news-collection", type=str, default="news", 
                        help="Firestore collection for unified news articles")
    
    args = parser.parse_args()
    
    # Import Firebase helper module
    try:
        from firebase_helper import count_documents
    except ImportError:
        print("Error importing firebase_helper.py. Make sure it's in the current directory.")
        return
    
    # Use the unified news collection only
    news_collection = args.news_collection
    source_collections = [news_collection]
    
    # Verify the news collection exists and has articles
    try:
        news_count = count_documents(news_collection)
        if news_count > 0:
            print(f"Using unified news collection with {news_count} articles")
        else:
            print(f"Warning: News collection exists but is empty. Make sure to scrape articles first.")
    except Exception as e:
        print(f"Error checking news collection: {str(e)}")
        print("Make sure the Firebase connection is properly configured.")
        return
    
    if args.tips:
        tips = parse_tips_markdown(
            args.tips, 
            news_collection
        )
        stored_count = store_in_firestore(args.tips_collection, tips)
        print(f"Stored {stored_count} tips in collection '{args.tips_collection}'")
    
    if args.summaries:
        summaries = parse_summaries_markdown(
            args.summaries, 
            news_collection
        )
        stored_count = store_in_firestore(args.summaries_collection, summaries)
        print(f"Stored {stored_count} summaries in collection '{args.summaries_collection}'")
    
    if not args.tips and not args.summaries:
        print("No input files specified. Use --tips or --summaries to provide input files.")
        parser.print_help()

if __name__ == "__main__":
    main() 