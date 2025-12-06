import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# We remove the hardcoded Enums! 
# The AI will generate these dynamically.

@dataclass
class DiscoveryAttempt:
    attempt_number: int
    user_input: str
    score: int
    feedback: str

class RelationalThinkingPhase:
    """
    Dynamic Phase 2: Relational Thinking
    Now capable of teaching ANY topic by asking the AI to define the pattern first.
    """
    
    def __init__(self, gemini_client, topic_name: str, user_id: str):
        self.client = gemini_client
        self.topic_name = topic_name # e.g. "CSS Grid", "Python Lists", "Rust Ownership"
        self.user_id = user_id
        
        # Load Prompts (The Intelligence)
        self.prompts = self._load_prompts()
        
        # State
        self.current_pattern_meta = {} # Populated dynamically by AI
        self.code_examples = []
        self.attempts = []
        self.is_complete = False
        
        # Added for compatibility with Orchestrator state checks
        self.state = "setup_complete" # simulating enum state for now

    def _load_prompts(self):
        """Load the JSON prompts that define the AI's personality"""
        try:
            # Adjust path as needed for your project structure
            path = Path(__file__).parent.parent / "prompts" / "discovery_prompts.json"
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading prompts: {e}")
            return {}

    def execute_phase(self):
        """
        Step 1: The "Cold Start" - AI identifies what to teach.
        """
        print(f"\n🧠 AI ANALYZING TOPIC: {self.topic_name}...")
        
        # 1. Ask AI to identify the pattern (Dynamic Intelligence)
        # We replace the hardcoded dictionary lookup with an LLM Call
        pattern_data = self._identify_pattern_dynamically()
        self.current_pattern_meta = pattern_data
        
        print(f"   Target Pattern: {pattern_data.get('name', 'Unknown')}")
        print(f"   Mental Model: {pattern_data.get('mental_model', 'Unknown')}")
        
        # 2. Ask AI to generate examples based on that pattern
        self.code_examples = self._generate_dynamic_examples(pattern_data)
        
        # 3. Present to User
        # Update internal state
        self.state = "awaiting_attempt"
        
        return {
            "status": "ready",
            "pattern_hidden": True, # We don't tell the user the name yet!
            "examples": self.code_examples,
            "instructions": "Look at these 3 examples. They look different, but they all follow the EXACT SAME logic. What is the hidden rule?",
            # Added for API Server compatibility (so it can display 'question')
            "question": "Look at these 3 examples. They look different, but they all follow the EXACT SAME logic. What is the hidden rule?"
        }

    def _identify_pattern_dynamically(self) -> Dict:
        """
        The Magic: Ask Gemini to define the curriculum on the fly.
        """
        prompt_template = self.prompts["identify_pattern"]["template"]
        final_prompt = prompt_template.format(topic=self.topic_name)
        
        try:
            # Call Gemini
            # Using the client.generate_content method directly as per updated client wrapper usage
            response = self.client.generate_content(final_prompt)
            # Parse JSON (Assuming your client returns text, we parse it)
            if response and hasattr(response, 'text'):
                return json.loads(self._clean_json(response.text))
            return json.loads(self._clean_json(str(response)))
        except Exception as e:
            print(f"AI Generation Failed: {e}")
            # Fallback for safety
            return {
                "name": "Fundamental Logic",
                "description": "How the code executes",
                "mental_model": "Input -> Process -> Output",
                "misconceptions": []
            }

    def _generate_dynamic_examples(self, pattern_data) -> List[Dict]:
        """
        Ask Gemini to create specific examples for the discovered pattern.
        """
        prompt_template = self.prompts["generate_examples"]["template"]
        final_prompt = prompt_template.format(
            pattern_name=pattern_data.get('name', 'General Logic'),
            pattern_desc=pattern_data.get('description', 'Standard behavior')
        )
        
        try:
            response = self.client.generate_content(final_prompt)
            text = response.text if response and hasattr(response, 'text') else str(response)
            data = json.loads(self._clean_json(text))
            return data.get("examples", [])
        except Exception as e:
            print(f"Example Generation Failed: {e}")
            return []

    def process_user_attempt(self, user_input: str, attempt_time: int = 0) -> Dict:
        """
        Evaluate user input against the AI-defined pattern.
        """
        prompt_template = self.prompts["evaluate_attempt"]["template"]
        final_prompt = prompt_template.format(
            pattern_name=self.current_pattern_meta.get('name', 'Unknown'),
            mental_model=self.current_pattern_meta.get('mental_model', 'Unknown'),
            user_input=user_input
        )
        
        try:
            response = self.client.generate_content(final_prompt)
            text = response.text if response and hasattr(response, 'text') else str(response)
            eval_data = json.loads(self._clean_json(text))
            
            score = eval_data.get("score", 0)
            
            # Log attempt
            self.attempts.append(DiscoveryAttempt(
                attempt_number=len(self.attempts)+1,
                user_input=user_input,
                score=score,
                feedback=eval_data.get("feedback", "")
            ))
            
            if score >= 4:
                self.is_complete = True
                self.state = "pattern_resolved"
                return {
                    "status": "pattern_resolved",
                    "score": score,
                    "feedback": f"Correct! The pattern was {self.current_pattern_meta.get('name')}.",
                    "mental_model": self.current_pattern_meta.get('mental_model'),
                    "pattern_name": self.current_pattern_meta.get('name'),
                    "user_discovered": True,
                    "discovery_score": score
                }
            else:
                return {
                    "status": "try_again",
                    "score": score,
                    "feedback": eval_data.get("feedback", "Keep trying!"),
                    "hint": "Try to focus on *why* the code behaves that way."
                }
        except Exception as e:
             print(f"Evaluation Failed: {e}")
             return {
                 "status": "error",
                 "feedback": "I'm having trouble evaluating that right now. Could you try rephrasing?"
             }

    def _clean_json(self, text: str) -> str:
        """Helper to clean markdown and extract JSON from responses"""
        text = text.strip()
        
        # Remove markdown fences first if present
        if "```json" in text:
            parts = text.split("```json")
            if len(parts) > 1:
                text = parts[1].split("```")[0]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) > 1:
                text = parts[1]
                
        # Find the first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            return text[start:end+1]
            
        return text.strip()