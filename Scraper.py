"""
Cybersecurity News Scraper - Firebase Firestore Version

This script scrapes articles from The Hacker News and Cyber News,
and stores them in Firebase Firestore.
"""

import sys
import time
import os
import hashlib
import base64
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from datetime import datetime
import argparse
from dotenv import load_dotenv
from firebase_helper import initialize_firebase, get_collection, create_index

# Load environment variables from .env file
load_dotenv()

# Set environment variables to avoid TensorFlow errors
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Disable GPU

# Set up console encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Firestore setup
def setup_firestore():
    """Connect to Firestore and set up database and collections"""
    try:
        # Initialize Firebase
        firebase = initialize_firebase()
        if not firebase:
            return None
        
        # Get collection name from environment variable
        collection_news = os.getenv("FIREBASE_COLLECTION_NEWS", "news")
        
        # Get collection reference
        news_collection = get_collection(collection_news)
        
        # Create indexes for faster lookups
        create_index(collection_news, "normalized_title")
        create_index(collection_news, "source_type")  # Add index for source_type
        
        print("Firebase Firestore connection established successfully")
        return {
            "client": firebase["client"],
            "db": firebase["db"],
            "news": collection_news  # Only use the unified news collection
        }
    except Exception as e:
        print(f"Error connecting to Firebase Firestore: {str(e)}")
        return None

# Encryption utilities
def generate_encryption_key(password, salt=None):
    """Generate a Fernet encryption key using a password"""
    if salt is None:
        # Use a consistent salt for reproducible encryption
        salt = b'cybersecurity_news_scraper_salt'
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    # Use a fixed password if none provided
    if password is None:
        password = b'default_encryption_password'
    elif isinstance(password, str):
        password = password.encode()
        
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

def encrypt_text(text, encryption_key=None):
    """Encrypt text using Fernet symmetric encryption"""
    if encryption_key is None:
        encryption_key = generate_encryption_key(None)
    
    f = Fernet(encryption_key)
    # Convert text to bytes if it's a string
    if isinstance(text, str):
        text = text.encode()
    
    # Encrypt and return as base64 string for easy storage
    encrypted_data = f.encrypt(text)
    return base64.b64encode(encrypted_data).decode('utf-8')

def decrypt_text(encrypted_text, encryption_key=None):
    """Decrypt text that was encrypted with Fernet"""
    if encryption_key is None:
        encryption_key = generate_encryption_key(None)
    
    f = Fernet(encryption_key)
    # Convert from base64 string to bytes
    if isinstance(encrypted_text, str):
        encrypted_text = base64.b64decode(encrypted_text)
    
    # Decrypt and return as string
    decrypted_data = f.decrypt(encrypted_text)
    return decrypted_data.decode('utf-8')

def normalize_title(title):
    """Normalize title for comparison - lowercase, remove punctuation, extra spaces"""
    if not title:
        return ""
    # Convert to lowercase
    normalized = title.lower()
    # Remove punctuation 
    normalized = re.sub(r'[^\w\s]', '', normalized)
    # Remove extra spaces and trim
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def generate_article_id(title):
    """Generate a unique ID from an article title using SHA-256"""
    # Handle None or empty titles
    if not title or title == "Title not found":
        # Use timestamp for articles without titles
        return hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()
    
    # Generate SHA-256 hash from title
    return hashlib.sha256(title.encode()).hexdigest()

# Store article in Firestore
def store_article(collection_name, article_data):
    """Store article in Firestore collection with unique ID and normalized title constraint"""
    try:
        # Import Firebase helper module functions
        from firebase_helper import find_one, insert_one, update_one, find
        
        # Check if article already exists by ID
        existing_by_id = find_one(collection_name, {"_id": article_data["_id"]})
        if existing_by_id:
            print(f"Article with ID {article_data['_id']} already exists in database")
            
            # Check if we have better data to update
            should_update = False
            update_data = {}
            
            # Check if date is better in new article
            if "date" in article_data and article_data["date"] != "Date not found" and existing_by_id.get("date") in [None, "", "Date not found"]:
                update_data["date"] = article_data["date"]
                should_update = True
            
            # Check if we have content in new article but not in existing
            if "description" in article_data and article_data["description"] != "No content found" and existing_by_id.get("description") in [None, "", "No content found"]:
                update_data["description"] = article_data["description"]
                should_update = True
            
            # Check if we have tags in new article but not in existing
            if "tags" in article_data and article_data["tags"] and existing_by_id.get("tags") in [None, ""]:
                update_data["tags"] = article_data["tags"]
                should_update = True
                
            # Check if we have a URL in new article but not in existing
            if "url" in article_data and article_data["url"] and existing_by_id.get("url") in [None, ""]:
                update_data["url"] = article_data["url"]
                should_update = True
                
            # Check if we should update source with better name
            if "source" in article_data and article_data["source"] in ["The Hacker News", "Cyber News"] and existing_by_id.get("source") in ["hackernews", "cybernews"]:
                update_data["source"] = article_data["source"]
                should_update = True
            
            # Update scraped_at timestamp
            update_data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Update the article if we have better data
            if should_update:
                result = update_one(
                    collection_name,
                    {"_id": article_data["_id"]},
                    {"$set": update_data}
                )
                print(f"Updated article with ID {article_data['_id']} with better data")
                return True
            else:
                print(f"No updates needed for article with ID {article_data['_id']}")
                return False
            
        # Generate normalized title for comparison
        if "title" in article_data:
            normalized_title = normalize_title(article_data["title"])
            
            # Add normalized title to the article data
            article_data["normalized_title"] = normalized_title
            
            # For the news collection, check if an article with the same normalized title exists from any source
            if collection_name == os.getenv("FIREBASE_COLLECTION_NEWS", "news"):
                # Check across all source types
                existing_by_title = find_one(collection_name, {"normalized_title": normalized_title})
                
                # Special case: If this is a new article but same title exists from different source, allow it
                if existing_by_title and "source_type" in existing_by_title and "source_type" in article_data:
                    if existing_by_title["source_type"] != article_data["source_type"]:
                        # Different source type, so this is a different article - proceed with insertion
                        article_data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        result = insert_one(collection_name, article_data)
                        print(f"Stored article from different source in unified collection with ID: {result['inserted_id']}")
                        return True
            else:
                # For legacy collections, check by title within that collection
                existing_by_title = find_one(collection_name, {"normalized_title": normalized_title})
            
            if existing_by_title:
                print(f"Article with similar title already exists in database (ID: {existing_by_title['_id']})")
                
                # Update this article if we have better data
                should_update = False
                update_data = {}
                
                # Same checks as above
                if "date" in article_data and article_data["date"] != "Date not found" and existing_by_title.get("date") in [None, "", "Date not found"]:
                    update_data["date"] = article_data["date"]
                    should_update = True
                
                if "description" in article_data and article_data["description"] != "No content found" and existing_by_title.get("description") in [None, "", "No content found"]:
                    update_data["description"] = article_data["description"]
                    should_update = True
                
                if "tags" in article_data and article_data["tags"] and existing_by_title.get("tags") in [None, ""]:
                    update_data["tags"] = article_data["tags"]
                    should_update = True
                    
                if "url" in article_data and article_data["url"] and existing_by_title.get("url") in [None, ""]:
                    update_data["url"] = article_data["url"]
                    should_update = True
                    
                if "source" in article_data and article_data["source"] in ["The Hacker News", "Cyber News"] and existing_by_title.get("source") in ["hackernews", "cybernews"]:
                    update_data["source"] = article_data["source"]
                    should_update = True
                
                # Update scraped_at timestamp
                update_data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Update the article if we have better data
                if should_update:
                    result = update_one(
                        collection_name,
                        {"_id": existing_by_title["_id"]},
                        {"$set": update_data}
                    )
                    print(f"Updated article with ID {existing_by_title['_id']} with better data")
                    return True
                else:
                    print(f"No updates needed for article with ID {existing_by_title['_id']}")
                    return False
        
        # If the article wasn't found by ID or normalized title, insert it
        article_data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = insert_one(collection_name, article_data)
        print(f"Article stored in Firestore with ID: {result['inserted_id']}")
        return True
    
    except Exception as e:
        print(f"Error storing article in Firestore: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def setup_webdriver():
    """Set up Chrome WebDriver"""
    chrome_options = Options()
    
    # Basic options
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Disable GPU and graphics completely
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument('--disable-gpu-sandbox')
    chrome_options.add_argument('--disable-accelerated-2d-canvas')
    chrome_options.add_argument('--disable-accelerated-jpeg-decoding')
    chrome_options.add_argument('--disable-webgl')
    chrome_options.add_argument('--disable-extensions')
    
    # Network related options
    chrome_options.add_argument('--proxy-server="direct://"')
    chrome_options.add_argument('--proxy-bypass-list=*')
    chrome_options.add_argument('--ignore-certificate-errors')
    
    # Performance optimizations
    chrome_options.add_argument('--disable-features=NetworkService')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disk-cache-size=0')
    chrome_options.add_argument('--disable-features=DnsOverHttps')
    chrome_options.add_argument('--dns-prefetch-disable')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--js-flags=--max_old_space_size=512')
    
    # Memory usage optimizations
    chrome_options.add_argument('--aggressive-cache-discard')
    chrome_options.add_argument('--disable-cache')
    chrome_options.add_argument('--disable-application-cache')
    chrome_options.add_argument('--disable-offline-load-stale-cache')
    chrome_options.add_argument('--disable-component-extensions-with-background-pages')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-media-session-api')
    chrome_options.add_argument('--disable-site-isolation-trials')
    chrome_options.add_argument('--disable-local-storage')
    chrome_options.add_argument('--single-process')  # Use a single process to reduce memory usage
    chrome_options.add_argument('--process-per-site')  # Limit processes
    chrome_options.add_argument('--disable-remote-fonts')  # Disable loading remote fonts
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')  # Disable images to save memory
    
    # Add user agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Create driver with increased page load timeout
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(20)  # Reduced timeout to 20 seconds
    
    # Set a smaller window size to reduce memory usage
    driver.set_window_size(1024, 768)
    
    return driver

def is_valid_url(url):
    """Check if a URL is valid and properly formatted"""
    if not url:
        return False
    # Basic validation - should start with http or https
    if not (url.startswith('http://') or url.startswith('https://')):
        return False
    # Accept any thehackernews domain (.com, .uk, etc.)
    if not ('thehackernews.' in url.lower()):
        return False
    return True

def is_driver_alive(driver):
    """Check if the WebDriver is still responsive"""
    try:
        # Execute a simple JavaScript to check if the driver is responsive
        driver.execute_script("return 1")
        return True
    except:
        return False

def reconnect_driver(driver):
    """Safely close the current driver and create a new one"""
    try:
        driver.quit()
    except:
        pass  # Ignore errors while closing
    
    print("WebDriver disconnected. Reconnecting...")
    time.sleep(2)  # Wait before creating a new driver
    return setup_webdriver()

def format_date(date_string):
    """Format date string to a standard format"""
    if not date_string or date_string == "Date not found":
        return date_string
        
    try:
        # Handle ISO format dates (YYYY-MM-DD)
        if re.match(r'^\d{4}-\d{2}-\d{2}', date_string):
            parsed_date = datetime.strptime(date_string.split('T')[0], '%Y-%m-%d')
            return parsed_date.strftime("%d %B %Y")
            
        # Just return the original if we can't parse it
        return date_string
    except:
        return date_string

def scrape_hackernews():
    """Scrape articles from The Hacker News"""
    # Setup Firestore
    firestore = setup_firestore()
    if not firestore:
        print("Unable to connect to Firestore. Scraping will be aborted.")
        return
    
    # Generate encryption key
    encryption_key = generate_encryption_key(None)
    
    driver = setup_webdriver()
    url = "https://thehackernews.com/"
    
    try:
        print(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "body-post"))
        )
        
        # Get all articles into separate links
        article_links = []
        
        # Find all article containers
        articles = driver.find_elements(By.CLASS_NAME, "body-post")
        print(f"Found {len(articles)} articles on the main page")
        
        # Process each article to extract basic info - don't limit to 10
        for i, article in enumerate(articles):
            try:
                # Get the article title
                title_element = article.find_element(By.CLASS_NAME, "home-title")
                title = title_element.text.strip()
                
                # Get the article URL
                article_url = None
                try:
                    link = article.find_element(By.CSS_SELECTOR, "a.story-link")
                    article_url = link.get_attribute("href")
                except NoSuchElementException:
                    try:
                        link = title_element.find_element(By.TAG_NAME, "a")
                        article_url = link.get_attribute("href")
                    except:
                        pass
                
                # Validate URL before proceeding
                if not article_url or not is_valid_url(article_url):
                    print(f"Skipping article #{i+1} due to invalid URL: {article_url}")
                    continue
                    
                # Get the date directly from the article on the main page
                date = "Date not found"
                try:
                    # Try various date selectors specific to the main page
                    date_selectors = [
                        (By.CLASS_NAME, "h-datetime"),
                        (By.CSS_SELECTOR, ".item-label"),
                        (By.CSS_SELECTOR, "span.h-datetime"),
                        (By.CSS_SELECTOR, ".meta-date"),
                        (By.CSS_SELECTOR, "[itemprop='datePublished']"),
                    ]
                    
                    for by_method, selector in date_selectors:
                        try:
                            date_element = article.find_element(by_method, selector)
                            raw_date = date_element.text.strip()
                            
                            # If we found a date, break out of the loop
                            if raw_date:
                                date = raw_date
                                break
                        except:
                            continue
                    
                    # Try to get it from metadata if visible date element failed
                    if date == "Date not found":
                        try:
                            # Execute JavaScript to find metadata date for this article
                            js_script = f"""
                                const article = document.getElementsByClassName('body-post')[{i}];
                                const metaTags = article.querySelectorAll('meta[itemprop="datePublished"], meta[property="article:published_time"]');
                                return metaTags.length > 0 ? metaTags[0].getAttribute('content') : null;
                            """
                            meta_date = driver.execute_script(js_script)
                            if meta_date:
                                date = meta_date
                        except:
                            pass
                
                except Exception as e:
                    print(f"Error extracting date from main page: {str(e)}")
                
                # Format the date properly if it's not "Date not found"
                if date != "Date not found":
                    try:
                        # Clean up the date for parsing
                        cleaned_date = date.strip()
                        original_date = cleaned_date  # Keep original for debugging
                        
                        print(f"  Original date format: '{cleaned_date}'")
                        
                        # Special case for "Mar" abbreviation which causes issues
                        if cleaned_date.startswith("Mar "):
                            print(f"  Found abbreviated month: {cleaned_date}")
                            try:
                                # Parse "Mar 19, 2025" format directly
                                match = re.search(r'Mar\s+(\d+),?\s+(\d{4})', cleaned_date)
                                if match:
                                    day, year = match.groups()
                                    day = day.zfill(2) if len(day) == 1 else day
                                    date = f"{day} March {year}"
                                    print(f"  Directly converted Mar date to: {date}")
                            except Exception as e:
                                print(f"  Special Mar handling failed: {str(e)}")
                        
                        # Handle other month abbreviations
                        month_abbr_map = {
                            "Jan": "January",
                            "Feb": "February",
                            "Mar": "March",
                            "Apr": "April",
                            "May": "May",  # May is already full name
                            "Jun": "June",
                            "Jul": "July",
                            "Aug": "August",
                            "Sep": "September",
                            "Oct": "October",
                            "Nov": "November",
                            "Dec": "December"
                        }
                        
                        # Replace month abbreviations with full names
                        for abbr, full in month_abbr_map.items():
                            if abbr in cleaned_date:
                                cleaned_date = cleaned_date.replace(abbr, full)
                                print(f"  Expanded month abbreviation to: {cleaned_date}")
                                break
                        
                        # Remove any "on" prefix that might be present
                        if cleaned_date.lower().startswith("on "):
                            cleaned_date = cleaned_date[3:]
                        
                        # Convert date to standard format (DD MONTH YYYY)
                        formatted_date = None
                        
                        # Try to handle dates like "March 19, 2025" or "March 19 2025"
                        month_day_year = re.search(r'([A-Za-z]+)\s+(\d{1,2})(?:[,\s]+)(\d{4})', cleaned_date)
                        if month_day_year:
                            month, day, year = month_day_year.groups()
                            try:
                                # Ensure day is padded to 2 digits
                                day = day.zfill(2) if len(day) == 1 else day
                                # Create a temporary date string in correct format
                                temp_date = f"{day} {month} {year}"
                                # Parse and reformat
                                parsed_date = datetime.strptime(temp_date, "%d %B %Y")
                                formatted_date = parsed_date.strftime("%d %B %Y")
                                print(f"  Formatted via pattern 1: '{formatted_date}'")
                            except Exception as e:
                                print(f"  Pattern 1 parsing error: {str(e)}")
                        
                        # Try to handle dates like "19 March 2025"
                        if not formatted_date and re.search(r'^\d{1,2}\s+[A-Za-z]+\s+\d{4}$', cleaned_date):
                            try:
                                # Handle potential case issues with month
                                day, month, year = cleaned_date.split()
                                # Ensure day is padded to 2 digits
                                day = day.zfill(2) if len(day) == 1 else day
                                # Make month title case
                                month = month.title()
                                temp_date = f"{day} {month} {year}"
                                parsed_date = datetime.strptime(temp_date, "%d %B %Y")
                                formatted_date = parsed_date.strftime("%d %B %Y")
                                print(f"  Formatted via pattern 2: '{formatted_date}'")
                            except Exception as e:
                                print(f"  Pattern 2 parsing error: {str(e)}")
                        
                        # Try to handle dates like "19/03/2025" or "19-03-2025"
                        if not formatted_date and re.search(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', cleaned_date):
                            try:
                                if "/" in cleaned_date:
                                    parsed_date = datetime.strptime(cleaned_date, "%d/%m/%Y")
                                else:
                                    parsed_date = datetime.strptime(cleaned_date, "%d-%m-%Y")
                                formatted_date = parsed_date.strftime("%d %B %Y")
                                print(f"  Formatted via pattern 3: '{formatted_date}'")
                            except Exception as e:
                                print(f"  Pattern 3 parsing error: {str(e)}")
                        
                        # Try to handle dates like "2025-03-19"
                        if not formatted_date and re.search(r'^\d{4}-\d{1,2}-\d{1,2}$', cleaned_date):
                            try:
                                parsed_date = datetime.strptime(cleaned_date, "%Y-%m-%d")
                                formatted_date = parsed_date.strftime("%d %B %Y")
                                print(f"  Formatted via pattern 4: '{formatted_date}'")
                            except Exception as e:
                                print(f"  Pattern 4 parsing error: {str(e)}")
                        
                        # Special case for The Hacker News date format (e.g., "Monday, March 18, 2024")
                        if not formatted_date and "," in cleaned_date:
                            try:
                                # Split by commas and take relevant parts
                                parts = cleaned_date.split(",")
                                if len(parts) >= 3:  # Format: Weekday, Month Day, Year
                                    month_day = parts[1].strip()
                                    year = parts[2].strip()
                                    month_day_match = re.search(r'([A-Za-z]+)\s+(\d{1,2})', month_day)
                                    if month_day_match:
                                        month, day = month_day_match.groups()
                                        day = day.zfill(2) if len(day) == 1 else day
                                        temp_date = f"{day} {month} {year}"
                                        parsed_date = datetime.strptime(temp_date, "%d %B %Y")
                                        formatted_date = parsed_date.strftime("%d %B %Y")
                                        print(f"  Formatted via pattern 5: '{formatted_date}'")
                                elif len(parts) == 2:  # Format might be Month Day, Year
                                    month_day = parts[0].strip()
                                    year = parts[1].strip()
                                    month_day_match = re.search(r'([A-Za-z]+)\s+(\d{1,2})', month_day)
                                    if month_day_match:
                                        month, day = month_day_match.groups()
                                        day = day.zfill(2) if len(day) == 1 else day
                                        temp_date = f"{day} {month} {year}"
                                        parsed_date = datetime.strptime(temp_date, "%d %B %Y")
                                        formatted_date = parsed_date.strftime("%d %B %Y")
                                        print(f"  Formatted via pattern 6: '{formatted_date}'")
                            except Exception as e:
                                print(f"  Pattern 5-6 parsing error: {str(e)}")
                        
                        # Handle cases where the date might be "X hours/days ago"
                        if not formatted_date and "ago" in cleaned_date.lower():
                            formatted_date = datetime.now().strftime("%d %B %Y")
                            print(f"  Using current date for 'ago' format: '{formatted_date}'")
                        
                        # If we found a formatted date, use it
                        if formatted_date:
                            date = formatted_date
                        else:
                            print(f"  WARNING: Could not format date '{original_date}' - keeping original")
                    
                    except Exception as date_err:
                        print(f"  Error formatting date '{date}': {str(date_err)}")
                        # Keep the original date if formatting fails
                
                # If date is still not found, use current date
                if date == "Date not found":
                    current_date = datetime.now()
                    date = current_date.strftime("%d %B %Y")
                    print(f"  Using current date: {date}")
                
                # Get tags directly from the article on the main page
                try:
                    tags_element = article.find_element(By.CLASS_NAME, "h-tags")
                    tags = tags_element.text.strip()
                except:
                    tags = "Tags not found"
                
                # Generate article ID and encrypt the title
                article_id = generate_article_id(title)
                encrypted_title = encrypt_text(title, encryption_key)
                
                # Check if article with this encrypted title already exists in database
                # Import the find_one function from firebase_helper
                from firebase_helper import find_one
                
                # Check if article already exists in the news collection with source_type=hackernews
                if find_one(firestore["news"], {"encrypted_title": encrypted_title, "source_type": "hackernews"}):
                    print(f"Skipping article #{i+1}: '{title[:40]}...' - Duplicate encrypted title found in database")
                    continue
                
                # Add the article to our list
                article_data = {
                    'index': i + 1,
                    'title': title,
                    'encrypted_title': encrypted_title,
                    'url': article_url,
                    'date': date,  # Store main page date
                    'tags': tags,   # Store main page tags
                    '_id': article_id  # Use article ID as Firestore document ID
                }
                
                article_links.append(article_data)
                print(f"Added article #{i+1}: {title[:50]}...")
                print(f"  URL: {article_url}")
                print(f"  Date: {date}")
                print(f"  Tags: {tags}")
                print(f"  ID: {article_id}")
                print(f"  Encrypted Title: {encrypted_title[:30]}...")
                
                # Stop if we've reached the maximum number of articles
                if len(article_links) >= MAX_ARTICLES:
                    print(f"Reached maximum number of articles ({MAX_ARTICLES})")
                    break
            
            except Exception as e:
                print(f"Error processing article on main page: {str(e)}")
                continue
        
        print(f"Collected {len(article_links)} articles from main page")
        print("-" * 80)
        
        # Now visit each article page separately
        for i, article in enumerate(article_links):
            try:
                # Check if driver is still alive, reconnect if needed
                if not is_driver_alive(driver):
                    driver = reconnect_driver(driver)
                
                url = article['url']
                title = article['title']
                date = article['date']  # Use date from main page
                tags = article['tags']  # Use tags from main page
                article_id = article['_id']  # Get article ID
                encrypted_title = article['encrypted_title']  # Get encrypted title
                
                print(f"\nProcessing article #{i+1}: {title}")
                print(f"URL: {url}")
                print(f"Date: {date}")
                print(f"Tags: {tags}")
                print(f"ID: {article_id}")
                
                # Check if this is a special domain URL (like .uk)
                is_special_domain = 'thehackernews.uk' in url.lower() or 'thehackernews.org' in url.lower()
                
                # Visit the article page with retry
                content = []
                max_retries = 2  # Reduced from 3 to 2
                success = False
                
                for retry in range(max_retries):
                    try:
                        # Check if driver is still alive before each attempt
                        if not is_driver_alive(driver):
                            driver = reconnect_driver(driver)
                            
                        # Visit the article page
                        driver.get(url)
                        time.sleep(2)  # Reduced from 5 to 2 seconds
                        
                        # Extract article content
                        try:
                            # Try to find the article body - using different selectors for special domains
                            content_selectors = [
                                ".articlebody", ".post-content", ".entry-content", ".article-content",
                                "article", "main .post", "main article", "#content article", 
                                ".content", ".main-content", ".single-content", ".post", 
                                "div[class*='article']", "div[class*='content']", "div[class*='post']"
                            ]
                            
                            for selector in content_selectors:
                                try:
                                    # Use a shorter timeout for faster iteration through selectors
                                    article_body = WebDriverWait(driver, 3).until(  # Reduced from 5 to 3
                                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                    )
                                    
                                    # Get all paragraphs
                                    paragraphs = article_body.find_elements(By.TAG_NAME, "p")
                                    
                                    # If no paragraphs found but we have the article body, try getting direct text
                                    if not paragraphs:
                                        # Try div elements
                                        paragraphs = article_body.find_elements(By.TAG_NAME, "div")
                                        # If still no luck, just use the article body itself
                                        if not paragraphs:
                                            text = article_body.text.strip()
                                            if text:
                                                content.append(text)
                                    else:
                                        for p in paragraphs:
                                            text = p.text.strip()
                                            if text and not any(skip in text.lower() for skip in [
                                                "read more:", "related:", "advertisement",
                                                "subscribe to our newsletter", "follow us"
                                            ]):
                                                content.append(text)
                                    
                                    if content:  # If we found content, break the loop
                                        success = True
                                        break
                                except:
                                    continue
                            
                            # If no content found using selectors, try JavaScript extraction
                            if not content:
                                print("Trying JavaScript content extraction...")
                                try:
                                    # First attempt - get all paragraph text
                                    content_script = """
                                        return Array.from(document.querySelectorAll('p'))
                                            .map(p => p.textContent.trim())
                                            .filter(text => text.length > 0); // Keep all non-empty paragraphs
                                    """
                                    js_content = driver.execute_script(content_script)
                                    
                                    if js_content and len(js_content) > 0:
                                        content = js_content
                                        success = True
                                    else:
                                        # Second attempt - get all text from elements that might contain content
                                        content_script = """
                                            const contentElements = document.querySelectorAll('article, .article-content, .post-content, .entry-content, .content, main');
                                            let allText = [];
                                            
                                            for (const element of contentElements) {
                                                if (element) {
                                                    // Get all text nodes within this element
                                                    const walker = document.createTreeWalker(
                                                        element,
                                                        NodeFilter.SHOW_TEXT,
                                                        null,
                                                        false
                                                    );
                                                    
                                                    let node;
                                                    let paragraphs = [];
                                                    let currentParagraph = "";
                                                    
                                                    while (node = walker.nextNode()) {
                                                        const text = node.textContent.trim();
                                                        if (text) {
                                                            currentParagraph += text + " ";
                                                            // Break into paragraphs at sensible places
                                                            if (text.endsWith('.') || text.endsWith('?') || text.endsWith('!')) {
                                                                if (currentParagraph.trim().length > 0) { // Keep all non-empty paragraphs
                                                                    paragraphs.push(currentParagraph.trim());
                                                                }
                                                                currentParagraph = "";
                                                            }
                                                        }
                                                    }
                                                    
                                                    // Add any remaining text
                                                    if (currentParagraph.trim().length > 0) {
                                                        paragraphs.push(currentParagraph.trim());
                                                    }
                                                    
                                                    if (paragraphs.length > 0) {
                                                        allText = allText.concat(paragraphs);
                                                    }
                                                }
                                            }
                                            
                                            return allText;
                                        """
                                        js_content = driver.execute_script(content_script)
                                        
                                        if js_content and len(js_content) > 0:
                                            content = js_content
                                            success = True
                                except Exception as js_error:
                                    print(f"JavaScript content extraction failed: {str(js_error)}")
                            
                            # If we found content, no need to retry
                            if success:
                                break
                        
                        except Exception as e:
                            print(f"Error extracting content (try {retry+1}): {str(e)}")
                            if retry == max_retries - 1:  # Last retry
                                raise
                    
                    except Exception as e:
                        print(f"Error loading page (try {retry+1}): {str(e)}")
                        # Check if this is a WebDriver connection issue
                        if "connection" in str(e).lower() or "session" in str(e).lower():
                            driver = reconnect_driver(driver)
                        
                        if retry == max_retries - 1:  # Last retry
                            raise
                        time.sleep(2)  # Wait before retrying
                
                # Post-process content to ensure consistency
                # Remove empty paragraphs
                content = [p for p in content if p.strip()]
                
                # Remove duplicate paragraphs
                unique_content = []
                content_set = set()
                for paragraph in content:
                    # Use first 50 chars as a fingerprint to identify duplicates
                    fingerprint = paragraph[:50].strip().lower()
                    if fingerprint and fingerprint not in content_set:
                        content_set.add(fingerprint)
                        unique_content.append(paragraph)
                
                # Sort content by paragraph length to ensure consistent ordering
                unique_content.sort(key=len, reverse=True)
                
                # Then re-sort by frequency of words in article title to get main content first
                if title and title != "Title not found":
                    title_words = set(title.lower().split())
                    
                    def count_title_keywords(paragraph):
                        words = paragraph.lower().split()
                        return sum(1 for word in words if word in title_words)
                    
                    unique_content.sort(key=count_title_keywords, reverse=True)
                
                # Replace content with processed content
                content = unique_content
                
                # Print what we found
                print(f"Content paragraphs: {len(content)} (after processing)")
                
                # Log first sentence of each paragraph to verify consistency
                print("Content summary (first 20 chars of each paragraph):")
                for i, para in enumerate(content[:5]):
                    if i < 5:  # Only show first 5 paragraphs
                        print(f"  Para {i+1}: {para[:20]}...")
                    else:
                        print(f"  (...and {len(content)-5} more paragraphs)")
                        break
                
                # Prepare article for Firestore storage
                description = "\n".join(content) if content else "No content found"
                
                # Store in Firestore with current timestamp
                article_document = {
                    "_id": article_id,
                    "title": title,
                    "encrypted_title": encrypted_title,
                    "url": url,
                    "date": date,
                    "tags": tags,
                    "description": description,
                    "source": "The Hacker News",
                    "source_type": "hackernews",  # Add source type identifier
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Store only in unified news collection
                store_article(firestore["news"], article_document)
                print('-' * 80)
            
            except Exception as e:
                print(f"Error processing article #{i+1}: {str(e)}")
                print('-' * 80)
                
                # Check if we need to reconnect the driver
                if "connection" in str(e).lower() or "session" in str(e).lower():
                    driver = reconnect_driver(driver)
                    
                continue
    
    except Exception as e:
        print(f"Error scraping The Hacker News: {str(e)}")
    
    finally:
        # Close the browser
        try:
            driver.quit()
        except:
            pass  # Ignore errors during driver close
        
        # Close Firestore connection
        if firestore:
            try:
                print("Firestore connection closed")
            except:
                pass

def scrape_cybernews():
    """Scrape articles from Cyber News"""
    # Setup Firestore
    firestore = setup_firestore()
    if not firestore:
        print("Unable to connect to Firestore. Scraping will be aborted.")
        return
    
    # Generate encryption key
    encryption_key = generate_encryption_key(None)
    
    driver = setup_webdriver()
    base_url = "https://cybernews.com/news/"

    try:
        print(f"Navigating to {base_url}")
        driver.get(base_url)
        
        # Add a shorter delay to ensure page loads
        time.sleep(3)  # Reduced from 10 to 3 seconds
        
        # First, collect all article links from the main page
        article_links = set()  # Using set to avoid duplicates
        
        try:
            # Try multiple approaches to find articles
            selectors = [
                "a[href*='/news/']",  # Any link containing /news/
                "div.article a",       # Links within article divs
                "article a",           # Links within article tags
                "div.post a",          # Links within post divs
                "h2 a",               # Links within headlines
                "div.title a"         # Links within title divs
            ]
            
            print("Searching for articles...")
            
            def is_valid_article_url(url):
                """Check if URL is a valid article URL"""
                if not url or not isinstance(url, str):
                    return False
                if not url.startswith("https://cybernews.com/news/"):
                    return False
                if url == base_url:
                    return False
                # Filter out pagination URLs
                if "/page/" in url:
                    return False
                # Filter out category pages
                if url.count('/') < 5:  # Valid article URLs have more segments
                    return False
                return True
            
            # First attempt with direct selectors
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        link = element.get_attribute("href")
                        if is_valid_article_url(link):
                            article_links.add(link)
                    except:
                        continue
            
            # If we don't have enough articles, try scrolling
            if len(article_links) < 20:
                print("Scrolling to find more articles...")
                # Scroll down a few times
                for _ in range(2):  # Reduced from 3 to 2 scrolls
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.5)  # Reduced from 3 to 1.5 seconds
                    
                    # Try all selectors again after scrolling
                    for selector in selectors:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            try:
                                link = element.get_attribute("href")
                                if is_valid_article_url(link):
                                    article_links.add(link)
                            except:
                                continue
            
            # If we still don't have enough articles, try JavaScript to get all links
            if len(article_links) < 20:
                print("Trying JavaScript approach...")
                # Get all links on the page using JavaScript
                links = driver.execute_script("""
                    return Array.from(document.getElementsByTagName('a'))
                        .map(a => a.href)
                        .filter(href => href && href.includes('/news/'));
                """)
                
                for link in links:
                    if is_valid_article_url(link):
                        article_links.add(link)
            
            # Convert to list and sort
            article_links = sorted(list(article_links))
            
            print(f"Found {len(article_links)} valid article links")
            if len(article_links) < 20:
                print("Warning: Found fewer articles than expected")
            print("-" * 80)
            
        except Exception as e:
            print(f"Error collecting article links: {str(e)}")
            return
        
        # Process the first N articles (limited by MAX_ARTICLES)
        num_articles = min(MAX_ARTICLES, len(article_links))
        print(f"Processing {num_articles} articles (limited by --limit={MAX_ARTICLES})")
        
        for i, article_link in enumerate(article_links[:num_articles], 1):
            try:
                # Check if driver is still alive, reconnect if needed
                if not is_driver_alive(driver):
                    driver = reconnect_driver(driver)
                    
                print(f"\nProcessing article {i} of {num_articles}")
                print(f"URL: {article_link}")
                
                # Try to load the article with retries
                max_retries = 2  # Reduced from 3 to 2
                for retry in range(max_retries):
                    try:
                        # Check if driver is still alive before each attempt
                        if not is_driver_alive(driver):
                            driver = reconnect_driver(driver)
                            
                        driver.get(article_link)
                        # Wait for the main content to load with multiple possible selectors
                        WebDriverWait(driver, 10).until(  # Reduced from 20 to 10 seconds
                            EC.presence_of_element_located((By.CSS_SELECTOR, "main, article, div.article-content"))
                        )
                        break
                    except Exception as e:
                        if retry == max_retries - 1:  # Last retry
                            print(f"Failed to load article after {max_retries} attempts: {str(e)}")
                            raise
                        else:
                            print(f"Retry {retry + 1}/{max_retries} loading article...")
                            # Check if this is a WebDriver connection issue
                            if "connection" in str(e).lower() or "session" in str(e).lower():
                                driver = reconnect_driver(driver)
                            time.sleep(2)  # Reduced from 5 to 2 seconds
                
                # Get article title
                title = "Title not found"
                try:
                    title_elem = WebDriverWait(driver, 5).until(  # Reduced from 10 to 5 seconds
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                    )
                    title = title_elem.text.strip()
                except:
                    pass
                
                # Generate article ID and encrypt the title
                article_id = generate_article_id(title)
                encrypted_title = encrypt_text(title, encryption_key)
                
                # Check if article with this encrypted title already exists in database
                # Import the find_one function from firebase_helper
                from firebase_helper import find_one
                
                # Check if article already exists in the news collection with source_type=cybernews
                if find_one(firestore["news"], {"encrypted_title": encrypted_title, "source_type": "cybernews"}):
                    print(f"Skipping article #{i}: '{title[:40]}...' - Duplicate encrypted title found in database")
                    continue
                
                # Get article date - improve date extraction
                date = "Date not found"
                try:
                    # Try multiple date selectors and formats, prioritizing metadata
                    date_selectors = [
                        # First try metadata tags (most reliable)
                        "meta[property='article:published_time']",
                        "meta[itemprop='datePublished']",
                        "meta[name='article:published_time']",
                        # Then try visible date elements
                        "time[datetime]",
                        "time.entry-date",
                        "span.date",
                        "div.article-date",
                        "div.post-date",
                        ".article-meta time",
                        ".post-meta time",
                        ".meta-date",
                        "[class*='publish-date']",
                        "[class*='post-date']",
                        "article time"
                    ]
                    
                    metadata_date = None
                    display_date = None
                    
                    for selector in date_selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                # Get all possible date values
                                datetime_attr = element.get_attribute("datetime")
                                content_attr = element.get_attribute("content")
                                text_content = element.text.strip()
                                
                                # For metadata tags, prefer content attribute
                                if element.tag_name == "meta":
                                    if content_attr:
                                        metadata_date = content_attr
                                        break
                                # For display elements, store but don't break
                                else:
                                    possible_date = datetime_attr or text_content
                                    if possible_date and not display_date:
                                        display_date = possible_date
                            
                            # If we found a metadata date, we can stop searching
                            if metadata_date:
                                break
                                
                        except Exception as e:
                            continue
                    
                    # Prefer metadata date over display date
                    date = metadata_date or display_date or "Date not found"
                    
                    # Clean up the date
                    if date and date != "Date not found":
                        date = date.strip()
                        # Remove any extra time information if present
                        if 'T' in date:
                            date = date.split('T')[0]
                        # Remove any timezone information if present
                        if '+' in date:
                            date = date.split('+')[0]
                        
                        # Try to convert to a more readable format
                        try:
                            from datetime import datetime
                            parsed_date = datetime.strptime(date, '%Y-%m-%d')
                            date = parsed_date.strftime('%d %B %Y')
                        except:
                            # If parsing fails, keep the original format
                            pass
                    
                    # If date is still not found after extraction attempts, use current date
                    if date == "Date not found":
                        current_date = datetime.now()
                        date = current_date.strftime("%d %B %Y")
                        print(f"  Using current date: {date}")
                        
                except Exception as e:
                    print(f"Error extracting date: {str(e)}")
                    # Use current date as fallback
                    current_date = datetime.now()
                    date = current_date.strftime("%d %B %Y")
                
                # Get full article content with multiple fallback options
                content = []
                content_selectors = [
                    "div.article-content",
                    "div.post-content",
                    "article .content",
                    "main article",
                    "div[class*='article-content']"
                ]
                
                for selector in content_selectors:
                    try:
                        content_element = WebDriverWait(driver, 5).until(  # Reduced from 10 to 5 seconds
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        
                        # Get all paragraphs
                        paragraphs = content_element.find_elements(By.TAG_NAME, "p")
                        
                        # Extract text from paragraphs
                        for p in paragraphs:
                            text = p.text.strip()
                            if text and not any(skip in text.lower() for skip in [
                                "read more:", "related:", "advertisement",
                                "subscribe to our newsletter", "follow us"
                            ]):
                                content.append(text)
                        
                        # If we didn't find much content with p tags, try div tags
                        if len(content) < 3:
                            print("  Few paragraphs found with p tags, trying div tags...")
                            div_paragraphs = content_element.find_elements(By.TAG_NAME, "div")
                            for div in div_paragraphs:
                                if div.get_attribute("class") and "content" in div.get_attribute("class"):
                                    text = div.text.strip()
                                    if text and not any(skip in text.lower() for skip in [
                                        "read more:", "related:", "advertisement",
                                        "subscribe to our newsletter", "follow us"
                                    ]):
                                        content.append(text)
                        
                        if content:  # If we found content, break the loop
                            break
                            
                    except:
                        continue
                
                # Try JavaScript extraction if we still don't have much content
                if not content or len(content) < 5:
                    print("  Few paragraphs found with standard extraction, trying JavaScript approach...")
                    try:
                        # Extract all paragraphs using JavaScript
                        js_script = """
                            return Array.from(document.querySelectorAll('p'))
                                .map(p => p.textContent.trim())
                                .filter(text => text.length > 0);
                        """
                        js_paragraphs = driver.execute_script(js_script)
                        
                        if js_paragraphs and len(js_paragraphs) > 0:
                            # Add each paragraph that isn't in the content list already
                            for para in js_paragraphs:
                                if para and not any(skip in para.lower() for skip in [
                                    "read more:", "related:", "advertisement",
                                    "subscribe to our newsletter", "follow us"
                                ]):
                                    content.append(para)
                            
                            print(f"  Added {len(js_paragraphs)} paragraphs via JavaScript extraction")
                    except Exception as js_err:
                        print(f"  JavaScript extraction error: {str(js_err)}")
                
                # Post-process content to ensure consistency - using simplified approach
                if content:
                    # Remove empty paragraphs
                    content = [p for p in content if p.strip()]
                    
                    # Remove duplicate paragraphs - simplified approach
                    seen = set()
                    unique_content = []
                    for p in content:
                        # Use first 30 chars to identify duplicates
                        key = p[:30].lower()
                        if key not in seen:
                            seen.add(key)
                            unique_content.append(p)
                    
                    content = unique_content
                
                # Create description from content
                description = "\n".join(content) if content else "No content found"
                
                # Store in Firestore with current timestamp and proper source
                article_document = {
                    "_id": article_id,
                    "title": title,
                    "encrypted_title": encrypted_title,
                    "url": article_link,
                    "date": date,
                    "description": description,
                    "source": "Cyber News",
                    "source_type": "cybernews",  # Add source type identifier
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Store only in unified news collection
                store_article(firestore["news"], article_document)
                print(f"Stored article in Firestore with ID: {article_id}")
                
                # Print what we found
                print(f"Content paragraphs: {len(content)} (after processing)")
                
                # Log first sentence of each paragraph to verify consistency
                print("Content summary (first 20 chars of each paragraph):")
                for j, para in enumerate(content[:5]):
                    if j < 5:  # Only show first 5 paragraphs
                        print(f"  Para {j+1}: {para[:20]}...")
                    else:
                        print(f"  (...and {len(content)-5} more paragraphs)")
                        break
                
                print("-" * 80)
            
            except Exception as e:
                print(f"Error processing article {i}: {str(e)}")
                print("-" * 80)
                
                # Check if we need to reconnect the driver
                if "connection" in str(e).lower() or "session" in str(e).lower():
                    driver = reconnect_driver(driver)
                    
                continue
    
    except Exception as e:
        print(f"Error scraping Cyber News: {str(e)}")
    
    finally:
        # Close the browser
        try:
            driver.quit()
        except:
            pass  # Ignore errors during driver close
        
        # Close Firestore connection
        if firestore:
            try:
                print("Firestore connection closed")
            except:
                pass

# Define a global variable for max articles
MAX_ARTICLES = 3  # Original value: 10

def verify_firestore_connection():
    """Verify the Firestore connection and list collections"""
    try:
        # Initialize Firebase
        firebase = initialize_firebase()
        if not firebase:
            return False
        
        # List all collections in the database
        collections = firebase["db"].list_collection_names()
        print(f"Successfully connected to Firestore database: {firebase['db'].name}")
        print(f"Available collections: {', '.join(collections)}")
        
        return True
    except Exception as e:
        print(f"Error verifying Firestore connection: {str(e)}")
        return False

def main():
    """Run both scrapers with default settings"""
    # First verify Firestore connection
    print("Verifying Firestore connection...")
    if not verify_firestore_connection():
        print("ERROR: Could not connect to Firestore. Please check your .env file and connection settings.")
        sys.exit(1)
    
    print("\n=== SCRAPING THE HACKER NEWS ===")
    scrape_hackernews()
    print("\n=== SCRAPING CYBER NEWS ===")
    scrape_cybernews()

# Run the main function if the script is executed directly
if __name__ == "__main__":
    main()
else:
    # If imported as a module, check if auto-scrape is disabled
    if not os.environ.get('NO_AUTO_SCRAPE'):
        # If imported as a module, use default settings
        print("=== SCRAPING THE HACKER NEWS ===")
        scrape_hackernews()
        print("=== SCRAPING CYBER NEWS ===")
        scrape_cybernews()
  
