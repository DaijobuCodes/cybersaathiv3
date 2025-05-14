#!/usr/bin/env python3
"""
Launch CyberSaathi Web Interface

This script launches just the web interface to display existing data
without running the full scraping and processing pipeline.
"""

import os
import sys
import argparse
import webbrowser
import threading
from web_interface import run_web_interface

def main():
    parser = argparse.ArgumentParser(description="Launch CyberSaathi Web Interface")
    parser.add_argument("--port", type=int, default=5000,
                      help="Port to run the web interface on (default: 5000)")
    parser.add_argument("--debug", action="store_true",
                      help="Run the web interface in debug mode")
    parser.add_argument("--no-browser", action="store_true",
                      help="Do not automatically open the browser")
    
    args = parser.parse_args()
    
    print("\n=================================================")
    print("       CyberSaathi Web Interface Launcher")
    print("=================================================\n")
    
    # Get the absolute path to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Check if we're in the right directory
    if not os.path.exists(os.path.join(project_root, "templates")):
        print("Warning: Templates directory not found.")
        print("The web interface will create it automatically.\n")
    
    print(f"Web interface will be available at: http://localhost:{args.port}")
    
    # Open browser in a separate thread after a short delay
    if not args.no_browser:
        threading.Timer(2.0, lambda: webbrowser.open(f'http://localhost:{args.port}')).start()
    
    # Start the Flask web interface
    run_web_interface(port=args.port, debug=args.debug)

if __name__ == "__main__":
    main() 