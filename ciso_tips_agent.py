#!/usr/bin/env python3
"""
CISO Tips Generation Agent

This script extracts context from cybersecurity articles and uses llama3.2:1b
model to generate actionable security tips for CISOs and non-technical users.
The output is formatted as 'Do's and Don'ts' for better readability.
"""

import argparse
import re
import json
import requests
import os
from typing import Dict, List, Any
from datetime import datetime
import time

def extract_articles_from_markdown(file_path: str) -> List[Dict[str, Any]]:
    """Extract full article content from markdown file"""
    print(f"Reading markdown file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match individual articles in markdown
    article_pattern = r'## (\d+)\. (.+?)(?=\n## \d+\.|\Z)'
    articles_raw = re.findall(article_pattern, content, re.DOTALL)
    
    articles = []
    for idx, article_content in articles_raw:
        # Extract title and content
        lines = article_content.strip().split('\n')
        title = lines[0].strip()
        
        # Extract metadata
        metadata = {}
        metadata_section = ""
        content_section = ""
        
        metadata_started = False
        content_started = False
        
        for line in lines[1:]:
            if line.startswith('**') and ':**' in line:
                metadata_started = True
                metadata_section += line + "\n"
            elif line.startswith('### Content') or line.startswith('### Summary'):
                metadata_started = False
                content_started = True
            elif metadata_started:
                metadata_section += line + "\n"
            elif content_started:
                content_section += line + "\n"
        
        # Parse metadata
        metadata_matches = re.findall(r'\*\*(.*?):\*\* (.*?)$', metadata_section, re.MULTILINE)
        for key, value in metadata_matches:
            metadata[key.lower()] = value.strip()
        
        # Create article object
        article = {
            'index': int(idx),
            'title': title,
            'content': content_section.strip(),
            'metadata': metadata
        }
        
        articles.append(article)
    
    print(f"Extracted {len(articles)} articles")
    return articles

def generate_tips_with_ollama(article: Dict[str, Any], max_retries=3, retry_delay=2):
    """Generate CISO tips from an article using Ollama's llama3.2:1b model"""
    # Construct prompt for the Ollama model
    prompt = f"""
You are acting as a Chief Information Security Officer (CISO) providing cybersecurity advice to non-technical users.
Based on the following article, create a list of practical "DO's" and "DON'Ts" for ordinary people to follow.
Use simple, non-technical language that anyone can understand.

Article Title: {article['title']}
Article Content:
{article['content']}

Your response should be structured as follows:
1. A very brief summary of the key security issue (2-3 sentences maximum)
2. A list of 3-5 "DO's" - specific actions people should take
3. A list of 3-5 "DON'Ts" - specific actions people should avoid

Your response should be in the following JSON format:
{{
  "summary": "Brief summary here",
  "dos": ["Do this", "Do that", ...],
  "donts": ["Don't do this", "Don't do that", ...]
}}

Remember: Keep everything simple, practical, and actionable for non-technical users.
Make sure to follow proper JSON syntax with quotes around all strings.
"""

    # Only use the llama3.2:1b model as specified
    model_variants = [
        "llama3.2:1b"  # Only use this model, no alternatives
    ]
    
    # Try each model variant until one works
    response = None
    error_messages = []
    
    for model_name in model_variants:
        # Call Ollama API
        for attempt in range(max_retries):
            try:
                print(f"Trying model: {model_name}")
                response = requests.post('http://localhost:11434/api/generate', 
                                      json={
                                          "model": model_name,
                                          "prompt": prompt,
                                          "stream": False,
                                          "temperature": 0.1,  # Low temperature for more factual responses
                                          "max_tokens": 1024
                                      })
                
                if response.status_code == 200:
                    # We found a working model, break out of the retry loop
                    break
                else:
                    error_messages.append(f"Model {model_name} error: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
            except Exception as e:
                error_messages.append(f"Model {model_name} exception: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        # If we got a successful response with this model, break out of model variants loop
        if response and response.status_code == 200:
            print(f"Successfully used model: {model_name}")
            break
    
    # If we have a successful response, process it
    if response and response.status_code == 200:
        # Extract the response
        result = response.json()
        response_text = result.get('response', '')
        
        # Try to extract JSON from the response using multiple methods
        try:
            # Try to find a properly formatted JSON object in the text
            # First, look for the most common pattern with the expected structure
            json_match = re.search(r'({[\s\S]*"summary"[\s\S]*"dos"[\s\S]*"donts"[\s\S]*})', response_text)
            
            if json_match:
                json_str = json_match.group(1)
                # Try to fix common JSON formatting issues
                try:
                    # Fix missing quotes around property values
                    fixed_json = re.sub(r':\s*([^"{}\[\],\s][^{}\[\],\s]*),', r': "\1",', json_str)
                    fixed_json = re.sub(r':\s*([^"{}\[\],\s][^{}\[\],\s]*)$', r': "\1"', fixed_json, flags=re.MULTILINE)
                    fixed_json = re.sub(r':\s*([^"{}\[\],\s][^{}\[\],\s]*)\s*}', r': "\1"}', fixed_json)
                    
                    # Try to parse the fixed JSON
                    try:
                        tips_json = json.loads(fixed_json)
                    except json.JSONDecodeError:
                        # If that failed, try a more aggressive fix for common errors
                        # - Fix missing quotes around string values in lists
                        list_pattern = r'\[(.*?)\]'
                        for list_match in re.finditer(list_pattern, fixed_json):
                            list_str = list_match.group(1)
                            items = [item.strip() for item in list_str.split(',')]
                            quoted_items = []
                            for item in items:
                                if item and not (item.startswith('"') and item.endswith('"')):
                                    quoted_items.append(f'"{item}"')
                                else:
                                    quoted_items.append(item)
                            fixed_list = f'[{", ".join(quoted_items)}]'
                            fixed_json = fixed_json.replace(list_match.group(0), fixed_list)
                        
                        # Try parsing again
                        tips_json = json.loads(fixed_json)
                except:
                    # If fixing didn't work, manually extract the data
                    summary_match = re.search(r'"summary"\s*:\s*"?(.*?)"?,\s*"dos"', json_str)
                    summary = summary_match.group(1) if summary_match else "No summary available."
                    
                    dos_match = re.search(r'"dos"\s*:\s*\[(.*?)\],', json_str, re.DOTALL)
                    dos_str = dos_match.group(1) if dos_match else ""
                    dos = []
                    for item in re.findall(r'"([^"]*)"', dos_str):
                        dos.append(item)
                    if not dos:
                        dos = ["No specific dos provided."]
                    
                    donts_match = re.search(r'"donts"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
                    donts_str = donts_match.group(1) if donts_match else ""
                    donts = []
                    for item in re.findall(r'"([^"]*)"', donts_str):
                        donts.append(item)
                    if not donts:
                        donts = ["No specific don'ts provided."]
                    
                    tips_json = {
                        "summary": summary,
                        "dos": dos,
                        "donts": donts
                    }
            else:
                # Fall back to extracting the info using regex patterns
                summary_match = re.search(r'summary["\s:]+([^"]+)', response_text, re.IGNORECASE)
                dos_items = re.findall(r'(?:Do|DO|DO\'s)(?:\s*\d+\.?\s*|\s*[-•*]\s*|\s*:?\s+)(.*?)(?=\n|$)', response_text)
                donts_items = re.findall(r'(?:Don\'t|Don\'t|DON\'T|Don\'t|DON\'T|DONTs)(?:\s*\d+\.?\s*|\s*[-•*]\s*|\s*:?\s+)(.*?)(?=\n|$)', response_text)
                
                tips_json = {
                    "summary": summary_match.group(1).strip() if summary_match else "No summary available.",
                    "dos": [item.strip() for item in dos_items if item.strip()] if dos_items else ["No specific dos provided."],
                    "donts": [item.strip() for item in donts_items if item.strip()] if donts_items else ["No specific don'ts provided."]
                }
            
            # Validate the structure of the JSON to ensure it has the required fields
            if "summary" not in tips_json:
                tips_json["summary"] = "No summary available."
            if "dos" not in tips_json or not tips_json["dos"]:
                tips_json["dos"] = ["No specific dos provided."]
            if "donts" not in tips_json or not tips_json["donts"]:
                tips_json["donts"] = ["No specific don'ts provided."]
            
            # Create the full response
            return {
                "article_id": article['metadata'].get('id', f"article_{article['index']}"),
                "title": article['title'],
                "source": article['metadata'].get('source', 'Unknown'),
                "date": article['metadata'].get('date', 'Unknown'),
                "tags": article['metadata'].get('tags', 'None'),
                "source_type": article['metadata'].get('source', 'Unknown').lower().replace(' ', ''),  # Add source_type
                "tips": tips_json,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Error parsing Ollama response for article '{article['title']}': {str(e)}")
            print(f"Raw response: {response_text}")
            
            # Create a best-effort result from the raw response
            # Extract key parts using simpler patterns
            try:
                summary = "Error parsing complete response. See raw response for details."
                dos = ["Keep your software updated", "Use strong passwords", "Be cautious with unknown links and attachments"]
                donts = ["Don't share sensitive information", "Don't use public Wi-Fi for sensitive transactions", "Don't ignore security warnings"]
                
                # Try to extract at least a summary from the text
                simple_summary = re.search(r'summary.*?[:"] *(.*?)(?=["\n]|dos)', response_text, re.IGNORECASE | re.DOTALL)
                if simple_summary:
                    summary = simple_summary.group(1).strip()
                
                tips_json = {
                    "summary": summary,
                    "dos": dos,
                    "donts": donts
                }
                
                return {
                    "article_id": article['metadata'].get('id', f"article_{article['index']}"),
                    "title": article['title'],
                    "source": article['metadata'].get('source', 'Unknown'),
                    "date": article['metadata'].get('date', 'Unknown'),
                    "tags": article['metadata'].get('tags', 'None'),
                    "source_type": article['metadata'].get('source', 'Unknown').lower().replace(' ', ''),  # Add source_type
                    "tips": tips_json,
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "parsing_error": str(e),
                    "raw_response": response_text
                }
            except:
                return {
                    "article_id": article['metadata'].get('id', f"article_{article['index']}"),
                    "title": article['title'],
                    "source": article['metadata'].get('source', 'Unknown'),
                    "date": article['metadata'].get('date', 'Unknown'),
                    "tags": article['metadata'].get('tags', 'None'),
                    "source_type": article['metadata'].get('source', 'Unknown').lower().replace(' ', ''),  # Add source_type
                    "error": f"Failed to parse response: {str(e)}",
                    "raw_response": response_text
                }
    else:
        # If all model variants and retries failed
        error_str = "\n".join(error_messages)
        print(f"All model attempts failed: {error_str}")
        return {
            "article_id": article['metadata'].get('id', f"article_{article['index']}"),
            "title": article['title'],
            "source": article['metadata'].get('source', 'Unknown'),
            "source_type": article['metadata'].get('source', 'Unknown').lower().replace(' ', ''),  # Add source_type
            "error": f"Ollama API error: Failed to find working model. Errors: {error_str}"
        }

def format_tips_as_markdown(tips_collection: List[Dict[str, Any]], output_file: str):
    """Format the tips as a markdown file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write("# CISO Security Tips for Non-Technical Users\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Number of articles: {len(tips_collection)}\n\n")
        
        # Write tips for each article
        for i, tips in enumerate(tips_collection):
            f.write(f"## {i+1}. {tips['title']}\n\n")
            
            # Write metadata
            f.write(f"**Source:** {tips.get('source', 'Unknown')}\n")
            f.write(f"**Date:** {tips.get('date', 'Unknown')}\n")
            if 'tags' in tips and tips['tags'] != 'None':
                f.write(f"**Tags:** {tips['tags']}\n")
            
            # Check if there was an error
            if 'error' in tips:
                f.write(f"\n### Error\n\n{tips['error']}\n\n")
                if 'raw_response' in tips:
                    f.write(f"Raw response: {tips['raw_response']}\n\n")
                continue
            
            # Write summary and tips
            if 'tips' in tips:
                # Summary
                if 'summary' in tips['tips']:
                    f.write(f"\n### Key Security Issue\n\n{tips['tips']['summary']}\n\n")
                
                # DO's
                if 'dos' in tips['tips'] and tips['tips']['dos']:
                    f.write("### DO's\n\n")
                    for do_item in tips['tips']['dos']:
                        f.write(f"✅ {do_item}\n\n")
                
                # DON'Ts
                if 'donts' in tips['tips'] and tips['tips']['donts']:
                    f.write("### DON'Ts\n\n")
                    for dont_item in tips['tips']['donts']:
                        f.write(f"❌ {dont_item}\n\n")
            
            # Add separator
            f.write("---\n\n")
    
    print(f"Tips saved to {output_file}")

def main():
    """Main function to process articles and generate CISO tips"""
    parser = argparse.ArgumentParser(description="Generate CISO tips from article summaries using Ollama")
    parser.add_argument("--input", type=str, required=True, 
                        help="Input file containing article summaries")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file for CISO tips (default: auto-generated)")
    parser.add_argument("--model", type=str, default="llama3.2:1b",
                        help="Ollama model to use (default: llama3.2:1b)")
    
    args = parser.parse_args()
    
    try:
        # Extract articles from the markdown file
        articles = extract_articles_from_markdown(args.input)
        
        # Generate tips for each article
        print(f"Generating tips using Ollama model: {args.model}")
        tips_collection = []
        
        for i, article in enumerate(articles):
            print(f"Processing article {i+1}/{len(articles)}: {article['title']}")
            tips = generate_tips_with_ollama(article)
            tips_collection.append(tips)
        
        # Format and save tips as markdown
        format_tips_as_markdown(tips_collection, args.output)
        
        print(f"\nSuccessfully generated CISO tips for {len(articles)} articles!")
        print(f"Tips saved to: {args.output}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise

if __name__ == "__main__":
    main() 