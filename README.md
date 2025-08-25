# CyberSaathi v3 - Cybersecurity Intelligence System

CyberSaathi is an AI-powered cybersecurity intelligence system that scrapes cybersecurity articles from multiple sources, generates AI-powered summaries and CISO tips, and provides a web interface for viewing the processed content.

## Features

- **Multi-Source Web Scraping:** Collects cybersecurity articles from The Hacker News and Cyber News using Selenium WebDriver
- **AI-Powered Summarization:** Uses Ollama's llama3.2:1b model to generate concise article summaries
- **CISO Tips Generation:** Creates actionable security recommendations (Do's and Don'ts) for each article
- **Firebase Firestore Integration:** Stores all scraped data, summaries, and tips in Firebase Firestore
- **Web Interface:** Clean Flask-based dashboard to view articles, summaries, and security tips
- **Unified Workflow:** Single command execution of the entire pipeline from scraping to web interface
- **Flexible CLI Options:** Skip specific steps, set limits, use existing files, and more

## Prerequisites

1. **Python 3.8+** (tested with Python 3.12)
2. **Firebase Project** with Firestore enabled
3. **Ollama** with llama3.2:1b model installed and running
4. **Chrome/Chromium Browser** with ChromeDriver for web scraping

### Firebase Setup

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select an existing one
3. Enable Firestore Database in your project
4. Go to Project Settings > Service Accounts
5. Click "Generate new private key" and download the JSON file
6. Keep this file secure - it contains sensitive credentials

### Ollama Setup

1. Install Ollama from [https://ollama.ai/](https://ollama.ai/)
2. Pull the required model:
   ```bash
   ollama pull llama3.2:1b
   ```
3. Start Ollama service:
   ```bash
   ollama serve
   ```

### Installation

1. Clone the repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your Firebase connection:
   - Create a `.env` file in the project root
   - Add your Firebase service account JSON file path:
     ```
     FIREBASE_SERVICE_ACCOUNT=path/to/your/firebase-service-account.json
     FIREBASE_COLLECTION_NEWS=news
     FIREBASE_COLLECTION_TIPS=tips
     FIREBASE_COLLECTION_SUMMARIES=summaries
     ```
4. Test the Firebase connection:
   ```bash
   python test_firebase_storage.py
   ```

## Troubleshooting Firebase Connection

If you encounter issues with Firebase:

1. Make sure your service account file path is correct in the `.env` file
2. Verify the JSON file contains all required fields (type, project_id, private_key_id, etc.)
3. Check that your Firebase project has Firestore enabled
4. Ensure your service account has proper permissions (Editor role)
5. Try running `test_firebase_storage.py` to diagnose specific issues

## Usage

### Complete Pipeline

Run the complete pipeline (scraping, summarization, CISO tips generation, and web interface):

```
python main.py
```

### Command Line Options

- `--limit N`: Limit number of articles to scrape (default: 10)
- `--skip-scrape`: Skip the scraping step and use existing markdown
- `--input-file FILE`: Use this markdown file instead of scraping
- `--summary-file FILE`: Use this summary file instead of generating new summaries
- `--skip-summaries`: Skip the summarization step
- `--skip-tips`: Skip the CISO tips generation step
- `--skip-storage`: Skip storing data in Firebase Firestore
- `--skip-web`: Skip launching the web interface
- `--cli-view`: View summaries and tips in CLI instead of web
- `--verbose`: Show detailed output
- `--web-port N`: Port to run the web interface on (default: 5000)

### Individual Components

**Launch Web Interface Only:**
```bash
python launch_web_interface.py
```

**Run Scraper Only:**
```bash
python Scraper.py
```

**Export Articles to Markdown:**
```bash
python export_to_markdown.py
```

**Query Stored Articles:**
```bash
python query_articles.py
```

**Query Stored Tips:**
```bash
python query_tips.py
```

The web interface will be available at http://localhost:5000 by default.

## Project Structure

### Core Components
- **main.py**: Unified workflow orchestrator with animated CLI interface
- **Scraper.py**: Web scraper for The Hacker News and Cyber News using Selenium
- **article_summarizer.py**: AI-powered article summarization using Ollama llama3.2:1b
- **ciso_tips_agent.py**: Generates actionable security tips (Do's and Don'ts)
- **web_interface.py**: Flask-based web dashboard
- **firebase_helper.py**: Firebase Firestore database utilities

### Utility Scripts
- **launch_web_interface.py**: Standalone web interface launcher
- **export_to_markdown.py**: Export Firestore data to markdown format
- **query_articles.py**: Query and search stored articles
- **query_tips.py**: Query and search stored security tips
- **store_tips_summaries.py**: Store processed data in Firebase
- **test_firebase_storage.py**: Firebase connection testing

### Data Management
- **check_firebase_data.py**: Check Firebase data integrity
- **fetch_firestore_data.py**: Fetch data from Firestore
- **fix_firebase_data.py**: Fix and clean Firebase data
- **update_firebase_data.py**: Update existing Firebase data

### Web Templates
- **cybersaathi-v2/templates/**: HTML templates for web interface
  - **index.html**: Main dashboard
  - **article_detail.html**: Article detail view
  - **error.html**: Error page

## Firebase Collections

The system uses the following collections in Firebase Firestore:

- **news** (or hackernews/cybernews): Scraped cybersecurity articles
- **tips**: AI-generated security recommendations with Do's and Don'ts
- **summaries**: AI-generated article summaries

### Document Structure

**Articles:**
```json
{
  "_id": "unique_article_id",
  "title": "Article Title",
  "content": "Article content",
  "url": "https://source-url.com",
  "source": "The Hacker News",
  "date": "2024-01-01",
  "tags": "cybersecurity, malware"
}
```

**Tips:**
```json
{
  "article_id": "unique_article_id",
  "tips": {
    "summary": "Brief overview",
    "dos": ["Do this", "Do that"],
    "donts": ["Don't do this", "Don't do that"]
  }
}
```

## Web Interface

The web interface provides three main views:

1. **Articles**: Shows all scraped articles
2. **Summaries**: Shows AI-generated summaries
3. **CISO Tips**: Shows actionable security recommendations

Click on any article to see its full details, summary, and security tips.

## Workflow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Scraper   │───▶│ Firebase Storage │───▶│  Summarization  │
│ (Selenium)      │    │   (Firestore)    │    │ (Ollama LLM)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Web Interface   │◀───│ Firebase Storage │◀───│  CISO Tips      │
│ (Flask)         │    │   (Firestore)    │    │ (Ollama LLM)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Data Flow
1. **Scraping**: Selenium WebDriver scrapes articles from news sites
2. **Storage**: Articles stored in Firebase Firestore
3. **Export**: Articles exported to markdown format
4. **Summarization**: Ollama processes articles to create summaries
5. **Tips Generation**: Ollama generates actionable security tips
6. **Web Interface**: Flask serves processed content via web dashboard

## Dependencies

Key Python packages (see `requirements.txt`):
- `firebase-admin==6.3.0` - Firebase Firestore integration
- `requests==2.31.0` - HTTP requests
- `beautifulsoup4==4.12.3` - HTML parsing
- `selenium` - Web scraping (ChromeDriver required)
- `ollama==0.1.7` - LLM integration
- `flask==2.3.3` - Web interface
- `colorama==0.4.6` - Terminal colors
- `tqdm==4.66.2` - Progress bars

## Output Files

The system generates timestamped files:
- `cybersecurity_articles_YYYYMMDD_HHMMSS.md` - Scraped articles
- `article_summaries_YYYYMMDD_HHMMSS.md` - AI summaries
- `ciso_tips_YYYYMMDD_HHMMSS.md` - Security recommendations

## Troubleshooting

**Ollama Issues:**
- Ensure Ollama service is running: `ollama serve`
- Check model is available: `ollama list`
- Pull model if missing: `ollama pull llama3.2:1b`

**Selenium Issues:**
- Install ChromeDriver and ensure it's in PATH
- Update Chrome browser to latest version
- Check firewall/antivirus blocking browser automation

**Firebase Issues:**
- Verify service account JSON file path in `.env`
- Check Firebase project has Firestore enabled
- Ensure service account has proper permissions

## License

This project is licensed under the MIT License.

## Acknowledgments

- **Ollama & LLama 3.2** for AI capabilities
- **The Hacker News & CyberNews** for cybersecurity content
- **Firebase Firestore** for cloud database
- **Flask & Selenium** for web technologies 