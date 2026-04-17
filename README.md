# 🤖 Denji Synthetic Command Interface

<div align="center">

**A sci-fi AI-powered terminal dashboard with personality, voice, camera, and neural core intelligence.**

[![GitHub](https://img.shields.io/badge/GitHub-SiddharthShah30%2Fdeskzen-blue?logo=github)](https://github.com/SiddharthShah30/deskzen)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](#-license)
[![Commits](https://img.shields.io/badge/Latest-v3.0%20(AI%20Brain)-blueviolet)](#-whats-new-in-v30)

**[Features](#-main-features) • [Installation](#-quick-install) • [Usage](#-usage) • [AI Integration](#-ai-integration) • [Documentation](#-documentation)**

</div>

---

## 🎯 Overview

**Denji** is a production-ready terminal UI assistant that combines personality, AI intelligence, and system monitoring into one immersive experience. Based on TARS from *Interstellar*, it features:

- 🧠 **OpenCode AI Brain** - Full-featured open-source AI agent (Ollama → OpenCode → Rule-based fallbacks)
- 🎭 **Personality Engine** - TARS-inspired humor-aware responses (0-100% adjustable)
- 🎙️ **Multi-Modal I/O** - Typing, voice input/output, camera integration
- 📊 **Real-Time Dashboard** - Sci-fi HUD with system telemetry & neural core chat
- 📋 **Productivity Tools** - Todo list, calendar, pomodoro timer, news/stocks
- 🎵 **Audio System** - Music player, spectrum visualizer, audio synthesis
- 🌐 **System Integration** - Network monitoring, face detection, focus modes

**Designed for:** Developers, writers, deep workers, and anyone who loves Terminal UIs.

---

## 🚀 Quick Install

Choose your OS:

### Windows (Easiest - 30 seconds)
```powershell
# Double-click install.bat
# OR
powershell -ExecutionPolicy Bypass -File install.ps1
```

### macOS / Linux
```bash
bash install.sh
# OR via curl
curl -fsSL https://raw.githubusercontent.com/SiddharthShah30/deskzen/main/install.sh | bash
```

**That's it!** The script handles:
- ✅ Python 3.9+ check
- ✅ Virtual environment setup
- ✅ All dependencies (OpenCV, voice, TTS, audio)
- ✅ Denji installation

**Time:** 2-5 minutes | **Space:** ~500 MB

### After Installation
```bash
# Activate environment
source .venv/bin/activate          # macOS/Linux
# .\.venv\Scripts\Activate.ps1     # Windows

# Run Denji
python main.py
# OR
denji
```

You'll see the **OpenCode Credits Splash**, then the **Denji Neural Core Dashboard**.

---

## 🎬 What's New in v3.0

### AI Brain Integration ✨
- **OpenCode Agent** - Full-featured open-source AI that understands the Denji codebase
- **Multi-Level Fallbacks** - Ollama (local) → OpenCode CLI → Rule-based responses
- **Live Conversation** - Chat history visible in Neural Core panel on dashboard
- **Intelligent Responses** - Context-aware, codebase-aware answers
- **No API Keys** - Completely open-source and privacy-focused

### Neural Core Dashboard 🧠
- Replaced subsystem display with **full todo list** in right panel
- **AI conversation panel** in center (replaces static telemetry)
- **Live input display** showing what you're typing
- **3-panel HUD layout** - Ship Telemetry | Neural Core (AI) | Todo List

### Production Installation 📦
- **One-command installers** (Windows `.bat`/`.ps1`, macOS/Linux `.sh`)
- **Professional documentation** (INSTALLATION.md, INSTALL_METHODS.md)
- **Safe uninstall** with data preservation
- **Works across all platforms** (Windows, macOS, Linux)

### Code Quality 🏆
- **OpenCode credits** on startup
- **Full contributor attribution**
- **Professional-grade installation**
- **Comprehensive documentation**

---

## ✨ Main Features

### 🧠 AI Brain (NEW!)
- **OpenCode Integration** - Open-source AI agent for anything
- **Ollama Support** - Optional local LLM for faster inference
- **Fallback Chain** - Always has intelligent responses
- **Codebase Awareness** - Understands the Denji system
- **Terminal-Native** - Built for CLI environments

### 🎭 TARS Personality System
- **Mood States** - Idle, Listening, Processing, Speaking, Happy, Sad
- **Humor Adjustment** - 0-100% humor level (adjust with +/-)
- **Context-Aware** - Personality responds to your actions
- **Animated Interface** - Scanline header, pulsing indicators

### 🎙️ Voice & Audio
- **Speech Recognition** - Voice input with multi-fallback (sounddevice → SpeechRecognition)
- **Text-to-Speech** - Voice output (pyttsx3 → SAPI → PowerShell)
- **Real-Time Visualization** - Live spectrum analyzer
- **Audio System** - Music player, custom synthesis, YouTube streams

### 📷 Camera Integration
- **Face Detection** - OpenCV with Windows DirectShow support
- **Attention Tracking** - Eye position affects dashboard
- **Safe Startup** - Async initialization won't block app launch
- **Multi-Fallback** - DirectShow → Generic fallback

### 📊 Dashboard & Views

| View | Purpose |
|------|---------|
| **Home (Neural Core)** | AI brain, conversation history, system stats |
| **Clock + Music** | Large clock, now-playing, spectrum visualizer |
| **Focus (Pomodoro)** | Timer with work/break modes, deep focus support |
| **Neofetch** | Animated system information display |
| **Network** | Real-time bandwidth monitoring, device info |
| **Library** | Music/audio management (local, YouTube) |
| **Calendar** | Day/Week/Month views, event management, ICS sync |
| **Video** | Local/YouTube video playback |
| **News & Stocks** | RSS feeds, market data, watchlists |

### 📋 Productivity Tools
- **Todo List** - Persistent JSON storage, completable items
- **Calendar** - Full event management with ICS support
- **Pomodoro** - Customizable focus modes (Coding, Reading, Deep Work)
- **News Feed** - Real-time RSS integration
- **Stock Tracking** - Market data and watchlists

### 🔒 On Launch
- **Credits Splash Screen** - Acknowledges OpenCode & contributors
- **Safe Boot Path** - Voice & personality engines load async
- **System Check** - Verifies all components are ready
- **Professional Greeting** - "All systems online"

---

## 🎮 Usage

### Keyboard Commands

**Global (from any view):**
- `t` - Type command (home view)
- `v` - Voice input (home view)
- `o` - Add todo (home view)
- `+` / `-` - Adjust humor level (home view)
- `c` - Toggle camera (home view)
- `Space` - Play/pause music
- `z` / `x` - Previous/next track
- `←` / `→` - Switch views
- `q` - Quit

**In typing mode (after pressing `t`):**
- `Enter` - Submit command/message to AI
- `Escape` - Cancel
- `Backspace` - Delete character
- `Ctrl+W` - Delete word
- `Ctrl+U` - Clear line

**Todo list (after pressing `o`):**
- `Enter` - Add new todo
- `Escape` - Cancel

### Example Commands

```
# Type mode (press 't')
"hello"                      → AI responds with greeting
"how does the voice work?"   → AI explains voice system
"tell me about the camera"   → AI describes camera integration
"what can I do?"             → AI lists available features
"what is the neural core?"   → AI explains the AI brain

# Quick commands (home view)
v  → Listen for voice command
o  → Add a todo item
+  → Increase humor
-  → Decrease humor
c  → Toggle camera
```

---

## 🧠 AI Integration

### How It Works

**Intelligent Response Fallback Chain:**

1. **Ollama Local LLM** (fastest, optional)
   - If you have Ollama running, Denji uses it first
   - ~200ms response time
   - Fully local, no internet needed

2. **OpenCode CLI Agent** (intelligent, default)
   - Full-featured open-source AI
   - Understands complex contexts
   - No API keys required
   - Automatic detection after `npm install -g opencode-ai@latest`

3. **Rule-Based Responses** (always available)
   - Patterns for common questions
   - Denji system knowledge built-in
   - Never fails
   - Professional fallback

### Setup (Optional Enhancements)

#### Install OpenCode AI
```bash
# Any of these work
npm install -g opencode-ai@latest
bun install -g opencode-ai@latest
scoop install opencode          # Windows

# Verify
opencode --version
```

After installation, Denji automatically detects and uses it!

#### Install Ollama (Optional Speed Boost)
```bash
# https://ollama.ai
ollama pull neural-chat
ollama serve
```

Run in one terminal, then launch Denji in another.

### AI Features

- **Context-Aware** - Understands you're using Denji
- **Codebase Knowledge** - Knows voice, camera, todo, personality systems
- **Conversation History** - Maintains context across messages
- **Intelligent Routing** - Routes to Ollama/OpenCode automatically
- **Always Responsive** - Never times out (rule-based fallback)

---

## 📁 Project Structure

```
denji/
├── main.py                 # Main application (8000+ LOC)
├── denji_ai.py            # AI brain module (OpenCode integration)
├── denji_standby/
│   ├── voice.py           # Speech synthesis & recognition
│   ├── personality.py     # TARS humor engine
│   ├── tars_ui.py         # Dashboard UI renderer
│   └── ...                # Other modules
├── install.bat            # Windows double-click installer
├── install.ps1            # Windows PowerShell installer
├── install.sh             # macOS/Linux bash installer
├── uninstall.ps1          # Windows uninstaller
├── uninstall.sh           # macOS/Linux uninstaller
├── pyproject.toml         # Package configuration
├── README.md              # This file
├── INSTALLATION.md        # Detailed installation guide
├── INSTALL_METHODS.md     # All installation options
├── INSTALL_SCRIPTS.md     # Script reference
└── AI_INTEGRATION.md      # AI setup guide
```

---

## 📦 Dependencies

### Automatically Installed
- **pyttsx3** - Text-to-speech
- **SpeechRecognition** - Voice input
- **sounddevice** - Audio capture
- **opencv-python** - Computer vision & face detection
- **numpy** - Math/array operations
- **requests** - HTTP client
- **psutil** - System information
- **feedparser** - News feed parsing
- **icalendar** - Calendar support

### System Requirements
| Requirement | Details |
|-------------|---------|
| **OS** | Windows 10+, macOS 10.13+, Linux (any modern distro) |
| **Python** | 3.9 or higher |
| **RAM** | 512 MB minimum, 2 GB recommended |
| **Disk** | 500 MB for installation |
| **Terminal** | 72×24 characters minimum |

### Optional
- **Node.js** - For OpenCode CLI (`npm install -g opencode-ai@latest`)
- **Ollama** - For local LLM inference (https://ollama.ai)

---

## 🛠️ Installation Methods

### Method 1: Automated Scripts (Recommended)

**Windows - Double-click:**
- Right-click `install.bat` → "Run as Administrator"

**Windows - PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

**macOS/Linux:**
```bash
bash install.sh
```

### Method 2: Via Package Manager

**Homebrew (macOS):**
```bash
brew install python@3.11
cd /path/to/denji
bash install.sh
```

**APT (Ubuntu/Debian):**
```bash
sudo apt-get install python3 python3-pip python3-venv
cd /path/to/denji
bash install.sh
```

### Method 3: Manual

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .\.venv\Scripts\Activate.ps1 # Windows

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install pyttsx3 SpeechRecognition sounddevice opencv-python numpy requests psutil feedparser icalendar

# Install Denji
pip install -e .
```

See [INSTALLATION.md](INSTALLATION.md) for detailed instructions.

---

## 🗑️ Uninstall

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

### macOS/Linux
```bash
bash uninstall.sh
```

Safely removes all packages while preserving your todo list and calendar data.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[INSTALLATION.md](INSTALLATION.md)** | Complete setup guide with troubleshooting |
| **[INSTALL_METHODS.md](INSTALL_METHODS.md)** | All installation options & comparisons |
| **[INSTALL_SCRIPTS.md](INSTALL_SCRIPTS.md)** | Quick reference for installer scripts |
| **[AI_INTEGRATION.md](AI_INTEGRATION.md)** | AI brain setup & configuration |

---

## 🎓 Getting Started

### 1. Install
```bash
bash install.sh          # macOS/Linux
# or install.ps1         # Windows
```

### 2. Run
```bash
source .venv/bin/activate
python main.py
# or
denji
```

### 3. Explore
- Press `?` for help (if available)
- Press `t` to start typing
- Press `Enter` to submit to AI
- See your AI responses in the Neural Core panel
- Press `←` / `→` to explore other views
- Press `q` to quit

### 4. Customize (Optional)
- Increase humor: `+` / `-`
- Enable camera: `c`
- Add todos: `o`
- Try voice: `v`

---

## 🔬 Development

### Run Tests
```bash
python -m pytest
```

### Code Structure
- **main.py** - Central application (8076 lines)
- **denji_ai.py** - AI engine (OpenCode integration)
- **denji_standby/** - Modular subsystems

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 🏆 Credits

### OpenCode Foundation
Built with the [OpenCode](https://github.com/anomalyco/opencode) agent architecture.

**OpenCode Creators:**
- [@thdxr](https://github.com/thdxr) - Founder & Lead Developer
- [@adamdotdevin](https://github.com/adamdotdevin) - Core Architecture
- [@rekram1-node](https://github.com/rekram1-node) - Infrastructure
- [860+ Community Contributors](https://github.com/anomalyco/opencode/graphs/contributors)

### Denji Contributors
- **Siddharth Shah** - Designer & Developer

### Libraries & Technologies
- **Python** - Core language
- **Curses** - Terminal UI
- **OpenCV** - Computer vision
- **pyttsx3** - Speech synthesis
- **SpeechRecognition** - Voice input
- **sounddevice** - Audio capture
- **numpy** - Numerical computing

---

## 📄 License

Denji Synthetic Command Interface is licensed under the **MIT License**.

See [LICENSE](LICENSE) for details.

### Third-Party Licenses
- OpenCode: MIT License
- OpenCV: Apache 2.0
- pyttsx3: MIT License
- SpeechRecognition: BSD License
- sounddevice: MIT License

All dependencies follow their respective licenses.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 🐛 Bug Reports

Found an issue? [Open a GitHub Issue](https://github.com/SiddharthShah30/deskzen/issues) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your OS and Python version

---

## 🚀 Roadmap

- [ ] Web-based dashboard companion
- [ ] Mobile app for remote control
- [ ] Custom model training
- [ ] Plugin system
- [ ] Advanced voice commands
- [ ] Real-time collaboration features
- [ ] Cloud integration (optional)

---

## 📧 Contact & Support

- **GitHub Issues** - Report bugs & request features
- **Discussions** - Ask questions & share ideas
- **Documentation** - See [INSTALLATION.md](INSTALLATION.md) & [AI_INTEGRATION.md](AI_INTEGRATION.md)

---

## 🎉 Acknowledgments

- **TARS** from *Interstellar* - Inspiration for personality & design
- **OpenCode** - Foundation for AI agent architecture
- **All Contributors** - Making Denji better

---

## ⭐ Star History

If you find Denji useful, please consider giving it a star on GitHub!

[![GitHub Star](https://img.shields.io/github/stars/SiddharthShah30/deskzen?style=social)](https://github.com/SiddharthShah30/deskzen)

---

<div align="center">

**Built with ❤️ using Python + Terminal Magic**

*"Humans are good at art. At least, I think so. If the apocalypse comes, beep boop."* — TARS

[Install Now](#-quick-install) • [Documentation](#-documentation) • [GitHub](https://github.com/SiddharthShah30/deskzen)

</div>
