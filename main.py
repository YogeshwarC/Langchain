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
from google import genai

from core.teaching_orchestrator import TeachingOrchestrator
from interfaces.terminal_interface import TerminalInterface
from utils.logging_manager import setup_logging
from database.session_store import SessionManager

def initialize_system():
    """Initialize all system components"""
    
    # 1. Load environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        # For development/testing purposes, we might want to continue or exit. 
        # Given the previous context, let's print a warning but allow exit.
        # sys.exit(1)
        pass # Allow continuing for structure verification tasks if key isn't set yet
    
    # 2. Initialize Gemini
    if api_key:
        gemini_client = genai.Client(api_key=api_key)
    else:
        gemini_client = None
    
    # 3. Setup logging
    logger = setup_logging()
    
    # 4. Initialize session manager
    session_manager = SessionManager()
    
    return {
        "client": gemini_client,
        "logger": logger,
        "session_manager": session_manager
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
        session_manager=system_components["session_manager"],
        logger=system_components["logger"]
    )
    
    # Start terminal interface
    terminal = TerminalInterface(orchestrator)
    terminal.start_session()

def resume_session(system_components, user_id):
    """Resume existing session"""
    session_data = system_components["session_manager"].load_session(user_id)
    
    if not session_data:
        print(f"❌ No session found for {user_id}")
        return start_new_session(system_components)
    
    # Recreate orchestrator with saved state
    orchestrator = TeachingOrchestrator(
        gemini_client=system_components["client"],
        user_id=user_id,
        session_manager=system_components["session_manager"],
        logger=system_components["logger"],
        restore_from=session_data
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
            show_progress_dashboard(system["session_manager"])
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
