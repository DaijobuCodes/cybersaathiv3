# CyberSaathi Web Interface with Firebase

This README provides instructions for running the CyberSaathi web interface with Firebase Firestore as the backend database.

## Prerequisites

1. Python 3.7 or higher
2. Firebase project with Firestore database
3. Firebase service account credentials (JSON file)

## Setup

1. Make sure your Firebase service account credentials file is available. The default path is:
   ```
   C:/Users/deevp/Downloads/cybers-b3f99-firebase-adminsdk-fbsvc-6da50d3aa3.json
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Ensure your `.env` file has the correct Firebase settings:
   ```
   FIREBASE_SERVICE_ACCOUNT=C:/Users/deevp/Downloads/cybers-b3f99-firebase-adminsdk-fbsvc-6da50d3aa3.json
   FIREBASE_COLLECTION_HACKERNEWS=hackernews
   FIREBASE_COLLECTION_CYBERNEWS=cybernews
   FIREBASE_COLLECTION_TIPS=tips
   FIREBASE_COLLECTION_SUMMARIES=summaries
   ```

## Data Management

We've created several tools to help you manage your Firebase data:

1. **check_firebase_data.py**: Checks the current data structure in Firebase.
2. **fix_firebase_data.py**: Fixes data structure issues.
3. **update_firebase_data.py**: Adds sample summaries and tips for testing.
4. **fetch_firestore_data.py**: Displays all data in Firebase for debugging.
5. **fix_and_update_firebase.py**: Runs all the above tools in sequence.

For detailed information about these tools, see `FIREBASE_DATA_TOOLS.md`.

## Running the Web Interface

To start the web interface:

```
python web_interface.py
```

This will start a Flask server at http://localhost:5000.

## Troubleshooting

If you encounter issues with displaying tips and summaries:

1. Check your Firebase connection by running:
   ```
   python check_firebase_data.py
   ```

2. If issues are found, fix the data structure:
   ```
   python fix_firebase_data.py
   ```

3. Ensure you have sample data:
   ```
   python update_firebase_data.py
   ```

4. For a comprehensive fix, run:
   ```
   python fix_and_update_firebase.py
   ```

## Data Structure

The data in Firebase should follow this structure:

1. **Articles** are stored in `hackernews` and `cybernews` collections.

2. **Summaries** are stored in the `summaries` collection:
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

3. **Tips** are stored in the `tips` collection with a nested structure:
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