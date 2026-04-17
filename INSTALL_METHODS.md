# 🚀 Denji Installation Methods - Complete Reference

All available ways to install Denji Synthetic Command Interface.

---

## ⚡ Super Fast (30 seconds)

Choose based on your OS:

### Windows - Double-click
```
1. Download or navigate to project folder
2. Right-click install.bat
3. Select "Run as Administrator"
4. Done! ✓
```

### macOS/Linux - One liner
```bash
bash install.sh
```

---

## 🔧 Installation Options by OS

### Windows

#### Option 1: Double-click (Easiest!)
```
Right-click install.bat → Run as Administrator → Done
```

#### Option 2: PowerShell (Any folder)
```powershell
cd /path/to/denji
powershell -ExecutionPolicy Bypass -File install.ps1
```

#### Option 3: Command Prompt (Any folder)
```cmd
cd \path\to\denji
install.bat
```

#### Option 4: Manual (If scripts fail)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install pyttsx3 SpeechRecognition sounddevice opencv-python numpy requests psutil feedparser icalendar windows-curses
pip install -e .
```

---

### macOS

#### Option 1: Bash script
```bash
cd /path/to/denji
bash install.sh
```

#### Option 2: Curl pipe (Direct)
```bash
curl -fsSL https://raw.githubusercontent.com/SiddharthShah30/deskzen/main/install.sh | bash
```

#### Option 3: With Homebrew first
```bash
brew install python@3.11
cd /path/to/denji
bash install.sh
```

#### Option 4: Manual
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install pyttsx3 SpeechRecognition sounddevice opencv-python numpy requests psutil feedparser icalendar
pip install -e .
```

---

### Linux (Ubuntu/Debian)

#### Option 1: Auto with system packages
```bash
cd /path/to/denji
bash install.sh
```
(Automatically installs Python 3, pip, venv with sudo)

#### Option 2: Curl pipe
```bash
curl -fsSL https://raw.githubusercontent.com/SiddharthShah30/deskzen/main/install.sh | bash
```

#### Option 3: Manual steps
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv curl

# Setup Denji
cd /path/to/denji
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install pyttsx3 SpeechRecognition sounddevice opencv-python numpy requests psutil feedparser icalendar
pip install -e .
```

#### Option 4: Fedora/RHEL
```bash
sudo yum install python3 python3-pip curl
cd /path/to/denji
bash install.sh
```

---

## 🗑️ Uninstall Options

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

### macOS/Linux
```bash
bash uninstall.sh
```

### Manual Uninstall (Any OS)
```bash
# Deactivate environment if active
deactivate  # or just open new terminal

# Remove virtual environment
rm -rf .venv        # macOS/Linux
rmdir /s .venv      # Windows

# Remove cache
rm -rf __pycache__
rm -rf build dist *.egg-info
```

---

## ✅ Verify Installation

After any installation method:

```bash
# Activate environment
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

# Test imports
python -c "import cv2, pyttsx3, speech_recognition; print('✓ Ready!')"

# Launch Denji
python main.py
# or
denji
```

---

## 📋 File Reference

| File | OS | Method | How to Use |
|------|----|---------|----|
| `install.bat` | Windows | GUI | Double-click or `install.bat` |
| `install.ps1` | Windows | PowerShell | `powershell -File install.ps1` |
| `install.sh` | macOS/Linux | Bash | `bash install.sh` |
| `uninstall.ps1` | Windows | PowerShell | `powershell -File uninstall.ps1` |
| `uninstall.sh` | macOS/Linux | Bash | `bash uninstall.sh` |

---

## 🎯 Recommended Path by User Type

### "I just want it to work"
1. **Windows**: Double-click `install.bat`
2. **macOS/Linux**: `bash install.sh`

### "I know what I'm doing"
1. **Windows**: `powershell -ExecutionPolicy Bypass -File install.ps1`
2. **macOS/Linux**: `bash install.sh` or curl pipe

### "I like control"
Follow the manual steps for your OS above

### "I want the latest from GitHub"
```bash
git clone https://github.com/SiddharthShah30/deskzen.git
cd deskzen
bash install.sh              # macOS/Linux
# or
install.ps1                  # Windows
```

---

## 📦 What Gets Installed

**Always installed:**
- Python virtual environment
- pyttsx3 (text-to-speech)
- SpeechRecognition (voice input)
- sounddevice (audio capture)
- opencv-python (computer vision)
- numpy (math library)
- requests (HTTP client)
- psutil (system info)
- feedparser (news)
- icalendar (calendar)

**Windows-specific:**
- windows-curses (terminal UI)
- pywin32 (Windows features)

**Installation size:** ~500 MB
**Installation time:** 2-5 minutes (first time)

---

## 🚦 Troubleshooting by Installation Method

### Batch/PowerShell Scripts Won't Run (Windows)
```powershell
# Fix execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try
powershell -ExecutionPolicy Bypass -File install.ps1
```

### Bash Scripts Permission Error (macOS/Linux)
```bash
# Make executable
chmod +x install.sh uninstall.sh

# Then run
bash install.sh
```

### Python Not Found
- **Windows**: Install from https://python.org (add to PATH)
- **macOS**: `brew install python@3.11`
- **Linux**: `sudo apt-get install python3`

### Slow Installation
- First-time installation is slower (downloading packages)
- Subsequent installs are cached (faster)
- Use a stable internet connection
- OpenCV can take 1-2 minutes alone

### Installation Fails Halfway
```bash
# Try upgrading pip first
pip install --upgrade pip

# Then try the installer again
```

### Virtual Environment Won't Activate
```bash
# Windows
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
# Or if that fails:
. .venv/bin/activate
```

---

## 🔄 Update/Reinstall

### Update Denji (Keep configuration)
```bash
cd /path/to/denji
git pull origin main
pip install -e . --upgrade
```

### Fresh Install (Start from scratch)
```bash
# Uninstall first
bash uninstall.sh  # or uninstall.ps1 on Windows

# Then reinstall
bash install.sh    # or install.ps1 on Windows
```

### Just Update Dependencies
```bash
source .venv/bin/activate  # macOS/Linux
# or .\.venv\Scripts\Activate.ps1 on Windows

pip install --upgrade -r requirements.txt
```

---

## 🌴 Keeping It Clean

After installation, you can delete:
- `install.ps1`, `install.sh`, `install.bat` (scripts are only for setup)
- `uninstall.ps1`, `uninstall.sh` (keep if you might uninstall later)

But it's fine to keep them! They don't affect Denji at all.

---

## 📚 Documentation

- **INSTALLATION.md** - Full detailed guide with troubleshooting
- **INSTALL_SCRIPTS.md** - Quick reference for this document
- **README.md** - Feature overview and usage
- **AI_INTEGRATION.md** - AI brain setup (OpenCode, Ollama)

---

## 🎓 What Happens During Installation

Both installers do the same thing in this order:

1. ✅ Check Python 3.9+ is installed
2. ✅ Create `.venv/` virtual environment
3. ✅ Upgrade pip/setuptools/wheel
4. ✅ Install all Python dependencies
5. ✅ Install Denji in editable mode (develop mode)
6. ✅ Setup entry points (`denji` command)

Time breakdown:
- 10 sec: Python check + venv creation
- 20 sec: pip upgrade
- 2-4 min: Package downloads & installation
- 10 sec: Denji setup

Total: **2-5 minutes** ⏱️

---

## 🔐 Safety

✅ **No admin required** (except for system packages on Linux/macOS)
✅ **Fully reversible** - uninstall removes everything
✅ **Virtual environment** - isolated from your system
✅ **No changes to system Python** - uses local `.venv`
✅ **Open source** - see exactly what's installed
✅ **No telemetry** - no tracking or data collection

---

## 💡 Pro Tips

### Create an Alias (Skip activation step)
```bash
# Add to ~/.bashrc or ~/.zprofile
alias denji="source /path/to/denji/.venv/bin/activate && python main.py"

# Then just type: denji
```

### Install OpenCode AI (Optional)
```bash
npm install -g opencode-ai@latest
# Denji automatically uses it!
```

### Setup Ollama for Speed (Optional)
```bash
# https://ollama.ai
ollama pull neural-chat
ollama serve
# Run in another terminal
cd denji
python main.py
```

---

## 🎉 You're Done!

```bash
# Activate environment
source .venv/bin/activate      # macOS/Linux
# or .\.venv\Scripts\Activate  # Windows

# Run Denji
python main.py
# or just
denji

# You should see the credits splash + dashboard!
```

**Press `t` to start typing and talk to Denji's AI brain! 🧠**

---

Need help? See:
- INSTALLATION.md (full detailed guide)
- README.md (features and usage)
- GitHub Issues (report problems)

Happy coding! 🚀
