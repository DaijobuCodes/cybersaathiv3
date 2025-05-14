# CyberSaathi Firebase Integration Guide

This guide explains how to properly set up and test the Firebase Firestore integration for CyberSaathi v2.

## Overview of Changes

We made the following changes to improve the Firebase credential management:

1. Created a static `.env.template` file with placeholders for all necessary configuration
2. Improved error handling in `firebase_helper.py` to provide better diagnostics
3. Created `test_firebase_storage.py` to verify Firestore connectivity and data storage
4. Added detailed Firebase setup instructions to the README.md
5. Created a Windows batch script (`setup_firebase.bat`) for easy setup

## Step-by-Step Instructions

### 1. Setting Up Firebase Credentials

1. Run the setup script:
   ```
   setup_firebase.bat
   ```
   Or manually perform these steps:
   ```
   cp .env.template .env
   ```

2. Edit the `.env` file and update the `FIREBASE_SERVICE_ACCOUNT` variable with the full path to your Firebase service account JSON file

3. Make sure all the collection names are set correctly (the defaults should work fine)

### 2. Testing Your Firebase Connection

1. Run the test script:
   ```
   python test_firebase_storage.py
   ```

2. This script will:
   - Verify Firebase initialization
   - Test inserting a document
   - Test retrieving the document
   - Test querying a collection
   - Clean up test documents
   - Test storing in the actual news collection

3. If all tests pass, your Firebase integration is working correctly

### 3. What to Check if Testing Fails

If the test fails, check these common issues:

1. **File Path Issues**:
   - Make sure the file path in `.env` is correct
   - Check for typos or incorrect slashes
   - Ensure the file exists at the specified location

2. **Credential Issues**:
   - Verify the JSON file contains all required fields
   - Check if the service account has the necessary permissions
   - Make sure the project has Firestore enabled

3. **Network Issues**:
   - Check your internet connection
   - Make sure your firewall allows connections to Firebase

## Running the Application

With a properly configured Firebase integration, you can now:

1. Run the complete pipeline:
   ```
   python main.py
   ```

2. Run the web interface only:
   ```
   python launch_web_interface.py
   ```

3. Run the scraper only:
   ```
   python Scraper.py
   ```

## Firebase Collections Used

The system uses these Firestore collections:

1. `hackernews` - Articles from The Hacker News
2. `cybernews` - Articles from Cyber News
3. `tips` - Generated security tips
4. `summaries` - Generated article summaries

## Checking Data in Firebase Console

To verify data is being properly stored:

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Click on "Firestore Database" in the left menu
4. Browse your collections to see stored documents 