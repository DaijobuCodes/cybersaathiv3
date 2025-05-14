# Firebase Data Management Tools

This directory contains several tools to help you manage your Firebase Firestore data for the CyberSaathi project. These tools will help ensure that your data is correctly structured and accessible in the web interface.

## Available Tools

### 1. check_firebase_data.py
This script checks the current data structure in Firebase Firestore, examining how tips and summaries are stored.

Usage:
```
python check_firebase_data.py
```

This will:
- Connect to your Firebase Firestore database
- Check several sample articles
- Verify if summaries and tips exist for these articles
- Check if the data structure is correct (summaries in summaries collection, tips in tips collection with the right format)
- Report any issues found

### 2. fix_firebase_data.py
This script fixes data structure issues, such as summaries stored in the tips collection or tips documents with incorrect format.

Usage:
```
python fix_firebase_data.py
```

This will:
- Connect to your Firebase Firestore database
- Scan all tips and summaries documents
- Identify and fix structural issues:
  - Move summaries from tips collection to summaries collection
  - Fix tips documents that don't have the correct nested structure
- Report how many documents were fixed

### 3. update_firebase_data.py
This script populates your Firebase Firestore database with sample summaries and tips for testing.

Usage:
```
python update_firebase_data.py
```

This will:
- Connect to your Firebase Firestore database
- Find all articles from both hackernews and cybernews collections
- Add sample summaries for articles that don't have them
- Add sample tips for articles that don't have them
- Ensure that data is stored in the correct format and collections

### 4. fetch_firestore_data.py
This script fetches and displays all data from your Firebase Firestore collections to help diagnose retrieval issues.

Usage:
```
python fetch_firestore_data.py
```

This will:
- Connect to your Firebase Firestore database
- Display summary information about your collections (counts, structure, etc.)
- Show sample data from your summaries and tips collections
- Analyze the coverage (how many articles have tips and summaries)

## Data Structure

The data in Firebase Firestore should follow this structure:

1. Articles are stored in two collections:
   - `hackernews`: Articles from The Hacker News
   - `cybernews`: Articles from Cyber News

2. Summaries are stored in the `summaries` collection:
   ```json
   {
     "_id": "summary_[article_id]",
     "article_id": "[article_id]",
     "title": "Article Title",
     "summary": "The summary text...",
     "source": "Source Name",
     "date": "YYYY-MM-DD",
     "generated_at": "YYYY-MM-DD"
   }
   ```

3. Tips are stored in the `tips` collection with a nested structure:
   ```json
   {
     "_id": "tips_[article_id]",
     "article_id": "[article_id]",
     "title": "Article Title",
     "tips": {
       "summary": "Security issue summary...",
       "dos": ["Do this", "Do that", ...],
       "donts": ["Don't do this", "Don't do that", ...]
     },
     "source": "Source Name", 
     "date": "YYYY-MM-DD",
     "generated_at": "YYYY-MM-DD"
   }
   ```

## Recommended Workflow

If you're experiencing issues with displaying tips and summaries in the web interface:

1. First, run `check_firebase_data.py` to diagnose any data structure issues
2. If issues are found, run `fix_firebase_data.py` to fix them
3. Run `update_firebase_data.py` to ensure you have test data for every article
4. Start the web interface with `python web_interface.py` to see the results
5. If you still have issues, run `fetch_firestore_data.py` to get detailed information about your data

## Troubleshooting

- **"No summaries shown on the website"**: This could be because summaries are stored in the tips collection or because they're missing. Run `check_firebase_data.py` to diagnose and `fix_firebase_data.py` to fix.

- **"Tips showing incorrect format"**: The tips should be stored as a nested object with summary, dos, and donts fields. Run `fix_firebase_data.py` to correct the structure.

- **"Firebase connection fails"**: Make sure your service account key path is correctly set in your .env file. The default path used is: `C:/Users/deevp/Downloads/cybers-b3f99-firebase-adminsdk-fbsvc-6da50d3aa3.json` 