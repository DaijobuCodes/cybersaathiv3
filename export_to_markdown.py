#!/usr/bin/env python3
"""
Export Firebase Firestore Articles to Markdown File

This script exports all articles from the Firestore database to a well-formatted
Markdown file that can be used to feed an AI agent.
"""

import os
import sys
from datetime import datetime
import argparse
from dotenv import load_dotenv

# Import the encryption utilities from Scraper.py
from Scraper import generate_encryption_key, decrypt_text, setup_firestore

# Load environment variables
load_dotenv()

def format_article_to_markdown(article, index):
    """Format a single article as markdown"""
    # Get all article fields with fallbacks for missing data
    title = article.get('title', 'No Title')
    date = article.get('date', 'No Date')
    source = article.get('source', 'Unknown Source')
    url = article.get('url', 'No URL')
    tags = article.get('tags', 'No Tags')
    description = article.get('description', 'No content available')
    article_id = article.get('_id', 'No ID')
    
    # Format as markdown
    markdown = f"""
## {index}. {title}

**Source:** {source}  
**Date:** {date}  
**URL:** {url}  
**ID:** {article_id}  
**Tags:** {tags}

### Content:

{description}

---
"""
    return markdown

def export_to_markdown(collections=None, output_file=None, limit=None, include_encrypted=False, decrypt=False):
    """Export articles from Firestore to a markdown file"""
    try:
        # Import Firebase helper functions
        from firebase_helper import find, close
        
        # Connect to Firebase using the setup function from Scraper.py
        firebase = setup_firestore()
        if firebase is None:
            print("Failed to connect to Firebase Firestore. Check your credentials.")
            return False
        
        # Use only the unified news collection
        news_collection = os.getenv("FIREBASE_COLLECTION_NEWS", "news")
        collections = [news_collection]
        
        # Generate encryption key if needed
        key = None
        if decrypt:
            key = generate_encryption_key(None)
        
        # Set default output file if none provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"cybersecurity_articles_{timestamp}.md"
        
        # Start building the markdown content
        markdown_content = f"# Cybersecurity News Articles\n\n"
        markdown_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Initialize article counter
        article_count = 0
        
        # Process the news collection
        collection_name = news_collection
        # Get articles with optional limit
        query_limit = limit if limit else None
        articles = find(collection_name, limit=query_limit)
        
        if articles:
            # Group articles by source type
            articles_by_source = {}
            for article in articles:
                source_type = article.get("source_type", "unknown")
                if source_type not in articles_by_source:
                    articles_by_source[source_type] = []
                articles_by_source[source_type].append(article)
            
            # Process each source type as a separate section
            for source_type, source_articles in articles_by_source.items():
                markdown_content += f"## Source: {source_type}\n\n"
                
                # Process each article
                for article in source_articles:
                    article_count += 1
                    article_md = format_article_to_markdown(article, article_count)
                    
                    # Add decrypted title if requested
                    if decrypt and 'encrypted_title' in article:
                        try:
                            decrypted_title = decrypt_text(article['encrypted_title'], key)
                            article_md += f"**Decrypted Title:** {decrypted_title}\n\n"
                        except Exception as e:
                            article_md += f"**Error decrypting title:** {str(e)}\n\n"
                    
                    # Add encrypted title if requested
                    if include_encrypted and 'encrypted_title' in article:
                        article_md += f"**Encrypted Title:** {article['encrypted_title']}\n\n"
                    
                    markdown_content += article_md
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Exported {article_count} articles to {output_file}")
        
        # Close Firebase connection
        close()
        
        return True
    
    except Exception as e:
        print(f"Error exporting to markdown: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(description="Export Firebase Firestore articles to a Markdown file")
    parser.add_argument("--output", type=str, default=None,
                        help="Output markdown file name (default: cybersecurity_articles_TIMESTAMP.md)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum number of articles to export (default: all)")
    parser.add_argument("--include-encrypted", action="store_true",
                        help="Include encrypted titles in the output")
    parser.add_argument("--decrypt", action="store_true",
                        help="Include decrypted titles in the output")
    
    args = parser.parse_args()
    
    # Export to markdown using only the news collection
    export_to_markdown(
        output_file=args.output,
        limit=args.limit,
        include_encrypted=args.include_encrypted,
        decrypt=args.decrypt
    )

if __name__ == "__main__":
    main() 