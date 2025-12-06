
class SessionManager:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.sessions = {}
        
    def load_session(self, user_id):
        """Load session data for a specific user"""
        if user_id in self.sessions:
            # For now return the last session
            return self.sessions[user_id][-1] if self.sessions[user_id] else None
        return None
        
    def log_phase_completion(self, phase, result):
        if self.user_id not in self.sessions:
            self.sessions[self.user_id] = []
        self.sessions[self.user_id].append({"phase": phase, "result": result})
