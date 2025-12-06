import os
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from core.teaching_orchestrator import TeachingOrchestrator, SessionState
# Assuming Gemini credentials are env vars or handled internally by the client helper
from google import genai
from utils.gemini_client import GeminiClient

app = FastAPI(title="AI Tutor API")

# Enable CORS for frontend dev (if running separately, though we serve static now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance (simulated session)
# In real prod, this would be managed per user/session key
orchestrator: Optional[TeachingOrchestrator] = None

class ChatRequest(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    data: Optional[Dict] = {}

@app.on_event("startup")
async def startup_event():
    global orchestrator
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("WARNING: GEMINI_API_KEY not found. API functionality will be limited.")
        client = None
    else:
        client = genai.Client(api_key=api_key)
    
    # Initialize orchestrator
    # We might want to delay this until user login in a real app
    from database.student_database import StudentDatabase
    student_db = StudentDatabase()
    
    orchestrator = TeachingOrchestrator(
        gemini_client=client, 
        student_db=student_db,
        user_id="web_user_1"
    )
    # Start/Prime the session
    # orchestrator.start_teaching() # Usually starts the first phase

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    user_input = request.message
    
    # Use the unified process_user_input method
    result = orchestrator.process_user_input(user_input)
    
    # Normalize response
    response_text = result.get("instructions") or result.get("message") or result.get("feedback") or str(result)
    phase = orchestrator.current_state.value if hasattr(orchestrator, 'current_state') else "unknown"
    
    return {
        "response": response_text,
        "phase": phase,
        "data": result
    }

@app.get("/api/state")
async def get_state():
    if not orchestrator:
         return {"status": "not_initialized"}
    
    return {
        "current_phase": orchestrator.current_phase,
        "module": orchestrator.current_module,
        "user_id": orchestrator.user_id
    }

# Endpoint for code execution/preview (mock for security in this demo)
class CodeExecutionRequest(BaseModel):
    code: str
    language: str

@app.post("/api/execute")
async def execute_code(request: CodeExecutionRequest):
    # In a real tutor, this might run tests or validate HTML structure
    # For the preview window, the frontend usually renders HTML/CSS directly.
    # This endpoint might just be for "grading" or "analysis" via LLM.
    
    return {
        "status": "success",
        "analysis": "Code received. Preview should update on client side."
    }

# Serve Static Files (Frontend)
# Must be last to not override API routes
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

def run_server():
    print("Starting AI Tutor Web Server at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run_server()
