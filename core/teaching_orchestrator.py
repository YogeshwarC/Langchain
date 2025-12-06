"""
TEACHING ORCHESTRATOR - Master Controller
Coordinates all phases, manages user sessions, enforces 80/20 ratio
"""
import json
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from google import genai

from core.priming_phase import PrimingPhase, ModuleTopic
from core.relational_thinking import RelationalThinkingPhase, DiscoveryState
from core.interleaving import InterleavingPhase
from core.integrated_testing import IntegratedTestingPhase
from database.student_database import StudentDatabase
from utils.progress_tracker import ProgressTracker
from utils.gemini_client import GeminiClient

class TeachingMode(Enum):
    """Teaching modes based on user performance"""
    GUIDED = "guided"  # Step-by-step, more hints
    EXPLORATORY = "exploratory"  # User-led, fewer hints
    ACCELERATED = "accelerated"  # Fast track for advanced users
    REMEDIAL = "remedial"  # Extra practice for struggling users

class SessionState(Enum):
    """Current state of teaching session"""
    INITIALIZING = "initializing"
    PRIMING = "priming"
    RELATIONAL_THINKING = "relational_thinking"
    INTERLEAVING = "interleaving"
    INTEGRATED_TESTING = "integrated_testing"
    PRACTICAL_APPLICATION = "practical_application"
    REVIEW = "review"
    COMPLETED = "completed"
    PAUSED = "paused"

@dataclass
class UserProfile:
    """User learning profile and preferences"""
    user_id: str
    name: Optional[str] = None
    learning_style: str = "balanced"  # visual, auditory, kinesthetic, balanced
    pace: str = "moderate"  # slow, moderate, fast
    preferred_complexity: str = "practical"  # theoretical, practical, mixed
    confidence_level: int = 3  # 1-5
    attention_span_minutes: int = 25
    session_history: List[Dict] = field(default_factory=list)
    
@dataclass
class SessionMetrics:
    """Tracks session metrics for 80/20 ratio"""
    start_time: str
    theory_time_seconds: int = 0
    practice_time_seconds: int = 0
    interactions_count: int = 0
    hints_used: int = 0
    corrections_made: int = 0
    concepts_mastered: int = 0
    gaps_identified: int = 0
    current_ratio: Dict[str, float] = field(default_factory=lambda: {"theory": 0.0, "practice": 0.0})
    
@dataclass  
class PhaseTransition:
    """Manages transitions between phases"""
    from_phase: SessionState
    to_phase: SessionState
    transition_condition: str
    data_passed: Dict[str, Any]
    timestamp: str

class TeachingOrchestrator:
    """
    Master controller for AI Tutor system
    Coordinates all teaching phases, manages user sessions, enforces 80/20 ratio
    """
    
    def __init__(
        self,
        gemini_client: genai.Client,
        student_db: StudentDatabase,
        user_id: str,
        initial_topic: ModuleTopic = ModuleTopic.CSS_BASICS,
        teaching_mode: TeachingMode = TeachingMode.GUIDED,
        session_id: Optional[str] = None
    ):
        """
        Initialize Teaching Orchestrator
        
        Args:
            gemini_client: Initialized Gemini client
            student_db: StudentDatabase instance
            user_id: Unique user identifier
            initial_topic: Starting topic
            teaching_mode: Teaching style based on user level
            session_id: Optional session ID for resuming
        """
        # Core components
        self.client = gemini_client
        self.db = student_db
        self.user_id = user_id
        self.session_id = session_id or f"session_{int(time.time())}_{user_id}"
        
        # State management
        self.current_state = SessionState.INITIALIZING
        self.current_topic = initial_topic
        self.teaching_mode = teaching_mode
        self.previous_state = None
        
        # User profile
        self.user_profile = self._load_user_profile()
        
        # Phase instances (will be created as needed)
        self.priming_phase: Optional[PrimingPhase] = None
        self.relational_thinking: Optional[RelationalThinkingPhase] = None
        self.interleaving: Optional[InterleavingPhase] = None
        self.integrated_testing: Optional[IntegratedTestingPhase] = None
        
        # Data passing between phases
        self.phase_data = {
            "priming": {},
            "relational_thinking": {},
            "interleaving": {},
            "integrated_testing": {}
        }
        
        # Session tracking
        self.session_metrics = SessionMetrics(
            start_time=datetime.now().isoformat()
        )
        self.phase_transitions: List[PhaseTransition] = []
        self.interaction_history: List[Dict] = []
        
        # Progress tracking
        self.progress_tracker = ProgressTracker(user_id, student_db)
        
        # Configuration
        self.max_hints_per_phase = {
            "priming": 2,
            "relational_thinking": 3,
            "interleaving": 2,
            "integrated_testing": 2
        }
        
        self.phase_time_limits = {
            "priming": 15 * 60,  # 15 minutes
            "relational_thinking": 20 * 60,
            "interleaving": 15 * 60,
            "integrated_testing": 20 * 60
        }
        
        # Load curriculum
        self.curriculum = self._load_curriculum()
        
        # Start session
        self._initialize_session()
    
    def _load_user_profile(self) -> UserProfile:
        """Load or create user profile"""
        profile_data = self.db.get_user_profile(self.user_id)
        
        if profile_data:
            return UserProfile(
                user_id=self.user_id,
                name=profile_data.get("name"),
                learning_style=profile_data.get("learning_style", "balanced"),
                pace=profile_data.get("pace", "moderate"),
                preferred_complexity=profile_data.get("preferred_complexity", "practical"),
                confidence_level=profile_data.get("confidence_level", 3),
                attention_span_minutes=profile_data.get("attention_span_minutes", 25),
                session_history=profile_data.get("session_history", [])
            )
        else:
            # New user
            return UserProfile(user_id=self.user_id)
    
    def _load_curriculum(self) -> Dict[str, Any]:
        """Load curriculum structure"""
        return {
            "modules": [
                {
                    "id": "css_basics",
                    "topic": ModuleTopic.CSS_BASICS,
                    "prerequisites": [],
                    "estimated_time": "2 hours",
                    "learning_objectives": [
                        "Understand CSS selectors and specificity",
                        "Apply box model concepts",
                        "Create basic layouts"
                    ]
                },
                {
                    "id": "css_layout",
                    "topic": ModuleTopic.CSS_LAYOUT,
                    "prerequisites": ["css_basics"],
                    "estimated_time": "3 hours",
                    "learning_objectives": [
                        "Master Flexbox and Grid",
                        "Create responsive designs",
                        "Understand positioning"
                    ]
                },
                {
                    "id": "neumorphism",
                    "topic": ModuleTopic.NEUMORPHISM,
                    "prerequisites": ["css_basics"],
                    "estimated_time": "2.5 hours",
                    "learning_objectives": [
                        "Create neumorphic designs",
                        "Understand light sources and shadows",
                        "Apply accessibility considerations"
                    ]
                },
                {
                    "id": "css_animations",
                    "topic": ModuleTopic.CSS_ANIMATIONS,
                    "prerequisites": ["css_basics"],
                    "estimated_time": "2 hours",
                    "learning_objectives": [
                        "Create CSS animations and transitions",
                        "Understand timing functions",
                        "Optimize animation performance"
                    ]
                },
                {
                    "id": "responsive_design",
                    "topic": ModuleTopic.RESPONSIVE_DESIGN,
                    "prerequisites": ["css_basics", "css_layout"],
                    "estimated_time": "2.5 hours",
                    "learning_objectives": [
                        "Implement media queries",
                        "Create mobile-first designs",
                        "Test across device sizes"
                    ]
                }
            ],
            "completion_requirements": {
                "minimum_score": 3.0,  # 3/5 average
                "max_time_per_module": "4 hours",
                "required_practical_exercises": 2
            }
        }
    
    def _initialize_session(self):
        """Initialize new or resume existing session"""
        print(f"\n🎓 INITIALIZING AI TUTOR SESSION")
        print(f"   User: {self.user_id}")
        print(f"   Session: {self.session_id}")
        print(f"   Topic: {self.current_topic.value}")
        print(f"   Mode: {self.teaching_mode.value}")
        
        # Check if user has existing progress
        user_progress = self.db.get_user_progress(self.user_id)
        
        if user_progress and user_progress.get("current_topic"):
            # Resume from last topic
            last_topic = user_progress["current_topic"]
            try:
                self.current_topic = ModuleTopic[last_topic.upper()]
                print(f"   Resuming from: {last_topic}")
            except:
                print(f"   Starting fresh: {self.current_topic.value}")
        
        # Update session state
        self.current_state = SessionState.PRIMING
        
        # Log session start
        self.db.log_session_start(
            user_id=self.user_id,
            session_id=self.session_id,
            topic=self.current_topic.value,
            mode=self.teaching_mode.value
        )
        
        # Log interaction
        self._log_interaction("system", "session_initialized", {
            "topic": self.current_topic.value,
            "mode": self.teaching_mode.value,
            "user_profile": {
                "learning_style": self.user_profile.learning_style,
                "pace": self.user_profile.pace
            }
        })
    
    def start_teaching(self) -> Dict[str, Any]:
        """
        Start the teaching process
        Returns first phase instructions
        """
        print(f"\n🚀 STARTING TEACHING PROCESS")
        print(f"   Current state: {self.current_state.value}")
        
        if self.current_state == SessionState.PRIMING:
            return self._start_priming_phase()
        elif self.current_state == SessionState.RELATIONAL_THINKING:
            return self._resume_relational_thinking()
        elif self.current_state == SessionState.INTERLEAVING:
            return self._resume_interleaving()
        elif self.current_state == SessionState.INTEGRATED_TESTING:
            return self._resume_integrated_testing()
        else:
            return self._handle_unexpected_state()
    
    def _start_priming_phase(self) -> Dict[str, Any]:
        """Start Phase 1: Priming"""
        print(f"\n📘 STARTING PHASE 1: PRIMING")
        
        # Create PrimingPhase instance
        self.priming_phase = PrimingPhase(
            llm=self.client,  # Note: Needs to be adapted for direct Gemini client
            topic=self.current_topic
        )
        
        # Execute priming phase
        priming_result = self.priming_phase.execute_priming_phase()
        
        # Store phase data
        self.phase_data["priming"] = priming_result
        
        # Update session state
        self._transition_to(SessionState.RELATIONAL_THINKING, "priming_completed")
        
        # Update metrics
        self._update_theory_time(10 * 60)  # Estimate 10 minutes
        
        # Log completion
        self.db.log_phase_completion(
            user_id=self.user_id,
            phase="priming",
            data={
                "topic": self.current_topic.value,
                "terminology_learned": len(priming_result.get("terminology", [])),
                "syntax_explained": len(priming_result.get("syntax_etymology", [])),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Prepare for next phase
        next_phase_prep = {
            "message": "Great! Now let's discover patterns in code.",
            "requires_user_action": False,
            "next_phase": "relational_thinking"
        }
        
        return {
            "status": "phase_completed",
            "phase": "priming",
            "result": priming_result,
            "summary": self.priming_phase.get_priming_summary(),
            "next_phase": next_phase_prep,
            "instructions": "Phase 1 complete. Ready for pattern discovery? (type 'yes' to continue)"
        }
    
    def _resume_relational_thinking(self) -> Dict[str, Any]:
        """Resume or start Phase 2: Relational Thinking"""
        print(f"\n🔍 RESUMING PHASE 2: RELATIONAL THINKING")
        
        if not self.relational_thinking:
            # Create new instance
            self.relational_thinking = RelationalThinkingPhase(
                gemini_client=self.client,
                topic=self.current_topic,
                priming_data=self.phase_data["priming"],
                user_id=self.user_id,
                max_attempts=self._get_max_attempts_for_mode()
            )
            
            # Start phase
            relational_start = self.relational_thinking.execute_phase()
            
            return {
                "status": "phase_started",
                "phase": "relational_thinking",
                "data": relational_start,
                "state": "awaiting_pattern_attempt",
                "instructions": "Look at the 3 examples. What pattern do you see?"
            }
        else:
            # Already have instance, return current state
            return self._get_current_relational_state()
    
    def _get_current_relational_state(self) -> Dict[str, Any]:
        """Get current state of relational thinking phase"""
        if not self.relational_thinking:
            return {"error": "No relational thinking phase active"}
        
        state = self.relational_thinking.state
        
        if state == DiscoveryState.SETUP:
            return {"status": "setup_complete", "instructions": "Examples presented"}
        elif state == DiscoveryState.DISCOVERY_PROMPT:
            return {"status": "awaiting_attempt", "instructions": "What pattern do you see?"}
        elif state == DiscoveryState.BLOCKING_LOOP:
            return {"status": "evaluating_attempt", "instructions": "Processing your answer..."}
        else:
            return {"status": state.value, "instructions": "Continue with phase"}
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input based on current state
        Main interaction handler
        """
        # Log interaction
        self._log_interaction("user", "input", {"text": user_input[:200]})
        
        # Update metrics
        self.session_metrics.interactions_count += 1
        
        # Route based on current state
        if self.current_state == SessionState.PRIMING:
            return self._process_priming_input(user_input)
        elif self.current_state == SessionState.RELATIONAL_THINKING:
            return self._process_relational_input(user_input)
        elif self.current_state == SessionState.INTERLEAVING:
            return self._process_interleaving_input(user_input)
        elif self.current_state == SessionState.INTEGRATED_TESTING:
            return self._process_testing_input(user_input)
        elif self.current_state == SessionState.PRACTICAL_APPLICATION:
            return self._process_practice_input(user_input)
        else:
            return {"error": f"Unknown state: {self.current_state}"}
    
    def _process_relational_input(self, user_input: str) -> Dict[str, Any]:
        """Process input during relational thinking phase"""
        if not self.relational_thinking:
            return {"error": "Relational thinking phase not initialized"}
        
        # Check for special commands
        if user_input.lower() in ["hint", "help", "give me a hint"]:
            return self._provide_hint("relational_thinking")
        
        if user_input.lower() in ["skip", "show answer"]:
            return self._skip_pattern_discovery()
        
        # Process as pattern discovery attempt
        attempt_result = self.relational_thinking.process_user_attempt(
            user_input=user_input,
            attempt_time=30  # Estimate 30 seconds thinking time
        )
        
        # Check if pattern resolved
        if attempt_result.get("status") == "pattern_resolved":
            # Store phase data
            self.phase_data["relational_thinking"] = attempt_result
            
            # Update progress
            self.progress_tracker.update_pattern_discovery(
                pattern_name=attempt_result.get("pattern_name", ""),
                score=attempt_result.get("discovery_score", 0),
                user_discovered=attempt_result.get("user_discovered", False)
            )
            
            # Check if ready for next phase
            if attempt_result.get("next_step") == "find_exceptions":
                # Move to exceptions phase
                exceptions_start = self.relational_thinking.start_exceptions_phase()
                return {
                    **attempt_result,
                    "next_action": "propose_exception",
                    "exceptions_instructions": exceptions_start
                }
            else:
                # Complete relational thinking phase
                return self._complete_relational_thinking(attempt_result)
        
        return attempt_result
    
    def _complete_relational_thinking(self, final_result: Dict) -> Dict[str, Any]:
        """Complete relational thinking phase and transition"""
        # Get phase completion data
        phase_log = self.relational_thinking.get_phase_log()
        
        # Update database
        self.db.log_phase_completion(
            user_id=self.user_id,
            phase="relational_thinking",
            data={
                "topic": self.current_topic.value,
                "pattern_discovered": final_result.get("pattern_name"),
                "discovery_score": final_result.get("discovery_score"),
                "user_discovered": final_result.get("user_discovered"),
                "exceptions_found": len(phase_log.get("exception_discovery", {}).get("exceptions_found", [])),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Transition to next phase
        self._transition_to(SessionState.INTERLEAVING, "relational_thinking_completed")
        
        # Start interleaving phase
        return self._start_interleaving_phase()
    
    def _start_interleaving_phase(self) -> Dict[str, Any]:
        """Start Phase 3: Interleaving"""
        print(f"\n🎭 STARTING PHASE 3: INTERLEAVING")
        
        # Create InterleavingPhase instance
        self.interleaving = InterleavingPhase(
            gemini_client=self.client,
            topic=self.current_topic,
            pattern_discovery_data=self.phase_data["relational_thinking"],
            user_id=self.user_id,
            student_db=self.db,
            thinking_level="high"
        )
        
        # Start phase
        interleaving_start = self.interleaving.execute_phase()
        
        return {
            "status": "phase_started",
            "phase": "interleaving",
            "data": interleaving_start,
            "state": "analogy_generation",
            "instructions": "Create a real-world analogy for the pattern"
        }
    
    def _process_interleaving_input(self, user_input: str) -> Dict[str, Any]:
        """Process input during interleaving phase"""
        if not self.interleaving:
            return {"error": "Interleaving phase not initialized"}
        
        # Get current state
        state = self.interleaving.state
        
        if state.value == "analogy_generation":
            # Evaluate analogy
            analogy_result = self.interleaving.evaluate_analogy(user_input)
            
            if analogy_result.get("next_phase") == "what_if_exploration":
                # Move to what-if scenarios
                what_if_start = self.interleaving.start_what_if_scenario()
                return {
                    **analogy_result,
                    "next_action": "submit_what_if_scenario",
                    "what_if_instructions": what_if_start
                }
            
            return analogy_result
        
        elif state.value == "what_if_exploration":
            # Evaluate what-if scenario
            scenario_result = self.interleaving.evaluate_what_if_scenario(user_input)
            
            if scenario_result.get("phase_complete"):
                # Move to compound questions
                compound_start = self.interleaving._generate_compound_question()
                return {
                    **scenario_result,
                    "next_action": "answer_compound_question",
                    "compound_question": compound_start
                }
            
            return scenario_result
        
        elif state.value == "compound_question":
            # Get current question ID (simplified - would track in real implementation)
            if self.interleaving.compound_questions:
                question_id = self.interleaving.compound_questions[0].question_id
                compound_result = self.interleaving.evaluate_compound_answer(
                    question_id=question_id,
                    user_answer=user_input
                )
                
                if compound_result.get("phase_complete"):
                    # Complete interleaving phase
                    return self._complete_interleaving_phase()
                
                return compound_result
        
        return {"error": f"Unknown interleaving state: {state.value}"}
    
    def _complete_interleaving_phase(self) -> Dict[str, Any]:
        """Complete interleaving phase and transition"""
        # Get completion data
        completion = self.interleaving.complete_phase()
        
        # Store phase data
        self.phase_data["interleaving"] = completion
        
        # Update database
        self.db.log_phase_completion(
            user_id=self.user_id,
            phase="interleaving",
            data={
                "topic": self.current_topic.value,
                "analogies_created": completion["performance_metrics"]["analogies_created"],
                "what_if_scenarios": completion["performance_metrics"]["what_if_scenarios"],
                "interleaving_score": completion["performance_metrics"]["interleaving_score"],
                "curiosity_score": completion["performance_metrics"]["curiosity_score"],
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Transition to next phase
        self._transition_to(SessionState.INTEGRATED_TESTING, "interleaving_completed")
        
        # Start integrated testing
        return self._start_integrated_testing()
    
    def _start_integrated_testing(self) -> Dict[str, Any]:
        """Start Phase 4: Integrated Testing"""
        print(f"\n🧪 STARTING PHASE 4: INTEGRATED TESTING")
        
        # Combine all previous phase data
        all_phase_data = {
            "priming": self.phase_data["priming"],
            "relational_thinking": self.phase_data["relational_thinking"],
            "interleaving": self.phase_data["interleaving"]
        }
        
        # Create IntegratedTestingPhase instance
        self.integrated_testing = IntegratedTestingPhase(
            gemini_client=self.client,
            topic=self.current_topic,
            all_phase_data=all_phase_data,
            user_id=self.user_id,
            student_db=self.db,
            thinking_level="high",
            question_count=3  # Configurable
        )
        
        # Start phase
        testing_start = self.integrated_testing.execute_phase()
        
        return {
            "status": "phase_started",
            "phase": "integrated_testing",
            "data": testing_start,
            "state": "answering_questions",
            "instructions": "Answer the integrated questions that combine current and past knowledge"
        }
    
    def _process_testing_input(self, user_input: str) -> Dict[str, Any]:
        """Process input during integrated testing"""
        if not self.integrated_testing:
            return {"error": "Integrated testing phase not initialized"}
        
        # Get current question
        current_question = self.integrated_testing.get_current_question()
        
        if not current_question:
            # No current question, might be between questions
            return {"status": "awaiting_question", "instructions": "Waiting for next question..."}
        
        # Check for hint request
        if user_input.lower() in ["hint", "help"]:
            hint = self.integrated_testing.get_hint(
                question_id=current_question["question_id"],
                hint_number=0
            )
            return {"status": "hint_provided", "hint": hint}
        
        # Submit answer
        answer_result = self.integrated_testing.submit_answer(
            question_id=current_question["question_id"],
            user_answer=user_input,
            time_spent_seconds=60,  # Estimate 1 minute
            confidence_rating=3  # Default confidence
        )
        
        # Check if testing complete
        if answer_result.get("next_action") == "complete_testing":
            return self._complete_integrated_testing()
        
        return answer_result
    
    def _complete_integrated_testing(self) -> Dict[str, Any]:
        """Complete integrated testing phase"""
        # Get completion data
        completion = self.integrated_testing.complete_testing()
        
        # Store phase data
        self.phase_data["integrated_testing"] = completion
        
        # Update database
        self.db.log_phase_completion(
            user_id=self.user_id,
            phase="integrated_testing",
            data={
                "topic": self.current_topic.value,
                "questions_answered": completion["performance_metrics"]["questions_answered"],
                "average_score": completion["performance_metrics"]["average_score"],
                "accuracy_rate": completion["performance_metrics"]["accuracy_rate"],
                "gaps_addressed": completion["performance_metrics"]["gaps_addressed"],
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Check 80/20 ratio
        theory_completion = self._check_theory_completion()
        
        if theory_completion:
            # All theory phases complete, move to practical application
            self._transition_to(SessionState.PRACTICAL_APPLICATION, "theory_completed")
            
            # Generate practical problems
            practical_problems = self.integrated_testing.get_practical_problems()
            
            return {
                "status": "theory_completed",
                "message": "🎉 All theory phases complete! Now for the 20% practice.",
                "theory_summary": self._generate_theory_summary(),
                "practical_problems": practical_problems,
                "next_phase": "practical_application",
                "instructions": "Start with the first practical problem"
            }
        else:
            return {"error": "Theory completion check failed"}
    
    def _check_theory_completion(self) -> bool:
        """Check if all theory phases are complete"""
        required_phases = ["priming", "relational_thinking", "interleaving", "integrated_testing"]
        
        for phase in required_phases:
            if not self.phase_data.get(phase):
                print(f"❌ Missing phase data: {phase}")
                return False
        
        # Check 80/20 ratio (simplified - would track actual time)
        total_theory_time = sum([
            self.phase_time_limits["priming"],
            self.phase_time_limits["relational_thinking"],
            self.phase_time_limits["interleaving"],
            self.phase_time_limits["integrated_testing"]
        ])
        
        # For now, assume theory is 80%
        theory_ratio = 0.8
        
        self.session_metrics.current_ratio = {
            "theory": theory_ratio,
            "practice": 1 - theory_ratio
        }
        
        print(f"✅ Theory completion check passed")
        print(f"   Theory/Practice ratio: {theory_ratio:.0%}/{100-theory_ratio*100:.0%}")
        
        return True
    
    def _generate_theory_summary(self) -> Dict[str, Any]:
        """Generate summary of theory phases"""
        summary = {
            "topic": self.current_topic.value,
            "phases_completed": ["priming", "relational_thinking", "interleaving", "integrated_testing"],
            "performance_summary": {},
            "knowledge_gains": [],
            "time_spent": f"~{sum(self.phase_time_limits.values()) / 60:.1f} minutes"
        }
        
        # Add phase-specific summaries
        if self.phase_data["priming"]:
            summary["knowledge_gains"].append(
                f"Learned {len(self.phase_data['priming'].get('terminology', []))} key terms"
            )
        
        if self.phase_data["relational_thinking"]:
            pattern_name = self.phase_data["relational_thinking"].get("pattern_name", "pattern")
            discovery_score = self.phase_data["relational_thinking"].get("discovery_score", 0)
            summary["performance_summary"]["pattern_discovery"] = f"{discovery_score}/5"
            summary["knowledge_gains"].append(f"Discovered '{pattern_name}' pattern")
        
        if self.phase_data["interleaving"]:
            metrics = self.phase_data["interleaving"].get("performance_metrics", {})
            summary["performance_summary"]["interleaving"] = metrics.get("interleaving_score", "N/A")
            summary["performance_summary"]["curiosity"] = metrics.get("curiosity_score", "N/A")
            summary["knowledge_gains"].append("Created analogies and explored edge cases")
        
        if self.phase_data["integrated_testing"]:
            metrics = self.phase_data["integrated_testing"].get("performance_metrics", {})
            summary["performance_summary"]["testing_accuracy"] = metrics.get("accuracy_rate", "N/A")
            summary["knowledge_gains"].append("Integrated concepts through testing")
        
        return summary
    
    def _process_practice_input(self, user_input: str) -> Dict[str, Any]:
        """Process input during practical application phase"""
        # This would handle the 20% practice phase
        # For now, placeholder implementation
        
        return {
            "status": "practice_phase",
            "message": "Practical application phase - coming soon!",
            "current_activity": "practice_problem",
            "instructions": "Work on the practical problems generated in Phase 4"
        }
    
    def _provide_hint(self, phase: str) -> Dict[str, Any]:
        """Provide hint based on current phase"""
        hint_count = self.session_metrics.hints_used
        
        # Check hint limits
        max_hints = self.max_hints_per_phase.get(phase, 2)
        if hint_count >= max_hints:
            return {
                "status": "hint_limit_reached",
                "message": f"You've used all {max_hints} hints for this phase.",
                "suggestion": "Try to reason through the problem step by step."
            }
        
        # Provide phase-specific hint
        if phase == "relational_thinking" and self.relational_thinking:
            hint = self.relational_thinking.provide_hint()
            self.session_metrics.hints_used += 1
            return {"status": "hint_provided", "hint": hint}
        
        elif phase == "interleaving" and self.interleaving:
            # Simplified hint for interleaving
            self.session_metrics.hints_used += 1
            return {
                "status": "hint_provided",
                "hint": {
                    "content": "Think about how this concept appears in everyday life.",
                    "type": "analogy_prompt"
                }
            }
        
        # Generic hint
        self.session_metrics.hints_used += 1
        return {
            "status": "hint_provided",
            "hint": "Look for patterns and relationships between the examples."
        }
    
    def _skip_pattern_discovery(self) -> Dict[str, Any]:
        """Skip pattern discovery after maximum attempts"""
        if not self.relational_thinking:
            return {"error": "No relational thinking phase active"}
        
        # Force pattern resolution
        forced_result = self.relational_thinking._handle_pattern_resolution({
            "score": 0,
            "feedback": "Pattern revealed by request"
        })
        
        # Store phase data
        self.phase_data["relational_thinking"] = forced_result
        
        # Update metrics
        self.session_metrics.corrections_made += 1
        
        # Move to exceptions phase
        exceptions_start = self.relational_thinking.start_exceptions_phase()
        
        return {
            "status": "pattern_revealed",
            "message": "Pattern revealed. Let's explore its exceptions.",
            "pattern_details": forced_result.get("pattern_details", {}),
            "next_action": "propose_exception",
            "exceptions_instructions": exceptions_start
        }
    
    def _transition_to(self, new_state: SessionState, reason: str):
        """Transition to new state with logging"""
        print(f"\n🔄 TRANSITION: {self.current_state.value} → {new_state.value}")
        print(f"   Reason: {reason}")
        
        # Create transition record
        transition = PhaseTransition(
            from_phase=self.current_state,
            to_phase=new_state,
            transition_condition=reason,
            data_passed={},
            timestamp=datetime.now().isoformat()
        )
        
        self.phase_transitions.append(transition)
        self.previous_state = self.current_state
        self.current_state = new_state
        
        # Log transition
        self._log_interaction("system", "state_transition", {
            "from": transition.from_phase.value,
            "to": transition.to_phase.value,
            "reason": reason,
            "timestamp": transition.timestamp
        })
    
    def _update_theory_time(self, seconds: int):
        """Update theory time tracking"""
        self.session_metrics.theory_time_seconds += seconds
        
        # Calculate current ratio
        total_time = self.session_metrics.theory_time_seconds + self.session_metrics.practice_time_seconds
        
        if total_time > 0:
            theory_ratio = self.session_metrics.theory_time_seconds / total_time
            self.session_metrics.current_ratio = {
                "theory": theory_ratio,
                "practice": 1 - theory_ratio
            }
            
            # Check if ratio is maintained
            if theory_ratio > 0.85:  # Exceeding 85% theory
                print(f"⚠️  Warning: Theory ratio at {theory_ratio:.0%} - consider more practice")
    
    def _log_interaction(self, actor: str, action: str, data: Dict):
        """Log user-system interaction"""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "actor": actor,
            "action": action,
            "data": data,
            "session_state": self.current_state.value,
            "topic": self.current_topic.value
        }
        
        self.interaction_history.append(interaction)
        
        # Also log to database
        self.db.log_interaction(self.user_id, interaction)
    
    def _get_max_attempts_for_mode(self) -> int:
        """Get maximum attempts based on teaching mode"""
        attempts_map = {
            TeachingMode.GUIDED: 5,
            TeachingMode.EXPLORATORY: 3,
            TeachingMode.ACCELERATED: 2,
            TeachingMode.REMEDIAL: 7
        }
        return attempts_map.get(self.teaching_mode, 5)
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "current_state": self.current_state.value,
            "current_topic": self.current_topic.value,
            "teaching_mode": self.teaching_mode.value,
            "phase_progress": list(self.phase_data.keys()),
            "metrics": {
                "interactions": self.session_metrics.interactions_count,
                "hints_used": self.session_metrics.hints_used,
                "theory_practice_ratio": self.session_metrics.current_ratio,
                "session_duration": f"{(time.time() - datetime.fromisoformat(self.session_metrics.start_time).timestamp()):.0f}s"
            },
            "user_profile": {
                "learning_style": self.user_profile.learning_style,
                "pace": self.user_profile.pace,
                "confidence": self.user_profile.confidence_level
            }
        }
    
    def pause_session(self) -> Dict[str, Any]:
        """Pause current session for later resumption"""
        self.previous_state = self.current_state
        self.current_state = SessionState.PAUSED
        
        # Save session state to database
        session_state = {
            "current_state": self.previous_state.value,
            "current_topic": self.current_topic.value,
            "phase_data": self.phase_data,
            "session_metrics": self.__dict_to_serializable(self.session_metrics.__dict__),
            "interaction_history": self.interaction_history[-50:],  # Last 50 interactions
            "phase_transitions": [
                {
                    "from": t.from_phase.value,
                    "to": t.to_phase.value,
                    "reason": t.transition_condition,
                    "timestamp": t.timestamp
                }
                for t in self.phase_transitions
            ]
        }
        
        self.db.save_session_state(self.user_id, self.session_id, session_state)
        
        return {
            "status": "session_paused",
            "session_id": self.session_id,
            "paused_at": datetime.now().isoformat(),
            "resume_info": f"Use session_id '{self.session_id}' to resume"
        }
    
    def resume_session(self, session_state: Dict) -> bool:
        """Resume session from saved state"""
        try:
            # Restore state
            self.current_state = SessionState(session_state["current_state"])
            self.current_topic = ModuleTopic[session_state["current_topic"].upper()]
            self.phase_data = session_state["phase_data"]
            
            # Restore metrics
            metrics_data = session_state["session_metrics"]
            self.session_metrics = SessionMetrics(**metrics_data)
            
            # Restore transitions
            self.phase_transitions = [
                PhaseTransition(
                    from_phase=SessionState(t["from"]),
                    to_phase=SessionState(t["to"]),
                    transition_condition=t["reason"],
                    data_passed={},
                    timestamp=t["timestamp"]
                )
                for t in session_state.get("phase_transitions", [])
            ]
            
            print(f"✅ Session resumed: {self.session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to resume session: {e}")
            return False
    
    def complete_session(self) -> Dict[str, Any]:
        """Complete current session with summary"""
        # Calculate final metrics
        session_duration = time.time() - datetime.fromisoformat(self.session_metrics.start_time).timestamp()
        
        # Generate session summary
        summary = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "topic": self.current_topic.value,
            "start_time": self.session_metrics.start_time,
            "end_time": datetime.now().isoformat(),
            "duration_seconds": int(session_duration),
            "phases_completed": list(self.phase_data.keys()),
            "final_metrics": {
                "total_interactions": self.session_metrics.interactions_count,
                "hints_used": self.session_metrics.hints_used,
                "concepts_mastered": self.session_metrics.concepts_mastered,
                "gaps_identified": self.session_metrics.gaps_identified,
                "final_theory_practice_ratio": self.session_metrics.current_ratio
            },
            "achievements": self._calculate_session_achievements(),
            "next_recommendations": self._generate_next_recommendations()
        }
        
        # Log session completion
        self.db.log_session_completion(self.user_id, self.session_id, summary)
        
        # Update user progress
        self.db.update_user_progress(
            user_id=self.user_id,
            updates={
                "current_topic": self.current_topic.value,
                "last_session": self.session_id,
                "total_sessions": self.user_profile.session_history + 1,
                "last_updated": datetime.now().isoformat()
            }
        )
        
        # Update state
        self.current_state = SessionState.COMPLETED
        
        return {
            "status": "session_completed",
            "summary": summary,
            "message": "🎉 Great work! Session completed successfully."
        }
    
    def _calculate_session_achievements(self) -> List[str]:
        """Calculate achievements earned in this session"""
        achievements = []
        
        # Check phase completion
        if len(self.phase_data) >= 4:
            achievements.append("Theory Master")
        
        # Check hint usage
        if self.session_metrics.hints_used == 0:
            achievements.append("Independent Learner")
        elif self.session_metrics.hints_used <= 2:
            achievements.append("Resourceful Thinker")
        
        # Check interaction count
        if self.session_metrics.interactions_count >= 20:
            achievements.append("Active Participant")
        
        # Check ratio maintenance
        ratio = self.session_metrics.current_ratio.get("theory", 0)
        if 0.75 <= ratio <= 0.85:  # Within 80/20 target range
            achievements.append("Balanced Learner")
        
        return achievements if achievements else ["Session Completer"]
    
    def _generate_next_recommendations(self) -> List[str]:
        """Generate next learning recommendations"""
        recommendations = []
        
        # Based on performance
        if self.session_metrics.concepts_mastered >= 3:
            recommendations.append("Move to next topic in curriculum")
        else:
            recommendations.append("Review current topic before advancing")
        
        # Based on hints used
        if self.session_metrics.hints_used >= 5:
            recommendations.append("Practice more foundational concepts")
        
        # Based on ratio
        if self.session_metrics.current_ratio.get("theory", 0) > 0.85:
            recommendations.append("Focus on practical application next session")
        
        # Next topic suggestion
        next_topic = self._suggest_next_topic()
        if next_topic:
            recommendations.append(f"Next topic: {next_topic.value}")
        
        return recommendations
    
    def _suggest_next_topic(self) -> Optional[ModuleTopic]:
        """Suggest next topic based on curriculum"""
        current_module = None
        for module in self.curriculum["modules"]:
            if module["topic"] == self.current_topic:
                current_module = module
                break
        
        if not current_module:
            return None
        
        # Find next module that has prerequisites satisfied
        for module in self.curriculum["modules"]:
            if module == current_module:
                continue
            
            prerequisites = module.get("prerequisites", [])
            if not prerequisites or current_module["id"] in prerequisites:
                return module["topic"]
        
        return None
    
    def __dict_to_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format"""
        if isinstance(obj, dict):
            return {k: self.__dict_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.__dict_to_serializable(v) for v in obj]
        elif hasattr(obj, '__dict__'):
            return self.__dict_to_serializable(obj.__dict__)
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)


# ============================================================================
# SIMPLIFIED VERSION FOR INITIAL IMPLEMENTATION
# ============================================================================

class SimpleTeachingOrchestrator:
    """
    Simplified version for initial implementation
    Focuses on core functionality without all features
    """
    
    def __init__(self, gemini_client, user_id, topic=ModuleTopic.CSS_BASICS):
        self.client = gemini_client
        self.user_id = user_id
        self.topic = topic
        
        # Simple state tracking
        self.current_phase = "priming"
        self.phase_data = {}
        self.session_active = True
        
        # Mock database (replace with real one)
        self.db = MockDatabase()
        
        print(f"\n🎓 SIMPLE AI TUTOR STARTED")
        print(f"   User: {user_id}")
        print(f"   Topic: {topic.value}")
    
    def start(self):
        """Start the teaching process"""
        if self.current_phase == "priming":
            return self._run_priming_phase()
        elif self.current_phase == "relational_thinking":
            return self._run_relational_thinking()
        elif self.current_phase == "interleaving":
            return self._run_interleaving()
        elif self.current_phase == "integrated_testing":
            return self._run_integrated_testing()
        else:
            return {"error": "Unknown phase"}
    
    def _run_priming_phase(self):
        """Run Phase 1: Priming"""
        print("\n📘 PHASE 1: PRIMING")
        
        # Create priming phase
        from core.priming_phase import PrimingPhase
        
        priming = PrimingPhase(self.client, self.topic)
        result = priming.execute_priming_phase()
        
        # Store data
        self.phase_data["priming"] = result
        
        # Move to next phase
        self.current_phase = "relational_thinking"
        
        return {
            "phase": "priming",
            "status": "complete",
            "data": result,
            "next": "relational_thinking",
            "instructions": "Type 'next' to continue to pattern discovery"
        }
    
    def _run_relational_thinking(self):
        """Run Phase 2: Relational Thinking"""
        print("\n🔍 PHASE 2: RELATIONAL THINKING")
        
        from core.relational_thinking import RelationalThinkingPhase
        
        relational = RelationalThinkingPhase(
            gemini_client=self.client,
            topic=self.topic,
            priming_data=self.phase_data["priming"],
            user_id=self.user_id,
            max_attempts=3
        )
        
        result = relational.execute_phase()
        
        # Store instance for later interaction
        self.relational_instance = relational
        
        return {
            "phase": "relational_thinking",
            "status": "started",
            "data": result,
            "instructions": "Look at the 3 examples and describe the pattern you see"
        }
    
    def process_input(self, user_input):
        """Process user input based on current phase"""
        if not self.session_active:
            return {"error": "Session not active"}
        
        if self.current_phase == "relational_thinking":
            return self._process_relational_input(user_input)
        elif self.current_phase == "interleaving":
            return self._process_interleaving_input(user_input)
        elif self.current_phase == "integrated_testing":
            return self._process_testing_input(user_input)
        else:
            return {"error": f"Cannot process input in phase: {self.current_phase}"}
    
    def _process_relational_input(self, user_input):
        """Process input for relational thinking"""
        if not hasattr(self, 'relational_instance'):
            return {"error": "Relational thinking not initialized"}
        
        # Special commands
        if user_input.lower() == "next":
            # Skip to next phase for demo
            return self._move_to_interleaving()
        
        if user_input.lower() == "hint":
            hint = self.relational_instance.provide_hint()
            return {"type": "hint", "hint": hint}
        
        # Process as pattern attempt
        result = self.relational_instance.process_user_attempt(user_input, 30)
        
        if result.get("status") == "pattern_resolved":
            # Store data
            self.phase_data["relational_thinking"] = result
            
            # Move to next phase
            return self._move_to_interleaving()
        
        return result
    
    def _move_to_interleaving(self):
        """Move to interleaving phase"""
        self.current_phase = "interleaving"
        
        print("\n🎭 MOVING TO PHASE 3: INTERLEAVING")
        
        return {
            "phase": "transition",
            "from": "relational_thinking",
            "to": "interleaving",
            "message": "Great! Now let's create analogies and explore edge cases.",
            "instructions": "Type 'start' to begin interleaving phase"
        }
    
    def get_status(self):
        """Get current status"""
        return {
            "user_id": self.user_id,
            "current_phase": self.current_phase,
            "topic": self.topic.value,
            "phases_completed": list(self.phase_data.keys()),
            "session_active": self.session_active
        }


class MockDatabase:
    """Mock database for testing"""
    def log_interaction(self, user_id, interaction):
        print(f"[DB] Logged interaction: {interaction.get('action')}")
    
    def log_phase_completion(self, user_id, phase, data):
        print(f"[DB] Logged phase completion: {phase}")


# ============================================================================
# DEMONSTRATION
# ============================================================================

def demonstrate_orchestrator():
    """Demonstrate TeachingOrchestrator"""
    
    print("🚀 TEACHING ORCHESTRATOR DEMONSTRATION")
    print("=" * 60)
    
    # Mock Gemini client
    class MockGeminiClient:
        def __init__(self):
            self.models = self.Models()
        
        class Models:
            def generate_content(self, model, contents):
                print(f"\n[Gemini called: {contents[:50]}...]")
                
                response_text = ""
                
                if "terminology" in contents.lower() or "key terms" in contents.lower():
                    response_text = '''
                    [
                        {
                            "term": "Selector",
                            "definition": "Matches elements",
                            "acronym": false
                        },
                        {
                            "term": "Property",
                            "definition": "Style attribute",
                            "acronym": false
                        },
                        {
                            "term": "Value",
                            "definition": "Setting",
                            "acronym": false
                        }
                    ]
                    '''
                elif "syntax" in contents.lower() or "etymology" in contents.lower():
                    response_text = '''
                    [
                        {
                            "syntax_element": ".",
                            "symbol_name": "Dot",
                            "origin": "Greek",
                            "logic_reason": "Grouping",
                            "memory_hook": "Connects things"
                        }
                    ]
                    '''
                else:
                    response_text = '{"test": "response"}'
                
                class Response:
                    text = response_text
                
                return type('obj', (object,), {'text': Response.text})()
    
    # Create simple orchestrator
    mock_client = MockGeminiClient()
    
    orchestrator = SimpleTeachingOrchestrator(
        gemini_client=mock_client,
        user_id="test_user_001",
        topic=ModuleTopic.CSS_BASICS
    )
    
    print("\n1. Starting session...")
    start_result = orchestrator.start()
    
    print(f"\n2. Phase: {start_result['phase']}")
    print(f"   Status: {start_result['status']}")
    
    if start_result['phase'] == 'priming':
        print(f"\n3. Priming complete, moving to relational thinking...")
        
        # Simulate user saying 'next'
        next_result = orchestrator.process_input("next")
        
        print(f"\n4. Now in: {next_result.get('to')}")
        print(f"   Message: {next_result.get('message')}")
    
    print(f"\n5. Current status:")
    status = orchestrator.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print(f"\n✅ TeachingOrchestrator implementation ready!")


if __name__ == "__main__":
    demonstrate_orchestrator()