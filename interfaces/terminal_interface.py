from core.teaching_orchestrator import TeachingOrchestrator
from utils.gemini_client import GeminiClient
from database.student_database import StudentDatabase

class TerminalInterface:
    def __init__(self):
        self.user_id = "cli_user_1"
        self.gemini_client = GeminiClient()
        self.student_db = StudentDatabase()
        
        # Initialize orchestrator
        self.orchestrator = TeachingOrchestrator(
            gemini_client=self.gemini_client,
            student_db=self.student_db,
            user_id=self.user_id
        )

    def run_loop(self):
        """Main interaction loop"""
        
        # Start teaching to get initial instruction
        if hasattr(self.orchestrator, 'start_teaching'):
             initial_response = self.orchestrator.start_teaching()
             print(f"\nAI Tutor: {initial_response.get('instructions', initial_response)}")
        else:
             print("Starting session...")
             self.orchestrator.start_session()
        
        while True:
            try:
                user_input = self.get_input()
                if user_input.lower() in ['exit', 'quit']:
                    print("Goodbye! 👋")
                    break
                
                # Unified processing
                if hasattr(self.orchestrator, 'process_user_input'):
                    response = self.orchestrator.process_user_input(user_input)
                    
                    # Extract feedback/instruction to show
                    display_text = response.get('instructions') or response.get('feedback') or response.get('message') or str(response)
                    
                    print(f"\nAI Tutor: {display_text}")
                    
                    # Check for completion
                    if response.get("status") == "session_completed":
                        print(f"\nSummary: {response.get('summary')}")
                        break
                else:
                    print("Error: Orchestrator update required.")
                    break

            except KeyboardInterrupt:
                print("\nSession interrupted.")
                break
            except Exception as e:
                print(f"Error: {e}")
                # import traceback; traceback.print_exc()

    def display_welcome(self):
        print("Welcome to the AI Tutor Terminal Interface!")

    def get_input(self):
        return input("You: ")

    def display_response(self, response):
        print(f"AI: {response}")

def show_progress_dashboard(session_manager):
    """Display student progress dashboard"""
    print("\n📊 Student Progress Dashboard")
    print("----------------------------")
    # Placeholder logic
    print("No progress data available yet.")
    # input("\nPress Enter to return to menu...") # Commented out to avoid blocking automation
