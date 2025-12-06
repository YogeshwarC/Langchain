
import sys
import os
import json
# Add project root to path
sys.path.append(os.getcwd())

from core.teaching_orchestrator import TeachingOrchestrator, SessionState
from database.student_database import StudentDatabase
from utils.gemini_client import GeminiClient

# Mock Gemini Client to avoid API calls/costs during debug
class MockGeminiClient(GeminiClient):
    def generate_content(self, model, contents, config=None):
        class MockResponse:
            text = json.dumps({
                "examples": [
                    {"code": ".a { color: red; }", "description": "Example 1"},
                    {"code": "#b { color: blue; }", "description": "Example 2"},
                    {"code": "div { color: green; }", "description": "Example 3"}
                ],
                "pattern_summary": "Specificity rules",
                "score": 5,
                "feedback": "Great job!",
                "explanation": "Test explanation"
            })
        return MockResponse()

def debug_response_structure():
    db = StudentDatabase()
    client = MockGeminiClient()
    
    orchestrator = TeachingOrchestrator(
        gemini_client=client,
        student_db=db,
        user_id="debug_user"
    )
    
    # 1. Simulate Priming Completion
    orchestrator.current_state = SessionState.PRIMING
    orchestrator.phase_data["priming"] = {"terminology": [{"term": "selector"}]}
    
    # 2. Simulate User "Hi" to trigger transition to Relational Thinking
    print("\n--- TRIGGERING TRANSITION TO RELATIONAL THINKING ---")
    response_1 = orchestrator.process_user_input("Hi")
    
    print("\n--- RESPONSE KEYS ---")
    print(json.dumps(response_1, indent=2, default=str))
    
    # Check if 'examples' is at top level or nested
    if "examples" in response_1:
        print("\n✅ 'examples' found at top level.")
    elif "data" in response_1 and "examples" in response_1["data"]:
        print("\n❌ 'examples' is NESTED inside 'data'. API Server will miss this!")
    else:
        print("\n❌ 'examples' NOT FOUND anywhere.")

if __name__ == "__main__":
    debug_response_structure()
