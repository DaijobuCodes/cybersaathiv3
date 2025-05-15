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
You are acting as a Chief Information Security Officer (CISO) providing cybersecurity advice based on recent threats.
Based on the following article, create a list of practical "DO's" and "DON'Ts" for users to follow.
Focus on specific, actionable advice directly related to the article's topic and threat vector.
Your tips must be highly specific to the exact cybersecurity issue described in the article.

Article Title: {article['title']}
Article Content:
{article['content']}

Your response should be structured as follows:
1. A specific summary of the key security issue in this exact article (2-3 sentences)
2. A list of 4-5 "DO's" - specific actions people should take to protect from THIS SPECIFIC threat
3. A list of 4-5 "DON'Ts" - specific actions people should avoid related to THIS SPECIFIC threat

Your response must be in the following JSON format:
{{
  "summary": "Brief summary here",
  "dos": ["Do this", "Do that", ...],
  "donts": ["Don't do this", "Don't do that", ...]
}}

IMPORTANT: Each "DO" and "DON'T" must be specific to the exact security threat discussed in the article.
DO NOT provide generic cybersecurity advice. Make all tips directly actionable for the specific issue.
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
        # Process the successful response as before
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
                except Exception as e:
                    # Fallback if JSON parsing completely fails
                    tips_json = {"summary": "Error parsing JSON", "dos": [], "donts": []} 
                
                # Process as before
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
                "source_type": article['metadata'].get('source', 'Unknown').lower().replace(' ', ''),
                "tips": tips_json,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            # Process exceptions as before
            print(f"Error parsing Ollama response for article '{article['title']}': {str(e)}")
            print(f"Raw response: {response_text}")
            
            # Attempt to salvage what we can or create a better placeholder
            try:
                # Existing fallback code...
                # But improved to be more specific to the article
                summary = "Error parsing complete response. See raw response for details."
                
                # Extract potential security issues from article content
                content = article['content']
                title = article['title']
                
                # Look for cybersecurity terms in content
                security_terms = {
                    "vulnerability": ["patch systems", "update software", "check for CVEs", "don't ignore security patches"],
                    "malware": ["use antivirus", "scan downloaded files", "avoid suspicious attachments", "don't click unknown links"],
                    "phishing": ["verify sender emails", "check URLs before clicking", "be wary of urgent requests", "don't share credentials"],
                    "ransomware": ["backup important data", "use offline backups", "isolate infected systems", "don't pay the ransom"],
                    "password": ["use strong passwords", "enable 2FA", "use a password manager", "don't reuse passwords"],
                    "data breach": ["monitor accounts", "change affected passwords", "check for suspicious activity", "don't ignore breach notifications"],
                    "exploit": ["apply security patches", "disable vulnerable features", "use protective measures", "don't use outdated software"]
                }
                
                found_terms = []
                related_dos = []
                related_donts = []
                
                # Find security terms in the article
                for term, advice in security_terms.items():
                    if term.lower() in content.lower() or term.lower() in title.lower():
                        found_terms.append(term)
                        # Each term has 4 pieces of advice, first 2 are dos, last 2 are don'ts
                        related_dos.extend(advice[:2])
                        related_donts.extend(advice[2:])
                
                # If no specific terms found, look for general security-related content
                if not found_terms:
                    # Try to extract a specific issue from title or first paragraph
                    first_paragraph = content.split('\n\n')[0] if '\n\n' in content else content[:300]
                    summary = f"This article discusses security issues related to {title}. Users should be aware of potential cybersecurity risks mentioned in the article."
                    
                    # Use generic but relevant advice
                    related_dos = [
                        "Keep all your systems and software up to date with security patches",
                        "Use strong, unique passwords for your accounts",
                        "Enable two-factor authentication when available",
                        "Be cautious with email attachments and links from unknown sources"
                    ]
                    related_donts = [
                        "Don't share sensitive information on unsecured websites",
                        "Don't use public Wi-Fi for sensitive transactions without a VPN",
                        "Don't reuse passwords across multiple sites",
                        "Don't ignore security warnings from your devices"
                    ]
                else:
                    # Create a more specific summary based on found terms
                    term_list = ", ".join(found_terms)
                    summary = f"This article highlights security issues related to {term_list}. Users should follow specific recommendations to protect themselves from these threats."
                
                # Create the final fallback json
                tips_json = {
                    "summary": summary,
                    "dos": related_dos,
                    "donts": related_donts
                }
                
                return {
                    "article_id": article['metadata'].get('id', f"article_{article['index']}"),
                    "title": article['title'],
                    "source": article['metadata'].get('source', 'Unknown'),
                    "date": article['metadata'].get('date', 'Unknown'),
                    "tags": article['metadata'].get('tags', 'None'),
                    "source_type": article['metadata'].get('source', 'Unknown').lower().replace(' ', ''),
                    "tips": tips_json,
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "parsing_error": str(e),
                    "raw_response": response_text
                }
            except:
                # Extreme fallback with article-specific modifications
                title_words = article['title'].split()
                security_topic = "cybersecurity issue"
                for word in title_words:
                    if word.lower() in ["vulnerability", "exploit", "malware", "phishing", "ransomware", "breach", "attack"]:
                        security_topic = word.lower()
                        break
                
                return {
                    "article_id": article['metadata'].get('id', f"article_{article['index']}"),
                    "title": article['title'],
                    "source": article['metadata'].get('source', 'Unknown'),
                    "date": article['metadata'].get('date', 'Unknown'),
                    "tags": article['metadata'].get('tags', 'None'),
                    "source_type": article['metadata'].get('source', 'Unknown').lower().replace(' ', ''),
                    "tips": {
                        "summary": f"The article discusses a {security_topic} that users should be aware of. Following specific security practices can help mitigate risks associated with this threat.",
                        "dos": [
                            f"Keep your systems updated with the latest security patches",
                            f"Enable additional security features like firewalls and antivirus",
                            f"Use strong, unique passwords for each of your accounts",
                            f"Backup your important data regularly to protect against data loss"
                        ],
                        "donts": [
                            f"Don't click on suspicious links or download attachments from unknown sources",
                            f"Don't share sensitive information on unsecured platforms",
                            f"Don't ignore security warnings from your applications or operating system",
                            f"Don't use the same password across multiple sites or services"
                        ]
                    },
                    "error": f"Failed to parse response: {str(e)}",
                    "raw_response": response_text
                }
    else:
        # If all model variants and retries failed
        error_str = "\n".join(error_messages)
        print(f"All model attempts failed: {error_str}")
        
        # Create article-specific fallback
        title_words = article['title'].split()
        security_topic = "cybersecurity issue"
        for word in title_words:
            if word.lower() in ["vulnerability", "exploit", "malware", "phishing", "ransomware", "breach", "attack"]:
                security_topic = word.lower()
                break
        
        return {
            "article_id": article['metadata'].get('id', f"article_{article['index']}"),
            "title": article['title'],
            "source": article['metadata'].get('source', 'Unknown'),
            "source_type": article['metadata'].get('source', 'Unknown').lower().replace(' ', ''),
            "tips": {
                "summary": f"The article discusses a {security_topic} that requires attention. While automated tips generation failed, following good security practices is recommended.",
                "dos": [
                    f"Keep all software updated with security patches",
                    f"Use strong authentication methods",
                    f"Backup important data regularly",
                    f"Stay informed about {security_topic} threats"
                ],
                "donts": [
                    f"Don't ignore security warnings related to this {security_topic}",
                    f"Don't click suspicious links or download unknown attachments",
                    f"Don't share sensitive information without verification",
                    f"Don't use outdated software vulnerable to known exploits"
                ]
            },
            "error": f"Ollama API error: Failed to find working model. Errors: {error_str}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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