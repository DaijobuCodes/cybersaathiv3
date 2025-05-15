#!/usr/bin/env python3
"""
CyberSaathi Web Interface - Firebase Firestore Version

This script provides a web interface to view articles, summaries, and tips
stored in Firebase Firestore.
"""

import os
import sys
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Flask application
app = Flask(__name__)

# Get Firebase collection names
firebase_collection_news = os.getenv("FIREBASE_COLLECTION_NEWS", "news")
firebase_collection_tips = os.getenv("FIREBASE_COLLECTION_TIPS", "tips")
firebase_collection_summaries = os.getenv("FIREBASE_COLLECTION_SUMMARIES", "summaries")

# Connect to Firebase Firestore
def get_db_connection():
    try:
        # Import Firebase helper module
        from firebase_helper import initialize_firebase
        
        # Initialize Firebase
        firebase = initialize_firebase()
        return firebase
    except Exception as e:
        print(f"Error connecting to Firebase Firestore: {str(e)}")
        return None

@app.route('/')
def index():
    """Home page with tabs for articles, summaries, and tips"""
    # Import Firebase helper functions
    try:
        from firebase_helper import find, find_one, count_documents, insert_one, close
    except ImportError as e:
        return render_template('error.html', error=f"Could not import Firebase helper functions: {str(e)}")
    
    # Initialize Firebase
    firebase = get_db_connection()
    if firebase is None:
        return render_template('error.html', error="Could not connect to Firebase Firestore")
    
    try:
        # Get articles from the unified news collection
        all_articles = find(firebase_collection_news, sort=[("scraped_at", -1)])
        
        # Get summaries and count them
        try:
            summaries = find(firebase_collection_summaries)
            summaries_count = len(summaries)
        except Exception as e:
            print(f"Error getting summaries: {str(e)}")
            summaries = []
            summaries_count = 0
        
        # Get tips and count them
        try:
            tips = find(firebase_collection_tips)
            tips_count = len(tips)
        except Exception as e:
            print(f"Error getting tips: {str(e)}")
            tips = []
            tips_count = 0
        
        # Check for imbalance in article counts and create missing summaries/tips
        articles_count = len(all_articles)
        if articles_count > summaries_count or articles_count > tips_count:
            print(f"Imbalance detected: {articles_count} articles, {summaries_count} summaries, {tips_count} tips")
            
            # Get article IDs from the news collection
            article_ids = {article.get("_id"): article for article in all_articles if "_id" in article}
            
            # Check each article for summaries and tips
            summaries_added = 0
            tips_added = 0
            
            # Try importing the summarization and tips functions
            try_model_generation = False
            try:
                # Try to import the summarization functions
                from article_summarizer import summarize_with_ollama
                from ciso_tips_agent import generate_tips_with_ollama
                try_model_generation = True
                print("Successfully imported model functions for live generation")
            except ImportError as e:
                print(f"Could not import model functions for live generation: {e}")
                try_model_generation = False
            
            for article_id, article in article_ids.items():
                # Check for summary
                summary = find_one(firebase_collection_summaries, {"article_id": article_id})
                if not summary:
                    # Try to generate a real summary if possible
                    generated_summary = None
                    if try_model_generation and 'description' in article and article['description']:
                        try:
                            # Format article for summarization
                            summarization_article = {
                                'id': article_id,
                                'title': article.get('title', 'Unknown Title'),
                                'content': article.get('description', ''),
                                'source': article.get('source', 'Unknown'),
                                'date': article.get('date', 'Unknown'),
                                'tags': article.get('tags', 'Unknown')
                            }
                            # Try to summarize
                            result = summarize_with_ollama(summarization_article)
                            if result and result["status"] == "success":
                                generated_summary = result["summary"]
                                print(f"Successfully generated real summary for article: {article['title']}")
                        except Exception as e:
                            print(f"Error generating real summary: {str(e)}")
                            generated_summary = None
                    
                    # Create summary - either generated or a better placeholder
                    if generated_summary:
                        summary_text = generated_summary
                    else:
                        # Create a better placeholder based on article content if available
                        if 'description' in article and article['description']:
                            content = article['description']
                            # Get first 200 characters as a preview
                            preview = content[:200] + "..." if len(content) > 200 else content
                            summary_text = f"Placeholder summary based on content preview: {preview}"
                        else:
                            summary_text = "No summary available. This is a placeholder created to ensure all articles have summaries."
                    
                    # Create placeholder summary
                    placeholder_summary = {
                        "article_id": article_id,
                        "title": article.get('title', 'Unknown Title'),
                        "summary": summary_text,
                        "source": article.get('source', 'Unknown'),
                        "source_type": article.get('source_type', article.get('source', 'unknown').lower().replace(' ', '')),
                        "date": article.get('date', 'Unknown'),
                        "generated_at": datetime.now().strftime("%Y-%m-%d")
                    }
                    # Add _id field for Firestore document ID
                    placeholder_summary["_id"] = article_id
                    
                    # Store placeholder summary
                    insert_one(firebase_collection_summaries, placeholder_summary)
                    summaries_added += 1
                
                # Check for tips
                tip = find_one(firebase_collection_tips, {"article_id": article_id})
                if not tip:
                    # Try to generate real tips if possible
                    generated_tips = None
                    if try_model_generation and 'description' in article and article['description']:
                        try:
                            # Format article for tips generation
                            tips_article = {
                                'title': article.get('title', 'Unknown Title'),
                                'content': article.get('description', ''),
                                'metadata': {
                                    'id': article_id,
                                    'source': article.get('source', 'Unknown'),
                                    'date': article.get('date', 'Unknown'),
                                    'tags': article.get('tags', 'Unknown')
                                }
                            }
                            # Try to generate tips
                            result = generate_tips_with_ollama(tips_article)
                            if result and 'tips' in result and isinstance(result['tips'], dict):
                                generated_tips = result['tips']
                                print(f"Successfully generated real tips for article: {article['title']}")
                        except Exception as e:
                            print(f"Error generating real tips: {str(e)}")
                            generated_tips = None
                    
                    # Use generated tips or create a better placeholder based on the article
                    if generated_tips:
                        tips_content = generated_tips
                    else:
                        # Create context-specific placeholder based on article title and content
                        topic_keywords = []
                        if 'title' in article:
                            # Extract likely keywords from title (nouns and technical terms)
                            title_words = article['title'].split()
                            for word in title_words:
                                if word[0].isupper() or any(tech_term in word.lower() for tech_term in 
                                                        ['cve', 'exploit', 'vulnerability', 'attack', 'malware', 
                                                         'ransomware', 'phishing', 'hack', 'breach', 'security']):
                                    topic_keywords.append(word)
                        
                        summary_prefix = ""
                        if topic_keywords:
                            topic = ", ".join(topic_keywords[:3])  # Use up to 3 keywords
                            summary_prefix = f"For issues related to {topic}, "
                        
                        tips_content = {
                            "summary": f"{summary_prefix}Here are some general cybersecurity recommendations until specific tips can be generated.",
                            "dos": [
                                "Keep your software and operating systems updated with the latest security patches",
                                "Use strong, unique passwords for each of your accounts",
                                "Enable two-factor authentication wherever available",
                                "Be vigilant about suspicious emails, links, and attachments"
                            ],
                            "donts": [
                                "Don't share sensitive information on unsecured websites",
                                "Don't use public Wi-Fi for sensitive transactions without a VPN",
                                "Don't reuse passwords across multiple sites",
                                "Don't ignore security warnings from your operating system or applications"
                            ]
                        }
                    
                    # Create placeholder tips
                    placeholder_tips = {
                        "article_id": article_id,
                        "title": article.get('title', 'Unknown Title'),
                        "source": article.get('source', 'Unknown'),
                        "date": article.get('date', 'Unknown'),
                        "source_type": article.get('source_type', article.get('source', 'unknown').lower().replace(' ', '')),
                        "tips": tips_content,
                        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    # Add _id field for Firestore document ID
                    placeholder_tips["_id"] = article_id
                    
                    # Store placeholder tips
                    insert_one(firebase_collection_tips, placeholder_tips)
                    tips_added += 1
            
            # If we've added any summaries or tips, reload them
            if summaries_added > 0:
                print(f"Added {summaries_added} placeholder summaries")
                summaries = find(firebase_collection_summaries)
                summaries_count = len(summaries)
            
            if tips_added > 0:
                print(f"Added {tips_added} placeholder tips")
                tips = find(firebase_collection_tips)
                tips_count = len(tips)
                
            # Force count update
            summaries_count = len(summaries) if summaries else 0
            tips_count = len(tips) if tips else 0
        
        # Map summaries and tips to articles by article_id
        article_summaries = {}
        article_tips = {}
        
        # Process summaries - match by article_id and also try _id for compatibility
        for summary in summaries:
            if "article_id" in summary:
                article_id = summary["article_id"]
                article_summaries[article_id] = summary
            elif "_id" in summary and "_id" in summary:
                # For compatibility with older data format
                article_id = summary["_id"]
                article_summaries[article_id] = summary
                
        # Process tips - match by article_id and also try _id for compatibility
        for tip in tips:
            if "article_id" in tip:
                article_id = tip["article_id"]
                article_tips[article_id] = tip
            elif "_id" in tip and "_id" in tip:
                # For compatibility with older data format
                article_id = tip["_id"]
                article_tips[article_id] = tip
        
        # Group articles by source type
        hackernews_articles = []
        cybernews_articles = []
        
        # Process all articles
        for article in all_articles:
            article_id = article.get("_id")
            source_type = article.get("source_type", "unknown")
            
            # Add summary if available
            if article_id in article_summaries:
                article["summary"] = article_summaries[article_id].get("summary", "No summary available")
            else:
                article["summary"] = "No summary available"
                
            # Add tips if available
            if article_id in article_tips:
                if "tips" in article_tips[article_id] and isinstance(article_tips[article_id]["tips"], dict):
                    article["tips"] = article_tips[article_id]["tips"]
                else:
                    article["tips"] = {"dos": [], "donts": [], "summary": "No tips available"}
            else:
                article["tips"] = {"dos": [], "donts": [], "summary": "No tips available"}
                
            # Group articles by source type
            if source_type == "hackernews":
                # Ensure source name is set for hackernews articles
                if "source" not in article or not article["source"]:
                    article["source"] = "The Hacker News"
                hackernews_articles.append(article)
            elif source_type == "cybernews":
                # Ensure source name is set for cybernews articles
                if "source" not in article or not article["source"]:
                    article["source"] = "Cyber News"
                    cybernews_articles.append(article)
        
        # Get accurate counts
        hackernews_count = len(hackernews_articles)
        cybernews_count = len(cybernews_articles)
        
        # Close Firebase connection
        close()
        
        # Render template with data
        return render_template('index.html', 
                              articles=all_articles,
                              hackernews_count=hackernews_count,
                              cybernews_count=cybernews_count,
                              summaries_count=summaries_count,
                              tips_count=tips_count,
                              timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        # Close Firebase connection
        close()
        import traceback
        traceback.print_exc()
        return render_template('error.html', error=str(e))

@app.route('/article/<article_id>')
def article_detail(article_id):
    """Detailed view of a single article with summary and tips"""
    # Import Firebase helper functions
    try:
        from firebase_helper import find_one, insert_one, close
    except ImportError as e:
        return render_template('error.html', error=f"Could not import Firebase helper functions: {str(e)}")
    
    # Initialize Firebase
    firebase = get_db_connection()
    if firebase is None:
        return render_template('error.html', error="Could not connect to Firebase Firestore")
    
    try:
        # Get article from the unified news collection
        article = find_one(firebase_collection_news, {"_id": article_id})
        
        # If article not found
        if not article:
            # Close Firebase connection
            close()
            return render_template('error.html', error=f"Article with ID '{article_id}' not found")
        
        # Ensure source name is correctly set based on source_type
        source_type = article.get("source_type", "unknown")
        if "source" not in article or not article["source"]:
            if source_type == "hackernews":
                article["source"] = "The Hacker News"
            elif source_type == "cybernews":
                article["source"] = "Cyber News"
            else:
                article["source"] = "Unknown Source"
        
        # Try importing the summarization and tips functions for real-time generation
        try_model_generation = False
        try:
            # Try to import the summarization functions
            from article_summarizer import summarize_with_ollama
            from ciso_tips_agent import generate_tips_with_ollama
            try_model_generation = True
            print("Successfully imported model functions for live generation in article detail")
        except ImportError as e:
            print(f"Could not import model functions for live generation in article detail: {e}")
            try_model_generation = False
        
        # Get summary from summaries collection
        summary = find_one(firebase_collection_summaries, {"article_id": article_id})
        
        # Determine if we need to regenerate the summary (it's a placeholder or missing)
        needs_summary_regeneration = False
        if not summary:
            needs_summary_regeneration = True
        elif "summary" in summary and isinstance(summary["summary"], str):
            placeholder_indicators = [
                "No summary available", 
                "This is a placeholder", 
                "Placeholder summary"
            ]
            if any(indicator in summary["summary"] for indicator in placeholder_indicators):
                needs_summary_regeneration = True
        
        # If we need a real summary, try to generate one
        if needs_summary_regeneration and try_model_generation and 'description' in article and article['description']:
            try:
                # Format article for summarization
                summarization_article = {
                    'id': article_id,
                    'title': article.get('title', 'Unknown Title'),
                    'content': article.get('description', ''),
                    'source': article.get('source', 'Unknown'),
                    'date': article.get('date', 'Unknown'),
                    'tags': article.get('tags', 'Unknown')
                }
                # Try to summarize
                result = summarize_with_ollama(summarization_article)
                if result and result["status"] == "success":
                    generated_summary = result["summary"]
                    print(f"Successfully generated real summary in article detail for: {article['title']}")
                    
                    # Create or update the summary in the database
                    new_summary = {
                        "article_id": article_id,
                        "title": article.get('title', 'Unknown Title'),
                        "summary": generated_summary,
                        "source": article.get('source', 'Unknown'),
                        "source_type": article.get('source_type', article.get('source', 'unknown').lower().replace(' ', '')),
                        "date": article.get('date', 'Unknown'),
                        "generated_at": datetime.now().strftime("%Y-%m-%d")
                    }
                    # Add _id field for Firestore document ID
                    new_summary["_id"] = article_id
                    
                    # Store or update the summary
                    insert_one(firebase_collection_summaries, new_summary)
                    
                    # Update the summary for display
                    article["summary"] = generated_summary
                elif result and result["status"] == "placeholder":
                    # Use the improved placeholder if generated
                    article_specific_placeholder = result["summary"]
                    
                    # Create or update the placeholder
                    new_summary = {
                        "article_id": article_id,
                        "title": article.get('title', 'Unknown Title'),
                        "summary": article_specific_placeholder,
                        "source": article.get('source', 'Unknown'),
                        "source_type": article.get('source_type', article.get('source', 'unknown').lower().replace(' ', '')),
                        "date": article.get('date', 'Unknown'),
                        "generated_at": datetime.now().strftime("%Y-%m-%d")
                    }
                    # Add _id field for Firestore document ID
                    new_summary["_id"] = article_id
                    
                    # Store the improved placeholder
                    insert_one(firebase_collection_summaries, new_summary)
                    
                    # Update the summary for display
                    article["summary"] = article_specific_placeholder
                else:
                    # Fall back to existing summary or create a basic one
                    if summary and "summary" in summary:
                        article["summary"] = summary["summary"]
                    else:
                        article["summary"] = "Summary generation failed. Please check back later."
            except Exception as e:
                print(f"Error generating real summary in article detail: {str(e)}")
                # Use existing summary if available
                if summary and "summary" in summary:
                    article["summary"] = summary["summary"]
                else:
                    article["summary"] = f"No summary available for '{article.get('title')}'."
        else:
            # Use existing summary
            if summary and "summary" in summary:
                article["summary"] = summary["summary"]
            else:
                article["summary"] = f"No summary available for '{article.get('title')}'."
        
        # Get tips from tips collection
        tips = find_one(firebase_collection_tips, {"article_id": article_id})
        
        # Determine if we need to regenerate the tips (placeholder or missing)
        needs_tips_regeneration = False
        if not tips:
            needs_tips_regeneration = True
        elif "tips" in tips and isinstance(tips["tips"], dict) and "summary" in tips["tips"]:
            placeholder_indicators = [
                "No tips available", 
                "This is a placeholder", 
                "basic security recommendations"
            ]
            if any(indicator.lower() in tips["tips"]["summary"].lower() for indicator in placeholder_indicators):
                needs_tips_regeneration = True
            
            # Also check if all tips are generic
            generic_dos = [
                "Keep your software and operating systems updated",
                "Use strong, unique passwords for each account",
                "Enable two-factor authentication",
                "Be cautious with email attachments"
            ]
            if "dos" in tips["tips"] and all(any(generic in tip for generic in generic_dos) for tip in tips["tips"]["dos"]):
                needs_tips_regeneration = True
        
        # If we need real tips, try to generate them
        if needs_tips_regeneration and try_model_generation and 'description' in article and article['description']:
            try:
                # Format article for tips generation
                tips_article = {
                    'title': article.get('title', 'Unknown Title'),
                    'content': article.get('description', ''),
                    'metadata': {
                        'id': article_id,
                        'source': article.get('source', 'Unknown'),
                        'date': article.get('date', 'Unknown'),
                        'tags': article.get('tags', 'Unknown')
                    }
                }
                # Try to generate tips
                result = generate_tips_with_ollama(tips_article)
                if result and 'tips' in result and isinstance(result['tips'], dict):
                    generated_tips = result['tips']
                    print(f"Successfully generated real tips in article detail for: {article['title']}")
                    
                    # Update the tips in the database
                    new_tips = {
                        "article_id": article_id,
                        "title": article.get('title', 'Unknown Title'),
                        "source": article.get('source', 'Unknown'),
                        "date": article.get('date', 'Unknown'),
                        "source_type": article.get('source_type', article.get('source', 'unknown').lower().replace(' ', '')),
                        "tips": generated_tips,
                        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    # Add _id field for Firestore document ID
                    new_tips["_id"] = article_id
                    
                    # Store the new tips
                    insert_one(firebase_collection_tips, new_tips)
                    
                    # Update the tips for display
                    article["tips"] = generated_tips
                else:
                    # Fall back to existing tips or create basic ones
                    if tips and "tips" in tips and isinstance(tips["tips"], dict):
                        article["tips"] = tips["tips"]
                    else:
                        article["tips"] = {
                            "summary": "Tips generation failed. Please check back later.",
                            "dos": ["Keep software updated", "Use strong passwords", "Be cautious with unknown links"],
                            "donts": ["Don't share sensitive information", "Don't reuse passwords", "Don't ignore security warnings"]
                        }
            except Exception as e:
                print(f"Error generating real tips in article detail: {str(e)}")
                # Use existing tips if available
                if tips and "tips" in tips and isinstance(tips["tips"], dict):
                    article["tips"] = tips["tips"]
                else:
                    article["tips"] = {
                        "summary": f"No security tips available for '{article.get('title')}'.",
                        "dos": [], 
                        "donts": []
                    }
        else:
            # Use existing tips
            if tips and "tips" in tips and isinstance(tips["tips"], dict):
                article["tips"] = tips["tips"]
            else:
                article["tips"] = {
                    "summary": "No security tips available.",
                    "dos": [], 
                    "donts": []
                }
        
        # Close Firebase connection
        close()
        
        # Render the article detail template
        return render_template('article_detail.html', article=article)
    
    except Exception as e:
        # Close Firebase connection
        close()
        import traceback
        traceback.print_exc()
        return render_template('error.html', error=f"Error retrieving article: {str(e)}")

def run_web_interface(host='127.0.0.1', port=5000, debug=False):
    """Run the Flask web interface"""
    # Create template directory if it doesn't exist
    os.makedirs('cybersaathi-v2/templates', exist_ok=True)
    
    # Create necessary template files
    create_templates()
    
    # Set Flask app template folder to absolute path
    app.template_folder = os.path.join(os.getcwd(), 'cybersaathi-v2/templates')
    
    # Run the Flask app
    print(f"Starting web interface at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

def create_templates():
    """Create required template files"""
    # Create index.html template
    index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberSaathi Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #3f51b5;
            --primary-dark: #2c3e94;
            --secondary-color: #ff4081;
            --text-color: #333;
            --text-light: #757575;
            --bg-color: #f9fafc;
            --card-bg: #ffffff;
            --card-border: #e0e0e0;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --shadow-hover: 0 8px 15px rgba(0, 0, 0, 0.15);
            --success: #4caf50;
            --danger: #f44336;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(120deg, var(--primary-color), var(--primary-dark));
            color: white;
            padding: 30px 0;
            text-align: center;
            box-shadow: var(--shadow);
            border-bottom: 4px solid var(--secondary-color);
        }
        
        header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        /* Dashboard Stats */
        .dashboard-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .stat-card {
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 25px 20px;
            text-align: center;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            border-top: 4px solid var(--primary-color);
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-hover);
        }
        
        .stat-card h3 {
            color: var(--primary-color);
            font-size: 1.4rem;
            margin-bottom: 10px;
        }
        
        .stat-card p {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 10px 0;
            color: var(--secondary-color);
        }
        
        .stat-card span {
            display: block;
            color: var(--text-light);
            font-size: 1rem;
        }
        
        /* Tabs */
        .tab {
            display: flex;
            background-color: var(--card-bg);
            border-radius: 12px 12px 0 0;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border: 1px solid var(--card-border);
            border-bottom: none;
        }
        
        .tab button {
            flex: 1;
            background-color: transparent;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 16px;
            font-family: 'Poppins', sans-serif;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--text-color);
            transition: all 0.3s ease;
            position: relative;
        }
        
        .tab button:after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background-color: transparent;
            transition: all 0.3s ease;
        }
        
        .tab button:hover {
            background-color: rgba(63, 81, 181, 0.08);
        }
        
        .tab button.active {
            color: var(--primary-color);
            font-weight: 600;
        }
        
        .tab button.active:after {
            background-color: var(--primary-color);
        }
        
        .tabcontent {
            display: none;
            padding: 30px;
            border: 1px solid var(--card-border);
            border-top: none;
            border-radius: 0 0 12px 12px;
            background-color: var(--card-bg);
            animation: fadeEffect 0.5s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        
        @keyframes fadeEffect {
            from {opacity: 0;}
            to {opacity: 1;}
        }
        
        /* Article Cards */
        .tab-row {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 25px;
        }
        
        .article-card {
            border-radius: 12px;
            overflow: hidden;
            background-color: var(--card-bg);
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            height: 100%;
            border: 1px solid var(--card-border);
        }
        
        .article-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-hover);
        }
        
        .article-card-header {
            padding: 20px 20px 15px;
            border-bottom: 1px solid var(--card-border);
        }
        
        .article-card h3 {
            color: var(--primary-color);
            font-size: 1.2rem;
            line-height: 1.4;
            margin-bottom: 10px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .article-card .meta {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            color: var(--text-light);
            font-size: 0.9rem;
            margin-bottom: 5px;
        }
        
        .article-card .meta span {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .article-card .meta span:before {
            content: '';
            display: inline-block;
            width: 12px;
            height: 12px;
            background-color: var(--primary-color);
            border-radius: 50%;
            opacity: 0.7;
        }
        
        .article-card .content {
            padding: 20px;
            flex-grow: 1;
        }
        
        .article-card .content p {
            color: var(--text-color);
            font-size: 0.95rem;
            margin-bottom: 10px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .article-card-footer {
            padding: 15px 20px;
            border-top: 1px solid var(--card-border);
        }
        
        .article-card a.detail-link {
            display: inline-block;
            padding: 8px 16px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.9rem;
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        
        .article-card a.detail-link:hover {
            background-color: var(--primary-dark);
            transform: translateY(-2px);
        }
        
        /* Tips Sections */
        .tips-section {
            margin-top: 20px;
        }
        
        .tips-section h4 {
            color: var(--primary-color);
            font-size: 1.1rem;
            margin-bottom: 10px;
        }
        
        .tips-list {
            list-style-type: none;
            padding-left: 5px;
        }
        
        .tips-list li {
            margin-bottom: 8px;
            padding-left: 25px;
            position: relative;
            font-size: 0.9rem;
        }
        
        .dos-list li:before {
            content: "✅";
            position: absolute;
            left: 0;
        }
        
        .donts-list li:before {
            content: "❌";
            position: absolute;
            left: 0;
        }
        
        /* Footer */
        footer {
            text-align: center;
            padding: 30px;
            color: var(--text-light);
            font-size: 0.9rem;
            margin-top: 50px;
            border-top: 1px solid var(--card-border);
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-light);
        }
        
        .empty-state h3 {
            color: var(--primary-color);
            margin-bottom: 10px;
        }
        
        .empty-state p {
            max-width: 500px;
            margin: 0 auto;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .tab-row {
                grid-template-columns: 1fr;
            }
            
            .dashboard-summary {
                grid-template-columns: repeat(2, 1fr);
            }
            
            header h1 {
                font-size: 2rem;
            }
            
            .tab button {
                font-size: 0.9rem;
                padding: 12px 8px;
            }
            
            .tabcontent {
                padding: 20px;
            }
        }
        
        @media (max-width: 480px) {
            .dashboard-summary {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>CyberSaathi Dashboard</h1>
        <p>Your Cybersecurity Insights Platform</p>
    </header>

    <div class="container">
        <div class="dashboard-summary">
            <div class="stat-card">
                <h3>HackerNews</h3>
                <p>{{ hackernews_count }}</p>
                <span>Articles</span>
            </div>
            <div class="stat-card">
                <h3>CyberNews</h3>
                <p>{{ cybernews_count }}</p>
                <span>Articles</span>
            </div>
            <div class="stat-card">
                <h3>Summaries</h3>
                <p>{{ summaries_count }}</p>
                <span>Generated</span>
            </div>
            <div class="stat-card">
                <h3>CISO Tips</h3>
                <p>{{ tips_count }}</p>
                <span>Generated</span>
            </div>
        </div>

        <div class="tab">
            <button class="tablinks active" onclick="openTab(event, 'Articles')">Articles</button>
            <button class="tablinks" onclick="openTab(event, 'Summaries')">Summaries</button>
            <button class="tablinks" onclick="openTab(event, 'Tips')">CISO Tips</button>
        </div>

        <div id="Articles" class="tabcontent" style="display: block;">
            <h2>Latest Cybersecurity Articles</h2>
            {% if articles %}
            <div class="tab-row">
                {% for article in articles %}
                <div class="article-card">
                    <div class="article-card-header">
                        <h3>{{ article.title }}</h3>
                        <div class="meta">
                            <span>{{ article.source }}</span>
                            <span>{{ article.date }}</span>
                        </div>
                    </div>
                    <div class="content">
                        <p>{{ article.description[:200] + '...' if article.description and article.description|length > 200 else article.description }}</p>
                    </div>
                    <div class="article-card-footer">
                        <a href="{{ url_for('article_detail', article_id=article._id) }}" class="detail-link">Read More</a>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <h3>No articles found</h3>
                <p>There are no articles in the database. Try running the scraper to fetch some articles.</p>
            </div>
            {% endif %}
        </div>

        <div id="Summaries" class="tabcontent">
            <h2>Article Summaries</h2>
            {% set has_summaries = false %}
            {% for article in articles %}
                {% if article.summary and article.summary != "No summary available" %}
                    {% set has_summaries = true %}
                {% endif %}
            {% endfor %}
            
            {% if has_summaries %}
            <div class="tab-row">
                {% for article in articles %}
                {% if article.summary and article.summary != "No summary available" %}
                <div class="article-card">
                    <div class="article-card-header">
                        <h3>{{ article.title }}</h3>
                        <div class="meta">
                            <span>{{ article.source }}</span>
                            <span>{{ article.date }}</span>
                        </div>
                    </div>
                    <div class="content">
                        <h4>Summary:</h4>
                        <p>{{ article.summary }}</p>
                    </div>
                    <div class="article-card-footer">
                        <a href="{{ url_for('article_detail', article_id=article._id) }}" class="detail-link">Read Full Article</a>
                    </div>
                </div>
                {% endif %}
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <h3>No summaries found</h3>
                <p>There are no article summaries in the database. Try running the complete pipeline with summaries generation.</p>
            </div>
            {% endif %}
        </div>

        <div id="Tips" class="tabcontent">
            <h2>CISO Security Tips</h2>
            {% set has_tips = false %}
            {% for article in articles %}
                {% if article.tips and article.tips.dos|length > 0 %}
                    {% set has_tips = true %}
                {% endif %}
            {% endfor %}
            
            {% if has_tips %}
            <div class="tab-row">
                {% for article in articles %}
                {% if article.tips and article.tips.dos|length > 0 %}
                <div class="article-card">
                    <div class="article-card-header">
                        <h3>{{ article.title }}</h3>
                        <div class="meta">
                            <span>{{ article.source }}</span>
                            <span>{{ article.date }}</span>
                        </div>
                    </div>
                    <div class="content">
                        <div class="tips-section">
                            <h4>Security Issue:</h4>
                            <p>{{ article.tips.summary }}</p>
                            
                            <h4>DO's:</h4>
                            <ul class="tips-list dos-list">
                                {% for do_item in article.tips.dos[:3] %}
                                <li>{{ do_item }}</li>
                                {% endfor %}
                                {% if article.tips.dos|length > 3 %}
                                <li>And {{ article.tips.dos|length - 3 }} more...</li>
                                {% endif %}
                            </ul>
                            
                            <h4>DON'Ts:</h4>
                            <ul class="tips-list donts-list">
                                {% for dont_item in article.tips.donts[:3] %}
                                <li>{{ dont_item }}</li>
                                {% endfor %}
                                {% if article.tips.donts|length > 3 %}
                                <li>And {{ article.tips.donts|length - 3 }} more...</li>
                                {% endif %}
                            </ul>
                        </div>
                    </div>
                    <div class="article-card-footer">
                        <a href="{{ url_for('article_detail', article_id=article._id) }}" class="detail-link">View All Tips</a>
                    </div>
                </div>
                {% endif %}
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <h3>No CISO tips found</h3>
                <p>There are no security tips in the database. Try running the complete pipeline with CISO tips generation.</p>
            </div>
            {% endif %}
        </div>

        <footer>
            <p>CyberSaathi v2.0 | Data Last Updated: {{ timestamp }}</p>
        </footer>
    </div>

    <script>
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].style.display = "none";
            }
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
            
            // Save active tab to local storage
            localStorage.setItem('activeTab', tabName);
        }
        
        // Check if there's a saved active tab
        document.addEventListener('DOMContentLoaded', function() {
            const activeTab = localStorage.getItem('activeTab');
            if (activeTab) {
                // Find the button for this tab
                const tablinks = document.getElementsByClassName("tablinks");
                for (let i = 0; i < tablinks.length; i++) {
                    if (tablinks[i].textContent === activeTab) {
                        // Simulate a click on the button
                        tablinks[i].click();
                        break;
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

    # Create article_detail.html template
    article_detail_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ article.title }} - CyberSaathi</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #3f51b5;
            --primary-dark: #2c3e94;
            --secondary-color: #ff4081;
            --text-color: #333;
            --text-light: #757575;
            --bg-color: #f9fafc;
            --card-bg: #ffffff;
            --card-border: #e0e0e0;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --shadow-hover: 0 8px 15px rgba(0, 0, 0, 0.15);
            --success: #4caf50;
            --danger: #f44336;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(120deg, var(--primary-color), var(--primary-dark));
            color: white;
            padding: 30px 0;
            text-align: center;
            box-shadow: var(--shadow);
            position: relative;
            border-bottom: 4px solid var(--secondary-color);
            margin-bottom: 30px;
        }
        
        header h1 {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        header .back-button {
            display: inline-block;
            padding: 8px 15px;
            background-color: rgba(255, 255, 255, 0.2);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 500;
            margin-top: 10px;
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.4);
        }
        
        header .back-button:hover {
            background-color: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
        
        .article-container {
            background-color: var(--card-bg);
            border-radius: 12px;
            box-shadow: var(--shadow);
            margin-bottom: 30px;
            overflow: hidden;
        }
        
        .article-header {
            padding: 30px;
            border-bottom: 1px solid var(--card-border);
            position: relative;
        }
        
        .article-title {
            font-size: 1.8rem;
            color: var(--primary-color);
            margin-bottom: 15px;
            line-height: 1.3;
        }
        
        .article-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .article-meta div {
            background-color: rgba(63, 81, 181, 0.1);
            padding: 5px 12px;
            border-radius: 50px;
            color: var(--primary-color);
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .article-meta div:before {
            content: '';
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: var(--primary-color);
            border-radius: 50%;
        }
        
        .article-actions {
            margin-top: 20px;
        }
        
        .source-link {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .source-link:hover {
            background-color: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        
        .article-section {
            padding: 30px;
            border-bottom: 1px solid var(--card-border);
        }
        
        .article-section h2 {
            font-size: 1.5rem;
            color: var(--primary-color);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--primary-color);
            display: inline-block;
        }
        
        .article-content {
            line-height: 1.8;
        }
        
        .article-content p {
            margin-bottom: 15px;
            font-size: 1.05rem;
        }
        
        .tips-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 25px;
        }
        
        .tips-box {
            background-color: var(--bg-color);
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .tips-box.dos {
            border-top: 4px solid var(--success);
        }
        
        .tips-box.donts {
            border-top: 4px solid var(--danger);
        }
        
        .tips-box h3 {
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.2rem;
            color: var(--primary-color);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .dos h3:before {
            content: "✅";
        }
        
        .donts h3:before {
            content: "❌";
        }
        
        .tips-list {
            list-style-type: none;
        }
        
        .tips-list li {
            margin-bottom: 12px;
            padding-left: 25px;
            position: relative;
        }
        
        .dos-list li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: var(--success);
            font-weight: bold;
        }
        
        .donts-list li:before {
            content: "✗";
            position: absolute;
            left: 0;
            color: var(--danger);
            font-weight: bold;
        }
        
        .security-issue {
            background-color: rgba(63, 81, 181, 0.08);
            border-left: 4px solid var(--primary-color);
            padding: 15px 20px;
            margin-bottom: 25px;
            border-radius: 0 8px 8px 0;
        }
        
        .security-issue h3 {
            margin-top: 0;
            color: var(--primary-color);
            font-size: 1.2rem;
            margin-bottom: 10px;
        }
        
        .no-data {
            padding: 30px;
            text-align: center;
            color: var(--text-light);
        }
        
        .no-data p {
            margin-bottom: 0;
        }
        
        footer {
            text-align: center;
            padding: 30px 0;
            color: var(--text-light);
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .article-title {
                font-size: 1.5rem;
            }
            
            .article-section {
                padding: 20px;
            }
            
            .tips-container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>CyberSaathi Article</h1>
        <a href="{{ url_for('index') }}" class="back-button">← Back to Dashboard</a>
    </header>

    <div class="container">
        <div class="article-container">
            <div class="article-header">
                <h1 class="article-title">{{ article.title }}</h1>
                
                <div class="article-meta">
                    <div>{{ article.source }}</div>
                    <div>{{ article.date }}</div>
                    {% if article.source_type %}
                    <div>{{ article.source_type|capitalize }}</div>
                    {% endif %}
                </div>
                
                {% if article.url %}
                <div class="article-actions">
                    <a href="{{ article.url }}" target="_blank" class="source-link">Read Original Article</a>
                </div>
                {% endif %}
            </div>
            
            <div class="article-section">
                <h2>Article Content</h2>
                <div class="article-content">
                    {% if article.description %}
                        {% for paragraph in article.description.split('\n') %}
                            {% if paragraph.strip() %}
                            <p>{{ paragraph }}</p>
                            {% endif %}
                        {% endfor %}
                    {% else %}
                        <div class="no-data">
                            <p>No content available for this article.</p>
                        </div>
                    {% endif %}
                </div>
            </div>
            
            <div class="article-section">
                <h2>Article Summary</h2>
                <div class="article-content">
                    {% if article.summary and article.summary != "No summary available" %}
                        {% for paragraph in article.summary.split('\n') %}
                            {% if paragraph.strip() %}
                            <p>{{ paragraph }}</p>
                            {% endif %}
                        {% endfor %}
                    {% else %}
                        <div class="no-data">
                            <p>No summary available for this article.</p>
                        </div>
                    {% endif %}
                </div>
            </div>
            
            <div class="article-section">
                <h2>CISO Security Tips</h2>
                
                {% if article.tips and article.tips.summary and article.tips.dos|length > 0 %}
                    <div class="security-issue">
                        <h3>Key Security Issue</h3>
                        <p>{{ article.tips.summary }}</p>
                    </div>
                    
                    <div class="tips-container">
                        <div class="tips-box dos">
                            <h3>DO's</h3>
                            {% if article.tips.dos|length > 0 %}
                            <ul class="tips-list dos-list">
                                {% for do_item in article.tips.dos %}
                                <li>{{ do_item }}</li>
                                {% endfor %}
                            </ul>
                            {% else %}
                            <p>No recommendations available.</p>
                            {% endif %}
                        </div>
                        
                        <div class="tips-box donts">
                            <h3>DON'Ts</h3>
                            {% if article.tips.donts|length > 0 %}
                            <ul class="tips-list donts-list">
                                {% for dont_item in article.tips.donts %}
                                <li>{{ dont_item }}</li>
                                {% endfor %}
                            </ul>
                            {% else %}
                            <p>No warnings available.</p>
                            {% endif %}
                        </div>
                    </div>
                {% else %}
                    <div class="no-data">
                        <p>No CISO tips available for this article.</p>
                    </div>
                {% endif %}
            </div>
        </div>

        <footer>
            <p>CyberSaathi v2.0 | Article scraped on: {{ article.scraped_at }}</p>
        </footer>
    </div>
</body>
</html>
"""

    # Create error.html template
    error_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - CyberSaathi</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #3f51b5;
            --primary-dark: #2c3e94;
            --secondary-color: #ff4081;
            --text-color: #333;
            --bg-color: #f9fafc;
            --card-bg: #ffffff;
            --shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            --error-color: #f44336;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            line-height: 1.6;
        }
        
        .error-container {
            background-color: var(--card-bg);
            border-radius: 12px;
            box-shadow: var(--shadow);
            width: 90%;
            max-width: 500px;
            overflow: hidden;
            text-align: center;
            border-top: 5px solid var(--error-color);
        }
        
        .error-header {
            background-color: #ffebee;
            padding: 25px;
        }
        
        .error-symbol {
            font-size: 4rem;
            color: var(--error-color);
            margin-bottom: 15px;
        }
        
        .error-content {
            padding: 30px;
        }
        
        h1 {
            color: var(--error-color);
            font-size: 1.8rem;
            margin-bottom: 15px;
        }
        
        p {
            margin-bottom: 25px;
            color: var(--text-color);
            font-size: 1.1rem;
        }
        
        .return-button {
            display: inline-block;
            padding: 12px 25px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .return-button:hover {
            background-color: var(--primary-dark);
            transform: translateY(-3px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-header">
            <div class="error-symbol">⚠️</div>
        </div>
        <div class="error-content">
            <h1>Error Occurred</h1>
            <p>{{ error }}</p>
            <a href="{{ url_for('index') }}" class="return-button">Return to Dashboard</a>
        </div>
    </div>
</body>
</html>
"""

    # Write the template files
    templates_dir = 'cybersaathi-v2/templates'
    os.makedirs(templates_dir, exist_ok=True)
    
    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
        
    with open(os.path.join(templates_dir, 'article_detail.html'), 'w', encoding='utf-8') as f:
        f.write(article_detail_html)
        
    with open(os.path.join(templates_dir, 'error.html'), 'w', encoding='utf-8') as f:
        f.write(error_html)

if __name__ == "__main__":
    print("=============================================")
    print("       CyberSaathi Web Interface")
    print("=============================================\n")
    
    run_web_interface(debug=True) 