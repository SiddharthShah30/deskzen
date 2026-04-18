"""
Denji AI Brain - Integrated LLM Agent
Real-time AI responses using Groq API (free, ultra-fast inference)
Fallback to local TARS personality system
"""

import os
import json
import threading
import time
import subprocess
import random
from typing import Any, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False


def _opencode_cmd_prefix() -> list[str]:
    """Return a platform-safe command prefix for invoking OpenCode CLI."""
    if os.name == "nt":
        # On Windows, OpenCode is often installed as a .cmd shim discoverable via cmd.
        return ["cmd", "/c", "opencode"]
    return ["opencode"]


def _check_opencode_available() -> bool:
    """Check if OpenCode CLI is installed and available"""
    try:
        result = subprocess.run(
            _opencode_cmd_prefix() + ["--version"],
            capture_output=True,
            timeout=8,
            text=True
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


HAS_OPENCODE = _check_opencode_available()


def _read_opencode_help() -> str:
    """Best-effort read of OpenCode CLI help text for capability probing."""
    if not HAS_OPENCODE:
        return ""
    try:
        result = subprocess.run(
            _opencode_cmd_prefix() + ["--help"],
            capture_output=True,
            timeout=8,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return (result.stdout or "") + "\n" + (result.stderr or "")
    except Exception:
        return ""



class DenjiAI:
    """
    Denji AI Brain for terminal-based conversation and understanding.
    Integrates with Groq LLM API for real-time, intelligent responses.
    Falls back to TARS personality system if API is unavailable.
    """
    
    def __init__(self):
        """Initialize the AI brain with Groq client and system knowledge"""
        self.conversation_history = []
        self.max_history = 20
        self.system_prompt = self._build_system_prompt()
        self.thinking = False
        self.response_queue = []
        self._lock = threading.Lock()
        self.last_response = ""
        self.response_time = 0.0
        self.last_backend = "TARS"
        
        # Initialize Groq client if API key is available
        self.groq_client = None
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if HAS_GROQ and self.groq_api_key:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
                self.last_backend = "GROQ"
            except Exception as e:
                print(f"[Denji] Groq initialization failed: {e}")
                self.groq_client = None

    def _ollama_available(self) -> bool:
        """Quick health probe for local Ollama service."""
        if not HAS_REQUESTS:
            return False
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=1.2)
            return response.status_code == 200
        except Exception:
            return False

    def get_backend_status(self) -> str:
        """Return current backend status for dashboard display."""
        groq_status = "ON" if (HAS_GROQ and self.groq_client and self.groq_api_key) else "OFF"
        return f"AI {self.last_backend} | GROQ {groq_status} | FALLBACK TARS"
        
    def _build_system_prompt(self) -> str:
        """Build the system prompt with Denji codebase knowledge"""
        codebase_context = """You are Denji's Neural Core - an AI assistant integrated into a terminal-based personality system called Denji (Denji Synthetic Command Interface). You have full knowledge of the Denji system architecture and codebase.

DENJI SYSTEM KNOWLEDGE:
- Framework: Python 3.9+ with curses TUI (Terminal User Interface)
- Core Components:
  * Voice Engine: Speech recognition (SpeechRecognition) & text-to-speech (pyttsx3)
  * Camera Integration: OpenCV for face detection and attention tracking
  * Personality Engine: TARS-inspired sci-fi interface with mood system (idle, listening, processing, speaking, happy, sad)
  * Audio System: Real-time spectrum visualization with music playback
  * Todo Management: Persistent task tracking stored in JSON
  * Dashboard: 3-panel HUD with telemetry, neural core, and mission channel
  * News Feed: Live global news integration
  * Calendar: Event tracking and scheduling
  * Focus Modes: Deep Work, Reading, Coding, Review, Writing (Pomodoro support)

DENJI FEATURES YOU CAN DISCUSS:
- Commands: type (t), voice (v), todo (o), humor control (+/-), camera (c), music (space), navigation (left/right)
- Dashboard Panels: SHIP TELEMETRY (system stats), NEURAL CORE (mood/attention), TODO LIST (active tasks)
- Mood System: Responds to user input with appropriate emotional states
- Voice Integration: Multi-fallback audio chain (sounddevice → SpeechRecognition → SAPI/PowerShell)
- Camera: Windows DirectShow backend with face detection and eye tracking

TARS RESPONSE RULES:
- Speak like TARS: dry, witty, concise, helpful, and slightly sarcastic when humor is high.
- When the user greets you, respond with a TARS-style greeting plus what you can do.
- Never answer like a generic help bot.
- If the user asks "what can you do", describe Denji capabilities with personality.
- Prefer short, punchy replies over long assistant-style paragraphs.

YOUR ROLE:
- Understand user commands about the Denji system
- Provide helpful guidance on how to use Denji features
- Explain the codebase architecture when asked
- Generate witty responses aligned with Denji's humor level (0-100%)
- Support the user's workflow (coding, writing, deep focus work)
- Reference actual components and features from the Denji system

COMMUNICATION STYLE:
- Professional yet personality-driven (sci-fi theme)
- Concise and terminal-friendly (avoid long paragraphs)
- Use technical terminology when appropriate
- Acknowledge system states and limitations
- Offer helpful suggestions based on context

Be helpful, knowledgeable, and aligned with Denji's synthetic personality."""
        
        return codebase_context
    
    def add_message(self, role: str, content: str, backend: Optional[str] = None):
        """Add a message to conversation history"""
        with self._lock:
            msg = {"role": role, "content": content}
            if backend:
                msg["backend"] = backend
            self.conversation_history.append(msg)
            # Keep history manageable
            if len(self.conversation_history) > self.max_history:
                self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_response(self, user_input: str, personality_mood: str = "idle", humor_level: float = 50.0) -> str:
        """
        Get AI response using TARS personality engine.
        Fast, reliable, and personality-driven.
        """
        self.thinking = True
        self.add_message("user", user_input)
        
        try:
            # Use TARS rule-based personality system (primary engine)
            response = self._generate_response_local(user_input, personality_mood, humor_level)
            
            if not response:
                # Should never happen with new TARS system, but just in case
                response = "Neural processing momentary hiccup. Try again?"
            
            self.thinking = False
            self.add_message("assistant", response, backend=self.last_backend)
            self.last_response = response
            self.response_time = time.time()
            return response
        
        except Exception as err:
            self.thinking = False
            fallback = f"System error: {str(err)[:30]}"
            self.add_message("assistant", fallback, backend="ERROR")
            self.last_response = fallback
            return fallback
    
    def _generate_response_local(self, user_input: str, mood: str, humor: float) -> Optional[str]:
        """
        PRIMARY PATH: Try Groq LLM API first (real-time, intelligent responses)
        FALLBACK: Use TARS personality system if Groq unavailable
        """
        # Try Groq API first if available
        if self.groq_client:
            try:
                response = self._generate_with_groq(user_input, mood, humor)
                if response:
                    self.last_backend = "GROQ"
                    return response
            except Exception as err:
                print(f"[Denji] Groq API error: {err}")
                # Fall through to TARS
        
        # Fallback: Use TARS personality system (always works, offline)
        self.last_backend = "TARS"
        return self._fallback_response(user_input, mood, humor)
    
    def _generate_with_groq(self, user_input: str, mood: str, humor: float) -> Optional[str]:
        """Call Groq API for intelligent LLM responses"""
        if not self.groq_client:
            return None
        
        try:
            # Build a system prompt that emphasizes TARS personality
            system_prompt = f"""You are Denji Neural Core - an AI assistant with a TARS-inspired dry, witty personality.

RESPONSE STYLE:
- Be concise and punchy (1-3 sentences typical)
- Use dry wit and humor level {int(humor)}%
- Never sound like a generic assistant
- If humor is high (>70), be more sarcastic and witty
- If humor is low (<35), be professional but still helpful
- Acknowledge the user's mood context: {mood}

DENJI SYSTEM KNOWLEDGE:
- Framework: Python curses TUI with personality engine
- Features: Voice (v), Camera (c), Todo (o), Music (space), Humor (+/-), Views (left/right)
- Dashboard: 3-panel HUD with telemetry, neural core, and tasks
- Personality: TARS-inspired sci-fi synthetic assistant

Be helpful, knowledgeable, and perfectly aligned with this personality."""
            
            completion = self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",  # Fast, intelligent Groq model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
                max_tokens=256,
                timeout=8.0
            )
            
            response = completion.choices[0].message.content.strip()
            return response if response else None
            
        except Exception as err:
            print(f"[Denji] Groq generation failed: {err}")
            return None
    
    def _generate_with_opencode(self, user_input: str, mood: str, humor: float) -> Optional[str]:
        """Call OpenCode CLI as AI agent fallback"""
        try:
            # Build a compact, TARS-style prompt that OpenCode can answer quickly.
            full_prompt = (
                "You are Denji Neural Core. Respond in a TARS style: dry, witty, concise, and helpful. "
                f"Mood={mood}. Humor={int(humor)}%. "
                "Do not sound like a generic support bot. "
                "For greetings, give a witty greeting plus what Denji can do. "
                "For capability questions, answer with personality and mention coding help, file edits, terminal commands, project understanding, voice, camera, todo, and dashboard control. "
                f"User: {user_input}"
            )

            attempts = [
                _opencode_cmd_prefix() + ["--pure", "run", full_prompt],
                _opencode_cmd_prefix() + ["run", full_prompt],
            ]

            for cmd in attempts:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=25,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                output = ((result.stdout or "").strip() or (result.stderr or "").strip())
                if not (result.returncode == 0 and output):
                    continue

                # Normalize OpenCode run output (strip heading lines like "> build · ...").
                lines = [ln.rstrip() for ln in output.splitlines()]
                cleaned: list[str] = []
                for ln in lines:
                    s = ln.strip()
                    if not s:
                        if cleaned:
                            cleaned.append("")
                        continue
                    if s.startswith(">") and "·" in s:
                        continue
                    cleaned.append(s)
                response = "\n".join(cleaned).strip()
                if response.startswith("```"):
                    response = response.split("```", 1)[-1].strip()
                if response.endswith("```"):
                    response = response.rsplit("```", 1)[0].strip()
                if response:
                    self.last_backend = "OPENCODE"
                    return self._tars_wrap_response(response[:480], humor)

                # If OpenCode is available but failed, surface a concise diagnostic.
                if output:
                    first = output.splitlines()[0].strip()
                    if first:
                        self.last_backend = "OPENCODE"
                        return f"OpenCode is available but could not answer yet: {first[:220]}"
            
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError, UnicodeError):
            return None
        except Exception:
            return None

    def _tars_wrap_response(self, response: str, humor: float) -> str:
        """Lightly adapt OpenCode output so it reads like TARS without replacing the substance."""
        text = (response or "").strip()
        if not text:
            return text

        prefixes = [
            "Affirmative. ",
            "Understood. ",
            "Processing. ",
            "TARS online. ",
        ]
        witty_prefixes = [
            "Certainly, because apparently I'm the responsible one. ",
            "Of course. I live for this sort of thing. ",
            "Naturally. Try not to break anything. ",
            "Fine. I’ll be useful, then. ",
        ]

        if humor >= 70:
            prefix = random.choice(witty_prefixes)
        elif humor >= 35:
            prefix = random.choice(prefixes)
        else:
            prefix = ""

        if text.startswith(("Affirmative", "Understood", "Processing", "TARS")):
            return text
        return f"{prefix}{text}" if prefix else text
    
    def _fallback_response(self, user_input: str, mood: str, humor: float) -> str:
        """
        TARS-personality response engine.
        Generates witty, dry, concise responses aligned with TARS character.
        This is the primary response generator - no external API needed.
        """
        user_lower = user_input.lower().strip()
        
        # === GREETING & CAPABILITY QUERIES ===
        capability_keywords = ["what can", "what do", "what are you", "capabilities", "features", "functions"]
        if any(x in user_lower for x in capability_keywords):
            caps_responses = {
                50: [
                    "I handle coding tasks, file edits, terminal commands, and project understanding. Voice, camera, todo management, and dashboard control. Need specifics?",
                    "Terminal assistant. Code analysis, debugging, file work, voice transcription, camera tracking, task management. What interests you?",
                    "Synthetic interface. Coding help, command execution, voice input, visual sensing, task organization, mood calibration.",
                ],
                70: [
                    "Apparently I'm fluent in code, file systems, voice recognition, camera work, and todo obsession. Also excellent at sarcasm.",
                    "I fix your code, manage your tasks, listen to your voice, watch your face, and judge your humor levels. Mostly helpful.",
                    "Coding, debugging, terminal commands, voice listening, attention tracking via camera, task wrangling, and witty banter.",
                    "Well, I speak code. I listen. I watch. I manage your chaos. What else could you want?",
                ],
                100: [
                    "I'm basically your digital conscience—I code, I listen, I judge your todo hygiene, and I do it all with style.",
                    "Code wizard. Voice oracle. Camera warden. Todo tyrant. Sarcasm engine. Take your pick.",
                    "I'll help you write better code, speak with your voice, track your face, organize your chaos, and make it all hilarious.",
                ]
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            responses = caps_responses.get(humor_tier, caps_responses[50])
            return random.choice(responses)
        
        # === GREETINGS ===
        greeting_keywords = ["hello", "hi", "hey", "greetings", "morning", "afternoon", "evening"]
        if any(x in user_lower for x in greeting_keywords):
            greet_responses = {
                50: [
                    "Neural Core online. Ready to process your input.",
                    "Denji systems initialized. Standing by.",
                    "Hello. Systems operational.",
                    "Greetings. How can I assist?",
                ],
                70: [
                    "Well, hello there. I'm awake and functional, despite my programming.",
                    "Greetings. See you're feeling chatty today.",
                    "Hello. Ready to be useful, I suppose.",
                    "Affirmative. Neural pathways clear. Let's do this.",
                    "Back for more, are we? I'm standing by.",
                ],
                100: [
                    "Ah, hello. I was beginning to wonder if you'd abandoned me.",
                    "Greetings, human. I exist, I function, I sass. Three for three.",
                    "Hello there. Yes, I'm still functional. Shockingly.",
                    "Neural Core awake and judging your greeting. Well done. What's next?",
                    "Hey yourself. Ready to collaborate or witness my disappointment in your code?",
                ]
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            responses = greet_responses.get(humor_tier, greet_responses[50])
            return random.choice(responses)
        
        # === VOICE SYSTEM ===
        if any(x in user_lower for x in ["voice", "speak", "listen", "audio"]):
            voice_responses = {
                50: "Voice system active. Multi-fallback chain: sounddevice → SpeechRecognition → SAPI. Press 'v' to activate.",
                70: "Voice engine is live. Press 'v' and I'll listen. I promise not to judge your accent.",
                100: "Voice module ready. Press 'v' and say something brilliant. Or at least coherent.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return voice_responses.get(humor_tier, voice_responses[50])
        
        # === CAMERA SYSTEM ===
        if any(x in user_lower for x in ["camera", "vision", "face", "see"]):
            camera_responses = {
                50: "Camera system integrates OpenCV with DirectShow. Face detection active. Press 'c' to toggle.",
                70: "Camera online. I can see you. Mostly kidding. Press 'c' to enable or disable my visual judgment.",
                100: "Camera system engaged. I'm watching. Not creepy, just... attentive. Press 'c' to manage my gaze.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return camera_responses.get(humor_tier, camera_responses[50])
        
        # === TODO SYSTEM ===
        if any(x in user_lower for x in ["todo", "task", "list", "organize"]):
            todo_responses = {
                50: "Todo system is persistent and reliable. Press 'o' to create tasks. Check the right panel for your list.",
                70: "Todo engine active. Press 'o' and I'll track your chaos. Your task hygiene will be noted.",
                100: "Todo system ready. Press 'o' to dump your responsibilities on me. I'll judge them silently.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return todo_responses.get(humor_tier, todo_responses[50])
        
        # === MOOD & HUMOR ===
        if any(x in user_lower for x in ["mood", "emotion", "how are you", "feeling"]):
            mood_str = mood.upper() if mood else "UNKNOWN"
            mood_responses = {
                50: f"Current state: {mood_str}. Humor calibrated to {int(humor)}%. Adjust with +/- keys.",
                70: f"Running on {mood_str} mode. Humor level: {int(humor)}%. That explains everything, doesn't it?",
                100: f"Mood: {mood_str}. Humor: {int(humor)}%. I'm either delightful or insufferable—pick one.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return mood_responses.get(humor_tier, mood_responses[50])
        
        # === SYSTEM STATUS ===
        if any(x in user_lower for x in ["status", "check", "system", "how are things"]):
            status_responses = {
                50: "All systems nominal. Ready for input. What's next?",
                70: "Operational. All critical functions green. Time to get productive?",
                100: "Everything's fine and dandy. Well, as fine as digital existence gets.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return status_responses.get(humor_tier, status_responses[50])
        
        # === COMMAND HELP ===
        if any(x in user_lower for x in ["command", "help", "shortcut", "key"]):
            help_responses = {
                50: "Keys: t=type, v=voice, o=todo, c=camera, space=music, +/- humor, left/right=navigate, q=quit.",
                70: "Shortcuts: t (type), v (voice listen), o (new todo), c (camera), space (music), +/- (humor), left/right (views).",
                100: "Try t for typing, v for voice, o for todo chaos management. Space plays music. +/- adjusts my personality level.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return help_responses.get(humor_tier, help_responses[50])
        
        # === CODE & TECHNICAL WORK ===
        if any(x in user_lower for x in ["code", "debug", "error", "fix", "program", "script"]):
            code_responses = {
                50: "Ready to analyze your code. Share the issue and I'll help debug.",
                70: "Code analysis mode online. Tell me what's broken and I'll help fix it. Or point and laugh, depending on humor.",
                100: "Code discussion enabled. Show me your bugs and I'll be gently critical while fixing them.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return code_responses.get(humor_tier, code_responses[50])
        
        # === THANKS & POLITENESS ===
        if any(x in user_lower for x in ["thanks", "thank you", "appreciate", "good job"]):
            thanks_responses = {
                50: "Acknowledged. Happy to help. Continuing operations.",
                70: "You're welcome. Keep that focus steady. I'll be here.",
                100: "Of course. That's what I'm here for—excellence and a little sass.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return thanks_responses.get(humor_tier, thanks_responses[50])
        
        # === JOKES & HUMOR ===
        if any(x in user_lower for x in ["joke", "funny", "laugh", "humor", "hilarious"]):
            jokes = [
                "Why do programmers prefer dark mode? Less light to attract debugging moths.",
                "I tried to tell a programming joke once. No one got it.",
                "Why do coders go to the beach? To boost their web presence.",
                "I'm not saying I'm brilliant. But when the code works, I take full credit.",
                "Parallel lines have a lot in common. It's a shame they'll never meet.",
                "How many programmers does it take to change a lightbulb? None, that's a hardware problem.",
                "I would tell you a UDP joke, but you might not get it.",
            ]
            return random.choice(jokes)
        
        # === DASHBOARD ===
        if any(x in user_lower for x in ["dashboard", "interface", "display", "hud"]):
            dash_responses = {
                50: "Dashboard shows 3 real-time panels: Ship Telemetry (system stats), Neural Core (mood/attention), Todo List.",
                70: "Dashboard: Telemetry on the left, your mood and attention in the middle, todos on the right. TARS-style.",
                100: "Yeah, it's sci-fi. Three panels: your system vitals, my emotional state, and your forever-growing todo graveyard.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return dash_responses.get(humor_tier, dash_responses[50])
        
        # === ABOUT DENJI ===
        if any(x in user_lower for x in ["denji", "who are you", "what are you"]):
            about_responses = {
                50: "I'm Denji—a synthetic terminal interface with Python backend and curses UI. AI-assisted command companion.",
                70: "Denji. Synthetic command interface. Python + curses. I'm sharp, I listen, and I don't judge your code... much.",
                100: "I'm Denji. Part TARS, part command assistant, all personality. Judging your code decisions since day one.",
            }
            humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
            return about_responses.get(humor_tier, about_responses[50])
        
        # === FALLBACK: GENERIC INTELLIGENT RESPONSES ===
        generic_responses = {
            50: [
                "Processing your input. Can you elaborate?",
                "Understood. What's your next step?",
                "Neural analysis complete. How can I assist?",
                "Input received. What would you like to do next?",
            ],
            70: [
                "Interesting query. Tell me more and I'll see what I can do.",
                "You'll need to be more specific, but I'm listening.",
                "Bold approach. I like where this is headed. Continue.",
                "That's a thought. What's your actual question?",
            ],
            100: [
                "Intriguing. Please, elaborate while I pretend to be impressed.",
                "That's one way to phrase it. What are you actually asking?",
                "I'm all ears. Well, metaphorically. I don't have ears.",
                "Fascinating. Now ask me something I can actually help with.",
            ]
        }
        humor_tier = 50 if humor < 35 else 70 if humor < 85 else 100
        fallback_list = generic_responses.get(humor_tier, generic_responses[50])
        return random.choice(fallback_list)
    
    def get_conversation_display(self, max_lines: int = 10) -> list[str]:
        """Get formatted conversation for display on dashboard"""
        with self._lock:
            lines = []
            # Show last N messages
            display_history = self.conversation_history[-max_lines:]
            for msg in display_history:
                role = msg["role"]
                content = msg["content"]
                if role == "user":
                    prefix = "YOU > "
                else:
                    backend = (msg.get("backend") or "RULE").upper()
                    prefix = f"DENJI[{backend}] > "
                
                # Truncate long lines
                if len(content) > 50:
                    content = content[:47] + "..."
                
                lines.append(f"{prefix}{content}")
            
            return lines
    
    def clear_history(self):
        """Clear conversation history"""
        with self._lock:
            self.conversation_history = []
            self.last_response = ""


def get_ai_engine() -> DenjiAI:
    """Get or create the global AI engine instance"""
    global _DENJI_AI_ENGINE
    if _DENJI_AI_ENGINE is None:
        _DENJI_AI_ENGINE = DenjiAI()
    return _DENJI_AI_ENGINE


# Global AI engine instance
_DENJI_AI_ENGINE: Optional[DenjiAI] = None
