"""
INTEGRATED TESTING PHASE (Phase 4)
Creates compound questions that require both current and past knowledge
Uses knowledge gaps from Database Doc 4 for spaced repetition
"""
import json
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from google import genai
from google.genai import types

from core.priming_phase import ModuleTopic
from database.student_database import StudentDatabase

class QuestionType(Enum):
    """Types of integrated test questions"""
    CODE_ANALYSIS = "code_analysis"  # Analyze buggy code
    CODE_CORRECTION = "code_correction"  # Fix broken code
    DESIGN_CHALLENGE = "design_challenge"  # Create solution
    DEBUGGING = "debugging"  # Find and explain bug
    PERFORMANCE_OPTIMIZATION = "performance_optimization"  # Improve code
    ACCESSIBILITY_AUDIT = "accessibility_audit"  # Audit for accessibility

class DifficultyLevel(Enum):
    """Question difficulty levels"""
    BEGINNER = "beginner"  # Single concept, clear answer
    INTERMEDIATE = "intermediate"  # 2-3 concepts, some interpretation
    ADVANCED = "advanced"  # Multiple concepts, open-ended
    EXPERT = "expert"  # Real-world complexity, multiple solutions

@dataclass
class IntegratedQuestion:
    """Represents an integrated test question"""
    question_id: str
    question_type: QuestionType
    question_text: str
    code_snippet: Optional[str] = None
    current_topic: str = ""
    past_topics: List[str] = field(default_factory=list)
    targeted_gaps: List[str] = field(default_factory=list)
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    expected_time_minutes: int = 5
    hints_available: List[str] = field(default_factory=list)
    scoring_rubric: Dict[str, Any] = field(default_factory=dict)
    model_answer: Optional[str] = None
    common_mistakes: List[str] = field(default_factory=list)

@dataclass
class UserAnswer:
    """Represents user's answer to integrated question"""
    answer_id: str
    question_id: str
    user_response: str
    time_spent_seconds: int = 0
    scores: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    gap_addressed: bool = False
    feedback: str = ""
    timestamp: str = ""
    improvements_needed: List[str] = field(default_factory=list)
    confidence_rating: int = 0  # 1-5, user's self-rated confidence

@dataclass
class KnowledgeReinforcement:
    """Tracks which knowledge gaps were reinforced"""
    gap_id: str
    concept: str
    reinforcement_score: int = 0  # 0-5, how well gap was addressed
    questions_attempted: int = 0
    correct_attempts: int = 0
    last_reinforced: str = ""
    next_review_date: str = ""

class IntegratedTestingPhase:
    """
    Implements Phase 4: Integrated Testing
    Creates compound questions mixing current topic with past knowledge gaps
    Implements spaced repetition based on Database Doc 4
    """
    
    def __init__(
        self,
        gemini_client: genai.Client,
        topic: ModuleTopic,
        all_phase_data: Dict,  # Combined data from previous 3 phases
        user_id: str,
        student_db: StudentDatabase,
        thinking_level: str = "high",
        question_count: int = 3
    ):
        """
        Initialize Integrated Testing Phase
        
        Args:
            gemini_client: Initialized Gemini client
            topic: Current module topic
            all_phase_data: Combined results from Priming, Relational, Interleaving
            user_id: Unique user identifier
            student_db: StudentDatabase instance
            thinking_level: "high" or "low" for Gemini 3 Pro
            question_count: Number of integrated questions to generate
        """
        self.client = gemini_client
        self.topic = topic
        self.all_phase_data = all_phase_data
        self.user_id = user_id
        self.db = student_db
        self.thinking_level = thinking_level
        self.question_count = min(max(question_count, 1), 5)  # 1-5 questions
        
        # State tracking
        self.current_question_index = 0
        self.questions_answered = 0
        self.correct_answers = 0
        self.total_testing_time = 0
        
        # Data storage
        self.integrated_questions: List[IntegratedQuestion] = []
        self.user_answers: List[UserAnswer] = []
        self.knowledge_reinforcements: List[KnowledgeReinforcement] = []
        self.practical_problems_generated: List[Dict] = []
        
        # Get knowledge gaps (from Database Doc 4)
        self.knowledge_gaps = self.db.get_knowledge_gaps(self.user_id)
        self.active_gaps = [gap for gap in self.knowledge_gaps 
                           if not gap.get("addressed", False)]
        
        # Get user's learning history
        self.learning_history = self.db.get_learning_history(self.user_id)
        
        # Phase log
        self.phase_log = {
            "phase": "integrated_testing",
            "topic": topic.value,
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "questions_generated": 0,
            "questions_answered": 0,
            "average_score": 0,
            "gaps_targeted": [],
            "gaps_addressed": [],
            "testing_duration": 0,
            "confidence_trend": [],
            "practical_problems": []
        }
        
        # Model selection
        self.model = "gemini-1.5-pro-latest"
        
        # Load topic-specific testing configurations
        self._load_testing_configurations()
    
    def _load_testing_configurations(self):
        """Load topic-specific testing strategies"""
        self.testing_configs = {
            ModuleTopic.CSS_BASICS: {
                "question_types": [QuestionType.CODE_CORRECTION, QuestionType.DEBUGGING],
                "code_contexts": ["responsive layout", "form styling", "navigation menu"],
                "common_integrations": ["HTML semantics", "browser dev tools", "CSS resets"]
            },
            ModuleTopic.NEUMORPHISM: {
                "question_types": [QuestionType.DESIGN_CHALLENGE, QuestionType.ACCESSIBILITY_AUDIT],
                "code_contexts": ["button design", "card components", "form elements"],
                "common_integrations": ["color theory", "user experience", "performance considerations"]
            },
            ModuleTopic.CSS_ANIMATIONS: {
                "question_types": [QuestionType.PERFORMANCE_OPTIMIZATION, QuestionType.CODE_ANALYSIS],
                "code_contexts": ["loading animations", "interactive elements", "page transitions"],
                "common_integrations": ["JavaScript timing", "user preferences", "battery considerations"]
            }
        }
        
        self.current_config = self.testing_configs.get(
            self.topic,
            self.testing_configs[ModuleTopic.CSS_BASICS]
        )
    
    def execute_phase(self) -> Dict[str, Any]:
        """
        Main entry point: execute integrated testing phase
        
        Returns:
            Dict with first question and testing instructions
        """
        print(f"\n{'='*60}")
        print(f"PHASE 4: INTEGRATED TESTING - {self.topic.value.upper()}")
        print(f"{'='*60}")
        
        # Generate integrated questions
        self._generate_integrated_questions()
        
        if not self.integrated_questions:
            return {
                "status": "error",
                "message": "Could not generate integrated questions",
                "fallback": self._create_fallback_question()
            }
        
        # Get first question
        first_question = self._format_question_for_display(0)
        
        # Calculate testing metrics
        total_gaps_targeted = len(set(
            gap for q in self.integrated_questions 
            for gap in q.targeted_gaps
        ))
        
        return {
            "status": "testing_started",
            "total_questions": len(self.integrated_questions),
            "current_question": 1,
            "question": first_question,
            "instructions": self._get_testing_instructions(),
            "scoring_info": self._get_scoring_information(),
            "time_recommendation": "Spend 5-10 minutes per question",
            "gaps_targeted": total_gaps_targeted,
            "question_types": [q.question_type.value for q in self.integrated_questions],
            "difficulty_distribution": self._calculate_difficulty_distribution(),
            "next_action": "answer_question"
        }
    
    def _generate_integrated_questions(self):
        """
        Generate compound questions integrating current topic with past knowledge gaps
        Uses spaced repetition based on gap severity and last review
        """
        print(f"\n🧠 Generating {self.question_count} integrated questions...")
        
        # Select knowledge gaps to target (spaced repetition algorithm)
        gaps_to_target = self._select_gaps_for_review()
        
        if not gaps_to_target and not self.active_gaps:
            # No gaps to target, create general integration questions
            gaps_to_target = [{"concept": "general_integration", "gap_id": "general"}]
        
        # Determine question types based on topic and gaps
        question_types = self._determine_question_types(gaps_to_target)
        
        # Generate each question
        for i in range(self.question_count):
            # Select gap(s) for this question
            if gaps_to_target:
                target_gap = gaps_to_target[i % len(gaps_to_target)]
            else:
                target_gap = {"concept": "general_web_development", "gap_id": f"general_{i}"}
            
            # Generate question
            question = self._generate_single_question(i, target_gap, question_types[i % len(question_types)])
            
            if question:
                self.integrated_questions.append(question)
        
        # Update phase log
        self.phase_log["questions_generated"] = len(self.integrated_questions)
        self.phase_log["gaps_targeted"] = [
            gap["gap_id"] for gap in gaps_to_target[:self.question_count]
        ]
        
        print(f"✅ Generated {len(self.integrated_questions)} integrated questions")
        unique_gaps = set(g['gap_id'] for g in gaps_to_target)
        print(f"   Targeting {len(unique_gaps)} knowledge gaps")
    
    def _select_gaps_for_review(self) -> List[Dict]:
        """
        Select knowledge gaps for review using spaced repetition algorithm
        Prioritizes:
        1. High severity gaps
        2. Gaps not recently reviewed
        3. Gaps related to current topic
        """
        if not self.active_gaps:
            return []
        
        # Score each gap for review priority
        gap_scores = []
        
        for gap in self.active_gaps:
            score = 0
            
            # 1. Severity (higher = more priority)
            severity = gap.get("severity", 1)
            score += severity * 10
            
            # 2. Time since last review (longer = more priority)
            last_reviewed = gap.get("last_reviewed", "")
            if last_reviewed:
                try:
                    last_date = datetime.strptime(last_reviewed, "%Y-%m-%d %H:%M:%S")
                    days_since = (datetime.now() - last_date).days
                    score += min(days_since * 2, 20)  # Cap at 20
                except:
                    score += 15  # Never reviewed
            else:
                score += 15  # Never reviewed
            
            # 3. Relevance to current topic
            if self._is_gap_relevant_to_topic(gap):
                score += 10
            
            # 4. Number of times addressed (fewer = more priority)
            times_addressed = gap.get("times_addressed", 0)
            score -= times_addressed * 5
            
            gap_scores.append((score, gap))
        
        # Sort by score (descending)
        gap_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Select top gaps (max 1 gap per question)
        selected_gaps = [gap for _, gap in gap_scores[:self.question_count]]
        
        return selected_gaps
    
    def _is_gap_relevant_to_topic(self, gap: Dict) -> bool:
        """Check if knowledge gap is relevant to current topic"""
        gap_topic = gap.get("related_module", "").lower()
        current_topic = self.topic.value.lower()
        
        # Direct match
        if gap_topic == current_topic:
            return True
        
        # Related topics
        topic_groups = {
            "css": ["css_basics", "css_layout", "css_animations"],
            "design": ["neumorphism", "css_animations", "responsive_design"]
        }
        
        for group, topics in topic_groups.items():
            if gap_topic in topics and current_topic in topics:
                return True
        
        return False
    
    def _determine_question_types(self, gaps: List[Dict]) -> List[QuestionType]:
        """Determine appropriate question types based on gaps and topic"""
        base_types = self.current_config["question_types"]
        
        # Adjust based on gap types
        question_types = []
        
        for i in range(self.question_count):
            if i < len(gaps):
                gap = gaps[i]
                gap_concept = gap.get("concept", "").lower()
                
                if "debug" in gap_concept or "bug" in gap_concept:
                    question_types.append(QuestionType.DEBUGGING)
                elif "performance" in gap_concept:
                    question_types.append(QuestionType.PERFORMANCE_OPTIMIZATION)
                elif "accessibility" in gap_concept:
                    question_types.append(QuestionType.ACCESSIBILITY_AUDIT)
                elif "design" in gap_concept:
                    question_types.append(QuestionType.DESIGN_CHALLENGE)
                else:
                    question_types.append(base_types[i % len(base_types)])
            else:
                question_types.append(base_types[i % len(base_types)])
        
        return question_types
    
    def _generate_single_question(self, index: int, target_gap: Dict, 
                                question_type: QuestionType) -> Optional[IntegratedQuestion]:
        """Generate a single integrated question"""
        
        # Get context from previous phases
        priming_data = self.all_phase_data.get("priming", {})
        relational_data = self.all_phase_data.get("relational_thinking", {})
        interleaving_data = self.all_phase_data.get("interleaving", {})
        
        # Prepare prompt
        prompt = f"""
        Generate an INTEGRATED TEST QUESTION for web development.
        
        CURRENT TOPIC: {self.topic.value}
        TARGETED KNOWLEDGE GAP: {target_gap.get('concept', 'General integration')}
        GAP CONTEXT: {target_gap.get('root_cause', 'Needs reinforcement')}
        
        QUESTION TYPE: {question_type.value}
        
        REQUIREMENTS:
        1. Must require understanding of BOTH current topic AND past concept
        2. Should be practical/coding-oriented
        3. Include a code snippet if appropriate
        4. Make it challenging but solvable for intermediate learner
        5. Test application, not just recall
        
        CONTEXT FROM PREVIOUS LEARNING:
        - Key terms learned: {', '.join([t.get('term', '') for t in priming_data.get('terminology', [])[:3]])}
        - Pattern discovered: {relational_data.get('pattern_name', 'N/A')}
        - Mental model: {relational_data.get('mental_model', 'N/A')}
        
        QUESTION STRUCTURE:
        1. Scenario/context description
        2. Specific task or problem
        3. Code snippet (if applicable)
        4. Clear question
        
        Return JSON:
        {{
            "question_text": "The complete question",
            "code_snippet": "Relevant HTML/CSS/JS code or null",
            "difficulty": "beginner/intermediate/advanced",
            "expected_time_minutes": 3-10,
            "scoring_rubric": {{
                "current_topic_application": "0-5 points",
                "past_concept_integration": "0-5 points",
                "solution_correctness": "0-5 points",
                "code_quality": "0-5 points",
                "explanation_clarity": "0-5 points"
            }},
            "model_answer": "Example correct answer",
            "common_mistakes": ["list of common errors"],
            "hints": ["hint1", "hint2", "hint3"],
            "learning_objectives": ["what this question tests"],
            "real_world_relevance": "Why this matters"
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    thinking_config=types.ThinkingConfig(
                        thinking_level=self.thinking_level
                    )
                )
            )
            
            question_data = json.loads(response.text)
            
            # Create question object
            question = IntegratedQuestion(
                question_id=f"integrated_{int(time.time())}_{index}_{self.user_id}",
                question_type=question_type,
                question_text=question_data["question_text"],
                code_snippet=question_data.get("code_snippet"),
                current_topic=self.topic.value,
                past_topics=[target_gap.get("concept", "past_concept")],
                targeted_gaps=[target_gap.get("gap_id", "general")],
                difficulty=DifficultyLevel(question_data.get("difficulty", "intermediate")),
                expected_time_minutes=question_data.get("expected_time_minutes", 5),
                hints_available=question_data.get("hints", []),
                scoring_rubric=question_data.get("scoring_rubric", {}),
                model_answer=question_data.get("model_answer"),
                common_mistakes=question_data.get("common_mistakes", [])
            )
            
            return question
            
        except Exception as e:
            print(f"⚠️  Error generating question {index}: {e}")
            return None
    
    def _format_question_for_display(self, question_index: int) -> Dict[str, Any]:
        """Format question for display to user"""
        if question_index >= len(self.integrated_questions):
            return {}
        
        question = self.integrated_questions[question_index]
        
        formatted = {
            "question_id": question.question_id,
            "question_number": question_index + 1,
            "total_questions": len(self.integrated_questions),
            "type": question.question_type.value,
            "difficulty": question.difficulty.value,
            "text": question.question_text,
            "expected_time": f"{question.expected_time_minutes} minutes",
            "hints_available": len(question.hints_available),
            "targeted_gaps": question.targeted_gaps,
            "past_topics_integrated": question.past_topics
        }
        
        if question.code_snippet:
            formatted["code_snippet"] = question.code_snippet
            formatted["code_language"] = self._detect_code_language(question.code_snippet)
        
        # Add scoring information
        if question.scoring_rubric:
            formatted["scoring_criteria"] = list(question.scoring_rubric.keys())
        
        return formatted
    
    def _detect_code_language(self, code: str) -> str:
        """Detect programming language from code snippet"""
        if "<!DOCTYPE" in code or "<html" in code:
            return "html"
        elif "{" in code and ":" in code and ";" in code:  # Basic CSS detection
            return "css"
        elif "function" in code or "const " in code or "let " in code:
            return "javascript"
        else:
            return "mixed"
    
    def _get_testing_instructions(self) -> str:
        """Get instructions for integrated testing"""
        instructions = [
            "🧪 INTEGRATED TESTING INSTRUCTIONS:",
            "",
            "1. These questions test your ability to COMBINE concepts",
            "2. You'll need both CURRENT knowledge and PAST learning",
            "3. Take your time - quality matters more than speed",
            "4. Explain your thinking, not just the final answer",
            "5. Use the hints if you get stuck (available for each question)",
            "",
            f"📊 You have {len(self.integrated_questions)} questions to complete",
            f"⏱️  Estimated time: {sum(q.expected_time_minutes for q in self.integrated_questions)} minutes",
            "",
            "Remember: The goal is to find connections between concepts!"
        ]
        
        return "\n".join(instructions)
    
    def _get_scoring_information(self) -> Dict[str, Any]:
        """Get information about scoring"""
        if not self.integrated_questions:
            return {}
        
        # Sample rubric from first question
        sample_rubric = self.integrated_questions[0].scoring_rubric
        
        return {
            "rubric_categories": list(sample_rubric.keys()),
            "points_per_category": "0-5 points each",
            "total_possible": len(sample_rubric) * 5,
            "passing_threshold": "60% overall",
            "emphasis": "Application and integration over memorization"
        }
    
    def _calculate_difficulty_distribution(self) -> Dict[str, int]:
        """Calculate distribution of difficulty levels"""
        distribution = {"beginner": 0, "intermediate": 0, "advanced": 0, "expert": 0}
        
        for question in self.integrated_questions:
            distribution[question.difficulty.value] += 1
        
        return distribution
    
    def _create_fallback_question(self) -> Dict[str, Any]:
        """Create fallback question if generation fails"""
        fallback_questions = {
            ModuleTopic.CSS_BASICS: {
                "question": "A developer has created a responsive navigation menu, but the hover states don't work on mobile devices. The menu uses CSS :hover pseudo-class and media queries. What's the issue and how would you fix it while maintaining desktop hover effects?",
                "type": "debugging",
                "code": """/* CSS */
.nav-item {
  padding: 10px;
  background: #f0f0f0;
}

.nav-item:hover {
  background: #007bff;
  color: white;
}

/* Media query for mobile */
@media (max-width: 768px) {
  .nav-menu {
    flex-direction: column;
  }
}""",
                "targets": ["CSS pseudo-classes", "responsive design", "touch devices"]
            },
            ModuleTopic.NEUMORPHISM: {
                "question": "You've designed a neumorphic button that looks great on desktop but on mobile devices, the subtle shadows are barely visible in bright sunlight. How would you modify the design to ensure good visibility across all devices and lighting conditions while maintaining the neumorphic aesthetic?",
                "type": "design_challenge",
                "code": """/* Current neumorphic button */
.neumorphic-btn {
  background: #e0e5ec;
  border-radius: 10px;
  box-shadow: 5px 5px 10px #b8b9be,
              -5px -5px 10px #ffffff;
  padding: 15px 30px;
  border: none;
}""",
                "targets": ["accessibility", "responsive design", "visual hierarchy"]
            }
        }
        
        fallback = fallback_questions.get(
            self.topic,
            fallback_questions[ModuleTopic.CSS_BASICS]
        )
        
        return {
            "question": fallback["question"],
            "type": fallback["type"],
            "code_snippet": fallback.get("code", ""),
            "targets": fallback["targets"],
            "instructions": "This is a fallback question. Please answer as completely as possible."
        }
    
    def get_current_question(self) -> Optional[Dict[str, Any]]:
        """Get the current question for display"""
        if self.current_question_index >= len(self.integrated_questions):
            return None
        
        return self._format_question_for_display(self.current_question_index)
    
    def get_hint(self, question_id: str, hint_number: int = 0) -> Optional[Dict[str, Any]]:
        """Get a hint for a specific question"""
        question = next((q for q in self.integrated_questions 
                        if q.question_id == question_id), None)
        
        if not question or not question.hints_available:
            return None
        
        hint_index = min(hint_number, len(question.hints_available) - 1)
        
        return {
            "hint": question.hints_available[hint_index],
            "hint_number": hint_index + 1,
            "total_hints": len(question.hints_available),
            "next_hint_available": hint_index < len(question.hints_available) - 1
        }
    
    def submit_answer(self, question_id: str, user_answer: str, 
                     time_spent_seconds: int, confidence_rating: int = 3) -> Dict[str, Any]:
        """
        Submit and evaluate user's answer
        """
        # Find the question
        question = next((q for q in self.integrated_questions 
                        if q.question_id == question_id), None)
        
        if not question:
            return {"error": "Question not found"}
        
        # Evaluate answer
        evaluation = self._evaluate_answer(question, user_answer)
        
        # Create answer record
        answer_id = f"answer_{int(time.time())}_{self.user_id}"
        user_answer_record = UserAnswer(
            answer_id=answer_id,
            question_id=question_id,
            user_response=user_answer,
            time_spent_seconds=time_spent_seconds,
            scores=evaluation["scores"],
            overall_score=evaluation["overall_score"],
            gap_addressed=evaluation.get("gap_addressed", False),
            feedback=evaluation["feedback"],
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            improvements_needed=evaluation.get("improvements_needed", []),
            confidence_rating=confidence_rating
        )
        
        self.user_answers.append(user_answer_record)
        
        # Update statistics
        self.questions_answered += 1
        self.total_testing_time += time_spent_seconds
        
        if user_answer_record.overall_score >= 3:  # 3/5 or higher is considered correct
            self.correct_answers += 1
        
        # Update knowledge reinforcement tracking
        self._update_knowledge_reinforcement(question, user_answer_record)
        
        # Update phase log
        self.phase_log["questions_answered"] = self.questions_answered
        self.phase_log["average_score"] = (
            sum(a.overall_score for a in self.user_answers) / len(self.user_answers)
            if self.user_answers else 0
        )
        self.phase_log["testing_duration"] = self.total_testing_time
        self.phase_log["confidence_trend"].append(confidence_rating)
        
        if evaluation.get("gap_addressed"):
            self.phase_log["gaps_addressed"].append(question.targeted_gaps[0])
        
        # Determine next action
        if self.current_question_index < len(self.integrated_questions) - 1:
            self.current_question_index += 1
            next_question = self.get_current_question()
            next_action = "answer_next_question"
        else:
            next_action = "complete_testing"
        
        # Prepare response
        response = {
            "status": "answer_evaluated",
            "answer_id": answer_id,
            "question_id": question_id,
            "scores": evaluation["scores"],
            "overall_score": user_answer_record.overall_score,
            "score_category": self._get_score_category(user_answer_record.overall_score),
            "feedback": evaluation["feedback"],
            "model_answer": evaluation.get("model_answer_excerpt", ""),
            "time_spent": f"{time_spent_seconds}s",
            "confidence_rating": confidence_rating,
            "next_action": next_action
        }
        
        if next_action == "answer_next_question":
            response["next_question"] = next_question
            response["progress"] = f"{self.current_question_index + 1}/{len(self.integrated_questions)}"
        
        return response
    
    def _evaluate_answer(self, question: IntegratedQuestion, 
                        user_answer: str) -> Dict[str, Any]:
        """Evaluate user's answer using Gemini"""
        
        prompt = f"""
        Evaluate a student's answer to an integrated web development question.
        
        QUESTION: {question.question_text}
        
        QUESTION TYPE: {question.question_type.value}
        CURRENT TOPIC: {question.current_topic}
        PAST TOPICS INTEGRATED: {', '.join(question.past_topics)}
        
        SCORING RUBRIC:
        {json.dumps(question.scoring_rubric, indent=2)}
        
        COMMON MISTAKES TO WATCH FOR:
        {json.dumps(question.common_mistakes, indent=2)}
        
        MODEL ANSWER (for reference):
        {question.model_answer[:500] if question.model_answer else 'N/A'}
        
        STUDENT'S ANSWER: "{user_answer}"
        
        EVALUATION TASKS:
        1. Score each rubric category (0-5)
        2. Calculate overall score (weighted average)
        3. Determine if targeted knowledge gap was addressed
        4. Provide specific, constructive feedback
        5. Identify strengths and areas for improvement
        6. Suggest how to improve the answer
        
        Return JSON:
        {{
            "scores": {{
                "current_topic_application": 0-5,
                "past_concept_integration": 0-5,
                "solution_correctness": 0-5,
                "code_quality": 0-5,
                "explanation_clarity": 0-5
            }},
            "overall_score": 0-5,
            "gap_addressed": true/false,
            "gap_improvement_score": 0-5,
            "feedback": "Detailed feedback paragraph",
            "strengths": ["what student did well"],
            "areas_for_improvement": ["specific areas to work on"],
            "model_answer_excerpt": "Key part of model answer",
            "improvements_needed": ["concrete suggestions"],
            "knowledge_demonstrated": ["list of concepts demonstrated"]
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    thinking_config=types.ThinkingConfig(
                        thinking_level="low"
                    )
                )
            )
            
            evaluation = json.loads(response.text)
            
            # Calculate overall score if not provided
            if "overall_score" not in evaluation:
                scores = evaluation.get("scores", {})
                if scores:
                    evaluation["overall_score"] = sum(scores.values()) / len(scores)
                else:
                    evaluation["overall_score"] = 0
            
            return evaluation
            
        except Exception as e:
            print(f"❌ Error evaluating answer: {e}")
            
            return {
                "scores": {"overall": 3},
                "overall_score": 3,
                "feedback": "Thank you for your answer. Let's continue.",
                "strengths": ["Attempted the question"],
                "areas_for_improvement": ["Could provide more detail"]
            }
    
    def _get_score_category(self, score: float) -> str:
        """Convert numeric score to category"""
        if score >= 4.5:
            return "Excellent"
        elif score >= 4.0:
            return "Very Good"
        elif score >= 3.0:
            return "Good"
        elif score >= 2.0:
            return "Needs Improvement"
        else:
            return "Needs Significant Work"
    
    def _update_knowledge_reinforcement(self, question: IntegratedQuestion, 
                                      user_answer: UserAnswer):
        """Update knowledge reinforcement tracking"""
        for gap_id in question.targeted_gaps:
            # Find or create reinforcement record
            reinforcement = next(
                (r for r in self.knowledge_reinforcements if r.gap_id == gap_id),
                None
            )
            
            if not reinforcement:
                # Find gap in active gaps
                gap = next((g for g in self.active_gaps if g.get("gap_id") == gap_id), {})
                
                reinforcement = KnowledgeReinforcement(
                    gap_id=gap_id,
                    concept=gap.get("concept", "unknown"),
                    reinforcement_score=0,
                    questions_attempted=0,
                    correct_attempts=0,
                    last_reinforced=time.strftime("%Y-%m-%d %H:%M:%S"),
                    next_review_date=self._calculate_next_review_date()
                )
                self.knowledge_reinforcements.append(reinforcement)
            
            # Update reinforcement record
            reinforcement.questions_attempted += 1
            
            if user_answer.overall_score >= 3:  # Considered correct
                reinforcement.correct_attempts += 1
            
            reinforcement.reinforcement_score = int(
                (reinforcement.correct_attempts / reinforcement.questions_attempted) * 5
            )
            reinforcement.last_reinforced = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Update gap in database if addressed
            if user_answer.gap_addressed and reinforcement.reinforcement_score >= 3:
                self.db.update_knowledge_gap(
                    user_id=self.user_id,
                    gap_id=gap_id,
                    updates={
                        "addressed": True,
                        "addressed_in": "integrated_testing",
                        "addressed_timestamp": reinforcement.last_reinforced,
                        "reinforcement_score": reinforcement.reinforcement_score,
                        "times_addressed": reinforcement.questions_attempted
                    }
                )
    
    def _calculate_next_review_date(self) -> str:
        """Calculate next review date using spaced repetition"""
        # Simple spaced repetition: review after 1 day, then 3 days, then 7 days, etc.
        next_days = 1  # Start with 1 day
        
        # If user has multiple reinforcements, increase interval
        if len(self.knowledge_reinforcements) > 0:
            next_days = min(30, 2 ** len(self.knowledge_reinforcements))  # Cap at 30 days
        
        next_date = datetime.now() + timedelta(days=next_days)
        return next_date.strftime("%Y-%m-%d")
    
    def complete_testing(self) -> Dict[str, Any]:
        """
        Complete the integrated testing phase
        Generate practical problems and prepare summary
        """
        # Generate practical problems based on performance
        self._generate_practical_problems()
        
        # Calculate final metrics
        final_score = (
            sum(a.overall_score for a in self.user_answers) / len(self.user_answers)
            if self.user_answers else 0
        )
        
        accuracy_rate = (
            self.correct_answers / self.questions_answered * 100
            if self.questions_answered > 0 else 0
        )
        
        avg_time_per_question = (
            self.total_testing_time / self.questions_answered
            if self.questions_answered > 0 else 0
        )
        
        # Calculate confidence consistency
        confidence_trend = self.phase_log.get("confidence_trend", [])
        confidence_consistency = (
            sum(1 for i in range(1, len(confidence_trend)) 
                if abs(confidence_trend[i] - confidence_trend[i-1]) <= 1) / max(1, len(confidence_trend) - 1) * 100
        )
        
        # Update phase log
        self.phase_log["final_score"] = final_score
        self.phase_log["accuracy_rate"] = accuracy_rate
        self.phase_log["avg_time_per_question"] = avg_time_per_question
        self.phase_log["confidence_consistency"] = confidence_consistency
        self.phase_log["completion_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare for practical application (20% practice part)
        practical_prep = self._prepare_for_practical_application()
        
        summary = self._generate_phase_summary()
        
        return {
            "status": "testing_complete",
            "phase": "integrated_testing",
            "summary": summary,
            "performance_metrics": {
                "questions_answered": self.questions_answered,
                "total_questions": len(self.integrated_questions),
                "accuracy_rate": f"{accuracy_rate:.1f}%",
                "average_score": f"{final_score:.1f}/5",
                "total_time": f"{self.total_testing_time}s",
                "avg_time_per_question": f"{avg_time_per_question:.1f}s",
                "gaps_targeted": len(set(
                    gap for q in self.integrated_questions 
                    for gap in q.targeted_gaps
                )),
                "gaps_addressed": len(self.phase_log.get("gaps_addressed", [])),
                "confidence_consistency": f"{confidence_consistency:.1f}%"
            },
            "achievements": self._calculate_achievements(final_score, accuracy_rate),
            "knowledge_consolidation": self._assess_knowledge_consolidation(),
            "practical_problems_generated": len(self.practical_problems_generated),
            "next_step": "practical_application",
            "practical_application_prep": practical_prep,
            "database_updates": {
                "doc6_practical_problems": len(self.practical_problems_generated),
                "doc4_gaps_updated": len(self.knowledge_reinforcements),
                "testing_results_logged": True
            }
        }
    
    def _generate_practical_problems(self):
        """Generate practical problems based on testing performance"""
        print(f"\n🔧 Generating practical problems based on test performance...")
        
        # Identify weak areas from testing
        weak_areas = self._identify_weak_areas()
        
        if not weak_areas:
            weak_areas = [{"concept": self.topic.value, "reason": "general practice"}]
        
        # Generate practical problems
        for i, area in enumerate(weak_areas[:3]):  # Max 3 problems
            problem = self._generate_practical_problem(i, area)
            if problem:
                self.practical_problems_generated.append(problem)
                
                # Log to Database Doc 6
                self.db.log_practical_problem(
                    user_id=self.user_id,
                    problem_data={
                        "problem_id": problem["problem_id"],
                        "title": problem["title"],
                        "description": problem["description"],
                        "targeted_concepts": area.get("concepts", []),
                        "difficulty": problem.get("difficulty", "intermediate"),
                        "estimated_time": problem.get("estimated_time", "15-30 minutes"),
                        "success_criteria": problem.get("success_criteria", []),
                        "generated_from": "integrated_testing",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                )
        
        # Update phase log
        self.phase_log["practical_problems"] = [
            p["title"] for p in self.practical_problems_generated
        ]
        
        print(f"✅ Generated {len(self.practical_problems_generated)} practical problems")
        print(f"   Logged to Database Doc 6")
    
    def _identify_weak_areas(self) -> List[Dict]:
        """Identify weak areas from testing performance"""
        weak_areas = []
        
        # Analyze low-scoring answers
        low_scoring_answers = [a for a in self.user_answers if a.overall_score < 3]
        
        for answer in low_scoring_answers:
            # Find the question
            question = next((q for q in self.integrated_questions 
                           if q.question_id == answer.question_id), None)
            
            if question:
                weak_area = {
                    "concepts": question.past_topics + [question.current_topic],
                    "question_type": question.question_type.value,
                    "evidence": f"Score: {answer.overall_score}/5",
                    "feedback": answer.improvements_needed[:2] if answer.improvements_needed else ["Needs more practice"],
                    "reason": "Low score on integrated question"
                }
                weak_areas.append(weak_area)
        
        # Also consider areas where user took too long
        slow_answers = [a for a in self.user_answers 
                       if a.time_spent_seconds > 300]  # > 5 minutes
        
        for answer in slow_answers:
            question = next((q for q in self.integrated_questions 
                           if q.question_id == answer.question_id), None)
            
            if question and question.difficulty != DifficultyLevel.ADVANCED:
                weak_area = {
                    "concepts": question.past_topics + [question.current_topic],
                    "question_type": question.question_type.value,
                    "evidence": f"Time: {answer.time_spent_seconds}s",
                    "feedback": ["Needs faster application of concepts"],
                    "reason": "Slow response time"
                }
                weak_areas.append(weak_area)
        
        return weak_areas
    
    def _generate_practical_problem(self, index: int, weak_area: Dict) -> Optional[Dict]:
        """Generate a practical coding problem"""
        
        prompt = f"""
        Generate a PRACTICAL CODING PROBLEM for web development practice.
        
        WEAK AREAS IDENTIFIED: {weak_area.get('concepts', ['General practice'])}
        REASON: {weak_area.get('reason', 'Needs reinforcement')}
        
        PROBLEM REQUIREMENTS:
        1. Should be hands-on coding exercise
        2. Should target the weak areas specifically
        3. Should have clear success criteria
        4. Should be solvable in 15-30 minutes
        5. Should be practical/real-world relevant
        
        FORMAT:
        - Title: Descriptive title
        - Description: Clear problem statement
        - Requirements: Specific things to implement
        - Success criteria: How to know it's done correctly
        - Difficulty: beginner/intermediate/advanced
        - Estimated time: 15-30 minutes
        - Starter code (optional): Basic HTML/CSS structure
        
        Return JSON.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            problem_data = json.loads(response.text)
            
            problem_data["problem_id"] = f"practical_{int(time.time())}_{index}_{self.user_id}"
            problem_data["targeted_weak_area"] = weak_area
            
            return problem_data
            
        except Exception as e:
            print(f"⚠️  Error generating practical problem: {e}")
            return None
    
    def _prepare_for_practical_application(self) -> Dict[str, Any]:
        """Prepare for the 20% practical application phase"""
        return {
            "phase": "practical_application",
            "theory_practice_ratio": "80% theory complete, 20% practice starting",
            "practical_problems_available": len(self.practical_problems_generated),
            "recommended_start": "Immediately after testing",
            "estimated_total_time": f"{len(self.practical_problems_generated) * 25} minutes",
            "focus_areas": list(set(
                concept for p in self.practical_problems_generated
                for concept in p.get("targeted_concepts", [])
            )),
            "success_metrics": [
                "Code compiles/runs without errors",
                "Meets all requirements",
                "Follows best practices",
                "Clean, readable code"
            ],
            "next_steps": [
                "Review practical problems",
                "Start with easiest problem",
                "Apply concepts from all 4 theory phases",
                "Use Database Doc 6 for tracking"
            ]
        }
    
    def _calculate_achievements(self, final_score: float, accuracy_rate: float) -> List[str]:
        """Calculate achievements earned"""
        achievements = []
        
        if final_score >= 4.5:
            achievements.append("Integrated Testing Master")
        elif final_score >= 4.0:
            achievements.append("Excellent Integrator")
        elif final_score >= 3.0:
            achievements.append("Competent Integrator")
        
        if accuracy_rate >= 90:
            achievements.append("High Accuracy")
        elif accuracy_rate >= 75:
            achievements.append("Solid Performance")
        
        if self.questions_answered == len(self.integrated_questions):
            achievements.append("Completionist")
        
        if len(self.practical_problems_generated) >= 2:
            achievements.append("Practice-Ready")
        
        # Check for consistency
        confidence_trend = self.phase_log.get("confidence_trend", [])
        if len(confidence_trend) >= 2:
            if all(3 <= c <= 4 for c in confidence_trend):
                achievements.append("Confidently Consistent")
        
        return achievements if achievements else ["Testing Participant"]
    
    def _assess_knowledge_consolidation(self) -> Dict[str, Any]:
        """Assess how well knowledge was consolidated"""
        if not self.user_answers:
            return {"level": "unknown", "confidence": "low"}
        
        avg_score = sum(a.overall_score for a in self.user_answers) / len(self.user_answers)
        avg_confidence = sum(a.confidence_rating for a in self.user_answers) / len(self.user_answers)
        
        # Determine consolidation level
        if avg_score >= 4.0 and avg_confidence >= 4.0:
            level = "strong"
        elif avg_score >= 3.0 and avg_confidence >= 3.0:
            level = "moderate"
        elif avg_score >= 2.0:
            level = "basic"
        else:
            level = "weak"
        
        # Identify strongest and weakest areas
        question_scores = {}
        for answer in self.user_answers:
            question = next((q for q in self.integrated_questions 
                           if q.question_id == answer.question_id), None)
            if question:
                key = f"{question.current_topic}+{'+'.join(question.past_topics[:1])}"
                question_scores[key] = question_scores.get(key, []) + [answer.overall_score]
        
        avg_question_scores = {
            k: sum(scores) / len(scores) 
            for k, scores in question_scores.items()
        }
        
        strongest = max(avg_question_scores.items(), key=lambda x: x[1]) if avg_question_scores else ("none", 0)
        weakest = min(avg_question_scores.items(), key=lambda x: x[1]) if avg_question_scores else ("none", 0)
        
        return {
            "consolidation_level": level,
            "average_score": avg_score,
            "average_confidence": avg_confidence,
            "strongest_area": strongest[0],
            "strongest_score": strongest[1],
            "weakest_area": weakest[0],
            "weakest_score": weakest[1],
            "recommendation": self._get_consolidation_recommendation(level, avg_score)
        }
    
    def _get_consolidation_recommendation(self, level: str, score: float) -> str:
        """Get recommendation based on consolidation level"""
        recommendations = {
            "strong": "Excellent consolidation! Ready for advanced topics or real projects.",
            "moderate": "Good understanding. Some review of weaker areas recommended before advancing.",
            "basic": "Basic understanding achieved. Recommend additional practice before new topics.",
            "weak": "Needs significant review. Revisit core concepts before continuing."
        }
        return recommendations.get(level, "Continue with next topic carefully.")
    
    def _generate_phase_summary(self) -> str:
        """Generate human-readable summary"""
        summary_lines = [
            f"🧪 INTEGRATED TESTING PHASE COMPLETE",
            f"   Topic: {self.topic.value}",
            f"   Questions: {self.questions_answered}/{len(self.integrated_questions)} answered",
            f"   Average score: {self.phase_log.get('average_score', 0):.1f}/5",
            f"   Accuracy: {self.phase_log.get('accuracy_rate', 0):.1f}%",
            f"   Time spent: {self.total_testing_time}s total",
            f"   Gaps addressed: {len(self.phase_log.get('gaps_addressed', []))}",
            f"   Practical problems generated: {len(self.practical_problems_generated)}",
            f"   Next: Practical application (20% practice phase)"
        ]
        
        return "\n".join(summary_lines)
    
    def get_practical_problems(self) -> List[Dict]:
        """Get generated practical problems for display"""
        return self.practical_problems_generated
    
    def get_phase_log(self) -> Dict[str, Any]:
        """Get complete phase log"""
        return self.phase_log


# ============================================================================
# DEMONSTRATION
# ============================================================================

def demonstrate_integrated_testing():
    """Demonstrate Integrated Testing Phase"""
    
    # Mock classes
    class MockGeminiClient:
        def models(self):
            class Models:
                @staticmethod
                def generate_content(model, contents, config=None):
                    print(f"\n[Gemini called: {contents[:200]}...]")
                    
                    class Response:
                        text = json.dumps({
                            "question_text": "How would you debug a CSS specificity conflict in a large codebase?",
                            "code_snippet": "/* CSS with specificity conflict */\n.button { color: blue; }\n#submit.button { color: red; }\n.container .button { color: green; }",
                            "difficulty": "intermediate",
                            "expected_time_minutes": 5,
                            "scoring_rubric": {
                                "current_topic_application": "0-5 points",
                                "past_concept_integration": "0-5 points",
                                "solution_correctness": "0-5 points"
                            },
                            "model_answer": "Use browser dev tools to inspect computed styles...",
                            "common_mistakes": ["Using !important", "Not checking inheritance"],
                            "hints": ["Check browser dev tools", "Consider specificity hierarchy"]
                        })
                    
                    return type('obj', (object,), {'text': text})()
            
            return Models()
    
    class MockStudentDatabase:
        def get_knowledge_gaps(self, user_id):
            return [
                {
                    "gap_id": "gap_001",
                    "concept": "CSS Specificity",
                    "root_cause": "Confuses ID and class specificity",
                    "severity": 4,
                    "addressed": False,
                    "last_reviewed": "2024-01-10 10:00:00"
                }
            ]
        
        def get_learning_history(self, user_id):
            return {"priming": True, "relational_thinking": True, "interleaving": True}
        
        def update_knowledge_gap(self, user_id, gap_id, updates):
            print(f"🔄 Updated gap {gap_id}")
        
        def log_practical_problem(self, user_id, problem_data):
            print(f"📝 Logged practical problem: {problem_data['problem_id']}")
    
    # Mock previous phase data
    mock_all_phase_data = {
        "priming": {"terminology": [{"term": "Specificity"}]},
        "relational_thinking": {
            "pattern_name": "CSS Specificity",
            "mental_model": "ID (100) > Class (10) > Element (1)"
        },
        "interleaving": {
            "analogies_created": 1,
            "what_if_scenarios": 2
        }
    }
    
    print("🚀 INTEGRATED TESTING PHASE DEMONSTRATION")
    print("=" * 60)
    
    mock_client = MockGeminiClient()
    mock_db = MockStudentDatabase()
    
    phase = IntegratedTestingPhase(
        gemini_client=mock_client,
        topic=ModuleTopic.CSS_BASICS,
        all_phase_data=mock_all_phase_data,
        user_id="demo_user",
        student_db=mock_db,
        question_count=2
    )
    
    print("\n1. Starting phase...")
    start_result = phase.execute_phase()
    
    print(f"\n2. Phase started:")
    print(f"   Questions: {start_result['total_questions']}")
    print(f"   Gaps targeted: {start_result['gaps_targeted']}")
    
    if start_result['total_questions'] > 0:
        print(f"\n3. First question:")
        question = start_result['question']
        print(f"   Type: {question.get('type')}")
        print(f"   Text: {question.get('text', '')[:80]}...")
        
        print(f"\n4. Submitting answer...")
        answer_result = phase.submit_answer(
            question_id=question["question_id"],
            user_answer="I would use browser dev tools to inspect the computed styles and see which rule is winning.",
            time_spent_seconds=120,
            confidence_rating=4
        )
        
        print(f"   Score: {answer_result.get('overall_score', 0)}/5")
        print(f"   Category: {answer_result.get('score_category', 'N/A')}")
        
        print(f"\n5. Completing testing...")
        completion = phase.complete_testing()
        
        print(f"\n📋 FINAL SUMMARY:")
        print(f"   Phase: {completion['phase']}")
        print(f"   Accuracy: {completion['performance_metrics']['accuracy_rate']}")
        print(f"   Average score: {completion['performance_metrics']['average_score']}")
        print(f"   Gaps addressed: {completion['performance_metrics']['gaps_addressed']}")
        print(f"   Practical problems: {completion['practical_problems_generated']}")
        print(f"   Achievements: {', '.join(completion['achievements'])}")
        print(f"   Next step: {completion['next_step']}")
    
    print(f"\n✅ Integrated Testing Phase implementation ready!")

if __name__ == "__main__":
    demonstrate_integrated_testing()