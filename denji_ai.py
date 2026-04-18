"""
Denji AI Brain - Integrated OpenCode Agent
Powered by open-source AI technology with credits to:
  • OpenCode (Anomaly Co) - Foundation for AI agent architecture
  • Contributors: @thdxr, @adamdotdevin, @rekram1-node, and 860+ contributors
  • Extended for Denji Terminal Standby System
"""

import os
import json
import threading
import time
import subprocess
from typing import Any, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def _check_opencode_available() -> bool:
    """Check if OpenCode CLI is installed and available"""
    try:
        result = subprocess.run(
            ["opencode", "--version"],
            capture_output=True,
            timeout=2,
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
            ["opencode", "--help"],
            capture_output=True,
            timeout=3,
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
    Integrates with Denji's personality system and understands the codebase.
    """
    
    def __init__(self):
        """Initialize the AI brain with system knowledge"""
        self.conversation_history = []
        self.max_history = 20
        self.system_prompt = self._build_system_prompt()
        self.thinking = False
        self.response_queue = []
        self._lock = threading.Lock()
        self.last_response = ""
        self.response_time = 0.0
        self._opencode_help = _read_opencode_help()
        self.last_backend = "RULE"

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
        ollama = "UP" if self._ollama_available() else "DOWN"
        opencode = "ON" if HAS_OPENCODE else "OFF"
        return f"AI {self.last_backend} | OLLAMA {ollama} | OPENCODE {opencode}"
        
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
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        with self._lock:
            self.conversation_history.append({"role": role, "content": content})
            # Keep history manageable
            if len(self.conversation_history) > self.max_history:
                self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_response(self, user_input: str, personality_mood: str = "idle", humor_level: float = 50.0) -> str:
        """
        Get AI response to user input.
        For now, returns a mock response (local processing).
        Later, can integrate with actual LLM API.
        """
        self.thinking = True
        self.add_message("user", user_input)
        
        # Build context with current mood
        mood_context = f"\n[Current Denji mood: {personality_mood} | Humor level: {humor_level}%]"
        
        # Try to use an open API if available (Ollama local, or Hugging Face)
        response = self._generate_response_local(user_input, personality_mood, humor_level)
        
        if not response:
            # Fallback: Simple rule-based responses
            self.last_backend = "RULE"
            response = self._fallback_response(user_input, personality_mood, humor_level)
        
        self.thinking = False
        self.add_message("assistant", response)
        self.last_response = response
        self.response_time = time.time()
        
        return response
    
    def _generate_response_local(self, user_input: str, mood: str, humor: float) -> Optional[str]:
        """Try to use local/open LLM (Ollama first, then OpenCode CLI)"""
        
        # Try Ollama local inference first
        if HAS_REQUESTS:
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "neural-chat",  # Fast local model
                        "prompt": f"{self.system_prompt}\n\nUser: {user_input}\n\nDenji (mood={mood}, humor={humor}%):",
                        "stream": False,
                        "temperature": 0.7
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    result = response.json()
                    resp_text = result.get("response", "").strip()
                    if resp_text:
                        self.last_backend = "OLLAMA"
                        return resp_text
            except Exception:
                pass
        
        # Fallback: Try OpenCode CLI agent
        if HAS_OPENCODE:
            return self._generate_with_opencode(user_input, mood, humor)
        
        # Final fallback: return None to trigger rule-based response
        return None
    
    def _generate_with_opencode(self, user_input: str, mood: str, humor: float) -> Optional[str]:
        """Call OpenCode CLI as AI agent fallback"""
        try:
            # Build the prompt with system context
            full_prompt = f"""{self.system_prompt}

Current Context:
- User Input: {user_input}
- Denji Mood: {mood}
- Humor Level: {humor}%

Respond as Denji's Neural Core in a single, concise line. Keep it professional yet personality-driven."""
            
            help_text = (self._opencode_help or "").lower()
            attempts = []

            # Probe common non-interactive command shapes.
            if "--prompt" in help_text:
                attempts.append(["opencode", "--prompt", full_prompt])
            if "-p" in help_text or "--prompt" in help_text:
                attempts.append(["opencode", "-p", full_prompt])
            if " run" in help_text or "\nrun" in help_text:
                attempts.append(["opencode", "run", full_prompt])
                attempts.append(["opencode", "run", "--prompt", full_prompt])
            if "chat" in help_text:
                attempts.append(["opencode", "chat", full_prompt])

            # Fallback generic attempts if help probing is inconclusive.
            attempts.extend([
                ["opencode", "run", full_prompt],
                ["opencode", "--prompt", full_prompt],
                ["opencode", "-p", full_prompt],
            ])

            for cmd in attempts:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=15,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                except Exception:
                    continue

                output = (result.stdout or "").strip()
                if result.returncode == 0 and output:
                    response = output
                    if response.startswith("```"):
                        response = response.split("```", 1)[-1].strip()
                    if response.endswith("```"):
                        response = response.rsplit("```", 1)[0].strip()
                    self.last_backend = "OPENCODE"
                    return response[:240]
            
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError, UnicodeError):
            return None
        except Exception:
            return None
    
    def _fallback_response(self, user_input: str, mood: str, humor: float) -> str:
        """Rule-based fallback responses with Denji personality"""
        user_lower = user_input.lower()
        
        # Knowledge about the codebase
        if any(x in user_lower for x in ["how", "explain", "tell me", "what is"]):
            if "voice" in user_lower:
                return "Voice system uses multi-fallback chain: sounddevice → SpeechRecognition → SAPI/PowerShell. Currently Ready for input via 'v' key."
            elif "camera" in user_lower:
                return "Camera integrates OpenCV with Windows DirectShow backend. Uses face detection to track attention. Press 'c' to toggle."
            elif "todo" in user_lower:
                return "Todo system stores persistent tasks. Press 'o' to create new tasks, manage them from the right panel."
            elif "mood" in user_lower or "emotion" in user_lower:
                return f"Currently in {mood} state. Mood system responds to your interactions. Adjust humor with +/- keys."
            elif "dashboard" in user_lower or "tars" in user_lower:
                return "Dashboard shows 3 panels: Ship Telemetry (CPU/RAM/Humor), Neural Core (mood/attention), Todo List. Real-time HUD interface."
            elif "denji" in user_lower or "system" in user_lower:
                return "Denji is a synthetic command interface - terminal-based AI assistant with personality. Full codebase is Python + curses."
            elif "command" in user_lower or "help" in user_lower:
                return "Commands: t=type, v=voice, o=todo, c=camera, space=music, +/- humor, left/right=views, q=quit. Try 'o' to add todos."
        
        # User interaction patterns
        if any(x in user_lower for x in ["hello", "hi", "hey", "greetings"]):
            greetings = [
                "Neural Core online. Ready for your commands.",
                "Denji systems active. What can I process for you?",
                "Synthetic interface engaged. Standing by.",
                "Hello there. TARS unit initialized." if humor > 70 else "Greetings. Processing awaits."
            ]
            return greetings[hash(user_input) % len(greetings)]
        
        if any(x in user_lower for x in ["thanks", "thank you", "appreciate"]):
            return "Happy to assist. Keep coding, keep focused." if humor > 50 else "Acknowledged. Continuing operations."
        
        if any(x in user_lower for x in ["status", "check", "how are you"]):
            statuses = [
                "All systems nominal. Ready for input.",
                "Neural pathways clear. Standing by.",
                "Humor calibration optimal at {}%".format(int(humor))
            ]
            return statuses[hash(user_input) % len(statuses)]
        
        if any(x in user_lower for x in ["joke", "funny", "laugh"]):
            jokes = [
                "Why did the AI go to school? To improve its neural network!",
                "I'm not as funny as Claude, but I'm cheaper to run.",
                "Why do coders prefer dark mode? Light attracts bugs...and me.",
                "Have you tried turning it off and on again? Works 60% of the time, every time."
            ]
            return jokes[hash(user_input) % len(jokes)]
        
        if any(x in user_lower for x in ["code", "debug", "fix", "error"]):
            return "Analyzing your code context. Detail the issue and I'll help debug. What's the error state?"
        
        # Generic fallback
        fallbacks = [
            "Processing your input. Can you elaborate?",
            "Interesting. Tell me more about what you need.",
            "Neural analysis complete. How can I assist?",
            "Input registered. What's your next command?"
        ]
        return fallbacks[hash(user_input) % len(fallbacks)]
    
    def get_conversation_display(self, max_lines: int = 10) -> list[str]:
        """Get formatted conversation for display on dashboard"""
        with self._lock:
            lines = []
            # Show last N messages
            display_history = self.conversation_history[-max_lines:]
            for msg in display_history:
                role = msg["role"]
                content = msg["content"]
                prefix = "YOU > " if role == "user" else "DENJI > "
                
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
