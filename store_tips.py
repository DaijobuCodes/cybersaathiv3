"""
Script to store CISO tips in Firebase Firestore with date-wise organization.
All tips are stored in a dedicated 'tips' collection, organized by date.
"""

import os
import re
import argparse
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_firebase(service_account_path=None):
    """Establish connection to Firebase Firestore"""
    try:
        # Import Firebase helper module
        from firebase_helper import initialize_firebase as init_firebase
        
        # Initialize Firebase
        firebase = init_firebase(service_account_path)
        if firebase:
            print("Successfully connected to Firebase Firestore")
            return firebase
        else:
            raise Exception("Failed to initialize Firebase")
    except Exception as e:
        print(f"Error connecting to Firebase Firestore: {str(e)}")
        raise

def parse_tips_markdown(file_path: str) -> List[Dict[str, Any]]:
    """Parse the tips markdown file and extract article data"""
    print(f"Reading tips markdown file: {file_path}")
    
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
    
    # Process each article
    articles = []
    for i, section in enumerate(article_sections):
        # Clean up the section
        section = section.strip()
        if not section:
            continue
        
        # Extract title (first line is the title)
        title = section.split('\n')[0].strip()
        
        # Extract metadata
        metadata = {}
        metadata_matches = re.findall(r'\*\*(.*?):\*\* (.*?)$', section, re.MULTILINE)
        for key, value in metadata_matches:
            metadata[key.lower()] = value.strip()
        
        # Extract summary and tips
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
        
        # Create article object
        article = {
            'index': i + 1,
            'title': title,
            'summary': summary,
            'dos': dos,
            'donts': donts,
            'generation_date': generation_date,
            'metadata': metadata
        }
        
        articles.append(article)
    
    print(f"Extracted {len(articles)} article tips")
    return articles

def store_tips_in_firestore(articles: List[Dict[str, Any]], collection_prefix: str = "tips"):
    """Store article tips in Firestore with date-wise organization"""
    # Import Firebase helper module functions
    from firebase_helper import get_collection, delete_many, insert_one
    
    # Group articles by date
    articles_by_date = {}
    for article in articles:
        # Try to get the article date from metadata
        article_date = None
        if 'date' in article['metadata']:
            # Parse the date from the metadata - format may be like "20 March 2025"
            try:
                date_str = article['metadata']['date']
                # Try to parse various date formats
                date_formats = [
                    "%d %B %Y",  # 20 March 2025
                    "%B %d, %Y", # March 20, 2025
                    "%Y-%m-%d",  # 2025-03-20
                    "%d/%m/%Y",  # 20/03/2025
                    "%m/%d/%Y"   # 03/20/2025
                ]
                
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        article_date = parsed_date.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"Warning: Could not parse date '{date_str}' for article '{article['title']}': {str(e)}")
        
        # If we couldn't parse the article date, use generation date as fallback
        if not article_date:
            article_date = article['generation_date']
            print(f"Using generation date for article '{article['title']}' as fallback")
        
        # Add to appropriate date group
        if article_date not in articles_by_date:
            articles_by_date[article_date] = []
        articles_by_date[article_date].append(article)
    
    # Store articles in date-wise collections
    for date, date_articles in articles_by_date.items():
        collection_name = f"{collection_prefix}_{date.replace('-', '_')}"
        
        # Clear any existing documents in this collection to avoid duplicates
        try:
            result = delete_many(collection_name)
            deleted_count = result.get("deleted_count", 0)
            if deleted_count > 0:
                print(f"Cleared {deleted_count} existing documents from collection '{collection_name}'")
        except Exception as e:
            print(f"Warning: Could not clear existing documents from '{collection_name}': {str(e)}")
        
        # Prepare documents for insertion
        inserted_count = 0
        for article in date_articles:
            # Retrieve article ID from metadata or use default
            article_id = article['metadata'].get('id', f"article_{article['index']}")
            
            # Create a document with the article data
            doc = {
                '_id': article_id,  # Use as document ID in Firestore
                'title': article['title'],
                'summary': article['summary'],
                'dos': article['dos'],
                'donts': article['donts'],
                'source': article['metadata'].get('source', 'Unknown'),
                'date': article['metadata'].get('date', 'Unknown'),
                'tags': article['metadata'].get('tags', 'None'),
                'index': article['index'],
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Insert document into the collection
            try:
                result = insert_one(collection_name, doc)
                if result and 'inserted_id' in result:
                    inserted_count += 1
            except Exception as e:
                print(f"Error inserting document '{article_id}': {str(e)}")
        
        print(f"Stored {inserted_count} tips in collection '{collection_name}'")

def main():
    """Main function to run the storage process"""
    parser = argparse.ArgumentParser(description="Store CISO tips in Firebase Firestore with date-wise collections")
    parser.add_argument("--input", type=str, required=True,
                        help="Input markdown file containing article tips")
    parser.add_argument("--firebase-credentials", type=str, 
                        default=os.getenv("FIREBASE_SERVICE_ACCOUNT"),
                        help="Firebase service account credentials file path")
    parser.add_argument("--collection-prefix", type=str, default="tips",
                        help="Firestore collection prefix (default: tips)")
    
    args = parser.parse_args()
    
    try:
        # Initialize Firebase
        initialize_firebase(args.firebase_credentials)
        
        # Parse the tips markdown file
        articles = parse_tips_markdown(args.input)
        
        # Store articles in Firestore
        store_tips_in_firestore(articles, args.collection_prefix)
        
        print("\nSuccessfully completed storing CISO tips in Firebase Firestore!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 