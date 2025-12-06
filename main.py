#!/usr/bin/env python3
"""
AI Web Development Tutor - Main Entry Point
Orchestrates the complete teaching system
"""
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from utils.gemini_client import GeminiClient
from database.student_database import StudentDatabase
from utils.logging_manager import setup_logging

def initialize_system():
    """Initialize all system components"""
    
    # 1. Load environment
    load_dotenv()
    
    # 2. Initialize Gemini Client Wrapper
    gemini_client = GeminiClient()
    
    # 3. Setup logging
    logger = setup_logging()
    
    # 4. Initialize Student Database
    student_db = StudentDatabase()
    
    return {
        "client": gemini_client,
        "logger": logger,
        "student_db": student_db
    }

def start_new_session(system_components, user_id=None):
    """Start a new teaching session for a user"""
    
    # Create or retrieve user ID
    if not user_id:
        user_id = input("Enter your name or user ID: ").strip()
        if not user_id:
            user_id = f"user_{int(time.time())}"
    
    # Create orchestrator for this user
    orchestrator = TeachingOrchestrator(
        gemini_client=system_components["client"],
        user_id=user_id,
        student_db=system_components["student_db"]
    )
    
    # Start terminal interface
    terminal = TerminalInterface(orchestrator)
    terminal.start_session()

def resume_session(system_components, user_id):
    """Resume existing session"""
    # Check if user exists in DB or just start new session logic that handles resumption
    # For now, we trust the Orchestrator to handle state loading
    
    orchestrator = TeachingOrchestrator(
        gemini_client=system_components["client"],
        user_id=user_id,
        student_db=system_components["student_db"]
    )
    
    terminal = TerminalInterface(orchestrator)
    terminal.resume_session()

def configure_settings(system):
    print("Settings configuration not implemented yet.")

def main():
    """Main entry point with menu"""
    print("🎓 AI Web Development Tutor")
    print("=" * 50)
    
    # Initialize system once
    system = initialize_system()
    
    while True:
        print("\n📋 Main Menu:")
        print("1. Start new learning session")
        print("2. Resume previous session")
        print("3. View progress dashboard")
        print("4. Configure settings")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            start_new_session(system)
        elif choice == "2":
            user_id = input("Enter your user ID: ").strip()
            resume_session(system, user_id)
        elif choice == "3":
            # Show progress dashboard
            from interfaces.terminal_interface import show_progress_dashboard
            show_progress_dashboard(system["student_db"])
        elif choice == "4":
            # Configuration menu
            configure_settings(system)
        elif choice == "5":
            print("👋 Goodbye! Keep learning!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
