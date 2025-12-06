# File: database/student_database.py
"""
Centralized database manager for all 6 docs
Handles JSON file I/O with proper locking and error handling
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

class StudentDatabase:
    def __init__(self, db_path: str = "database/"):
        self.db_path = db_path
        self.locks = {}
        self._initialize_database()
        
        # Define file paths mapping
        self.files_map = {
            "progress": "curriculum_progress.json",
            "logs": "pattern_logs.json",
            "gaps": "knowledge_gaps.json",
            "analogies": "analogies.json",
            "problems": "practical_problems.json",
            "sessions": "user_sessions.json",
            "interactions": "interactions_log.json" # Extra for logging interactions
        }
    
    def _initialize_database(self):
        """Create database files if they don't exist"""
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
            
        files = [
            "curriculum_progress.json",
            "pattern_logs.json", 
            "knowledge_gaps.json",
            "analogies.json",
            "practical_problems.json",
            "user_sessions.json",
            "interactions_log.json"
        ]
        
        for file in files:
            path = os.path.join(self.db_path, file)
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    json.dump({}, f)

    def _get_lock(self, file_name: str):
        """Get or create a lock for a file"""
        if file_name not in self.locks:
            self.locks[file_name] = threading.Lock()
        return self.locks[file_name]

    def _read_doc(self, file_name: str) -> Dict:
        """Thread-safe read"""
        path = os.path.join(self.db_path, file_name)
        with self._get_lock(file_name):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}

    def _write_doc(self, file_name: str, data: Dict):
        """Thread-safe write"""
        path = os.path.join(self.db_path, file_name)
        with self._get_lock(file_name):
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)

    # --- Methods matching User Request and Orchestrator Requirements ---

    def get_user_progress(self, user_id: str) -> Dict:
        """Get user progress from Doc 1"""
        return self._read_doc("curriculum_progress.json").get(user_id, {})
    
    def update_user_progress(self, user_id: str, updates: Dict):
        """Update user progress"""
        data = self._read_doc("curriculum_progress.json")
        if user_id not in data:
            data[user_id] = {}
        data[user_id].update(updates)
        self._write_doc("curriculum_progress.json", data)

    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile (stored in sessions or progress for now)"""
        # Assuming profile might be in sessions or progress. 
        # Using sessions for profile info like name/preferences
        sessions = self._read_doc("user_sessions.json")
        user_sess = sessions.get(user_id, {})
        return user_sess.get("profile", {})

    def log_session_start(self, user_id: str, session_id: str, topic: str, mode: str):
        """Log session start"""
        data = self._read_doc("user_sessions.json")
        if user_id not in data:
            data[user_id] = {"profile": {}, "sessions": []}
        
        data[user_id]["sessions"].append({
            "session_id": session_id,
            "topic": topic,
            "mode": mode,
            "start_time": datetime.now().isoformat(),
            "status": "active"
        })
        self._write_doc("user_sessions.json", data)

    def log_phase_completion(self, user_id: str, phase: str, data: Dict):
        """Log phase completion to appropriate doc"""
        # Also log to a general sessions log or specific phase log
        # For simplicity, we update the latest session in user_sessions
        sessions_data = self._read_doc("user_sessions.json")
        if user_id in sessions_data and sessions_data[user_id]["sessions"]:
            # Append to last session
            last_session = sessions_data[user_id]["sessions"][-1]
            if "phases_completed" not in last_session:
                last_session["phases_completed"] = []
            
            last_session["phases_completed"].append({
                "phase": phase,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            self._write_doc("user_sessions.json", sessions_data)
        
        # Helper to log logging specific data (e.g. gaps to gaps file)
        if phase == "priming":
             # Maybe log gaps here?
             pass
        elif phase == "relational_thinking":
            # Log patterns?
            logs = self._read_doc("pattern_logs.json")
            if user_id not in logs: logs[user_id] = []
            logs[user_id].append(data)
            self._write_doc("pattern_logs.json", logs)

    def log_session_completion(self, user_id: str, session_id: str, summary: Dict):
        """Log session completion"""
        data = self._read_doc("user_sessions.json")
        if user_id in data:
            for session in data[user_id]["sessions"]:
                if session["session_id"] == session_id:
                    session["status"] = "completed"
                    session["summary"] = summary
                    session["end_time"] = datetime.now().isoformat()
                    break
            self._write_doc("user_sessions.json", data)
            
    def save_session_state(self, user_id: str, session_id: str, state: Dict):
        """Save paused session state"""
        data = self._read_doc("user_sessions.json")
        if user_id in data:
            for session in data[user_id]["sessions"]:
                if session["session_id"] == session_id:
                     session["saved_state"] = state
                     break
            self._write_doc("user_sessions.json", data)

    def log_interaction(self, user_id: str, interaction: Dict):
        """Log granular interaction"""
        data = self._read_doc("interactions_log.json")
        if user_id not in data:
            data[user_id] = []
        data[user_id].append(interaction)
        self._write_doc("interactions_log.json", data)

    def get_knowledge_gaps(self, user_id: str) -> List[Dict]:
        """Get knowledge gaps from Doc 4"""
        return self._read_doc("knowledge_gaps.json").get(user_id, [])
    
    def log_knowledge_gap(self, user_id: str, gap_data: Dict):
        """Log a new knowledge gap"""
        data = self._read_doc("knowledge_gaps.json")
        if user_id not in data:
            data[user_id] = []
        data[user_id].append(gap_data)
        self._write_doc("knowledge_gaps.json", data)

    def log_analogy(self, user_id: str, analogy_data: Dict):
        """Log analogy to Doc 5"""
        data = self._read_doc("analogies.json")
        if user_id not in data:
            data[user_id] = []
        data[user_id].append(analogy_data)
        self._write_doc("analogies.json", data)

    # --- Phase 4 Requirements ---
    
    def get_learning_history(self, user_id: str) -> Dict[str, Any]:
        """Aggregate learning history for context"""
        progress = self.get_user_progress(user_id)
        gaps = self.get_knowledge_gaps(user_id)
        
        return {
            "completed_modules": progress.get("completed_modules", []),
            "current_topic": progress.get("current_topic"),
            "knowledge_gaps_count": len(gaps)
        }

    def log_practical_problem(self, user_id: str, problem_data: Dict):
        """Log a practical problem"""
        data = self._read_doc("practical_problems.json")
        if user_id not in data:
            data[user_id] = []
        data[user_id].append(problem_data)
        self._write_doc("practical_problems.json", data)
