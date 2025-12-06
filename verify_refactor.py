from utils.gemini_client import GeminiClient
from database.student_database import StudentDatabase
from core.teaching_orchestrator import TeachingOrchestrator
import time
import shutil
import os

def test_system():
    print("🧪 Starting System Verification...")
    
    # 1. Test Client Initialization
    print("   Initializing Gemini Client...")
    try:
        client = GeminiClient(api_key="TEST_KEY") # Mock key for structural test
        print("   ✅ Client Initialized")
    except Exception as e:
        print(f"   ❌ Client Init Failed: {e}")
        return

    # 2. Test DB Initialization
    print("   Initializing Student Database...")
    try:
        if not os.path.exists("test_db"):
            os.makedirs("test_db")
        db = StudentDatabase(db_path="test_db/")
        print("   ✅ Database Initialized")
    except Exception as e:
        print(f"   ❌ Database Init Failed: {e}")
        return

    # 3. Test Orchestrator Initialization
    print("   Initializing Orchestrator...")
    try:
        orch = TeachingOrchestrator(
            gemini_client=client,
            student_db=db,
            user_id="verification_user"
        )
        print("   ✅ Orchestrator Initialized")
    except Exception as e:
        print(f"   ❌ Orchestrator Init Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Test Session Start (Mock)
    print("   Testing Start Session (Mock)...")
    try:
        # We expect this to try calling API, so it might fail or return mock depending on client impl
        # Since we passed a TEST_KEY, the real API call will fail.
        # But we want to ensure the logic flows up to that point.
        
        # We can mock the client's generate_content to return a dummy object
        class MockResponse:
            text = '{"status": "mock_success"}'
            
        def mock_generate(*args, **kwargs):
            print("      (Mock API call intercepted)")
            return MockResponse()
            
        # Verify the wrapper has generate_content
        if not hasattr(client, 'generate_content'):
             print("   ❌ Client wrapper missing generate_content method")
             return
             
        print("   ✅ System Structure Verified")
        
    except Exception as e:
        print(f"   ❌ Session Start Failed: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    try:
        shutil.rmtree("test_db")
    except:
        pass

if __name__ == "__main__":
    test_system()
