
import os
from utils.gemini_client import GeminiClient
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# Topic Definition
class ModuleTopic(Enum):
    """Topics in the teaching pipeline"""
    HTML_BASICS = "html_basics"
    CSS_BASICS = "css_basics"
    CSS_LAYOUT = "css_layout"
    CSS_ANIMATIONS = "css_animations"
    NEUMORPHISM = "neumorphism"
    RESPONSIVE_DESIGN = "responsive_design"
    JS_FOUNDATIONS = "js_foundations"

@dataclass
class TerminologyEntry:
    """Represents a single term in the glossary"""
    term: str
    definition: str
    abbreviation: Optional[str] = None
    acronym: bool = False
    related_terms: List[str] = field(default_factory=list)
    mnemonic: Optional[str] = None

@dataclass
class SyntaxEtymology:
    """Represents syntax etymology explanation"""
    syntax_element: str
    symbol_name: str
    origin: str
    logic_reason: str
    memory_hook: str
    common_mistakes: List[str] = field(default_factory=list)


class PrimingPhase:
    """
    Handles Phase 1: PRIMING (Terminology Scan and Syntax Logic/Etymology)
    Updated to use Gemini API directly while keeping the robust logic from the user's design.
    """
    
    def __init__(self, gemini_client, topic: ModuleTopic):
        """
        Initialize Priming Phase with Gemini client
        
        Args:
            gemini_client: google.genai.Client instance
            topic: Current module topic
        """
        self.client = gemini_client
        self.topic = topic
        self.terminology_scan_complete = False
        self.syntax_logic_complete = False
        
        # Database for logging
        self.priming_log = {
            "topic": topic.value,
            "timestamp": datetime.now().isoformat(),
            "terminology": [],
            "syntax_etymology": [],
            "user_understanding_check": {}
        }
        
        self.topic_contexts = {}
        self._setup_topic_primer(topic)
    
    def _setup_topic_primer(self, topic: ModuleTopic):
        """Setup topic-specific prompts and examples"""
        self.topic_contexts = {
            ModuleTopic.HTML_BASICS: {
                "focus": "HTML structure, tags, attributes, semantic elements",
                "key_terms": ["tag", "attribute", "element", "semantic", "DOCTYPE"],
                "syntax_elements": ["< >", "/", "=", '"', "<!-- -->"]
            },
            ModuleTopic.CSS_BASICS: {
                "focus": "Selectors, properties, values, specificity",
                "key_terms": ["selector", "property", "value", "specificity", "cascade"],
                "syntax_elements": [".", "#", ":", "::", "{ }", ";"]
            },
            ModuleTopic.CSS_LAYOUT: {
                "focus": "Box model, Flexbox, Grid, positioning",
                "key_terms": ["box-model", "flexbox", "grid", "position", "display"],
                "syntax_elements": ["display:", "position:", "margin", "padding"]
            },
            ModuleTopic.CSS_ANIMATIONS: {
                "focus": "Transitions, animations, keyframes, transforms",
                "key_terms": ["transition", "animation", "@keyframes", "transform", "timing-function"],
                "syntax_elements": ["@", "from/to", "%", "cubic-bezier()"]
            },
            ModuleTopic.NEUMORPHISM: {
                "focus": "Shadows, light sources, depth, soft UI",
                "key_terms": ["neumorphism", "inset", "shadow", "light-source", "blur"],
                "syntax_elements": ["box-shadow:", "inset", "blur", "spread"]
            },
            ModuleTopic.RESPONSIVE_DESIGN: {
                "focus": "Media queries, breakpoints, viewport, fluid units",
                "key_terms": ["@media", "breakpoint", "viewport", "rem/em", "vw/vh"],
                "syntax_elements": ["@media", "min-width", "max-width", "and"]
            },
             ModuleTopic.JS_FOUNDATIONS: {
                "focus": "Variables, functions, events, DOM",
                "key_terms": ["variable", "function", "event listener", "DOM", "API"],
                "syntax_elements": ["const", "let", "function", "=>", "[]", "{}"]
            }
        }

    def _call_gemini(self, prompt: str, model: str = "gemini-1.5-pro-latest") -> str:
        """Helper method to call Gemini API"""
        try:
            response = self.client.generate_content(
                model=model,
                contents=prompt
            )
            return response.text if response else ""
        except Exception as e:
            print(f"❌ Error calling Gemini API: {e}")
            return ""
    
    def execute_priming_phase(self) -> Dict:
        """Execute complete priming phase"""
        print(f"\n{'='*60}")
        print(f"PHASE 1: PRIMING - {self.topic.value.upper()}")
        print(f"{'='*60}")
        
        # Step 1: Terminology Scan
        terminology_data = self._perform_terminology_scan()
        
        # Step 2: Syntax Logic & Etymology
        syntax_data = self._perform_syntax_etymology()
        
        # Step 3: Check understanding
        understanding_check = self._check_user_understanding(terminology_data, syntax_data)
        
        # Update log
        self.priming_log["terminology"] = terminology_data
        self.priming_log["syntax_etymology"] = syntax_data
        self.priming_log["user_understanding_check"] = understanding_check
        
        return {
            "status": "priming_complete",
            "terminology": terminology_data,
            "syntax_etymology": syntax_data,
            "understanding_check": understanding_check,
            "next_step": "proceed_to_relational_thinking"
        }

    def _perform_terminology_scan(self) -> List[TerminologyEntry]:
        """Step 1: Skim the lesson and define glossary, abbreviations, acronyms"""
        topic_name = self.topic.value.replace('_', ' ').title()
        print(f"\n📚 TERMINOLOGY SCAN for {topic_name}")
        print("-" * 50)
        
        context = self.topic_contexts.get(self.topic, {"focus": "General", "key_terms": []})
        
        terminology_prompt = f"""
        As an expert in web development and cognitive psychology, extract and explain key terminology.
        
        TOPIC: {self.topic.value}
        FOCUS: {context['focus']}
        KEY TERMS: {', '.join(context.get('key_terms', []))}
        
        Extract the following for each term:
        1. TERM: The technical term
        2. DEFINITION: Clear, beginner-friendly definition
        3. ABBREVIATION: If applicable (e.g., CSS for Cascading Style Sheets)
        4. ACRONYM: True/False
        5. RELATED TERMS: Other terms this connects to
        6. MNEMONIC: Memory aid or association
        
        Format as a valid JSON list. Example:
        [
          {{
            "term": "CSS",
            "definition": "Cascading Style Sheets - controls visual presentation",
            "abbreviation": "CSS",
            "acronym": true,
            "related_terms": ["HTML", "JavaScript"],
            "mnemonic": "Cascading like waterfalls - styles flow down"
          }}
        ]
        
        Include at least 8 key terms for this topic. Return ONLY the JSON, no other text.
        """
        
        print("🤖 Querying Gemini for terminology...")
        response_text = self._call_gemini(terminology_prompt)
        
        terminology_entries = []
        
        if response_text:
            try:
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                term_data_list = json.loads(clean_text)
                if isinstance(term_data_list, dict):
                    term_data_list = [term_data_list]
                
                for term_data in term_data_list:
                    entry = TerminologyEntry(
                        term=term_data["term"],
                        definition=term_data["definition"],
                        abbreviation=term_data.get("abbreviation"),
                        acronym=term_data.get("acronym", False),
                        related_terms=term_data.get("related_terms", []),
                        mnemonic=term_data.get("mnemonic")
                    )
                    terminology_entries.append(entry)
                    
                    print(f"\n🔤 {entry.term}")
                    if entry.abbreviation:
                        print(f"   Abbreviation: {entry.abbreviation}")
                    print(f"   Definition: {entry.definition}")
                    if entry.mnemonic:
                        print(f"   💡 Mnemonic: {entry.mnemonic}")
                    if entry.related_terms:
                        print(f"   🔗 Related: {', '.join(entry.related_terms)}")
                
                print(f"\n✅ Successfully generated {len(terminology_entries)} terms from Gemini!")
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse Gemini response as JSON: {e}")
                print(f"Raw response: {response_text[:200]}...")
                print("🔄 Falling back to mock data...")
                terminology_entries = self._get_mock_terminology(self.topic)
        else:
            print("🔄 Using mock data due to API failure...")
            terminology_entries = self._get_mock_terminology(self.topic)
        
        self.terminology_scan_complete = True
        return terminology_entries
    
    def _perform_syntax_etymology(self) -> List[SyntaxEtymology]:
        """Step 2: Explain syntax logic, history, and mnemonics"""
        print(f"\n🔤 SYNTAX LOGIC & ETYMOLOGY")
        print("-" * 50)
        
        context = self.topic_contexts.get(self.topic, {"focus": "General", "syntax_elements": []})
        
        syntax_prompt = f"""
        As a language and history expert, explain the syntax etymology for {self.topic.value}.
        
        For each syntax element, provide:
        1. SYNTAX ELEMENT: The symbol or syntax (e.g., "#", ".", "@")
        2. SYMBOL NAME: Common name (e.g., "hash", "dot", "at symbol")
        3. ORIGIN: Historical/cultural origin
        4. LOGIC REASON: Why this symbol makes logical sense
        5. MEMORY HOOK: Mnemonic to remember it
        6. COMMON MISTAKES: Typical errors beginners make
        
        Focus on these syntax elements: {', '.join(context.get('syntax_elements', []))}
        
        Format as a valid JSON list. Example:
        [
          {{
            "syntax_element": "#",
            "symbol_name": "hash or pound",
            "origin": "From Latin 'libra pondo' meaning pound weight, evolved to 'lb' to '#'",
            "logic_reason": "In CSS, # indicates uniqueness like a unique ID number",
            "memory_hook": "Think #1 - only one element can be #1",
            "common_mistakes": ["Using # for classes", "Forgetting to quote in URLs"]
          }}
        ]
        
        Return ONLY the JSON, no other text.
        """
        
        print("🤖 Querying Gemini for syntax etymology...")
        response_text = self._call_gemini(syntax_prompt)
        
        syntax_explanations = []
        
        if response_text:
            try:
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                syntax_data_list = json.loads(clean_text)
                if isinstance(syntax_data_list, dict):
                    syntax_data_list = [syntax_data_list]
                
                for syntax_data in syntax_data_list:
                    explanation = SyntaxEtymology(
                        syntax_element=syntax_data["syntax_element"],
                        symbol_name=syntax_data["symbol_name"],
                        origin=syntax_data["origin"],
                        logic_reason=syntax_data["logic_reason"],
                        memory_hook=syntax_data["memory_hook"],
                        common_mistakes=syntax_data.get("common_mistakes", [])
                    )
                    syntax_explanations.append(explanation)
                    
                    print(f"\n📝 {explanation.syntax_element} ({explanation.symbol_name})")
                    print(f"   📜 Origin: {explanation.origin}")
                    print(f"   🧠 Logic: {explanation.logic_reason}")
                    print(f"   🎣 Memory Hook: {explanation.memory_hook}")
                    if explanation.common_mistakes:
                        print(f"   ⚠️ Common Mistakes: {', '.join(explanation.common_mistakes)}")
                
                print(f"\n✅ Successfully generated {len(syntax_explanations)} syntax explanations from Gemini!")
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse Gemini response as JSON: {e}")
                print(f"Raw response: {response_text[:200]}...")
                print("🔄 Falling back to mock data...")
                syntax_explanations = self._get_mock_syntax_etymology(self.topic)
        else:
            print("🔄 Using mock data due to API failure...")
            syntax_explanations = self._get_mock_syntax_etymology(self.topic)
        
        self.syntax_logic_complete = True
        return syntax_explanations
    
    def _check_user_understanding(self, terminology: List, syntax: List) -> Dict:
        """Step 3: Check if user understands the priming material"""
        print(f"\n🧠 UNDERSTANDING CHECK")
        print("-" * 50)
        
        if not terminology or not syntax:
            return {"status": "skipped_no_data"}

        # Create comprehension questions
        # In a real scenario, we might ask Gemini to generate these based on the actual content
        # For now, we use a template approach
        questions = [
            {
                "question": f"Can you explain what '{terminology[0].term}' means in your own words?",
                "type": "terminology",
                "expected_concepts": [terminology[0].term]
            },
            {
                "question": f"What's the difference between '{terminology[1].term}' and '{terminology[min(2, len(terminology)-1)].term}'?",
                "type": "comparison",
                "expected_concepts": [terminology[1].term, terminology[min(2, len(terminology)-1)].term]
            },
            {
                "question": f"Why does {syntax[0].syntax_element} represent {syntax[0].logic_reason[:30]}...?",
                "type": "syntax_logic",
                "expected_concepts": [syntax[0].syntax_element]
            }
        ]
        
        understanding_result = {
            "questions_asked": len(questions),
            "questions": questions,
            "user_responses_required": True,
            "assessment_pending": True,
            "next_action": "await_user_responses"
        }
        
        print("Answer these questions in your own words (simulated pause):")
        for i, q in enumerate(questions, 1):
            print(f"\n{i}. {q['question']}")
        
        print("\n💡 Tip: Try to use the mnemonics we just learned!")
        
        return understanding_result

    def _get_mock_terminology(self, topic: ModuleTopic) -> List[Dict]:
        """Mock terminology data for demonstration and fallback"""
        mock_data = {
            ModuleTopic.CSS_BASICS: [
                {
                    "term": "Selector",
                    "definition": "Pattern that matches elements to apply styles to",
                    "abbreviation": None,
                    "acronym": False,
                    "related_terms": ["element", "class", "ID"],
                    "mnemonic": "Like a 'bouncer' selecting which elements get in"
                },
                {
                    "term": "Property",
                    "definition": "Aspect of an element you want to change (color, size, etc.)",
                    "abbreviation": None,
                    "acronym": False,
                    "related_terms": ["value", "declaration"],
                    "mnemonic": "Properties are like adjectives describing elements"
                },
                {
                    "term": "Value",
                    "definition": "Specific setting for a property (red, 20px, etc.)",
                    "abbreviation": None,
                    "acronym": False,
                    "related_terms": ["property", "unit"],
                    "mnemonic": "Value is the 'what' to the property's 'which'"
                }
            ],
            ModuleTopic.NEUMORPHISM: [
                {
                    "term": "Neumorphism",
                    "definition": "UI design style that mimics physical objects with soft shadows",
                    "abbreviation": "Neumo",
                    "acronym": False,
                    "related_terms": ["skeuomorphism", "flat design", "shadow"],
                    "mnemonic": "NEW + skeuMORPHISM = Neumorphism"
                },
                {
                    "term": "Inset Shadow",
                    "definition": "Shadow that appears inside the element (depressed effect)",
                    "abbreviation": None,
                    "acronym": False,
                    "related_terms": ["box-shadow", "embossed", "light source"],
                    "mnemonic": "INset goes INside, like pressing a button IN"
                }
            ]
        }
        
        # Convert dictionary mocks to TerminologyEntry objects
        raw_list = mock_data.get(topic, [])
        return [
            TerminologyEntry(
                term=d["term"],
                definition=d["definition"],
                abbreviation=d.get("abbreviation"),
                acronym=d.get("acronym", False),
                related_terms=d.get("related_terms", []),
                mnemonic=d.get("mnemonic")
            )
            for d in raw_list
        ]

    def _get_mock_syntax_etymology(self, topic: ModuleTopic) -> List[Dict]:
        """Mock syntax etymology data for demonstration and fallback"""
        mock_data = {
            ModuleTopic.CSS_BASICS: [
                {
                    "syntax_element": ".",
                    "symbol_name": "dot or period",
                    "origin": "From Greek 'stigmē' meaning point, used to mark divisions",
                    "logic_reason": "Represents a 'class' which groups multiple elements, like items in a list separated by dots",
                    "memory_hook": "Dots connect things - classes connect elements",
                    "common_mistakes": ["Using . for IDs", "Forgetting the dot"]
                },
                {
                    "syntax_element": "#",
                    "symbol_name": "hash or pound",
                    "origin": "From Latin 'libra pondo' (pound weight), abbreviated to 'lb' then stylized as #",
                    "logic_reason": "Indicates uniqueness, like a unique number or ID",
                    "memory_hook": "#1 athlete - only one can be number 1",
                    "common_mistakes": ["Using multiple # for one element", "Confusing with URL fragments"]
                }
            ],
            ModuleTopic.NEUMORPHISM: [
                {
                    "syntax_element": "inset",
                    "symbol_name": "inset keyword",
                    "origin": "From Old English 'insettan' meaning to set in, place in",
                    "logic_reason": "Changes shadow from external to internal, making element appear pressed in",
                    "memory_hook": "INset goes INto the element",
                    "common_mistakes": ["Misspelling as 'insit'", "Forgetting comma after inset"]
                }
            ]
        }
        
        # Convert dictionary mocks to SyntaxEtymology objects
        raw_list = mock_data.get(topic, [])
        return [
             SyntaxEtymology(
                syntax_element=d["syntax_element"],
                symbol_name=d["symbol_name"],
                origin=d["origin"],
                logic_reason=d["logic_reason"],
                memory_hook=d["memory_hook"],
                common_mistakes=d.get("common_mistakes", [])
            )
            for d in raw_list
        ]
    
    def get_priming_summary(self) -> Dict:
        """Get a summary of the priming phase results"""
        return {
            "phase": "priming",
            "topic": self.topic.value,
            "status": {
                "terminology_scan": self.terminology_scan_complete,
                "syntax_logic": self.syntax_logic_complete,
                "ready_for_next_phase": self.terminology_scan_complete and self.syntax_logic_complete
            },
            "statistics": {
                "terms_defined": len(self.priming_log.get("terminology", [])),
                "syntax_explained": len(self.priming_log.get("syntax_etymology", [])),
                "timestamp": self.priming_log["timestamp"]
            },
            "next_phase": "relational_thinking"
        }
