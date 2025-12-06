from utils.gemini_client import GeminiClient
from database.student_database import StudentDatabase
from core.teaching_orchestrator import TeachingOrchestrator, SessionState

def test_topic_selection():
    print("🧪 Testing Topic Selection Logic...")
    
    # 1. Initialize
    client = GeminiClient(api_key="TEST_KEY")
    db = StudentDatabase(db_path="test_db/")
    orch = TeachingOrchestrator(client, db, "topic_test_user")
    
    # 2. Simulate Start
    orch.current_state = SessionState.TOPIC_SELECTION
    
    # 3. Test Invalid Input
    print("   Testing Invalid Topic...")
    response = orch.process_user_input("invalid_topic")
    if response.get("status") == "topic_selection_retry":
        print("   ✅ Correctly handled invalid topic")
    else:
        print(f"   ❌ Failed invalid topic test: {response}")

    # 4. Test Valid Input (CSS Basics)
    print("   Testing Valid Topic (css basics)...")
    
    # Mock priming start to avoid API call errors in test
    def mock_start_priming():
        return {"status": "priming_started", "message": "Mock priming"}
    orch._start_priming_phase = mock_start_priming
    
    response = orch.process_user_input("css basics")
    
    if orch.current_topic.value == "css_basics":
        print("   ✅ Topic set correctly")
    else:
        print(f"   ❌ Topic verify failed: {orch.current_topic}")
        
    print("   ✅ Topic Selection Test Complete")

if __name__ == "__main__":
    test_topic_selection()
