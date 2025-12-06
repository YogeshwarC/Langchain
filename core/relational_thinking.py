"""
RELATIONAL THINKING PHASE (Phase 2: Discovery Loop)
Implements inductive learning through pattern discovery
"""
import json
import time
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import re

from google import genai
from google.genai import types

from core.priming_phase import ModuleTopic

@dataclass
class CodeExample:
    """Represents a code example with metadata"""
    code: str
    description: str
    visual_output: Optional[str] = None  # For showing expected visual result
    key_pattern_element: str = ""  # Which part demonstrates the pattern
    complexity: str = "beginner"  # beginner/intermediate/advanced
    line_highlight: Optional[List[int]] = None  # Lines to highlight
    
@dataclass
class DiscoveryAttempt:
    """Tracks user's discovery attempts"""
    attempt_number: int
    user_input: str
    timestamp: str
    score: int = 0  # 0-5
    hint_given: bool = False
    hint_type: Optional[str] = None
    time_spent_seconds: float = 0.0
    
@dataclass  
class PatternDiscoveryResult:
    """Results of pattern discovery phase"""
    pattern_id: str
    discovered_pattern: str
    user_discovered: bool = False
    attempts_required: int = 0
    total_time_seconds: float = 0.0
    discovery_score: int = 0  # 0-5
    exceptions_found: List[Dict] = field(default_factory=list)
    exceptions_score: int = 0  # 0-5
    mental_model: Optional[str] = None
    analogy_quality: int = 0  # 0-5

class DiscoveryState(Enum):
    """Tracks where user is in discovery loop"""
    SETUP = "setup"  # Presenting 3 examples
    DISCOVERY_PROMPT = "discovery_prompt"  # Asking for pattern
    BLOCKING_LOOP = "blocking_loop"  # User attempting, giving hints
    PATTERN_REVEALED = "pattern_revealed"  # Pattern understood
    EXCEPTIONS_SEARCH = "exceptions_search"  # Looking for edge cases
    ANALOGY_GENERATION = "analogy_generation"  # Creating real-world analogy
    WHAT_IF_EXPLORATION = "what_if_exploration"  # Exploring edge cases
    COMPLETE = "complete"  # Phase complete

class PatternType(Enum):
    """Types of patterns to discover"""
    SELECTOR_SPECIFICITY = "selector_specificity"
    BOX_MODEL_RELATIONSHIPS = "box_model_relationships"
    FLEXBOX_ALIGNMENT = "flexbox_alignment"
    GRID_TEMPLATE = "grid_template"
    ANIMATION_TIMING = "animation_timing"
    NEUMORPHISM_SHADOW = "neumorphism_shadow"
    MEDIA_QUERY_BREAKPOINTS = "media_query_breakpoints"
    POSITIONING_CONTEXT = "positioning_context"

class RelationalThinkingPhase:
    """
    Implements Phase 2: Relational Thinking (Discovery Loop)
    Uses inductive learning: show 3 examples → user discovers pattern → find exceptions
    """
    
    def __init__(
        self, 
        gemini_client: genai.Client,
        topic: ModuleTopic,
        priming_data: Dict,  # From previous phase
        user_id: str,
        max_attempts: int = 5,
        thinking_level: str = "high"
    ):
        """
        Initialize Relational Thinking Phase
        
        Args:
            gemini_client: Initialized Gemini client
            topic: Current module topic
            priming_data: Results from PrimingPhase (terminology, syntax)
            user_id: Unique identifier for user session
            max_attempts: Maximum discovery attempts before revealing pattern
            thinking_level: "high" or "low" for Gemini 3 Pro
        """
        self.client = gemini_client
        self.topic = topic
        self.priming_data = priming_data
        self.user_id = user_id
        self.max_attempts = max_attempts
        self.thinking_level = thinking_level
        
        # State tracking
        self.state = DiscoveryState.SETUP
        self.current_attempts = 0
        self.discovery_start_time = None
        self.pattern_revealed = False
        
        # Pattern selection (based on topic)
        self.selected_pattern_type = self._select_pattern_for_topic()
        
        # Data storage
        self.code_examples: List[CodeExample] = []
        self.discovery_attempts: List[DiscoveryAttempt] = []
        self.pattern_result: Optional[PatternDiscoveryResult] = None
        self.exceptions: List[Dict] = []
        self.user_analogy: Optional[Dict] = None
        self.what_if_scenarios: List[Dict] = []
        
        # Gemini model selection
        self.model = "gemini-1.5-pro-latest"  # Change to gemini-3-pro-preview if available
        
        # Phase logging (for Database Doc 2)
        self.phase_log = {
            "phase": "relational_thinking",
            "topic": topic.value,
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pattern_type": self.selected_pattern_type.value,
            "pattern_discovery": {
                "examples_shown": [],
                "attempts": [],
                "final_score": 0,
                "time_taken": 0
            },
            "exception_discovery": {
                "exceptions_found": [],
                "exceptions_score": 0
            },
            "analogy_generation": {
                "analogy_created": False,
                "analogy_quality": 0
            },
            "what_if_scenarios": [],
            "knowledge_gaps_identified": []
        }
        
        # Load pattern-specific configurations
        self._load_pattern_configuration()
    
    def _select_pattern_for_topic(self) -> PatternType:
        """Select appropriate pattern type based on topic"""
        pattern_mapping = {
            ModuleTopic.CSS_BASICS: PatternType.SELECTOR_SPECIFICITY,
            ModuleTopic.CSS_LAYOUT: PatternType.FLEXBOX_ALIGNMENT,
            ModuleTopic.CSS_ANIMATIONS: PatternType.ANIMATION_TIMING,
            ModuleTopic.NEUMORPHISM: PatternType.NEUMORPHISM_SHADOW,
            ModuleTopic.RESPONSIVE_DESIGN: PatternType.MEDIA_QUERY_BREAKPOINTS,
            ModuleTopic.HTML_BASICS: PatternType.BOX_MODEL_RELATIONSHIPS
        }
        return pattern_mapping.get(self.topic, PatternType.SELECTOR_SPECIFICITY)
    
    def _load_pattern_configuration(self):
        """Load configuration for the selected pattern type"""
        self.pattern_configs = {
            PatternType.SELECTOR_SPECIFICITY: {
                "name": "CSS Selector Specificity",
                "description": "More specific selectors override less specific ones",
                "mental_model": "Specificity score: ID (100) > Class (10) > Element (1)",
                "key_question": "Which selector would win in a conflict?",
                "hint_strategy": "focus_on_specificity_score"
            },
            PatternType.FLEXBOX_ALIGNMENT: {
                "name": "Flexbox Alignment Rules",
                "description": "justify-content aligns on main axis, align-items on cross axis",
                "mental_model": "Main axis = direction of flex, Cross axis = perpendicular",
                "key_question": "Which property controls which axis?",
                "hint_strategy": "contrast_axes"
            },
            PatternType.NEUMORPHISM_SHADOW: {
                "name": "Neumorphic Shadow Relationships",
                "description": "Light source determines shadow direction; inset vs outset shadows",
                "mental_model": "Shadows opposite light source; inset = pressed, outset = raised",
                "key_question": "Where would shadows appear given this light source?",
                "hint_strategy": "visualize_light_source"
            }
        }
        
        self.current_pattern = self.pattern_configs.get(
            self.selected_pattern_type,
            self.pattern_configs[PatternType.SELECTOR_SPECIFICITY]
        )
    
    def execute_phase(self) -> Dict[str, Any]:
        """
        Main entry point: executes complete relational thinking phase
        
        Returns:
            Dict with phase results and next steps
        """
        print(f"\n{'='*60}")
        print(f"PHASE 2: RELATIONAL THINKING - {self.topic.value.upper()}")
        print(f"Pattern: {self.current_pattern['name']}")
        print(f"{'='*60}")
        
        # Step 1: Generate and present 3 examples
        self._generate_three_examples()
        
        # Present examples with visual aids
        presentation = self._present_examples_with_context()
        
        # Step 2: Ask discovery question
        discovery_prompt = self._create_discovery_prompt()
        
        # Update phase log
        self.phase_log["pattern_discovery"]["examples_shown"] = [
            {
                "code": ex.code[:100] + "..." if len(ex.code) > 100 else ex.code,
                "description": ex.description
            } 
            for ex in self.code_examples
        ]
        
        return {
            "status": "discovery_initiated",
            "state": self.state.value,
            "pattern_type": self.current_pattern["name"],
            "examples": presentation["examples"],
            "visual_aids": presentation.get("visual_aids", []),
            "question": discovery_prompt["question"],
            "instructions": discovery_prompt["instructions"],
            "constraints": discovery_prompt.get("constraints", ""),
            "next_action": "await_user_pattern_attempt",
            "hint_available": True,
            "max_attempts": self.max_attempts
        }
    
    def _generate_three_examples(self):
        """
        Generate 3 distinct code examples with hidden pattern
        Each example demonstrates the pattern from a different angle
        """
        print(f"\n🔍 Generating discovery examples for {self.current_pattern['name']}...")
        
        # Get relevant terminology from priming phase
        relevant_terms = []
        if "terminology" in self.priming_data:
            relevant_terms = [t.get("term", "") for t in self.priming_data["terminology"][:5]]
        
        prompt = f"""
        As an expert programming educator, create 3 DISTINCT code examples that demonstrate this pattern:
        
        PATTERN: {self.current_pattern['name']}
        DESCRIPTION: {self.current_pattern['description']}
        MENTAL MODEL: {self.current_pattern['mental_model']}
        TOPIC: {self.topic.value}
        
        REQUIREMENTS FOR EACH EXAMPLE:
        1. Should look visually/structurally different from others
        2. Must demonstrate the SAME underlying pattern
        3. Should include HTML and/or CSS code
        4. Vary complexity: beginner, intermediate, advanced
        5. Include comments explaining what's happening
        
        FORMAT REQUIREMENTS:
        - Example 1: Simple, minimal version
        - Example 2: Practical, real-world use case  
        - Example 3: Complex, edge case version
        
        Return JSON with this structure:
        {{
            "pattern_summary": "Brief summary of the pattern",
            "examples": [
                {{
                    "code": "Full code example with comments",
                    "description": "What this demonstrates",
                    "complexity": "beginner/intermediate/advanced",
                    "key_element": "Which part shows the pattern",
                    "visual_description": "What the user would see visually"
                }},
                // 2 more examples
            ],
            "common_misconceptions": ["list", "of", "misconceptions"],
            "pattern_variations": ["different ways this pattern manifests"]
        }}
        
        Focus on making the pattern discoverable but not obvious.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,  # Creative generation
                    thinking_config=types.ThinkingConfig(
                        thinking_level=self.thinking_level
                    )
                )
            )
            
            examples_data = json.loads(response.text)
            
            # Create CodeExample objects
            for i, ex_data in enumerate(examples_data["examples"][:3]):
                code_example = CodeExample(
                    code=ex_data["code"],
                    description=ex_data["description"],
                    visual_output=ex_data.get("visual_description", ""),
                    key_pattern_element=ex_data.get("key_element", ""),
                    complexity=ex_data.get("complexity", "beginner"),
                    line_highlight=self._determine_highlight_lines(ex_data["code"])
                )
                self.code_examples.append(code_example)
            
            # Store pattern metadata
            self.pattern_metadata = {
                "summary": examples_data["pattern_summary"],
                "misconceptions": examples_data.get("common_misconceptions", []),
                "variations": examples_data.get("pattern_variations", [])
            }
            
            print(f"✅ Generated {len(self.code_examples)} distinct examples")
            print(f"   Pattern: {self.current_pattern['name']}")
            print(f"   Misconceptions to watch for: {len(self.pattern_metadata['misconceptions'])}")
            
        except Exception as e:
            print(f"❌ Error generating examples: {e}")
            self._load_fallback_examples()
    
    def _determine_highlight_lines(self, code: str) -> List[int]:
        """Determine which lines to highlight in code display"""
        lines = code.split('\n')
        highlight_lines = []
        
        # Simple heuristic: highlight lines with key syntax
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ['#', '.', ':', '{', '}', '@', '!important']):
                if i < 20:  # Limit highlights
                    highlight_lines.append(i + 1)  # 1-indexed for display
        
        return highlight_lines[:3]  # Max 3 highlights
    
    def _load_fallback_examples(self):
        """Fallback examples if Gemini fails"""
        if self.selected_pattern_type == PatternType.SELECTOR_SPECIFICITY:
            self.code_examples = [
                CodeExample(
                    code="""/* Example 1: Simple specificity */
.button {
    color: blue;  /* Less specific */
}

#submit.button {
    color: red;   /* More specific - wins! */
}""",
                    description="ID + class selector overrides class selector",
                    key_pattern_element="#submit.button",
                    complexity="beginner"
                ),
                CodeExample(
                    code="""/* Example 2: Multiple classes */
.nav .item {
    padding: 10px;  /* Specificity: 0,1,0 */
}

.item.active {
    padding: 20px;  /* Specificity: 0,2,0 - wins! */
}""",
                    description="More classes = higher specificity",
                    key_pattern_element=".item.active",
                    complexity="intermediate"
                ),
                CodeExample(
                    code="""/* Example 3: Inline styles */
div.container p {
    font-size: 14px;  /* Specificity: 0,0,2 */
}

<p style="font-size: 18px;">  <!-- Inline: 1,0,0 - wins! -->
    Inline styles beat everything!
</p>""",
                    description="Inline styles have highest specificity",
                    key_pattern_element="style=\"font-size: 18px\"",
                    complexity="advanced"
                )
            ]
        elif self.selected_pattern_type == PatternType.FLEXBOX_ALIGNMENT:
            self.code_examples = [
                CodeExample(
                    code="""/* justify-content on main axis */
.container {
    display: flex;
    justify-content: center;  /* Horizontal centering */
}""",
                    description="justify-content controls main axis (horizontal by default)",
                    key_pattern_element="justify-content: center",
                    complexity="beginner"
                ),
                # ... more examples
            ]
        
        self.pattern_metadata = {
            "summary": "Fallback pattern examples",
            "misconceptions": ["Common beginner mistakes"],
            "variations": ["Different applications"]
        }
    
    def _present_examples_with_context(self) -> Dict[str, Any]:
        """Display examples with visual aids and context"""
        print(f"\n🧩 DISCOVERY SETUP: 3 Examples with Hidden Pattern")
        print("-" * 50)
        
        examples_display = []
        visual_aids = []
        
        for i, example in enumerate(self.code_examples, 1):
            print(f"\n📋 EXAMPLE {i} ({example.complexity.upper()}):")
            print(f"   {example.description}")
            
            # Display code with highlights if available
            if example.line_highlight:
                print(f"   👁️  Focus on lines: {example.line_highlight}")
            
            print(f"   Code:\n{'='*40}")
            
            # Display code with line numbers
            lines = example.code.split('\n')
            for line_num, line in enumerate(lines, 1):
                marker = "→ " if line_num in example.line_highlight else "  "
                print(f"{marker}{line_num:3}: {line}")
            
            print('='*40)
            
            # Add visual description if available
            if example.visual_output:
                print(f"   🎯 Visual result: {example.visual_output}")
                visual_aids.append({
                    "example": i,
                    "visual_description": example.visual_output
                })
            
            examples_display.append({
                "number": i,
                "code_preview": example.code[:150] + "..." if len(example.code) > 150 else example.code,
                "description": example.description,
                "complexity": example.complexity
            })
        
        # Provide thinking guidance
        print(f"\n💡 THINKING GUIDE:")
        print(f"   1. Look for COMMONALITIES across all 3 examples")
        print(f"   2. Identify what's DIFFERENT but achieves similar results")
        print(f"   3. Think about the UNDERLYING RULE, not surface details")
        print(f"   4. Consider: \"What principle governs all these cases?\"")
        
        return {
            "examples": examples_display,
            "visual_aids": visual_aids,
            "thinking_guide": [
                "Look for commonalities",
                "Identify different approaches to same result",
                "Find underlying rule/principles",
                "Think abstractly, not literally"
            ]
        }
    
    def _create_discovery_prompt(self) -> Dict[str, str]:
        """Create the discovery prompt based on pattern type"""
        self.state = DiscoveryState.DISCOVERY_PROMPT
        self.discovery_start_time = time.time()
        
        prompts = {
            PatternType.SELECTOR_SPECIFICITY: {
                "question": "Look at these 3 CSS examples. Without using technical terms like 'specificity' or 'cascade', what invisible rule determines which style gets applied when there are conflicts?",
                "instructions": "Describe the rule in your own words as if explaining to a complete beginner. What principle decides which style 'wins'?",
                "constraints": "Don't mention browser, order, or !important. Focus on the selector patterns themselves."
            },
            PatternType.FLEXBOX_ALIGNMENT: {
                "question": "These examples all use Flexbox for alignment. What's the fundamental relationship between justify-content and align-items that remains true in all cases?",
                "instructions": "Think about axes and directions. What's the consistent rule about which property controls which direction?",
                "constraints": "Avoid specific property values. Focus on the conceptual relationship."
            },
            PatternType.NEUMORPHISM_SHADOW: {
                "question": "Look at these neumorphic designs. What invisible relationship exists between the light source position and shadow placement that's true in all examples?",
                "instructions": "Describe the geometric/spatial rule. How does light direction determine visual depth?",
                "constraints": "Don't mention specific CSS values. Focus on the light-shadow relationship principle."
            }
        }
        
        prompt_data = prompts.get(
            self.selected_pattern_type,
            prompts[PatternType.SELECTOR_SPECIFICITY]
        )
        
        return {
            **prompt_data,
            "pattern_name": self.current_pattern["name"],
            "hint_available_after": 1  # Hint available after 1 attempt
        }
    
    def process_user_attempt(self, user_input: str, attempt_time: float = 0.0) -> Dict[str, Any]:
        """
        Step 3: Process user's pattern discovery attempt
        Implements the Blocking Loop with persistence
        
        Args:
            user_input: User's description of the pattern
            attempt_time: Time user spent thinking (seconds)
            
        Returns:
            Evaluation with score, feedback, and next steps
        """
        self.current_attempts += 1
        
        # Create attempt record
        attempt = DiscoveryAttempt(
            attempt_number=self.current_attempts,
            user_input=user_input,
            timestamp=time.strftime("%H:%M:%S"),
            time_spent_seconds=attempt_time,
            score=0
        )
        
        print(f"\n🔄 ATTEMPT {self.current_attempts}/{self.max_attempts}")
        print(f"   Time spent: {attempt_time:.1f}s")
        print(f"   Your insight: \"{user_input}\"")
        
        # Evaluate the attempt
        evaluation = self._evaluate_pattern_attempt(user_input)
        
        # Update attempt record
        attempt.score = evaluation["score"]
        attempt.hint_given = evaluation.get("hint_given", False)
        attempt.hint_type = evaluation.get("hint_type")
        
        self.discovery_attempts.append(attempt)
        
        # Log to phase log
        self.phase_log["pattern_discovery"]["attempts"].append({
            "attempt": self.current_attempts,
            "input_preview": user_input[:100] + "..." if len(user_input) > 100 else user_input,
            "score": evaluation["score"],
            "time_spent": attempt_time,
            "hint_given": attempt.hint_given
        })
        
        # Check if pattern is discovered or max attempts reached
        if evaluation["score"] >= 4 or self.current_attempts >= self.max_attempts:
            return self._handle_pattern_resolution(evaluation)
        
        # Continue blocking loop
        self.state = DiscoveryState.BLOCKING_LOOP
        
        response = {
            "status": "blocking_loop",
            "attempt": self.current_attempts,
            "score": evaluation["score"],
            "feedback": evaluation["feedback"],
            "hint_available": evaluation.get("hint_available", True),
            "hint_type": evaluation.get("hint_type"),
            "next_action": "try_again_or_ask_for_hint",
            "misconceptions_addressed": evaluation.get("misconceptions_addressed", []),
            "thinking_prompts": evaluation.get("thinking_prompts", [])
        }
        
        # If score is low, suggest a hint
        if evaluation["score"] <= 2 and self.current_attempts >= 1:
            response["suggested_action"] = "request_hint"
        
        return response
    
    def _evaluate_pattern_attempt(self, user_input: str) -> Dict[str, Any]:
        """
        Evaluate user's pattern description using Gemini
        Returns detailed evaluation with specific feedback
        """
        # Prepare context for evaluation
        context = {
            "pattern_name": self.current_pattern["name"],
            "pattern_description": self.current_pattern["description"],
            "mental_model": self.current_pattern["mental_model"],
            "user_attempt": user_input,
            "common_misconceptions": self.pattern_metadata.get("misconceptions", []),
            "attempt_number": self.current_attempts,
            "max_attempts": self.max_attempts
        }
        
        prompt = f"""
        As a programming education expert, evaluate a student's attempt to discover a pattern.
        
        CONTEXT:
        Pattern being discovered: {context['pattern_name']}
        Correct description: {context['pattern_description']}
        Target mental model: {context['mental_model']}
        
        STUDENT'S ATTEMPT: "{context['user_attempt']}"
        
        COMMON MISCONCEPTIONS to watch for:
        {json.dumps(context['common_misconceptions'], indent=2)}
        
        EVALUATION RUBRIC:
        - Score 5: Correctly identifies core pattern, may use own words perfectly
        - Score 4: Mostly correct, minor misunderstanding or missing nuance
        - Score 3: Partially correct, identifies related concept but not exact pattern
        - Score 2: Vague or generic observation that could apply to many things
        - Score 1: Incorrect but shows some relevant thinking
        - Score 0: Completely incorrect or irrelevant
        
        TASKS:
        1. Assign score 0-5
        2. Provide CONSTRUCTIVE feedback (what they got right/wrong)
        3. If score < 4, identify which misconception they might have
        4. Determine if a hint would be helpful
        5. Suggest thinking prompts to guide them
        
        Return JSON:
        {{
            "score": 0-5,
            "feedback": "Specific, constructive feedback",
            "hint_available": true/false,
            "hint_type": "contrast/focus/simplify/visual" or null,
            "misconceptions_addressed": ["list of misconceptions in attempt"],
            "thinking_prompts": ["questions to guide thinking"],
            "strengths": ["what they got right"],
            "areas_for_improvement": ["what to focus on"]
        }}
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
            
            # Add scoring explanation
            score_explanations = {
                5: "Excellent! You've discovered the pattern!",
                4: "Very close! You've identified the key concept.",
                3: "Good progress! You're on the right track.",
                2: "Interesting observation. Look closer at the relationships.",
                1: "Let's refocus. Look for what's common across all examples.",
                0: "Let's approach this differently. Focus on what all examples share."
            }
            
            if evaluation["score"] in score_explanations:
                evaluation["score_explanation"] = score_explanations[evaluation["score"]]
            
            return evaluation
            
        except Exception as e:
            print(f"⚠️  Error evaluating attempt: {e}")
            # Default evaluation
            return {
                "score": 2,
                "feedback": "Interesting observation! Look closer at how the examples relate to each other. What's the fundamental rule that applies to all three?",
                "hint_available": True,
                "hint_type": "focus",
                "misconceptions_addressed": [],
                "thinking_prompts": [
                    "What do ALL examples have in common?",
                    "If you changed one example, would the same rule still apply?",
                    "What's the relationship between the different parts?"
                ],
                "strengths": ["Attempting to find patterns"],
                "areas_for_improvement": ["Look for underlying principles, not surface features"]
            }
    
    def provide_hint(self, hint_type: str = None) -> Dict[str, Any]:
        """
        Provide intelligent hint based on user's progress
        Different hint types: contrast, focus, simplify, visual
        """
        if not hint_type:
            # Determine best hint based on attempts and performance
            if self.current_attempts == 1:
                hint_type = "focus"
            elif self.current_attempts == 2:
                hint_type = "contrast"
            elif any(att.score >= 3 for att in self.discovery_attempts):
                hint_type = "simplify"
            else:
                hint_type = "visual"
        
        hint_methods = {
            "contrast": self._provide_contrast_hint,
            "focus": self._provide_focus_hint,
            "simplify": self._provide_simplify_hint,
            "visual": self._provide_visual_hint
        }
        
        hint_function = hint_methods.get(hint_type, self._provide_focus_hint)
        hint_result = hint_function()
        
        # Log hint provision
        self.phase_log["pattern_discovery"]["hints_given"] = \
            self.phase_log["pattern_discovery"].get("hints_given", [])
        self.phase_log["pattern_discovery"]["hints_given"].append({
            "attempt": self.current_attempts,
            "type": hint_type,
            "effectiveness": "pending"  # Would track if hint helped
        })
        
        # Update current attempt with hint info
        if self.discovery_attempts:
            self.discovery_attempts[-1].hint_given = True
            self.discovery_attempts[-1].hint_type = hint_type
        
        return {
            "status": "hint_provided",
            "hint_type": hint_type,
            "hint": hint_result["content"],
            "action": hint_result.get("action", "consider"),
            "thinking_task": hint_result.get("thinking_task", ""),
            "follow_up_question": hint_result.get("follow_up_question", "")
        }
    
    def _provide_contrast_hint(self) -> Dict[str, str]:
        """Show example that BREAKS the pattern"""
        # Generate or retrieve contrasting example
        prompt = f"""
        Create a CSS/HTML example that looks SIMILAR to the discovery examples 
        but intentionally BREAKS this pattern:
        
        Pattern: {self.current_pattern['name']}
        Pattern Rule: {self.current_pattern['description']}
        
        Create an example where the pattern does NOT apply, 
        to help students understand the pattern's boundaries.
        
        Return JSON:
        {{
            "code": "The contrasting code example",
            "explanation": "Why this breaks the pattern",
            "key_difference": "What makes this different"
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            contrast_data = json.loads(response.text)
            
            return {
                "content": f"Look at this contrasting example:\n\n{contrast_data['code']}\n\n"
                          f"This example BREAKS the pattern. {contrast_data['explanation']}",
                "action": "compare_and_contrast",
                "thinking_task": "Identify exactly how this differs from the original examples",
                "follow_up_question": "What change would make this example FOLLOW the pattern?"
            }
            
        except:
            # Simple fallback contrast
            if self.selected_pattern_type == PatternType.SELECTOR_SPECIFICITY:
                contrast_code = """/* This breaks the specificity pattern */
.button { color: red; }
.button { color: blue; } /* Same specificity - order matters instead! */"""
                
                return {
                    "content": f"Contrasting example:\n\n{contrast_code}\n\n"
                              "This has EQUAL specificity, so order matters instead of specificity.",
                    "action": "identify_difference",
                    "thinking_task": "Why doesn't specificity determine the winner here?"
                }
        
        return self._provide_focus_hint()  # Fallback
    
    def _provide_focus_hint(self) -> Dict[str, str]:
        """Focus attention on key element"""
        # Find common element across examples
        common_elements = self._analyze_common_elements()
        
        if common_elements:
            focus_element = random.choice(common_elements[:2])  # Pick one
            return {
                "content": f"Focus on this element that appears in all examples:\n\n"
                          f"» {focus_element}\n\n"
                          f"What role does this play in each example? "
                          f"How does it affect the outcome?",
                "action": "analyze_role",
                "thinking_task": "Trace how this element functions in each example"
            }
        
        # Fallback to pattern-specific focus
        focus_guides = {
            PatternType.SELECTOR_SPECIFICITY: "Look at the SELECTORS (the parts before { }). How are they structured?",
            PatternType.FLEXBOX_ALIGNMENT: "Look at the AXIS references. Which property mentions which axis?",
            PatternType.NEUMORPHISM_SHADOW: "Look at LIGHT SOURCE and SHADOW values. What's the relationship?"
        }
        
        return {
            "content": focus_guides.get(
                self.selected_pattern_type,
                "Look closely at the structure of each example. What repeats?"
            ),
            "action": "structural_analysis"
        }
    
    def _analyze_common_elements(self) -> List[str]:
        """Analyze code to find common syntactic elements"""
        common_elements = []
        
        if not self.code_examples:
            return common_elements
        
        # Extract selectors, properties, values
        all_code = " ".join([ex.code for ex in self.code_examples])
        
        # Look for CSS selectors
        selectors = re.findall(r'([.#][a-zA-Z0-9_-]+|\[[^\]]+\])', all_code)
        if selectors:
            from collections import Counter
            common_selectors = [sel for sel, count in Counter(selectors).items() 
                              if count >= len(self.code_examples) * 0.7]  # In 70%+ examples
            common_elements.extend(common_selectors)
        
        # Look for CSS properties
        properties = re.findall(r'([a-zA-Z-]+)\s*:', all_code)
        if properties:
            from collections import Counter
            common_props = [prop for prop, count in Counter(properties).items() 
                          if count >= len(self.code_examples)]
            common_elements.extend(common_props)
        
        return common_elements[:3]  # Return top 3
    
    def _provide_simplify_hint(self) -> Dict[str, str]:
        """Simplify the problem with leading questions"""
        simplify_questions = {
            PatternType.SELECTOR_SPECIFICITY: [
                "If you had to give each selector type a 'power level', what would they be?",
                "What makes one selector 'stronger' than another?",
                "How would you explain which style wins to a 10-year-old?"
            ],
            PatternType.FLEXBOX_ALIGNMENT: [
                "If flex-direction is row, which axis is horizontal?",
                "What's the difference between 'main' and 'cross' axis?",
                "If you change flex-direction, what happens to justify-content?"
            ]
        }
        
        questions = simplify_questions.get(
            self.selected_pattern_type,
            ["What's the simplest version of this pattern?", "How would this work with just two elements?"]
        )
        
        question = random.choice(questions)
        
        return {
            "content": f"Let's simplify: {question}\n\n"
                      "Try to answer this simpler question first.",
            "action": "answer_simplified",
            "follow_up_question": question
        }
    
    def _provide_visual_hint(self) -> Dict[str, str]:
        """Provide visual/spatial hint"""
        visual_hints = {
            PatternType.SELECTOR_SPECIFICITY: {
                "content": "Think of selectors like a hierarchy:\n\n"
                          "INLINE STYLES (most powerful)\n"
                          "↓↓↓\n"
                          "IDs (#something)\n"
                          "↓↓↓\n"
                          "Classes (.something)\n"
                          "↓↓↓\n"
                          "Elements (div, p)\n\n"
                          "Which level is each selector in?",
                "visual": "hierarchy_pyramid"
            },
            PatternType.FLEXBOX_ALIGNMENT: {
                "content": "Visualize the axes:\n\n"
                          "MAIN AXIS → direction of flex (row/column)\n"
                          "CROSS AXIS → perpendicular to main\n\n"
                          "justify-content → aligns on MAIN axis\n"
                          "align-items → aligns on CROSS axis",
                "visual": "axis_diagram"
            }
        }
        
        hint_data = visual_hints.get(
            self.selected_pattern_type,
            {"content": "Draw the examples. What spatial relationships do you see?"}
        )
        
        return {
            "content": hint_data["content"],
            "action": "visualize",
            "visual_aid": hint_data.get("visual", "")
        }
    
    def _handle_pattern_resolution(self, evaluation: Dict) -> Dict[str, Any]:
        """
        Handle when pattern is discovered or max attempts reached
        Moves to Step 4: Refinement & Exceptions
        """
        self.state = DiscoveryState.PATTERN_REVEALED
        self.pattern_revealed = True
        
        # Calculate metrics
        total_time = time.time() - self.discovery_start_time if self.discovery_start_time else 0
        
        # Determine discovery success
        user_discovered = evaluation["score"] >= 4
        discovery_score = 5 if user_discovered else max(0, 5 - self.current_attempts)
        
        # Create pattern result
        self.pattern_result = PatternDiscoveryResult(
            pattern_id=f"pattern_{int(time.time())}_{self.user_id}",
            discovered_pattern=self.current_pattern["name"],
            user_discovered=user_discovered,
            attempts_required=self.current_attempts,
            total_time_seconds=total_time,
            discovery_score=discovery_score,
            mental_model=self.current_pattern["mental_model"]
        )
        
        # Update phase log
        self.phase_log["pattern_discovery"]["final_score"] = discovery_score
        self.phase_log["pattern_discovery"]["time_taken"] = total_time
        self.phase_log["pattern_discovery"]["user_discovered"] = user_discovered
        
        # Log to database (Doc 2)
        self._log_to_database_doc2()
        
        # Generate pattern reveal
        pattern_reveal = self._reveal_pattern_with_insights()
        
        # Move to exceptions phase
        self.state = DiscoveryState.EXCEPTIONS_SEARCH
        
        response = {
            "status": "pattern_resolved",
            "user_discovered": user_discovered,
            "discovery_score": discovery_score,
            "total_attempts": self.current_attempts,
            "total_time": f"{total_time:.1f}s",
            "pattern_details": pattern_reveal,
            "next_step": "find_exceptions",
            "instructions": "Excellent! Now let's test the boundaries of this pattern. "
                          "Every rule has exceptions - can you find where this pattern breaks?",
            "mental_model": self.current_pattern["mental_model"],
            "database_updated": True,
            "doc2_score": discovery_score
        }
        
        if not user_discovered:
            response["teacher_note"] = "Pattern revealed after maximum attempts"
        
        return response
    
    def _reveal_pattern_with_insights(self) -> Dict[str, Any]:
        """Reveal the pattern with detailed explanations and insights"""
        # Generate deeper insights using Gemini
        prompt = f"""
        Provide a comprehensive explanation of this programming pattern:
        
        PATTERN: {self.current_pattern['name']}
        DESCRIPTION: {self.current_pattern['description']}
        MENTAL MODEL: {self.current_pattern['mental_model']}
        
        STUDENT CONTEXT:
        - Attempts needed: {self.current_attempts}
        - Discovered independently: {self.pattern_result.user_discovered}
        - Common misconceptions: {self.pattern_metadata.get('misconceptions', [])}
        
        Provide:
        1. Clear technical explanation
        2. Visual/spatial analogy
        3. Real-world comparison
        4. Why this pattern exists (design rationale)
        5. Most common mistakes to avoid
        
        Format as JSON.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            insights = json.loads(response.text)
        except:
            insights = {
                "technical_explanation": self.current_pattern['description'],
                "visual_analogy": "Like more specific rules overriding general ones",
                "real_world_comparison": "Like a detailed instruction overriding a general guideline",
                "design_rationale": "Provides predictable cascade of styles",
                "common_mistakes": self.pattern_metadata.get('misconceptions', [])
            }
        
        return {
            "pattern_name": self.current_pattern["name"],
            "official_description": self.current_pattern["description"],
            "mental_model": self.current_pattern["mental_model"],
            "key_insights": [
                f"Core principle: {self.current_pattern['description']}",
                f"Think of it as: {self.current_pattern['mental_model']}",
                f"This pattern appears in: {', '.join(self.pattern_metadata.get('variations', ['many contexts']))}"
            ],
            "technical_details": insights,
            "connection_to_priming": self._connect_to_priming_phase()
        }
    
    def _connect_to_priming_phase(self) -> List[str]:
        """Connect discovered pattern to previously learned terminology"""
        connections = []
        
        if "terminology" in self.priming_data:
            for term in self.priming_data["terminology"][:5]:
                term_name = term.get("term", "")
                if term_name and term_name.lower() in self.current_pattern["description"].lower():
                    connections.append(f"Relates to '{term_name}' from our terminology")
        
        return connections if connections else ["Builds on foundational concepts from Phase 1"]
    
    def _log_to_database_doc2(self):
        """Log pattern discovery results to Database Doc 2"""
        if not self.pattern_result:
            return
        
        doc2_entry = {
            "pattern_id": self.pattern_result.pattern_id,
            "pattern_name": self.current_pattern["name"],
            "discovery_score": self.pattern_result.discovery_score,
            "attempts_required": self.pattern_result.attempts_required,
            "user_discovered": self.pattern_result.user_discovered,
            "time_seconds": self.pattern_result.total_time_seconds,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "exceptions_found_count": 0,  # Will update
            "exceptions_score": 0,  # Will update
            "analogy_created": False,
            "analogy_quality": 0,
            "what_if_scenarios": 0
        }
        
        # Store for database integration
        self.phase_log["database_doc2_entry"] = doc2_entry
        
        print(f"\n📊 LOGGED TO DATABASE DOC 2:")
        print(f"   Pattern: {doc2_entry['pattern_name']}")
        print(f"   Score: {doc2_entry['discovery_score']}/5")
        print(f"   Discovered independently: {doc2_entry['user_discovered']}")
    
    # ============================================================================
    # EXCEPTIONS & EDGE CASES PHASE
    # ============================================================================
    
    def start_exceptions_phase(self) -> Dict[str, Any]:
        """
        Step 4: Guide user to find exceptions/edge cases
        """
        self.state = DiscoveryState.EXCEPTIONS_SEARCH
        
        print(f"\n🔬 EXCEPTIONS & EDGE CASES")
        print(f"Pattern: {self.current_pattern['name']}")
        print("-" * 50)
        
        prompt = f"""
        Create a challenge to help students find exceptions to this pattern:
        
        PATTERN: {self.current_pattern['name']}
        RULE: {self.current_pattern['description']}
        MENTAL MODEL: {self.current_pattern['mental_model']}
        
        Create:
        1. A provocative question to stimulate thinking about exceptions
        2. 2-3 example exceptions (for teacher reference)
        3. Evaluation criteria for student-proposed exceptions
        4. A scoring rubric (0-5) for exception quality
        
        Consider:
        - Browser-specific quirks
        - Edge cases in specifications
        - Practical limitations
        - Conflicting rules or properties
        
        Return JSON.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            exceptions_data = json.loads(response.text)
            
            # Store teacher's example exceptions
            self.teacher_exceptions = exceptions_data.get("example_exceptions", [])
            
            return {
                "status": "exceptions_phase",
                "challenge_question": exceptions_data.get("question", 
                    f"Where does the pattern '{self.current_pattern['name']}' break?"),
                "evaluation_criteria": exceptions_data.get("evaluation_criteria", 
                    ["Validity", "Creativity", "Specificity"]),
                "scoring_rubric": exceptions_data.get("scoring_rubric",
                    "0-5: 0=invalid, 3=valid but obvious, 5=creative and insightful"),
                "instructions": "Think creatively about real-world scenarios where this pattern might fail. "
                              "Consider browser quirks, edge cases, or conflicting rules.",
                "thinking_prompts": [
                    "What if a browser has a bug?",
                    "What extreme conditions would break this?",
                    "Are there conflicting rules that could override this pattern?",
                    "What about deprecated or experimental features?"
                ],
                "max_exceptions_to_find": 3,
                "next_action": "propose_exception"
            }
            
        except Exception as e:
            return {
                "status": "exceptions_phase",
                "challenge_question": f"Invent a scenario where '{self.current_pattern['name']}' doesn't work.",
                "evaluation_criteria": ["Is it a real exception?", "Is it creative?", "Is it specific?"],
                "scoring_rubric": "0-5 based on validity and insight",
                "instructions": "Think of edge cases or special situations.",
                "thinking_prompts": ["Browser bugs", "Extreme values", "Conflicting rules"],
                "max_exceptions_to_find": 3
            }
    
    def evaluate_exception_proposal(self, user_exception: str) -> Dict[str, Any]:
        """
        Evaluate user's proposed exception
        
        Args:
            user_exception: User's description of an exception
            
        Returns:
            Evaluation with validity score and feedback
        """
        prompt = f"""
        Evaluate a student's proposed exception to a programming pattern.
        
        PATTERN: {self.current_pattern['name']}
        PATTERN RULE: {self.current_pattern['description']}
        
        STUDENT'S PROPOSED EXCEPTION: "{user_exception}"
        
        TEACHER'S EXAMPLE EXCEPTIONS (for reference):
        {json.dumps(self.teacher_exceptions, indent=2)}
        
        EVALUATION DIMENSIONS:
        1. VALIDITY: Does it legitimately break/contradict the pattern? (true/false)
        2. CREATIVITY: Is it beyond obvious/common exceptions? (1-5)
        3. SPECIFICITY: Is it concrete and testable? (1-5)
        4. PRACTICALITY: Is it a real-world relevant scenario? (1-5)
        
        CALCULATE OVERALL SCORE (0-5):
        - 0: Invalid or irrelevant
        - 1-2: Valid but obvious/common
        - 3-4: Valid and somewhat creative
        - 5: Highly valid, creative, and specific
        
        Return JSON:
        {{
            "valid": true/false,
            "overall_score": 0-5,
            "dimension_scores": {{
                "creativity": 1-5,
                "specificity": 1-5,
                "practicality": 1-5
            }},
            "feedback": "Explain your evaluation",
            "suggestion": "How to improve this exception idea",
            "real_world_example": "If valid, provide a code example",
            "is_novel": "Is this different from common exceptions?",
            "knowledge_demonstrated": "What understanding does this show?"
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            evaluation = json.loads(response.text)
            
            # Store valid exceptions
            if evaluation.get("valid", False) and evaluation.get("overall_score", 0) >= 2:
                exception_record = {
                    "description": user_exception,
                    "score": evaluation["overall_score"],
                    "dimension_scores": evaluation.get("dimension_scores", {}),
                    "feedback": evaluation["feedback"],
                    "timestamp": time.strftime("%H:%M:%S"),
                    "real_world_example": evaluation.get("real_world_example", "")
                }
                self.exceptions.append(exception_record)
                
                # Update pattern result
                if self.pattern_result:
                    self.pattern_result.exceptions_found.append(exception_record)
                    self.pattern_result.exceptions_score = min(5, len(self.exceptions))
                
                # Update phase log
                self.phase_log["exception_discovery"]["exceptions_found"].append({
                    "description": user_exception[:100] + "..." if len(user_exception) > 100 else user_exception,
                    "score": evaluation["overall_score"]
                })
                self.phase_log["exception_discovery"]["exceptions_score"] = \
                    self.pattern_result.exceptions_score if self.pattern_result else 0
            
            # Check if enough exceptions found
            exceptions_found = len(self.exceptions)
            if exceptions_found >= 3:
                self.state = DiscoveryState.ANALOGY_GENERATION
                evaluation["phase_progress"] = "ready_for_analogy"
                evaluation["exceptions_summary"] = f"Found {exceptions_found} valid exceptions"
            
            return evaluation
            
        except Exception as e:
            return {
                "valid": False,
                "overall_score": 0,
                "feedback": "Let's think about this more carefully...",
                "suggestion": "Be more specific about how exactly the pattern breaks.",
                "is_novel": "unknown"
            }
    
    # ============================================================================
    # ANALOGY GENERATION PHASE
    # ============================================================================
    
    def start_analogy_generation(self) -> Dict[str, Any]:
        """
        Phase 3.1: Ask user to create real-world analogy
        """
        self.state = DiscoveryState.ANALOGY_GENERATION
        
        print(f"\n🎭 ANALOGY GENERATION")
        print("-" * 50)
        
        prompt = f"""
        Create a prompt asking students to create a real-world analogy for this pattern:
        
        PATTERN: {self.current_pattern['name']}
        PATTERN DESCRIPTION: {self.current_pattern['description']}
        MENTAL MODEL: {self.current_model['mental_model']}
        
        The prompt should:
        1. Explain what makes a good analogy
        2. Provide an example analogy
        3. Ask the student to create their own
        4. Include evaluation criteria
        
        Return JSON with prompt and evaluation rubric.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            analogy_data = json.loads(response.text)
            
            return {
                "status": "analogy_generation",
                "prompt": analogy_data.get("prompt", 
                    f"Create a real-world analogy for '{self.current_pattern['name']}'"),
                "example_analogy": analogy_data.get("example_analogy",
                    "Like a traffic light: red overrides green regardless of order"),
                "evaluation_criteria": analogy_data.get("evaluation_criteria",
                    ["Accuracy", "Creativity", "Clarity"]),
                "instructions": "Create an analogy that helps remember this pattern. "
                              "Think about everyday situations with similar rules.",
                "next_action": "submit_analogy"
            }
            
        except:
            return {
                "status": "analogy_generation",
                "prompt": f"Create a real-world analogy for '{self.current_pattern['name']}'",
                "example_analogy": "Like specific rules overriding general policies",
                "instructions": "Think of everyday situations with similar hierarchical rules.",
                "evaluation_criteria": ["Does it capture the essence?", "Is it memorable?", "Is it accurate?"]
            }
    
    def evaluate_analogy(self, user_analogy: str) -> Dict[str, Any]:
        """
        Evaluate user's created analogy
        """
        prompt = f"""
        Evaluate a student's analogy for a programming pattern.
        
        PATTERN: {self.current_pattern['name']}
        PATTERN ESSENCE: {self.current_pattern['description']}
        
        STUDENT'S ANALOGY: "{user_analogy}"
        
        EVALUATION CRITERIA:
        1. ACCURACY: Does it correctly represent the pattern? (1-5)
        2. CREATIVITY: Is it original and imaginative? (1-5)
        3. MEMORABILITY: Is it easy to remember? (1-5)
        4. CLARITY: Is it easy to understand? (1-5)
        
        Calculate overall score (0-5 average).
        
        Return JSON with scores and detailed feedback.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            evaluation = json.loads(response.text)
            
            # Store user analogy
            self.user_analogy = {
                "analogy": user_analogy,
                "evaluation": evaluation,
                "timestamp": time.strftime("%H:%M:%S")
            }
            
            # Update phase log
            self.phase_log["analogy_generation"]["analogy_created"] = True
            self.phase_log["analogy_generation"]["analogy_quality"] = \
                evaluation.get("overall_score", 0)
            
            # Update pattern result
            if self.pattern_result:
                self.pattern_result.analogy_quality = evaluation.get("overall_score", 0)
            
            # Move to next phase
            self.state = DiscoveryState.WHAT_IF_EXPLORATION
            evaluation["next_phase"] = "what_if_exploration"
            
            return evaluation
            
        except:
            return {
                "overall_score": 3,
                "feedback": "Good analogy! Let's explore edge cases next.",
                "next_phase": "what_if_exploration"
            }
    
    # ============================================================================
    # WHAT-IF SCENARIO PHASE
    # ============================================================================
    
    def start_what_if_exploration(self) -> Dict[str, Any]:
        """
        Phase 3.2: The "What If" Engine
        Ask user to create edge case scenarios
        """
        self.state = DiscoveryState.WHAT_IF_EXPLORATION
        
        print(f"\n🤔 WHAT-IF SCENARIO EXPLORATION")
        print("-" * 50)
        
        what_if_prompt = f"""
        Command: "Invent a specific browser scenario or screen size where 
        this {self.current_pattern['name']} would look terrible or break completely."
        
        Provide:
        1. The command to give the student
        2. Example scenarios (for teacher)
        3. Evaluation criteria
        4. Why this is important for web developers
        
        Return JSON.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=what_if_prompt
            )
            what_if_data = json.loads(response.text)
            
            return {
                "status": "what_if_exploration",
                "command": what_if_data.get("command",
                    f"Invent a specific browser scenario where {self.current_pattern['name']} breaks."),
                "example_scenarios": what_if_data.get("example_scenarios", []),
                "evaluation_criteria": what_if_data.get("evaluation_criteria",
                    ["Specificity", "Realism", "Impact", "Creativity"]),
                "importance": what_if_data.get("importance",
                    "Helps anticipate and prevent real-world bugs"),
                "instructions": "Think of extreme or unusual situations that would break this pattern.",
                "next_action": "submit_what_if_scenario"
            }
            
        except:
            return {
                "status": "what_if_exploration",
                "command": f"Invent a browser or device scenario where {self.current_pattern['name']} fails.",
                "instructions": "Consider screen sizes, browsers, user settings, or content extremes.",
                "evaluation_criteria": ["Is it specific?", "Could it really happen?", "Would it break things?"]
            }
    
    def evaluate_what_if_scenario(self, scenario: str) -> Dict[str, Any]:
        """
        Evaluate user's what-if scenario
        """
        prompt = f"""
        Evaluate a student's "what-if" scenario for breaking a pattern.
        
        PATTERN: {self.current_pattern['name']}
        
        STUDENT'S SCENARIO: "{scenario}"
        
        EVALUATE:
        1. SPECIFICITY: Is it concrete and detailed? (1-5)
        2. REALISM: Could it happen in real browsers? (1-5)
        3. IMPACT: Would it actually break things? (1-5)
        4. INSIGHT: Shows understanding of pattern limits (1-5)
        
        Return JSON with scores and feedback.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            evaluation = json.loads(response.text)
            
            # Store scenario
            self.what_if_scenarios.append({
                "scenario": scenario,
                "evaluation": evaluation,
                "timestamp": time.strftime("%H:%M:%S")
            })
            
            # Update phase log
            self.phase_log["what_if_scenarios"].append({
                "scenario": scenario[:100] + "..." if len(scenario) > 100 else scenario,
                "score": evaluation.get("overall_score", 0)
            })
            
            # Check if phase is complete
            if len(self.what_if_scenarios) >= 2:  # At least 2 good scenarios
                self.state = DiscoveryState.COMPLETE
                evaluation["phase_complete"] = True
            
            return evaluation
            
        except:
            return {
                "overall_score": 3,
                "feedback": "Interesting scenario! This helps understand pattern limits.",
                "phase_complete": len(self.what_if_scenarios) >= 2
            }
    
    # ============================================================================
    # PHASE COMPLETION
    # ============================================================================
    
    def complete_phase(self) -> Dict[str, Any]:
        """
        Complete the relational thinking phase
        Returns comprehensive results and prepares for next phase
        """
        self.state = DiscoveryState.COMPLETE
        
        # Calculate final metrics
        total_time = time.time() - self.discovery_start_time if self.discovery_start_time else 0
        
        # Update database logging
        if self.pattern_result:
            self.phase_log["pattern_discovery"]["final_score"] = self.pattern_result.discovery_score
            self.phase_log["exception_discovery"]["exceptions_score"] = self.pattern_result.exceptions_score
            self.phase_log["exception_discovery"]["exceptions_count"] = len(self.exceptions)
        
        # Identify knowledge gaps (for Database Doc 4)
        knowledge_gaps = self._identify_knowledge_gaps()
        self.phase_log["knowledge_gaps_identified"] = knowledge_gaps
        
        # Prepare for next phase (Interleaving)
        next_phase_prep = self._prepare_for_interleaving()
        
        # Generate comprehensive summary
        summary = self._generate_phase_summary()
        
        return {
            "status": "phase_complete",
            "phase": "relational_thinking",
            "summary": summary,
            "performance_metrics": {
                "total_attempts": self.current_attempts,
                "total_time_seconds": total_time,
                "discovery_score": self.pattern_result.discovery_score if self.pattern_result else 0,
                "exceptions_score": self.pattern_result.exceptions_score if self.pattern_result else 0,
                "valid_exceptions_found": len(self.exceptions),
                "analogy_quality": self.pattern_result.analogy_quality if self.pattern_result else 0,
                "what_if_scenarios": len(self.what_if_scenarios),
                "pattern_fully_explored": True
            },
            "pattern_details": {
                "name": self.current_pattern["name"],
                "mental_model": self.current_pattern["mental_model"],
                "user_discovered": self.pattern_result.user_discovered if self.pattern_result else False
            },
            "achievements": self._calculate_achievements(),
            "knowledge_gaps": knowledge_gaps,
            "next_phase": "interleaving",
            "next_phase_preparation": next_phase_prep,
            "database_updates": {
                "doc2": self.phase_log.get("database_doc2_entry", {}),
                "doc4": knowledge_gaps,
                "doc5": self.user_analogy if self.user_analogy else {}
            }
        }
    
    def _identify_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """Identify knowledge gaps for Database Doc 4"""
        gaps = []
        
        # Analyze discovery attempts
        if self.discovery_attempts:
            low_score_attempts = [a for a in self.discovery_attempts if a.score <= 2]
            if low_score_attempts:
                gap = {
                    "gap_id": f"gap_pattern_recognition_{int(time.time())}",
                    "concept": "Pattern Recognition",
                    "root_cause": "Difficulty identifying underlying principles from examples",
                    "severity": 5 - min(a.score for a in low_score_attempts),  # 1-5
                    "evidence": f"{len(low_score_attempts)} low-score attempts ({min(a.score for a in low_score_attempts)}/5 average)",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "related_module": self.topic.value,
                    "remediation_suggestions": [
                        "More practice with inductive reasoning",
                        "Explicit guidance on abstraction",
                        "Simpler pattern discovery exercises"
                    ]
                }
                gaps.append(gap)
        
        # Analyze exceptions found
        if len(self.exceptions) < 2:
            gap = {
                "gap_id": f"gap_critical_thinking_{int(time.time())}",
                "concept": "Critical Thinking / Edge Cases",
                "root_cause": "Difficulty imagining scenarios where rules break",
                "severity": 3 if len(self.exceptions) == 1 else 4,
                "evidence": f"Only {len(self.exceptions)} valid exceptions found (target: 3+)",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "related_module": self.topic.value,
                "remediation_suggestions": [
                    "Practice with 'what-if' scenarios",
                    "Study real-world browser quirks",
                    "Analyze bug reports for similar patterns"
                ]
            }
            gaps.append(gap)
        
        # Check analogy quality
        if self.pattern_result and self.pattern_result.analogy_quality < 3:
            gap = {
                "gap_id": f"gap_analogical_thinking_{int(time.time())}",
                "concept": "Analogical Reasoning",
                "root_cause": "Difficulty creating accurate analogies",
                "severity": 5 - self.pattern_result.analogy_quality,
                "evidence": f"Analogy quality score: {self.pattern_result.analogy_quality}/5",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "related_module": self.topic.value,
                "remediation_suggestions": [
                    "Practice relating abstract concepts to concrete examples",
                    "Study how experts create analogies",
                    "Analyze good/bad analogies for programming concepts"
                ]
            }
            gaps.append(gap)
        
        return gaps
    
    def _calculate_achievements(self) -> List[str]:
        """Calculate achievements earned during this phase"""
        achievements = []
        
        if self.pattern_result:
            if self.pattern_result.discovery_score == 5:
                achievements.append("Pattern Discovery Master")
            elif self.pattern_result.discovery_score >= 4:
                achievements.append("Quick Learner")
            
            if self.pattern_result.user_discovered:
                achievements.append("Independent Thinker")
            
            if len(self.exceptions) >= 3:
                achievements.append("Exception Hunter")
            elif len(self.exceptions) >= 1:
                achievements.append("Critical Thinker")
            
            if self.pattern_result.analogy_quality >= 4:
                achievements.append("Analogy Artist")
        
        if len(self.what_if_scenarios) >= 2:
            achievements.append("Scenario Explorer")
        
        if self.current_attempts <= 2 and self.pattern_result:
            if self.pattern_result.discovery_score >= 4:
                achievements.append("Efficient Learner")
        
        return achievements if achievements else ["Phase Completer"]
    
    def _prepare_for_interleaving(self) -> Dict[str, Any]:
        """Prepare data needed for next phase (Interleaving & Compound Questions)"""
        # Identify which previous concepts to interleave
        previous_concepts = []
        
        # Based on pattern type, determine related concepts
        if self.selected_pattern_type == PatternType.SELECTOR_SPECIFICITY:
            previous_concepts = ["CSS Cascade", "Inheritance", "Box Model"]
        
        # Generate compound question prompt
        prompt = f"""
        Create a compound question that requires understanding both:
        1. Current pattern: {self.current_pattern['name']}
        2. A related previous concept (choose from: {', '.join(previous_concepts)})
        
        The question should:
        - Require application of both concepts
        - Be practical/coding-oriented
        - Test deep understanding, not just recall
        - Have a clear correct answer
        
        Return JSON with question and explanation.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            compound_data = json.loads(response.text)
            
            return {
                "compound_question": compound_data.get("question",
                    f"How does {self.current_pattern['name']} interact with {previous_concepts[0] if previous_concepts else 'previous concepts'}?"),
                "question_explanation": compound_data.get("explanation",
                    "Tests understanding of both concepts and their interaction"),
                "related_concepts": previous_concepts,
                "difficulty": "intermediate",
                "requires": ["pattern_application", "concept_integration"]
            }
            
        except:
            return {
                "compound_question": f"Explain how {self.current_pattern['name']} affects website performance.",
                "related_concepts": previous_concepts,
                "difficulty": "intermediate"
            }
    
    def _generate_phase_summary(self) -> str:
        """Generate a human-readable summary of the phase"""
        if not self.pattern_result:
            return "Phase not completed."
        
        summary_lines = [
            f"📚 RELATIONAL THINKING PHASE COMPLETE",
            f"   Pattern: {self.current_pattern['name']}",
            f"   Discovery: {self.pattern_result.discovery_score}/5 "
            f"({'self-discovered' if self.pattern_result.user_discovered else 'guided'})",
            f"   Attempts: {self.pattern_result.attempts_required}",
            f"   Time: {self.pattern_result.total_time_seconds:.1f}s",
            f"   Exceptions found: {len(self.exceptions)} "
            f"(score: {self.pattern_result.exceptions_score}/5)",
            f"   Analogy quality: {self.pattern_result.analogy_quality}/5",
            f"   What-if scenarios: {len(self.what_if_scenarios)}",
            f"   Mental model: {self.current_pattern['mental_model'][:50]}..."
        ]
        
        return "\n".join(summary_lines)
    
    def get_phase_log(self) -> Dict[str, Any]:
        """Get the complete phase log for database integration"""
        return self.phase_log


# ============================================================================
# INTEGRATION WITH TEACHING ORCHESTRATOR
# ============================================================================

def integrate_with_orchestrator_example():
    """Example of how this integrates with TeachingOrchestrator"""
    
    class MockTeachingOrchestrator:
        """Simplified orchestrator for demonstration"""
        
        def __init__(self, gemini_client, user_id):
            self.client = gemini_client
            self.user_id = user_id
            self.current_phase = None
            self.phase_history = []
            
        def execute_relational_thinking(self, priming_result, topic):
            """Execute relational thinking phase"""
            print(f"\n🎓 ORCHESTRATOR: Starting Relational Thinking Phase")
            
            # Create phase instance
            self.current_phase = RelationalThinkingPhase(
                gemini_client=self.client,
                topic=topic,
                priming_data=priming_result,
                user_id=self.user_id,
                max_attempts=4  # Configurable
            )
            
            # Start phase
            phase_start = self.current_phase.execute_phase()
            self.phase_history.append({
                "action": "phase_started",
                "data": phase_start
            })
            
            return {
                "status": "phase_started",
                "phase_data": phase_start,
                "next_step": "process_user_input",
                "phase_instance": self.current_phase
            }
        
        def process_user_response(self, user_input):
            """Process user response in current phase"""
            if not self.current_phase:
                return {"error": "No active phase"}
            
            # Get current state
            state = self.current_phase.state
            
            if state in [DiscoveryState.DISCOVERY_PROMPT, DiscoveryState.BLOCKING_LOOP]:
                # User is attempting pattern discovery
                result = self.current_phase.process_user_attempt(user_input)
                
                if result.get("status") == "pattern_resolved":
                    # Pattern resolved, move to exceptions
                    exceptions_start = self.current_phase.start_exceptions_phase()
                    result["next_step"] = exceptions_start
                
                self.phase_history.append({
                    "state": state.value,
                    "user_input": user_input[:50],
                    "result": result.get("status", "unknown")
                })
                
                return result
            
            elif state == DiscoveryState.EXCEPTIONS_SEARCH:
                # User proposing exception
                result = self.current_phase.evaluate_exception_proposal(user_input)
                
                if result.get("phase_progress") == "ready_for_analogy":
                    # Enough exceptions, move to analogy
                    analogy_start = self.current_phase.start_analogy_generation()
                    result["next_phase"] = analogy_start
                
                return result
            
            # Handle other states...
            
            return {"status": "processed", "state": state.value}
        
        def complete_current_phase(self):
            """Complete the current phase"""
            if not self.current_phase:
                return {"error": "No active phase"}
            
            completion = self.current_phase.complete_phase()
            self.phase_history.append({
                "action": "phase_completed",
                "completion_data": completion
            })
            
            # Prepare for next phase (Interleaving)
            next_phase_prep = {
                "phase": "interleaving",
                "requires": ["database_doc4_access"],  # Need knowledge gaps
                "compound_question": completion.get("next_phase_preparation", {}),
                "user_ready": completion.get("performance_metrics", {}).get("pattern_fully_explored", False)
            }
            
            return {
                **completion,
                "orchestrator_next_steps": next_phase_prep
            }


# ============================================================================
# DEMONSTRATION
# ============================================================================

if __name__ == "__main__":
    print("🚀 RELATIONAL THINKING PHASE - DEMONSTRATION")
    print("=" * 60)
    
    # Create mock Gemini client
    class MockGeminiClient:
        def __init__(self):
            pass
        
        class models:
            @staticmethod
            def generate_content(model, contents, config=None):
                print(f"\n[Gemini API called: {contents[:100]}...]")
                
                class Response:
                    # Mock response for example generation
                    if "create 3 DISTINCT code examples" in contents:
                        text = json.dumps({
                            "pattern_summary": "Selector specificity determines style precedence",
                            "examples": [
                                {
                                    "code": "/* Example 1 */\n.button { color: blue; }\n#submit.button { color: red; }",
                                    "description": "ID + class overrides class alone",
                                    "complexity": "beginner",
                                    "key_element": "#submit.button",
                                    "visual_description": "Red text instead of blue"
                                },
                                {
                                    "code": "/* Example 2 */\n.nav .item { padding: 10px; }\n.item.active { padding: 20px; }",
                                    "description": "Two classes override one class",
                                    "complexity": "intermediate",
                                    "key_element": ".item.active",
                                    "visual_description": "Larger padding"
                                },
                                {
                                    "code": "/* Example 3 */\ndiv p { margin: 5px; }\nbody .content p { margin: 15px; }",
                                    "description": "More ancestors increase specificity",
                                    "complexity": "advanced",
                                    "key_element": "body .content p",
                                    "visual_description": "Larger margin"
                                }
                            ],
                            "common_misconceptions": [
                                "Order in CSS file matters most",
                                "!important is the only way to override",
                                "More properties = higher specificity"
                            ],
                            "pattern_variations": [
                                "Inline styles vs external CSS",
                                "!important exception",
                                "Browser-specific overrides"
                            ]
                        })
                    else:
                        text = '{"score": 3, "feedback": "Good observation! Look closer at selector structure."}'
                
                return type('obj', (object,), {'text': text})()
    
    # Mock priming data
    mock_priming = {
        "terminology": [
            {"term": "Selector", "definition": "Pattern to select elements"},
            {"term": "Specificity", "definition": "How specific a selector is"}
        ],
        "syntax_etymology": [
            {"syntax_element": "#", "symbol_name": "hash", "logic_reason": "Unique identifier"}
        ]
    }
    
    # Create and run phase
    mock_client = MockGeminiClient()
    phase = RelationalThinkingPhase(
        gemini_client=mock_client,
        topic=ModuleTopic.CSS_BASICS,
        priming_data=mock_priming,
        user_id="demo_user_001",
        max_attempts=3
    )
    
    print("\n1. Starting phase...")
    start_result = phase.execute_phase()
    
    print(f"\n2. Phase started:")
    print(f"   State: {start_result['state']}")
    print(f"   Pattern: {start_result['pattern_type']}")
    print(f"   Examples shown: {len(start_result['examples'])}")
    
    print(f"\n3. Simulating user attempts...")
    
    # First attempt (vague)
    attempt1 = phase.process_user_attempt(
        "They all change how elements look",
        attempt_time=30.5
    )
    print(f"\n   Attempt 1:")
    print(f"   Score: {attempt1['score']}/5")
    print(f"   Feedback: {attempt1['feedback'][:80]}...")
    
    # Get hint
    if attempt1.get('hint_available'):
        hint = phase.provide_hint()
        print(f"\n   Hint ({hint['hint_type']}): {hint['hint'][:80]}...")
    
    # Second attempt (better)
    attempt2 = phase.process_user_attempt(
        "Selectors with more dots or # symbols win",
        attempt_time=45.2
    )
    
    if attempt2.get('status') == 'pattern_resolved':
        print(f"\n4. Pattern resolved!")
        print(f"   Discovered: {attempt2['user_discovered']}")
        print(f"   Score: {attempt2['discovery_score']}/5")
        print(f"   Next: {attempt2['next_step']}")
        
        # Move to exceptions
        print(f"\n5. Starting exceptions phase...")
        exceptions = phase.start_exceptions_phase()
        print(f"   Question: {exceptions['challenge_question'][:80]}...")
        
        # Propose exception
        exception_eval = phase.evaluate_exception_proposal(
            "What if someone uses !important on the less specific selector?"
        )
        print(f"\n6. Exception evaluation:")
        print(f"   Valid: {exception_eval.get('valid', False)}")
        print(f"   Score: {exception_eval.get('overall_score', 0)}/5")
    
    # Complete phase
    print(f"\n7. Completing phase...")
    completion = phase.complete_phase()
    
    print(f"\n📋 FINAL SUMMARY:")
    print(f"   Phase: {completion['phase']}")
    print(f"   Discovery score: {completion['performance_metrics']['discovery_score']}/5")
    print(f"   Exceptions found: {completion['performance_metrics']['valid_exceptions_found']}")
    print(f"   Knowledge gaps: {len(completion['knowledge_gaps'])}")
    print(f"   Next phase: {completion['next_phase']}")
    
    print(f"\n✅ Relational Thinking Phase implementation ready!")