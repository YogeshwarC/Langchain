"""
INTERLEAVING & CURIOSITY PHASE (Phase 3)
Implements analogy generation and "what-if" edge case scenarios
Integrates current topic with past knowledge gaps
"""
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from google import genai
from google.genai import types

from core.priming_phase import ModuleTopic
from database.student_database import StudentDatabase

class InterleavingState(Enum):
    """Tracks state in interleaving phase"""
    ANALOGY_GENERATION = "analogy_generation"
    ANALOGY_EVALUATION = "analogy_evaluation"
    WHAT_IF_SETUP = "what_if_setup"
    WHAT_IF_SCENARIO = "what_if_scenario"
    COMPOUND_QUESTION = "compound_question"
    COMPLETE = "complete"

@dataclass
class UserAnalogy:
    """Represents user-created analogy"""
    analogy_id: str
    analogy_text: str
    pattern_relation: str
    creativity_score: int = 0  # 0-5
    accuracy_score: int = 0  # 0-5
    memorability_score: int = 0  # 0-5
    overall_score: int = 0  # 0-5
    feedback: str = ""
    timestamp: str = ""
    improvements_suggested: List[str] = field(default_factory=list)

@dataclass
class WhatIfScenario:
    """Represents edge case scenario"""
    scenario_id: str
    scenario_text: str
    edge_case_type: str  # browser, screen_size, content, performance, accessibility
    realism_score: int = 0  # 0-5
    impact_score: int = 0  # 0-5
    creativity_score: int = 0  # 0-5
    overall_score: int = 0  # 0-5
    solution_hint: str = ""
    timestamp: str = ""

@dataclass
class CompoundQuestion:
    """Represents compound question mixing current and past topics"""
    question_id: str
    question_text: str
    current_topic: str
    past_topic: str
    knowledge_gap_targeted: str
    difficulty: str  # easy, medium, hard
    expected_answer_elements: List[str]
    scoring_rubric: Dict[str, int]

class InterleavingPhase:
    """
    Implements Phase 3: Interleaving & Curiosity
    1. Analogy Generation: Create real-world analogies
    2. "What-If" Engine: Explore edge cases
    3. Compound Questions: Integrate current topic with past knowledge gaps
    """
    
    def __init__(
        self,
        gemini_client: genai.Client,
        topic: ModuleTopic,
        pattern_discovery_data: Dict,  # From Phase 2
        user_id: str,
        student_db: StudentDatabase,
        thinking_level: str = "high"
    ):
        """
        Initialize Interleaving Phase
        
        Args:
            gemini_client: Initialized Gemini client
            topic: Current module topic
            pattern_discovery_data: Results from RelationalThinkingPhase
            user_id: Unique user identifier
            student_db: StudentDatabase instance for accessing knowledge gaps
            thinking_level: "high" or "low" for Gemini 3 Pro
        """
        self.client = gemini_client
        self.topic = topic
        self.pattern_data = pattern_discovery_data
        self.user_id = user_id
        self.db = student_db
        self.thinking_level = thinking_level
        
        # State tracking
        self.state = InterleavingState.ANALOGY_GENERATION
        self.completed_steps = set()
        
        # Data storage
        self.user_analogies: List[UserAnalogy] = []
        self.what_if_scenarios: List[WhatIfScenario] = []
        self.compound_questions: List[CompoundQuestion] = []
        self.compound_answers: List[Dict] = []
        
        # Get knowledge gaps for this user (from Database Doc 4)
        self.knowledge_gaps = self.db.get_knowledge_gaps(self.user_id)
        
        # Phase log (for Database Doc 5 and integration)
        self.phase_log = {
            "phase": "interleaving",
            "topic": topic.value,
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "analogies_created": [],
            "what_if_scenarios": [],
            "compound_questions_asked": [],
            "interleaving_score": 0,
            "curiosity_score": 0
        }
        
        # Model selection
        self.model = "gemini-1.5-pro-latest"  # Change to gemini-3-pro-preview if available
        
        # Load topic-specific interleaving configurations
        self._load_topic_configurations()
    
    def _load_topic_configurations(self):
        """Load topic-specific interleaving strategies"""
        self.topic_configs = {
            ModuleTopic.CSS_BASICS: {
                "analogy_domains": ["traffic rules", "office hierarchy", "sports teams"],
                "what_if_focus": ["browser quirks", "user stylesheets", "print styles"],
                "compound_integration": ["HTML structure", "browser rendering", "performance"]
            },
            ModuleTopic.NEUMORPHISM: {
                "analogy_domains": ["physical materials", "lighting design", "architecture"],
                "what_if_focus": ["color blindness", "high contrast mode", "mobile screens"],
                "compound_integration": ["CSS box model", "accessibility", "responsive design"]
            },
            ModuleTopic.CSS_ANIMATIONS: {
                "analogy_domains": ["dance choreography", "film editing", "music composition"],
                "what_if_focus": ["low-power devices", "motion sensitivity", "browser support"],
                "compound_integration": ["JavaScript events", "performance budgets", "user experience"]
            }
        }
        
        self.current_config = self.topic_configs.get(
            self.topic,
            self.topic_configs[ModuleTopic.CSS_BASICS]
        )
    
    def execute_phase(self) -> Dict[str, Any]:
        """
        Main entry point: executes complete interleaving phase
        
        Returns:
            Dict with phase start information
        """
        print(f"\n{'='*60}")
        print(f"PHASE 3: INTERLEAVING & CURIOSITY - {self.topic.value.upper()}")
        print(f"{'='*60}")
        
        # Start with analogy generation
        analogy_start = self._start_analogy_generation()
        
        return {
            "status": "interleaving_started",
            "state": self.state.value,
            "current_step": "analogy_generation",
            "instructions": analogy_start["instructions"],
            "prompt": analogy_start["prompt"],
            "evaluation_criteria": analogy_start["evaluation_criteria"],
            "example": analogy_start["example"],
            "next_action": "submit_analogy",
            "steps_remaining": ["analogy_evaluation", "what_if_scenario", "compound_question"]
        }
    
    def _start_analogy_generation(self) -> Dict[str, Any]:
        """
        Step 3.1: Ask user to create real-world analogy
        """
        self.state = InterleavingState.ANALOGY_GENERATION
        
        # Get pattern information from Phase 2
        pattern_name = self.pattern_data.get("pattern_name", "the pattern")
        pattern_description = self.pattern_data.get("pattern_description", "")
        mental_model = self.pattern_data.get("mental_model", "")
        
        # Select analogy domain
        analogy_domains = self.current_config["analogy_domains"]
        selected_domain = analogy_domains[0]  # Could randomize
        
        # Get past analogies from Database Doc 5
        past_analogies = self.db.get_analogies(self.user_id)
        past_examples = [a.get("analogy_text", "")[:100] for a in past_analogies[:2]]
        
        prompt = f"""
        Create a prompt asking the student to create a real-world analogy for:
        
        PATTERN: {pattern_name}
        DESCRIPTION: {pattern_description}
        MENTAL MODEL: {mental_model}
        
        The student should:
        1. Choose a real-world domain (e.g., {', '.join(analogy_domains)})
        2. Create an analogy that captures the ESSENCE of the pattern
        3. Explain how each part maps to the technical concept
        
        Provide:
        1. The main prompt/question
        2. An example analogy (for reference)
        3. Clear evaluation criteria
        4. Tips for creating effective analogies
        
        Past analogies created by this student (for context):
        {json.dumps(past_examples, indent=2)}
        
        Return JSON.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level=self.thinking_level
                    )
                )
            )
            analogy_data = json.loads(response.text)
            
            return {
                "instructions": "Create a real-world analogy that helps remember this pattern.",
                "prompt": analogy_data.get("prompt", 
                    f"Create a real-world analogy for '{pattern_name}' that captures its essence."),
                "example": analogy_data.get("example_analogy",
                    "Example: CSS Specificity is like a company hierarchy - the CEO's order overrides a manager's order."),
                "evaluation_criteria": analogy_data.get("evaluation_criteria", [
                    "Accuracy: Correctly maps all key elements",
                    "Creativity: Original and imaginative",
                    "Memorability: Easy to remember and recall",
                    "Clarity: Clear explanation of mapping"
                ]),
                "tips": analogy_data.get("tips", [
                    "Think about everyday systems with similar rules",
                    "Focus on the relationships, not just the elements",
                    "Make it personal or funny to aid memory"
                ]),
                "domain_suggestions": analogy_domains
            }
            
        except Exception as e:
            print(f"⚠️  Error generating analogy prompt: {e}")
            
            return {
                "instructions": "Create a real-world analogy for the pattern we just discovered.",
                "prompt": f"Create an analogy for '{pattern_name}'. Think about: {', '.join(analogy_domains)}",
                "example": f"Example: {pattern_name} is like traffic rules - more specific signs override general ones.",
                "evaluation_criteria": [
                    "Does it correctly represent the pattern?",
                    "Is it creative and memorable?",
                    "Is the mapping clear and complete?"
                ],
                "domain_suggestions": analogy_domains
            }
    
    def evaluate_analogy(self, user_analogy: str) -> Dict[str, Any]:
        """
        Evaluate user's analogy using multiple criteria
        Logs to Database Doc 5
        """
        self.state = InterleavingState.ANALOGY_EVALUATION
        
        # Get pattern information
        pattern_name = self.pattern_data.get("pattern_name", "")
        pattern_description = self.pattern_data.get("pattern_description", "")
        
        prompt = f"""
        Evaluate a student's analogy for a programming pattern.
        
        PATTERN: {pattern_name}
        PATTERN DESCRIPTION: {pattern_description}
        
        STUDENT'S ANALOGY: "{user_analogy}"
        
        EVALUATION DIMENSIONS (score 0-5 for each):
        1. ACCURACY: Does it correctly map all key elements of the pattern?
        2. CREATIVITY: Is it original, imaginative, and not cliché?
        3. MEMORABILITY: Is it easy to remember and recall later?
        4. CLARITY: Is the mapping clear and well-explained?
        5. COMPLETENESS: Does it cover the pattern's full scope?
        
        SCORING GUIDELINES:
        - 5: Excellent - exceeds expectations
        - 4: Good - meets all requirements
        - 3: Adequate - minor issues
        - 2: Needs work - significant issues
        - 1: Poor - fundamentally flawed
        - 0: Irrelevant or incorrect
        
        Return JSON:
        {{
            "accuracy_score": 0-5,
            "creativity_score": 0-5,
            "memorability_score": 0-5,
            "clarity_score": 0-5,
            "completeness_score": 0-5,
            "overall_score": 0-5 (average),
            "strengths": ["list of what works well"],
            "improvements": ["specific suggestions for improvement"],
            "feedback": "Overall feedback paragraph",
            "analogy_quality": "poor/fair/good/excellent",
            "would_use_for_teaching": true/false
        }}
        
        Also provide an improved version of the analogy.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Consistent evaluation
                    thinking_config=types.ThinkingConfig(
                        thinking_level="low"  # Faster for evaluation
                    )
                )
            )
            evaluation = json.loads(response.text)
            
            # Create analogy record
            analogy_id = f"analogy_{int(time.time())}_{self.user_id}"
            user_analogy_record = UserAnalogy(
                analogy_id=analogy_id,
                analogy_text=user_analogy,
                pattern_relation=pattern_name,
                creativity_score=evaluation.get("creativity_score", 0),
                accuracy_score=evaluation.get("accuracy_score", 0),
                memorability_score=evaluation.get("memorability_score", 0),
                overall_score=evaluation.get("overall_score", 0),
                feedback=evaluation.get("feedback", ""),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                improvements_suggested=evaluation.get("improvements", [])
            )
            
            self.user_analogies.append(user_analogy_record)
            
            # Update phase log
            self.phase_log["analogies_created"].append({
                "analogy_id": analogy_id,
                "preview": user_analogy[:100] + "..." if len(user_analogy) > 100 else user_analogy,
                "overall_score": user_analogy_record.overall_score,
                "pattern": pattern_name
            })
            
            # Log to Database Doc 5
            self.db.log_analogy(
                user_id=self.user_id,
                analogy_data={
                    "analogy_id": analogy_id,
                    "analogy_text": user_analogy,
                    "pattern": pattern_name,
                    "topic": self.topic.value,
                    "scores": {
                        "accuracy": user_analogy_record.accuracy_score,
                        "creativity": user_analogy_record.creativity_score,
                        "memorability": user_analogy_record.memorability_score,
                        "overall": user_analogy_record.overall_score
                    },
                    "feedback": user_analogy_record.feedback,
                    "timestamp": user_analogy_record.timestamp,
                    "improvements": user_analogy_record.improvements_suggested
                }
            )
            
            print(f"\n📝 ANALOGY EVALUATION:")
            print(f"   Overall: {user_analogy_record.overall_score}/5")
            print(f"   Accuracy: {user_analogy_record.accuracy_score}/5")
            print(f"   Creativity: {user_analogy_record.creativity_score}/5")
            print(f"   ✅ Logged to Database Doc 5")
            
            # Move to next step
            self.completed_steps.add("analogy_generation")
            
            # If analogy is poor, offer to try again
            if user_analogy_record.overall_score < 3:
                return {
                    **evaluation,
                    "status": "analogy_evaluated",
                    "analogy_id": analogy_id,
                    "suggest_retry": True,
                    "retry_prompt": "Try creating another analogy with these improvements...",
                    "next_step": "retry_analogy_or_proceed"
                }
            
            # Proceed to what-if scenarios
            what_if_start = self._start_what_if_scenario()
            
            return {
                **evaluation,
                "status": "analogy_evaluated",
                "analogy_id": analogy_id,
                "logged_to_doc5": True,
                "next_step": "what_if_scenario",
                "what_if_instructions": what_if_start["instructions"],
                "what_if_prompt": what_if_start["prompt"]
            }
            
        except Exception as e:
            print(f"❌ Error evaluating analogy: {e}")
            
            return {
                "status": "analogy_evaluated",
                "overall_score": 3,
                "feedback": "Good analogy! Let's move to exploring edge cases.",
                "strengths": ["Created an analogy"],
                "improvements": ["Could be more specific"],
                "next_step": "what_if_scenario"
            }
    
    def _start_what_if_scenario(self) -> Dict[str, Any]:
        """
        Step 3.2: The "What-If" Engine
        Command user to create edge case scenarios
        """
        self.state = InterleavingState.WHAT_IF_SETUP
        
        pattern_name = self.pattern_data.get("pattern_name", "")
        current_topic = self.topic.value
        
        # Get what-if focus areas from config
        focus_areas = self.current_config["what_if_focus"]
        
        # Select a specific command based on topic
        commands = {
            ModuleTopic.NEUMORPHISM: 
                f"Invent a specific browser scenario or screen size where this {pattern_name} would look terrible.",
            ModuleTopic.CSS_ANIMATIONS:
                f"Invent a user scenario where these {pattern_name} would cause accessibility issues.",
            ModuleTopic.RESPONSIVE_DESIGN:
                f"Invent a specific device/browser combination where {pattern_name} would break completely."
        }
        
        command = commands.get(
            self.topic,
            f"Invent a specific scenario where {pattern_name} would fail or look bad."
        )
        
        # Get past what-if scenarios from database
        past_scenarios = self.db.get_what_if_scenarios(self.user_id)
        
        prompt = f"""
        Create a detailed "what-if" challenge for the student.
        
        TOPIC: {current_topic}
        PATTERN: {pattern_name}
        
        COMMAND TEMPLATE: "{command}"
        
        FOCUS AREAS to consider: {', '.join(focus_areas)}
        
        PAST SCENARIOS by this student (avoid repeating):
        {json.dumps(past_scenarios, indent=2)}
        
        Provide:
        1. The specific command to give the student
        2. Example scenarios (for teacher reference)
        3. Evaluation criteria for student's scenario
        4. Why this exercise is valuable
        
        Return JSON.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            what_if_data = json.loads(response.text)
            
            return {
                "instructions": "Think creatively about edge cases and failure scenarios.",
                "prompt": what_if_data.get("command", command),
                "example_scenarios": what_if_data.get("example_scenarios", []),
                "evaluation_criteria": what_if_data.get("evaluation_criteria", [
                    "Specificity: Concrete and detailed scenario",
                    "Realism: Could realistically happen",
                    "Impact: Would actually cause problems",
                    "Creativity: Beyond obvious edge cases"
                ]),
                "focus_areas": focus_areas,
                "value_explanation": what_if_data.get("value_explanation", 
                    "Helps anticipate real-world problems before they occur.")
            }
            
        except:
            return {
                "instructions": command,
                "prompt": command,
                "focus_areas": focus_areas,
                "evaluation_criteria": [
                    "Be specific about browser/device/conditions",
                    "Describe exactly what would go wrong",
                    "Explain why it would be problematic"
                ]
            }
    
    def evaluate_what_if_scenario(self, scenario: str) -> Dict[str, Any]:
        """
        Evaluate user's what-if scenario
        """
        self.state = InterleavingState.WHAT_IF_SCENARIO
        
        pattern_name = self.pattern_data.get("pattern_name", "")
        
        prompt = f"""
        Evaluate a student's "what-if" scenario for edge case thinking.
        
        PATTERN/TOPIC: {pattern_name}
        
        STUDENT'S SCENARIO: "{scenario}"
        
        EVALUATION DIMENSIONS (score 0-5 for each):
        1. SPECIFICITY: Is it concrete, detailed, and specific?
        2. REALISM: Could it realistically occur in production?
        3. IMPACT: Would it actually cause significant problems?
        4. CREATIVITY: Is it beyond obvious/common edge cases?
        5. PREVENTABILITY: Could developers prevent this scenario?
        
        SCORING:
        - 5: Excellent insight, highly valuable scenario
        - 4: Good scenario with clear issues
        - 3: Adequate but could be more specific
        - 2: Vague or unlikely scenario
        - 1: Poor quality or irrelevant
        - 0: Completely unrealistic
        
        Return JSON:
        {{
            "specificity_score": 0-5,
            "realism_score": 0-5,
            "impact_score": 0-5,
            "creativity_score": 0-5,
            "preventability_score": 0-5,
            "overall_score": 0-5,
            "scenario_quality": "poor/fair/good/excellent",
            "strengths": ["what's good about this scenario"],
            "weaknesses": ["what could be improved"],
            "feedback": "Detailed feedback",
            "potential_solution": "How to address this edge case",
            "real_world_example": "If this has happened in real projects"
        }}
        
        Also categorize the edge case type: browser, device, content, user, performance, accessibility, other.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            evaluation = json.loads(response.text)
            
            # Determine edge case type
            edge_case_type = self._categorize_edge_case(scenario, evaluation)
            
            # Create scenario record
            scenario_id = f"whatif_{int(time.time())}_{self.user_id}"
            what_if_record = WhatIfScenario(
                scenario_id=scenario_id,
                scenario_text=scenario,
                edge_case_type=edge_case_type,
                realism_score=evaluation.get("realism_score", 0),
                impact_score=evaluation.get("impact_score", 0),
                creativity_score=evaluation.get("creativity_score", 0),
                overall_score=evaluation.get("overall_score", 0),
                solution_hint=evaluation.get("potential_solution", ""),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            self.what_if_scenarios.append(what_if_record)
            
            # Update phase log
            self.phase_log["what_if_scenarios"].append({
                "scenario_id": scenario_id,
                "type": edge_case_type,
                "score": what_if_record.overall_score,
                "preview": scenario[:100] + "..." if len(scenario) > 100 else scenario
            })
            
            # Log to database
            self.db.log_what_if_scenario(
                user_id=self.user_id,
                scenario_data={
                    "scenario_id": scenario_id,
                    "scenario_text": scenario,
                    "pattern": pattern_name,
                    "topic": self.topic.value,
                    "edge_case_type": edge_case_type,
                    "scores": {
                        "realism": what_if_record.realism_score,
                        "impact": what_if_record.impact_score,
                        "creativity": what_if_record.creativity_score,
                        "overall": what_if_record.overall_score
                    },
                    "feedback": evaluation.get("feedback", ""),
                    "solution_hint": what_if_record.solution_hint,
                    "timestamp": what_if_record.timestamp
                }
            )
            
            print(f"\n🔍 WHAT-IF SCENARIO EVALUATION:")
            print(f"   Type: {edge_case_type}")
            print(f"   Score: {what_if_record.overall_score}/5")
            print(f"   Realism: {what_if_record.realism_score}/5")
            print(f"   ✅ Logged to database")
            
            # Move to next step
            self.completed_steps.add("what_if_scenario")
            
            # Check if we have enough scenarios
            if len(self.what_if_scenarios) >= 2:
                # Move to compound questions
                compound_start = self._generate_compound_question()
                
                return {
                    **evaluation,
                    "status": "what_if_evaluated",
                    "scenario_id": scenario_id,
                    "edge_case_type": edge_case_type,
                    "scenarios_completed": len(self.what_if_scenarios),
                    "next_step": "compound_question",
                    "compound_question": compound_start["question"],
                    "compound_instructions": compound_start["instructions"]
                }
            
            # Ask for another scenario
            return {
                **evaluation,
                "status": "what_if_evaluated",
                "scenario_id": scenario_id,
                "edge_case_type": edge_case_type,
                "next_action": "submit_another_scenario",
                "suggestions": "Try thinking about a different type of edge case...",
                "target_scenarios": 2
            }
            
        except Exception as e:
            print(f"❌ Error evaluating scenario: {e}")
            
            return {
                "status": "what_if_evaluated",
                "overall_score": 3,
                "feedback": "Interesting scenario! Let's think about how to prevent it.",
                "next_action": "proceed_to_compound"
            }
    
    def _categorize_edge_case(self, scenario: str, evaluation: Dict) -> str:
        """Categorize the edge case type"""
        scenario_lower = scenario.lower()
        
        # Check for categories
        if any(word in scenario_lower for word in ['browser', 'chrome', 'firefox', 'safari', 'edge']):
            return "browser"
        elif any(word in scenario_lower for word in ['screen', 'device', 'mobile', 'tablet', 'responsive']):
            return "screen_size"
        elif any(word in scenario_lower for word in ['content', 'text', 'image', 'video', 'dynamic']):
            return "content"
        elif any(word in scenario_lower for word in ['user', 'interaction', 'click', 'hover', 'scroll']):
            return "user_interaction"
        elif any(word in scenario_lower for word in ['performance', 'slow', 'lag', 'memory', 'cpu']):
            return "performance"
        elif any(word in scenario_lower for word in ['accessibility', 'blind', 'color', 'contrast', 'keyboard']):
            return "accessibility"
        else:
            return evaluation.get("edge_case_type", "other")
    
    def _generate_compound_question(self) -> Dict[str, Any]:
        """
        Step 3.3: Generate compound question integrating past knowledge gaps
        Uses Database Doc 4 (knowledge gaps) as source for past topics
        """
        self.state = InterleavingState.COMPOUND_QUESTION
        
        # Get relevant knowledge gaps for this user
        relevant_gaps = self._select_relevant_knowledge_gaps()
        
        if not relevant_gaps:
            # No gaps found, create generic compound question
            return self._create_generic_compound_question()
        
        # Select a knowledge gap to target
        selected_gap = relevant_gaps[0]
        
        # Generate compound question
        prompt = f"""
        Create a COMPOUND question that requires understanding of:
        
        CURRENT TOPIC: {self.topic.value}
        PAST TOPIC (from knowledge gap): {selected_gap['concept']}
        KNOWLEDGE GAP CONTEXT: {selected_gap.get('root_cause', '')}
        
        The question should:
        1. Require application of BOTH topics
        2. Be practical/coding-oriented
        3. Test DEEP understanding, not just recall
        4. Have a clear correct approach
        5. Be appropriate for a beginner/intermediate learner
        
        QUESTION FORMAT:
        - Present a realistic coding scenario
        - Ask how to solve it using both concepts
        - May include code to analyze or modify
        
        Return JSON:
        {{
            "question": "The compound question text",
            "current_topic_elements": ["elements from current topic needed"],
            "past_topic_elements": ["elements from past topic needed"],
            "difficulty": "easy/medium/hard",
            "expected_answer_components": ["list of key components in answer"],
            "scoring_rubric": {{
                "current_topic_application": "0-5 points",
                "past_topic_integration": "0-5 points",
                "solution_correctness": "0-5 points",
                "explanation_quality": "0-5 points"
            }},
            "hints_available": ["hint1", "hint2"],
            "real_world_context": "Why this combination matters in real projects"
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level=self.thinking_level
                    )
                )
            )
            question_data = json.loads(response.text)
            
            # Create compound question record
            question_id = f"compound_{int(time.time())}_{self.user_id}"
            compound_question = CompoundQuestion(
                question_id=question_id,
                question_text=question_data["question"],
                current_topic=self.topic.value,
                past_topic=selected_gap['concept'],
                knowledge_gap_targeted=selected_gap['gap_id'],
                difficulty=question_data.get("difficulty", "medium"),
                expected_answer_elements=question_data.get("expected_answer_components", []),
                scoring_rubric=question_data.get("scoring_rubric", {})
            )
            
            self.compound_questions.append(compound_question)
            
            return {
                "question": question_data["question"],
                "instructions": "This question requires you to combine current knowledge with past concepts.",
                "hints_available": question_data.get("hints_available", []),
                "scoring_rubric": question_data.get("scoring_rubric", {}),
                "question_id": question_id,
                "targeted_gap": selected_gap['concept'],
                "real_world_context": question_data.get("real_world_context", 
                    "Combining concepts is essential for real-world problem solving.")
            }
            
        except Exception as e:
            print(f"⚠️  Error generating compound question: {e}")
            return self._create_generic_compound_question()
    
    def _select_relevant_knowledge_gaps(self) -> List[Dict]:
        """Select relevant knowledge gaps for interleaving"""
        if not self.knowledge_gaps:
            return []
        
        # Filter gaps by severity and relevance
        relevant_gaps = []
        
        for gap in self.knowledge_gaps:
            # Check if gap is relevant to current topic
            if self._is_gap_relevant(gap):
                # Prioritize higher severity gaps
                relevant_gaps.append(gap)
        
        # Sort by severity (highest first) and recency
        relevant_gaps.sort(
            key=lambda x: (
                x.get("severity", 0), 
                1 if x.get("addressed", False) else 0  # Prioritize unaddressed
            ),
            reverse=True
        )
        
        return relevant_gaps[:3]  # Return top 3
    
    def _is_gap_relevant(self, gap: Dict) -> bool:
        """Check if knowledge gap is relevant to current topic"""
        gap_topic = gap.get("related_module", "").lower()
        current_topic = self.topic.value.lower()
        
        # Simple relevance check - could be enhanced
        topic_groups = {
            "css": ["css_basics", "css_layout", "css_animations"],
            "layout": ["css_layout", "responsive_design"],
            "design": ["neumorphism", "css_animations"]
        }
        
        for group, topics in topic_groups.items():
            if gap_topic in topics and current_topic in topics:
                return True
        
        # Check if gap mentions current topic concepts
        gap_context = gap.get("root_cause", "").lower()
        current_topic_keywords = {
            ModuleTopic.CSS_BASICS: ["selector", "specificity", "cascade"],
            ModuleTopic.NEUMORPHISM: ["shadow", "light", "depth", "inset"],
            ModuleTopic.CSS_ANIMATIONS: ["animation", "transition", "keyframes"]
        }
        
        keywords = current_topic_keywords.get(self.topic, [])
        if any(keyword in gap_context for keyword in keywords):
            return True
        
        return False
    
    def _create_generic_compound_question(self) -> Dict[str, Any]:
        """Create a generic compound question when no gaps are available"""
        generic_questions = {
            ModuleTopic.CSS_BASICS: 
                "How does CSS specificity interact with JavaScript style modifications? "
                "If you have `#id { color: red; }` and JavaScript sets `element.style.color = 'blue'`, which wins and why?",
            ModuleTopic.NEUMORPHISM:
                "How would you make a neumorphic design accessible for users with visual impairments? "
                "Consider both contrast ratios and interactive states.",
            ModuleTopic.CSS_ANIMATIONS:
                "How can CSS animations affect website performance, and what techniques would you use "
                "to ensure animations are smooth even on lower-end devices?"
        }
        
        question = generic_questions.get(
            self.topic,
            f"How does {self.topic.value} interact with other web technologies you've learned?"
        )
        
        question_id = f"compound_generic_{int(time.time())}"
        compound_question = CompoundQuestion(
            question_id=question_id,
            question_text=question,
            current_topic=self.topic.value,
            past_topic="general web development",
            knowledge_gap_targeted="general_integration",
            difficulty="medium",
            expected_answer_elements=["current topic application", "past knowledge integration", "practical considerations"],
            scoring_rubric={
                "current_topic_application": "0-5",
                "integration_quality": "0-5",
                "practicality": "0-5"
            }
        )
        
        self.compound_questions.append(compound_question)
        
        return {
            "question": question,
            "instructions": "Think about how this topic connects with other things you've learned.",
            "question_id": question_id,
            "targeted_gap": "general_integration",
            "real_world_context": "Real projects require combining multiple concepts effectively."
        }
    
    def evaluate_compound_answer(self, question_id: str, user_answer: str) -> Dict[str, Any]:
        """
        Evaluate user's answer to compound question
        Updates knowledge gaps based on performance
        """
        # Find the question
        question = next((q for q in self.compound_questions if q.question_id == question_id), None)
        
        if not question:
            return {"error": "Question not found"}
        
        prompt = f"""
        Evaluate a student's answer to a compound question.
        
        QUESTION: {question.question_text}
        
        CURRENT TOPIC: {question.current_topic}
        PAST TOPIC INTEGRATED: {question.past_topic}
        
        EXPECTED ANSWER COMPONENTS:
        {json.dumps(question.expected_answer_elements, indent=2)}
        
        STUDENT'S ANSWER: "{user_answer}"
        
        SCORING RUBRIC:
        {json.dumps(question.scoring_rubric, indent=2)}
        
        EVALUATION TASKS:
        1. Score each rubric category (0-5)
        2. Identify which expected components are present/missing
        3. Determine if the knowledge gap was addressed
        4. Provide specific feedback on integration quality
        
        Return JSON:
        {{
            "scores": {{
                "current_topic_application": 0-5,
                "past_topic_integration": 0-5,
                "solution_correctness": 0-5,
                "explanation_quality": 0-5,
                "overall": 0-5
            }},
            "components_present": ["list of present components"],
            "components_missing": ["list of missing components"],
            "gap_addressed": true/false,
            "gap_improvement_score": 0-5,
            "feedback": "Detailed feedback",
            "model_answer": "Example of good answer",
            "strengths": ["what student did well"],
            "areas_for_improvement": ["specific areas to work on"]
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            evaluation = json.loads(response.text)
            
            # Store answer
            answer_record = {
                "question_id": question_id,
                "user_answer": user_answer,
                "evaluation": evaluation,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.compound_answers.append(answer_record)
            
            # Update phase log
            self.phase_log["compound_questions_asked"].append({
                "question_id": question_id,
                "current_topic": question.current_topic,
                "past_topic": question.past_topic,
                "score": evaluation.get("scores", {}).get("overall", 0),
                "gap_addressed": evaluation.get("gap_addressed", False)
            })
            
            # Update knowledge gap in Database Doc 4 if addressed
            if evaluation.get("gap_addressed", False) and question.knowledge_gap_targeted != "general_integration":
                gap_improvement = evaluation.get("gap_improvement_score", 0)
                
                if gap_improvement >= 3:
                    # Mark gap as addressed
                    self.db.update_knowledge_gap(
                        user_id=self.user_id,
                        gap_id=question.knowledge_gap_targeted,
                        updates={
                            "addressed": True,
                            "addressed_in": "interleaving_phase",
                            "addressed_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "improvement_score": gap_improvement,
                            "addressing_question": question.question_text[:100]
                        }
                    )
                    print(f"   ✅ Knowledge gap '{question.knowledge_gap_targeted}' addressed!")
            
            # Check if phase is complete
            self.completed_steps.add("compound_question")
            
            if len(self.compound_questions) >= 1:  # Could require more questions
                self.state = InterleavingState.COMPLETE
                evaluation["phase_complete"] = True
                evaluation["next_step"] = "phase_completion"
            else:
                # Generate another compound question
                next_question = self._generate_compound_question()
                evaluation["next_question"] = next_question
            
            return evaluation
            
        except Exception as e:
            print(f"❌ Error evaluating compound answer: {e}")
            
            return {
                "scores": {"overall": 3},
                "feedback": "Thanks for your answer. Let's move forward.",
                "phase_complete": True
            }
    
    def complete_phase(self) -> Dict[str, Any]:
        """
        Complete the interleaving phase
        Calculate scores and prepare for next phase
        """
        if self.state != InterleavingState.COMPLETE:
            self.state = InterleavingState.COMPLETE
        
        # Calculate scores
        analogy_scores = [a.overall_score for a in self.user_analogies]
        what_if_scores = [s.overall_score for s in self.what_if_scenarios]
        compound_scores = [a["evaluation"].get("scores", {}).get("overall", 0) 
                          for a in self.compound_answers]
        
        avg_analogy = sum(analogy_scores) / len(analogy_scores) if analogy_scores else 0
        avg_what_if = sum(what_if_scores) / len(what_if_scores) if what_if_scores else 0
        avg_compound = sum(compound_scores) / len(compound_scores) if compound_scores else 0
        
        # Interleaving score (ability to connect concepts)
        interleaving_score = int((avg_compound * 0.5 + avg_analogy * 0.3 + avg_what_if * 0.2) * 20)
        
        # Curiosity score (creative thinking)
        curiosity_score = int((avg_what_if * 0.4 + avg_analogy * 0.4 + 
                             (1 if len(self.what_if_scenarios) >= 2 else 0) * 20) * 20)
        
        # Update phase log
        self.phase_log["interleaving_score"] = interleaving_score
        self.phase_log["curiosity_score"] = curiosity_score
        self.phase_log["completion_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Identify new knowledge gaps from this phase
        new_gaps = self._identify_new_knowledge_gaps()
        
        # Prepare for next phase (Integrated Testing)
        next_phase_prep = self._prepare_for_integrated_testing()
        
        summary = self._generate_phase_summary()
        
        return {
            "status": "phase_complete",
            "phase": "interleaving",
            "summary": summary,
            "performance_metrics": {
                "analogies_created": len(self.user_analogies),
                "avg_analogy_score": round(avg_analogy, 1),
                "what_if_scenarios": len(self.what_if_scenarios),
                "avg_what_if_score": round(avg_what_if, 1),
                "compound_questions": len(self.compound_questions),
                "avg_compound_score": round(avg_compound, 1),
                "interleaving_score": f"{interleaving_score}%",
                "curiosity_score": f"{curiosity_score}%",
                "knowledge_gaps_addressed": len([a for a in self.compound_answers 
                                                if a["evaluation"].get("gap_addressed", False)])
            },
            "achievements": self._calculate_achievements(
                avg_analogy, avg_what_if, avg_compound
            ),
            "new_knowledge_gaps": new_gaps,
            "next_phase": "integrated_testing",
            "next_phase_preparation": next_phase_prep,
            "database_updates": {
                "doc5_analogies": len(self.user_analogies),
                "doc5_what_if": len(self.what_if_scenarios),
                "doc4_gaps_addressed": len(new_gaps.get("addressed", [])),
                "doc4_new_gaps": len(new_gaps.get("identified", []))
            }
        }
    
    def _identify_new_knowledge_gaps(self) -> Dict[str, List]:
        """Identify knowledge gaps from interleaving performance"""
        identified_gaps = []
        addressed_gaps = []
        
        # Check analogy performance
        if self.user_analogies:
            low_analogy = [a for a in self.user_analogies if a.overall_score < 3]
            if low_analogy:
                gap = {
                    "gap_id": f"gap_analogical_{int(time.time())}",
                    "concept": "Analogical Reasoning",
                    "root_cause": "Difficulty creating accurate analogies for technical concepts",
                    "severity": 5 - int(sum(a.overall_score for a in low_analogy) / len(low_analogy)),
                    "evidence": f"Analogy scores: {', '.join(str(a.overall_score) for a in low_analogy)}/5",
                    "identified_in": "interleaving_phase",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "related_module": self.topic.value,
                    "remediation_suggestions": [
                        "Practice mapping technical concepts to everyday systems",
                        "Study how experts create technical analogies",
                        "Focus on relationship mapping rather than direct equivalence"
                    ]
                }
                identified_gaps.append(gap)
        
        # Check what-if performance
        if self.what_if_scenarios:
            low_scenarios = [s for s in self.what_if_scenarios if s.overall_score < 3]
            if low_scenarios:
                gap = {
                    "gap_id": f"gap_edge_case_{int(time.time())}",
                    "concept": "Edge Case Identification",
                    "root_cause": "Difficulty imagining realistic failure scenarios",
                    "severity": 5 - int(sum(s.overall_score for s in low_scenarios) / len(low_scenarios)),
                    "evidence": f"What-if scenario scores: {', '.join(str(s.overall_score) for s in low_scenarios)}/5",
                    "identified_in": "interleaving_phase",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "related_module": self.topic.value,
                    "remediation_suggestions": [
                        "Study real-world bug reports and failure cases",
                        "Practice thinking about user diversity (devices, abilities, contexts)",
                        "Learn about common web development pitfalls"
                    ]
                }
                identified_gaps.append(gap)
        
        # Check compound question performance
        if self.compound_answers:
            low_compound = [a for a in self.compound_answers 
                          if a["evaluation"].get("scores", {}).get("overall", 0) < 3]
            
            if low_compound:
                gap = {
                    "gap_id": f"gap_integration_{int(time.time())}",
                    "concept": "Concept Integration",
                    "root_cause": "Difficulty combining multiple concepts in problem solving",
                    "severity": 3,  # Medium severity
                    "evidence": f"Compound question scores below 3/5",
                    "identified_in": "interleaving_phase",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "related_module": self.topic.value,
                    "remediation_suggestions": [
                        "Practice breaking down multi-concept problems",
                        "Create concept maps showing relationships",
                        "Work on projects that require combining skills"
                    ]
                }
                identified_gaps.append(gap)
            
            # Check which gaps were addressed
            addressed = [a for a in self.compound_answers 
                        if a["evaluation"].get("gap_addressed", False)]
            addressed_gaps = [a["evaluation"].get("gap_id", "") for a in addressed]
        
        # Log new gaps to database
        for gap in identified_gaps:
            self.db.log_knowledge_gap(self.user_id, gap)
        
        return {
            "identified": identified_gaps,
            "addressed": addressed_gaps
        }
    
    def _calculate_achievements(self, avg_analogy: float, avg_what_if: float, 
                               avg_compound: float) -> List[str]:
        """Calculate achievements earned"""
        achievements = []
        
        if avg_analogy >= 4:
            achievements.append("Analogy Artist")
        elif avg_analogy >= 2:
            achievements.append("Creative Thinker")
        
        if avg_what_if >= 4:
            achievements.append("Edge Case Explorer")
        elif avg_what_if >= 2:
            achievements.append("Problem Anticipator")
        
        if avg_compound >= 4:
            achievements.append("Concept Integrator")
        elif avg_compound >= 2:
            achievements.append("Multi-Topic Thinker")
        
        if len(self.what_if_scenarios) >= 3:
            achievements.append("Scenario Generator")
        
        if len(self.user_analogies) >= 2 and avg_analogy >= 3:
            achievements.append("Double Analogy Creator")
        
        return achievements if achievements else ["Interleaving Participant"]
    
    def _prepare_for_integrated_testing(self) -> Dict[str, Any]:
        """Prepare data needed for Phase 4: Integrated Testing"""
        # Collect all knowledge gaps (including new ones)
        all_gaps = self.db.get_knowledge_gaps(self.user_id)
        
        # Filter for gaps that need testing
        gaps_needing_testing = [
            gap for gap in all_gaps 
            if not gap.get("addressed", False) and gap.get("severity", 0) >= 3
        ]
        
        # Select topics for testing
        test_topics = list(set([gap.get("related_module", "") for gap in gaps_needing_testing[:3]]))
        
        if not test_topics:
            test_topics = [self.topic.value]
        
        return {
            "phase": "integrated_testing",
            "requires": ["knowledge_gaps_doc4", "all_previous_topics"],
            "test_topics": test_topics,
            "current_topic": self.topic.value,
            "gap_count": len(gaps_needing_testing),
            "testing_approach": "compound_questions_with_feedback",
            "estimated_questions": min(5, len(gaps_needing_testing) + 2)
        }
    
    def _generate_phase_summary(self) -> str:
        """Generate human-readable summary"""
        summary_lines = [
            f"🎭 INTERLEAVING & CURIOSITY PHASE COMPLETE",
            f"   Topic: {self.topic.value}",
            f"   Analogies created: {len(self.user_analogies)}",
            f"   What-if scenarios: {len(self.what_if_scenarios)}",
            f"   Compound questions: {len(self.compound_questions)}",
            f"   Interleaving score: {self.phase_log.get('interleaving_score', 0)}%",
            f"   Curiosity score: {self.phase_log.get('curiosity_score', 0)}%",
            f"   Database updates:",
            f"     - Doc 5: {len(self.user_analogies)} analogies logged",
            f"     - Doc 4: {len(self.phase_log.get('new_knowledge_gaps', {}).get('identified', []))} gaps identified"
        ]
        
        return "\n".join(summary_lines)
    
    def get_phase_log(self) -> Dict[str, Any]:
        """Get complete phase log for database integration"""
        return self.phase_log
    
    def get_analogies_for_display(self) -> List[Dict]:
        """Get user analogies formatted for display"""
        return [
            {
                "analogy": a.analogy_text,
                "scores": {
                    "accuracy": a.accuracy_score,
                    "creativity": a.creativity_score,
                    "memorability": a.memorability_score,
                    "overall": a.overall_score
                },
                "feedback": a.feedback
            }
            for a in self.user_analogies
        ]
    
    def get_what_if_scenarios_for_display(self) -> List[Dict]:
        """Get what-if scenarios formatted for display"""
        return [
            {
                "scenario": s.scenario_text,
                "type": s.edge_case_type,
                "scores": {
                    "realism": s.realism_score,
                    "impact": s.impact_score,
                    "creativity": s.creativity_score,
                    "overall": s.overall_score
                },
                "solution_hint": s.solution_hint
            }
            for s in self.what_if_scenarios
        ]


# ============================================================================
# INTEGRATION EXAMPLE
# ============================================================================

def demonstrate_interleaving_phase():
    """Example of using InterleavingPhase"""
    
    # Mock classes for demonstration
    class MockGeminiClient:
        def models(self):
            class Models:
                @staticmethod
                def generate_content(model, contents, config=None):
                    print(f"\n[Gemini called: {contents[:150]}...]")
                    
                    class Response:
                        if "analogy" in contents:
                            text = json.dumps({
                                "accuracy_score": 4,
                                "creativity_score": 5,
                                "memorability_score": 4,
                                "clarity_score": 3,
                                "completeness_score": 4,
                                "overall_score": 4,
                                "strengths": ["Creative", "Memorable"],
                                "improvements": ["Could be clearer"],
                                "feedback": "Good analogy!",
                                "analogy_quality": "good"
                            })
                        else:
                            text = '{"scores": {"overall": 4}}'
                    
                    return type('obj', (object,), {'text': text})()
            
            return Models()
    
    class MockStudentDatabase:
        def get_knowledge_gaps(self, user_id):
            return [
                {
                    "gap_id": "gap_001",
                    "concept": "CSS Specificity",
                    "root_cause": "Confuses ID and class selectors",
                    "severity": 4,
                    "addressed": False
                }
            ]
        
        def log_analogy(self, user_id, analogy_data):
            print(f"📝 Logged analogy to Doc 5: {analogy_data['analogy_id']}")
        
        def log_what_if_scenario(self, user_id, scenario_data):
            print(f"📝 Logged what-if scenario: {scenario_data['scenario_id']}")
        
        def update_knowledge_gap(self, user_id, gap_id, updates):
            print(f"🔄 Updated gap {gap_id}: {updates}")
        
        def log_knowledge_gap(self, user_id, gap_data):
            print(f"📝 Logged new gap: {gap_data['gap_id']}")
        
        def get_analogies(self, user_id):
            return []
        
        def get_what_if_scenarios(self, user_id):
            return []
    
    # Mock pattern discovery data
    mock_pattern_data = {
        "pattern_name": "CSS Specificity",
        "pattern_description": "More specific selectors override less specific ones",
        "mental_model": "ID (100) > Class (10) > Element (1)",
        "discovery_score": 5,
        "user_discovered": True
    }
    
    # Create and run phase
    print("🚀 INTERLEAVING PHASE DEMONSTRATION")
    print("=" * 60)
    
    mock_client = MockGeminiClient()
    mock_db = MockStudentDatabase()
    
    phase = InterleavingPhase(
        gemini_client=mock_client,
        topic=ModuleTopic.CSS_BASICS,
        pattern_discovery_data=mock_pattern_data,
        user_id="demo_user",
        student_db=mock_db
    )
    
    print("\n1. Starting phase...")
    start_result = phase.execute_phase()
    
    print(f"\n2. Analogy prompt:")
    print(f"   Prompt: {start_result['prompt'][:80]}...")
    
    print(f"\n3. Evaluating analogy...")
    analogy_eval = phase.evaluate_analogy(
        "CSS Specificity is like a company - the CEO's order overrides a manager's order."
    )
    
    print(f"   Score: {analogy_eval.get('overall_score', 0)}/5")
    
    if analogy_eval.get('next_step') == 'what_if_scenario':
        print(f"\n4. What-if prompt: {analogy_eval.get('what_if_prompt', '')[:80]}...")
        
        print(f"\n5. Evaluating what-if scenario...")
        what_if_eval = phase.evaluate_what_if_scenario(
            "What if a user has a browser extension that adds !important to all their styles?"
        )
        
        print(f"   Score: {what_if_eval.get('overall_score', 0)}/5")
        
        if what_if_eval.get('next_step') == 'compound_question':
            print(f"\n6. Compound question:")
            print(f"   Question: {what_if_eval.get('compound_question', '')[:80]}...")
            
            print(f"\n7. Evaluating compound answer...")
            compound_eval = phase.evaluate_compound_answer(
                question_id=what_if_eval.get('question_id', 'test'),
                user_answer="You would need to use more specific selectors or JavaScript."
            )
            
            print(f"   Overall score: {compound_eval.get('scores', {}).get('overall', 0)}/5")
    
    print(f"\n8. Completing phase...")
    completion = phase.complete_phase()
    
    print(f"\n📋 FINAL SUMMARY:")
    print(f"   Phase: {completion['phase']}")
    print(f"   Interleaving score: {completion['performance_metrics']['interleaving_score']}")
    print(f"   Curiosity score: {completion['performance_metrics']['curiosity_score']}")
    print(f"   Achievements: {', '.join(completion['achievements'])}")
    print(f"   Next phase: {completion['next_phase']}")
    
    print(f"\n✅ Interleaving Phase implementation ready!")

if __name__ == "__main__":
    demonstrate_interleaving_phase()