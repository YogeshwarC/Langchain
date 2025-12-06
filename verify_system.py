
import sys
import os
import json
import unittest
# Add project root to path
sys.path.append(os.getcwd())

from core.teaching_orchestrator import TeachingOrchestrator, SessionState
from database.student_database import StudentDatabase
from utils.gemini_client import GeminiClient

# --- MOCKS ---
# --- MOCKS ---
class MockResponse:
    text = json.dumps({
        "examples": [
            {
                "code": ".test { color: red; }", 
                "description": "Test Example 1",
                "visual_description": "Red text"
            },
            {
                "code": "#unique { color: blue; }", 
                "description": "Test Example 2",
                "visual_description": "Blue text"
            }
        ],
        "pattern_summary": "Specificity Test Pattern",
        "score": 5,
        "feedback": "Perfect score!",
        "explanation": "Test explanation",
        "visual_aids": [{"visual_description": "A visual aid"}]
    })

class MockModels:
    def generate_content(self, model, contents, config=None):
        return MockResponse()

class MockGeminiClient:
    def __init__(self):
        self.models = MockModels()

# --- TESTS ---
class TestSystemIntegrity(unittest.TestCase):
    def setUp(self):
        self.db = StudentDatabase()
        self.client = MockGeminiClient()
        self.orchestrator = TeachingOrchestrator(
            gemini_client=self.client,
            student_db=self.db,
            user_id="test_user_verification"
        )

    def test_01_priming_transition_and_flattening(self):
        """Test that user input in Priming transitions to Relational Thinking AND data is flattened."""
        print("\n🧪 TEST 1: Priming -> Relational Thinking Transition & Flattening")
        
        # Manually set state to Priming with some data (simulating end of lecture)
        self.orchestrator.current_state = SessionState.PRIMING
        self.orchestrator.phase_data["priming"] = {"some": "data"}
        
        # User input should trigger transition
        response = self.orchestrator.process_user_input("Ready")
        
        # Check State Transition
        self.assertEqual(self.orchestrator.current_state, SessionState.RELATIONAL_THINKING, 
                         "❌ Failed to transition from PRIMING to RELATIONAL_THINKING")
        print("   ✅ Transition Successful")
        
        # Check Data Flattening (Crucial for Web Interface)
        # The mock returns 'examples' inside the 'data' key mainly, but our fix should flatten it.
        # Note: In RelationalThinkingPhase.execute_phase(), it returns a dict with "examples".
        # process_user_input should make sure these are at top level.
        
        self.assertIn("examples", response, "❌ 'examples' key missing from top-level response (Flattening failed)")
        self.assertIsInstance(response["examples"], list, "❌ 'examples' is not a list")
        self.assertEqual(len(response["examples"]), 2, "❌ Incorrect number of examples")
        print("   ✅ Data Flattening Successful (Examples found at root)")

    def test_02_visual_aids_presence(self):
        """Test that visual aids are also flattened and present."""
        print("\n🧪 TEST 2: Visual Aids Integrity")
        
        # Properly initialize the phase via the resumption logic which creates the object
        self.orchestrator.current_state = SessionState.RELATIONAL_THINKING
        self.orchestrator.relational_thinking = None # Ensure it's empty
        self.orchestrator.phase_data["priming"] = {"some": "data"} # Req for init
        
        # We need to call _resume_relational_thinking to create the object and get the first response
        # trying to call process_user_input directly when object is None will error as designed.
        # But we want to simulate the flow where it might be called.
        # Actually, process_user_input calls _process_relational_input, which fails if content is None.
        # So we must manually set it up or call the method that sets it up.
        
        response = self.orchestrator._resume_relational_thinking()
        
        # Now flatten it manually as process_user_input would, or better yet,
        # let's test process_user_input BUT we need to ensure the object exists first?
        # No, _resume_relational_thinking returns the dict we want to check for flattening.
        # Wait, the flattening happens in process_user_input.
        
        # So:
        # 1. Initialize object
        self.orchestrator._resume_relational_thinking()
        
        # 2. Now call process_user_input with some input to simulate next step
        # Note: calling _resume... executes the phase and returns the "Setup" state.
        # process_user_input checks input.
        
        # Let's just check the response of _resume_relational_thinking AND flattening.
        # Since _resume... is called by process_user_input during transition (Test 1), 
        # Test 1 actually covers the Flattening of the Initial Response.
        
        # Let's simple check if visual aids are in the response of Test 1.
        pass # Merged into Test 1 or re-run transition
        
        # RERUN TRANSITION logic for visual aids check:
        self.orchestrator.current_state = SessionState.PRIMING
        self.orchestrator.relational_thinking = None
        response = self.orchestrator.process_user_input("Go")
        
        self.assertIn("visual_aids", response, "❌ 'visual_aids' missing from top-level response")
        print("   ✅ Visual Aids Flattened Successfully")

if __name__ == "__main__":
    unittest.main()
