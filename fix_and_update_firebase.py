#!/usr/bin/env python3
"""
Fix and Update Firebase Data

This script runs all the Firebase data tools in sequence to check,
fix, and update your Firebase Firestore data.
"""

import os
import sys
import time
import subprocess

def run_command(command, description):
    """Run a shell command and return success status"""
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    
    try:
        # Run the command
        result = subprocess.run(command, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Command failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        return False

def main():
    """Run all the Firebase data tools in sequence"""
    print("CyberSaathi Firebase Data Management Tool")
    print("\nThis script will run all the Firebase data tools in sequence to fix and update your data.")
    
    # Ask for confirmation
    print("\nThe following steps will be performed:")
    print("1. Check Firebase data structure")
    print("2. Fix Firebase data structure issues")
    print("3. Update Firebase data with sample data")
    print("4. Verify the updated data")
    
    confirm = input("\nDo you want to continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation canceled.")
        return
    
    # Start timer
    start_time = time.time()
    
    # Step 1: Check Firebase data
    if not run_command("python check_firebase_data.py", "STEP 1: CHECKING FIREBASE DATA"):
        print("\nData check failed. Please fix the issues before continuing.")
        return
    
    # Step 2: Fix Firebase data
    if not run_command("python fix_firebase_data.py", "STEP 2: FIXING FIREBASE DATA"):
        print("\nData fix failed. Please resolve the issues before continuing.")
        return
    
    # Step 3: Update Firebase data
    if not run_command("python update_firebase_data.py", "STEP 3: UPDATING FIREBASE DATA"):
        print("\nData update failed. Please resolve the issues before continuing.")
        return
    
    # Step 4: Verify the updated data
    if not run_command("python fetch_firestore_data.py", "STEP 4: VERIFYING UPDATED DATA"):
        print("\nData verification failed. Please check your Firebase connection.")
        return
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("  ALL OPERATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Total time elapsed: {elapsed_time:.2f} seconds")
    
    # Ask if user wants to start the web interface
    start_web = input("\nDo you want to start the web interface to see the results? (y/n): ")
    if start_web.lower() == 'y':
        print("\nStarting web interface...")
        try:
            subprocess.Popen(["python", "web_interface.py"])
            print("Web interface started. Check http://localhost:5000 in your browser.")
        except Exception as e:
            print(f"Error starting web interface: {str(e)}")
            print("Try running 'python web_interface.py' manually.")
    else:
        print("\nTo start the web interface, run: python web_interface.py")
    
    print("\nDone!")

if __name__ == "__main__":
    main() 