# Denji Installation Guide

Complete installation instructions for Denji Synthetic Command Interface across all platforms.

## Quick Install (Recommended)

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

Or if you're in PowerShell already:
```powershell
.\install.ps1
```

### macOS / Linux
```bash
bash install.sh
```

Or via curl:
```bash
curl -fsSL https://raw.githubusercontent.com/SiddharthShah30/deskzen/main/install.sh | bash
```

---

## What Gets Installed

The installation script automatically installs:

### Core Python Dependencies
- **pyttsx3** - Text-to-speech synthesis
- **SpeechRecognition** - Voice input processing
- **sounddevice** - Audio capture with fallbacks
- **opencv-python** - Computer vision & face detection
- **numpy** - Numerical computations
- **requests** - HTTP client for API calls
- **psutil** - System information retrieval

### Optional Dependencies
- **feedparser** - News feed parsing
- **icalendar** - Calendar event handling
- **pywin32** - Windows-specific features (Windows only)
- **windows-curses** - Terminal UI (Windows only)

### Virtual Environment
- A Python virtual environment (`.venv`) isolated from your system Python
- All dependencies installed into the virtual environment
- Full dependency lockdown (no conflicts with other projects)

---

## Installation Methods

### Method 1: Automated Script (Easiest)

#### Windows
1. Open **PowerShell as Administrator**
2. Navigate to the Denji folder
3. Run: `.\install.ps1`
4. Wait for installation to complete
5. That's it! Run `python main.py` to launch Denji

#### macOS / Linux
1. Open **Terminal**
2. Navigate to the Denji folder
3. Run: `bash install.sh`
4. Enter your password when prompted (for system packages)
5. Wait for installation to complete
6. Run: `source .venv/bin/activate` then `python main.py`

### Method 2: Manual Installation

#### Step-by-step for Windows

1. **Install Python 3.9+**
   - Download from https://www.python.org/downloads/
   - ✓ Check "Add Python to PATH"

2. **Create virtual environment**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```powershell
   pip install --upgrade pip setuptools wheel
   pip install pyttsx3 SpeechRecognition sounddevice opencv-python numpy requests psutil feedparser icalendar windows-curses
   ```

4. **Install Denji**
   ```powershell
   pip install -e .
   ```

#### Step-by-step for macOS / Linux

1. **Install system dependencies**
   
   **macOS (using Homebrew):**
   ```bash
   brew install python@3.11
   brew install curl
   ```
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv curl
   ```
   
   **Fedora/RHEL:**
   ```bash
   sudo yum install python3 python3-pip curl
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install pyttsx3 SpeechRecognition sounddevice opencv-python numpy requests psutil feedparser icalendar
   ```

4. **Install Denji**
   ```bash
   pip install -e .
   ```

---

## Verification

After installation, verify everything works:

```bash
# Activate environment
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

# Check imports
python -c "import cv2, pyttsx3, speech_recognition; print('✓ All modules loaded')"

# Run Denji
python main.py
# Or
denji
```

---

## Running Denji

### Method 1: Direct Python
```bash
# Activate environment first
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

python main.py
```

### Method 2: Use Entry Point
```bash
denji
# Or
standby
```

(Only available after `pip install -e .`)

---

## Uninstalling Denji

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

### macOS / Linux
```bash
bash uninstall.sh
```

The uninstaller will:
- ✓ Remove the virtual environment
- ✓ Clean up cache and build artifacts
- ✓ Preserve your todo list and calendar data
- ✓ Keep the source code in place

To reinstall: Just run the install script again!

---

## Troubleshooting

### Issue: "Python not found"
**Windows:**
- Install Python from https://www.python.org/downloads/
- ✓ Check "Add Python to PATH" during installation
- Restart PowerShell after installation

**macOS:**
- `brew install python@3.11`
- Add to PATH: `export PATH="/usr/local/opt/python@3.11/bin:$PATH"` in `~/.zprofile`

**Linux:**
- `sudo apt-get install python3` (Ubuntu/Debian)
- `sudo yum install python3` (Fedora/RHEL)

### Issue: "Permission denied" (macOS/Linux)
Make install scripts executable:
```bash
chmod +x install.sh uninstall.sh
bash install.sh
```

### Issue: Virtual environment won't activate
**Windows:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source .venv/bin/activate
# If that fails, try:
. .venv/bin/activate
```

### Issue: "Module not found" during installation
This is usually a network issue. Try:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Or reinstall specific package:
```bash
pip install pyttsx3 --upgrade --force-reinstall
```

### Issue: OpenCV installation fails
This sometimes happens on macOS with Apple Silicon. Try:
```bash
pip install opencv-python-headless
```

---

## Optional Enhancements

### Install OpenCode AI Agent
For advanced AI capabilities:

**Windows:**
```powershell
npm install -g opencode-ai@latest
# Or
bun install -g opencode-ai@latest
# Or
scoop install opencode
```

**macOS:**
```bash
npm install -g opencode-ai@latest
# Or
brew tap anomalyco/tap
brew install opencode
```

**Linux:**
```bash
npm install -g opencode-ai@latest
# Or via your package manager
```

Verify:
```bash
opencode --version
```

### Install Ollama for Local LLM
For faster AI responses:

Visit https://ollama.ai and install, then:
```bash
ollama pull neural-chat
ollama serve
```

Denji will automatically detect and use it!

---

## Verifying Installation

Run the smoke test:

```bash
python -c "
from denji_ai import get_ai_engine
from denji_standby.voice import get_voice_engine
from denji_standby.personality import get_personality_engine

print('✓ AI Engine:', get_ai_engine().__class__.__name__)
print('✓ Voice Engine:', get_voice_engine().__class__.__name__)
print('✓ Personality Engine:', get_personality_engine(85).__class__.__name__)
print('✓ All systems online!')
"
```

---

## Directory Structure After Installation

```
denji/
├── .venv/                 # Virtual environment (created)
├── main.py               # Main application
├── denji_ai.py          # AI brain module
├── denji_standby/       # Core modules
│   ├── voice.py
│   ├── personality.py
│   └── ...
├── install.ps1          # Windows installer
├── install.sh           # macOS/Linux installer
├── uninstall.ps1        # Windows uninstaller
├── uninstall.sh         # macOS/Linux uninstaller
└── README.md            # Documentation
```

---

## Getting Help

- **Documentation**: See [README.md](README.md) and [AI_INTEGRATION.md](AI_INTEGRATION.md)
- **Issues**: Check GitHub issues or create a new one
- **Contributing**: See CONTRIBUTING.md
- **Community**: Join Discord or check discussions

---

## System Requirements

| Component | Requirement |
|-----------|------------|
| **Python** | 3.9 or higher |
| **RAM** | 512 MB minimum, 2 GB recommended |
| **Disk** | 500 MB for installation |
| **Terminal** | 72x24 characters minimum |
| **OS** | Windows 10+, macOS 10.13+, Linux (any modern distro) |

**Optional:**
- **OpenCode**: For advanced AI (npm required)
- **Ollama**: For local LLM inference (~4-8 GB disk)
- **Node.js**: For OpenCode (npm >= 10.0)

---

## License

Denji Synthetic Command Interface is open source and licensed under MIT.
Third-party dependencies follow their respective licenses (MIT, Apache, etc.).

---

## What's Next?

1. **Read the docs**: Check [README.md](README.md) for feature overview
2. **Explore AI**: See [AI_INTEGRATION.md](AI_INTEGRATION.md) for AI setup
3. **Launch Denji**: Run `python main.py` and press `?` for help
4. **Customize**: Edit settings in `denji_standby/` modules
5. **Contribute**: Submit PRs or open issues on GitHub

Happy coding with Denji! 🚀
