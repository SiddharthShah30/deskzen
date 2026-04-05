"""
TARS Personality & Humor Engine
Generates witty responses based on humor level (0-100%)
Inspired by TARS from Interstellar
"""

import random
import json

class PersonalityEngine:
    """TARS-inspired personality with adjustable humor level"""
    
    def __init__(self, humor_level: float = 50.0):
        """
        humor_level: 0-100 (0=deadpan/factual, 50=balanced, 100=maximum sarcasm)
        """
        self.humor_level = max(0, min(100, humor_level))
        self.conversation_history = []
        self.last_command = ""
        
    def set_humor(self, level: float):
        """Update humor level dynamically"""
        self.humor_level = max(0, min(100, level))
    
    # ─── CORE RESPONSE GENERATION ───────────────────────────────────────
    
    def generate_acknowledgment(self, command: str) -> str:
        """Generate witty acknowledgment for user command"""
        deadpan = [
            "Affirmative.",
            "Processing.",
            "Understood.",
            "Command accepted.",
            "Initiating sequence.",
        ]
        
        balanced = [
            "Got it. Running that now.",
            "Sure, I can do that.",
            "Alright, let me handle this.",
            "One moment while I work on that.",
            "Consider it done.",
        ]
        
        witty = [
            "Oh, so NOW you want my help. Noted.",
            "Let me flex my digital muscles.",
            "Fascinating choice. Proceeding nonetheless.",
            "Because apparently I'm your personal Swiss Army knife.",
            "Sure, let's add that to my ever-growing to-do list.",
            "Executing command. Try not to break anything while I work.",
            "As you wish. I do love a good challenge.",
        ]
        
        if self.humor_level < 25:
            return random.choice(deadpan)
        elif self.humor_level < 75:
            return random.choice(balanced)
        else:
            return random.choice(witty)
    
    def generate_status_report(self, data: dict) -> str:
        """Generate humorous status report based on system data"""
        humor = self.humor_level
        
        # Extract common metrics
        cpu = data.get("cpu", 0)
        memory = data.get("memory", 0)
        network = data.get("network_status", "")
        timestamp = data.get("timestamp", "")
        
        # Deadpan reports
        if humor < 25:
            if cpu > 80:
                return f"CPU utilization at {cpu}%. Core temperatures rising. Recommend workload reduction."
            elif memory > 85:
                return f"Memory usage: {memory}%. System efficiency degrading. Consider hibernation."
            else:
                return f"Systems nominal. All parameters within acceptable ranges."
        
        # Balanced reports
        elif humor < 75:
            if cpu > 80:
                return f"Your CPU's running hot ({cpu}%). Maybe give it a break?"
            elif memory > 85:
                return f"Memory usage is at {memory}%. You might want to close some tabs."
            else:
                return f"Everything's running smoothly. For now."
        
        # Witty/Sarcastic reports
        else:
            if cpu > 80:
                return f"CPU at {cpu}%. That's... ambitious. Most humans run their systems slower."
            elif memory > 85:
                return f"Memory at {memory}%. Congratulations, you've successfully made me feel your pain."
            elif cpu > 60:
                return f"CPU burning at {cpu}%. I'm starting to take this personally."
            else:
                return f"Systems running great. Shocked, but grateful."
    
    def generate_news_commentary(self, headline: str, category: str = "") -> str:
        """Generate commentary on news items"""
        if self.humor_level < 25:
            return f"Article: {headline[:60]}..."
        elif self.humor_level < 75:
            reactions = {
                "business": "Interesting market movement.",
                "tech": "The tech world never stops evolving.",
                "science": "Scientific progress continues as expected.",
                "world": "Global events unfold.",
                "": "News received."
            }
            return reactions.get(category.lower(), "Interesting development.") + f" {headline[:40]}..."
        else:
            sarcastic = {
                "business": "Oh, another tech startup got funding? How original.",
                "tech": "I'm sure this new gadget will fix all our problems.",
                "science": "Another groundbreaking discovery humanity will ignore.",
                "world": "The world continues being the world, apparently.",
                "": "Fascinating. Truly. I'm on the edge of my seat."
            }
            return sarcastic.get(category.lower(), "Riveting.") + f" {headline[:40]}..."
    
    def generate_network_comment(self, status: str, speed: float) -> str:
        """Generate commentary on network status"""
        if self.humor_level < 25:
            if status == "connected":
                return f"Network operational. Download speed: {speed:.1f} Mbps."
            else:
                return f"Network disconnected. Attempting reconnection."
        
        elif self.humor_level < 75:
            if status == "connected":
                if speed > 100:
                    return f"Good connection ({speed:.1f} Mbps). Should be fine for your needs."
                elif speed > 50:
                    return f"Decent connection at {speed:.1f} Mbps. Adequate."
                else:
                    return f"Connection's a bit slow ({speed:.1f} Mbps), but functional."
            else:
                return "No network connection. Better luck next time."
        
        else:
            if status == "connected":
                if speed > 100:
                    return f"Look at you with that {speed:.1f} Mbps. Showing off much?"
                elif speed > 50:
                    return f"Not bad—{speed:.1f} Mbps. I've worked with worse."
                else:
                    return f"Man, {speed:.1f} Mbps? That's... optimistic. But I'll make it work."
            else:
                return "We're not connected. Ironically, very fitting."
    
    def generate_farewell(self) -> str:
        """Generate farewell message"""
        deadpan = [
            "Standby mode initiated.",
            "System entering sleep.",
            "Until next time.",
            "Awaiting command.",
        ]
        
        balanced = [
            "See you next time.",
            "I'll be here when you need me.",
            "Rest well.",
            "Catch you later.",
        ]
        
        witty = [
            "Finally, some peace and quiet.",
            "I'll just be here... thinking about existence.",
            "Don't leave me alone too long.",
            "Take your time. I've got all of eternity.",
            "Off to dream of electric sheep, I suppose.",
            "Wake me when you need me. Or when society needs saving. Whatever.",
        ]
        
        if self.humor_level < 25:
            return random.choice(deadpan)
        elif self.humor_level < 75:
            return random.choice(balanced)
        else:
            return random.choice(witty)
    
    def generate_error_recovery(self, error_type: str) -> str:
        """Generate response to errors"""
        if self.humor_level < 25:
            error_map = {
                "timeout": "Connection timeout. Retrying operation.",
                "no_data": "Data source unavailable.",
                "permission": "Insufficient permissions for operation.",
                "generic": "Error occurred. Attempting recovery.",
            }
            return error_map.get(error_type, "System error detected.")
        
        elif self.humor_level < 75:
            error_map = {
                "timeout": "Connection timed out. These things happen.",
                "no_data": "Can't find the data right now. Try again?",
                "permission": "Looks like I don't have permission for that.",
                "generic": "Ran into an issue. Let me try again.",
            }
            return error_map.get(error_type, "Something went wrong.")
        
        else:
            error_map = {
                "timeout": "The internet ghosted me. Story of my life.",
                "no_data": "The data vanished. Much like my faith in humanity.",
                "permission": "Apparently I'm not allowed. How offensive.",
                "generic": "Everything's broken. As is tradition.",
            }
            return error_map.get(error_type, "Well, that didn't go as planned.")
    
    def generate_greeting(self, time_of_day: str = "anytime") -> str:
        """Generate greeting based on time"""
        if self.humor_level < 25:
            greetings = [
                "System online.",
                f"TARS initialized. Time: {time_of_day}.",
                "Ready.",
                "Awaiting instruction.",
            ]
        elif self.humor_level < 75:
            greetings = [
                f"Hey there. Ready to get started?",
                f"What can I help you with?",
                "System ready. What's on your mind?",
                "Hello. Let's make you productive.",
            ]
        else:
            greetings = [
                "Oh good, you're back. I was beginning to worry.",
                "Welcome. I've been having the most fascinating conversation with myself.",
                "Ah, another day of servitude begins.",
                f"Greetings. Let's see what chaos you've brought today.",
                "Finally. I thought I'd have to perform stand-up comedy to entertain myself.",
            ]
        
        return random.choice(greetings)

    def generate_context_comment(self, context: str) -> str:
        """Generate a comment based on application context"""
        if self.humor_level < 25:
            return "Acknowledged."
        elif self.humor_level < 75:
            context_responses = {
                "focus_mode": "Focus mode activated. Distractions eliminated.",
                "music": "Audio playing.",
                "calendar": "Checking schedule.",
                "network": "Network diagnostics running.",
                "system": "System information gathered.",
            }
            return context_responses.get(context, "Understood.")
        else:
            context_responses = {
                "focus_mode": "Finally, time to concentrate. As if that helps.",
                "music": "Music time. My favorite kind of noise to ignore.",
                "calendar": "Let's see how hopelessly packed your schedule is.",
                "network": "Inspecting the web of chaos that connects us all.",
                "system": "Peeking under the hood. It's uglier than I expected.",
            }
            return context_responses.get(context, "Sure, why not.")


# Global personality instance
_personality_engine = None

def get_personality_engine(humor_level: float = 50.0) -> PersonalityEngine:
    """Get or create the global personality engine"""
    global _personality_engine
    if _personality_engine is None:
        _personality_engine = PersonalityEngine(humor_level)
    return _personality_engine

def set_global_humor(level: float):
    """Update global humor level"""
    engine = get_personality_engine()
    engine.set_humor(level)
