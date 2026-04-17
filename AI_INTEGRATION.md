"""
Denji AI Brain Integration - Installation & Usage Guide
========================================================

FALLBACK CHAIN ARCHITECTURE:
1. Ollama Local LLM (http://localhost:11434)
2. OpenCode CLI Agent (open-source, deterministic AI)
3. Rule-Based Responses (always available fallback)

This hierarchy ensures Denji always has intelligent responses, even without internet or LLM access.
"""

# FALLBACK CHAIN: How It Works
# ============================

## Option 1: Ollama (Recommended for Speed)
# Install & run Ollama: https://ollama.ai
# Usage:
#   ollama pull neural-chat
#   ollama serve
# 
# Denji will automatically detect and use it. Fast, runs on your local machine.

## Option 2: OpenCode CLI Agent (Recommended for Capability)
# OpenCode is a full-featured, deterministic AI agent with no API key needed.
#
# Installation on Windows:
#   npm install -g opencode-ai@latest
#   # OR
#   bun install -g opencode-ai@latest
#   # OR
#   scoop install opencode
#
# After install, verify:
#   opencode --version
#
# Denji will automatically detect OpenCode and use it for intelligent responses.
# No setup needed - just install and Denji handles the rest!

## Option 3: Rule-Based Fallback
# Always available. Patterns recognized:
#   - Denji system questions
#   - Voice, camera, todo system
#   - Commands and features
#   - General greetings and interactions
#
# No external dependencies needed!


# QUICK START
# ===========

# 1. Install OpenCode (all one command):
#    npm install -g opencode-ai@latest
#
# 2. Verify installation:
#    opencode --version
#
# 3. Run Denji:
#    python main.py
#    # Or use denji command if installed
#
# 4. Type your questions:
#    Press 't' to enter typing mode
#    Type anything: "hello", "how does the camera work?", "what is the neural core?"
#    Press Enter to submit
#    Denji's AI brain responds with intelligent answers!


# WHAT OPENCODE DOES FOR DENJI
# ============================

# OpenCode brings:
# - Context-aware understanding of the Denji system
# - Full file and codebase awareness
# - Ability to perform complex reasoning
# - Deterministic, open-source AI (no proprietary APIs)
# - Supports Claude, OpenAI, Google, Ollama, or local models
#
# Denji uses OpenCode to:
# - Answer questions about the system architecture
# - Explain features and commands
# - Generate personality-aware responses
# - Understand user intent beyond simple keywords


# COMPARISON
# ==========

# Rule-Based Fallback:
#   Pros: Always available, no dependencies
#   Cons: Limited to predefined patterns
#
# OpenCode CLI:
#   Pros: Intelligent, open-source, no API keys, full reasoning
#   Cons: Requires installation
#
# Ollama Local LLM:
#   Pros: Very fast, local inference, no internet needed
#   Cons: Requires ~2-8GB memory depending on model


# TROUBLESHOOTING
# ===============

# Q: OpenCode is installed but Denji doesn't use it?
# A: Make sure 'opencode' is in your PATH. Test: opencode --version
#
# Q: OpenCode responses are slow?
# A: This is normal for the first call on new models. Install Ollama for speed.
#
# Q: I want to use a specific language model?
# A: OpenCode supports Claude, OpenAI, Google, Ollama, or local models.
#    See OpenCode docs: https://opencode.ai/docs
#
# Q: How do I switch between Ollama and OpenCode?
# A: Denji tries Ollama first, then OpenCode, then falls back to rules.
#    Just start whichever service you want running.


# OPENCODE GITHUB
# ===============
# Repository: https://github.com/anomalyco/opencode
# Full documentation: https://opencode.ai/
# Discord community: https://opencode.ai/discord
# 
# Founded by: @thdxr, @adamdotdevin, @rekram1-node
# Maintained by: Anomaly Co & 860+ community contributors


# CODE INTEGRATION DETAILS
# ========================

# See denji_ai.py for the actual implementation:
# - DenjiAI._generate_response_local() - orchestrates the fallback chain
# - DenjiAI._generate_with_opencode() - calls OpenCode CLI
# - HAS_OPENCODE flag - automatically set based on CLI availability
#
# The AI engine is instantiated in main.py:
#   DS.ai_engine = get_ai_engine() if HAS_AI_ENGINE else None
#
# When a command can't be handled by Denji (play music, open calendar, etc.),
# it routes to the AI engine:
#   - Try Ollama inference
#   - If that fails, try OpenCode CLI
#   - If both fail, use rule-based patterns
#   - Response displayed in Neural Core panel on dashboard
