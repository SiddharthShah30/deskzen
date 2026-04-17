# Denji Installation Scripts

One-command installation for Denji Synthetic Command Interface across all platforms.

## 🚀 Quick Start

### Windows (Choose One)

**Option 1: Double-click (Easiest)**
- Right-click `install.bat`
- Select "Run as Administrator"
- Follow the prompts

**Option 2: PowerShell**
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

**Option 3: Command Prompt** (must be Administrator)
```cmd
install.bat
```

---

### macOS / Linux

**Option 1: Direct bash**
```bash
bash install.sh
```

**Option 2: via curl**
```bash
curl -fsSL https://raw.githubusercontent.com/SiddharthShah30/deskzen/main/install.sh | bash
```

---

## 📦 What Gets Installed

✅ Python virtual environment (isolated, safe)
✅ All required Python packages
✅ OpenCV for computer vision
✅ Voice/TTS/Speech recognition
✅ Audio processing & visualization
✅ Everything needed to run Denji

**Total install time: 2-5 minutes**
**Space required: ~500 MB**

---

## 🗑️ Uninstall

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

### macOS / Linux
```bash
bash uninstall.sh
```

**Safely removes:**
- All installed packages
- Virtual environment
- Cache and build files

**Preserves:**
- Your todo list
- Calendar events
- Source code

---

## 📖 Full Documentation

See [`INSTALLATION.md`](INSTALLATION.md) for:
- Detailed step-by-step instructions
- Manual installation options
- Troubleshooting guide
- System requirements
- Optional enhancements (OpenCode, Ollama)

---

## ✅ After Installation

1. **Activate environment** (if not automatic):
   - Windows: `.\.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`

2. **Run Denji**:
   ```bash
   python main.py
   # Or use the entry point:
   denji
   ```

3. **First launch**:
   - You'll see a credits splash screen
   - Read about OpenCode & contributors
   - Then Denji's Neural Core dashboard loads
   - Press `t` to start typing!

---

## 🔧 Troubleshooting

**Python not found?**
- Install Python 3.9+ from https://www.python.org
- Make sure "Add to PATH" is checked

**Permission denied? (macOS/Linux)**
- `chmod +x install.sh uninstall.sh`
- Then try again

**Installation slow?**
- First install takes longer (downloading packages)
- Subsequent runs are faster
- Coffee break? ☕

**Still having issues?**
- See the full troubleshooting section in [`INSTALLATION.md`](INSTALLATION.md)
- Check GitHub issues
- Create a new issue with details

---

## 🎯 Next Steps

1. Read [`README.md`](README.md) for feature overview
2. Check [`AI_INTEGRATION.md`](AI_INTEGRATION.md) for AI setup
3. Launch Denji: `python main.py`
4. Explore features with `t` (type), `v` (voice), `o` (todo), etc.
5. Optional: Install OpenCode for advanced AI (`npm install -g opencode-ai@latest`)

---

## 💡 Pro Tips

**Activate environment automatically:**
Create an alias in your shell:
```bash
# Add to ~/.bashrc or ~/.zprofile
alias denji="source /path/to/denji/.venv/bin/activate && python main.py"
```

**Keep Denji updated:**
```bash
cd /path/to/denji
git pull origin main
pip install -e . --upgrade
```

**Install OpenCode for better AI:**
```bash
npm install -g opencode-ai@latest
```
Then Denji will automatically use it!

**Use Ollama for faster LLM:**
```bash
ollama pull neural-chat
ollama serve
```
Denji prioritizes Ollama → OpenCode → Rule-based responses.

---

## 📋 Installation Files

| File | Purpose | OS |
|------|---------|-----|
| `install.bat` | Double-click installer | Windows |
| `install.ps1` | PowerShell installer | Windows |
| `install.sh` | Bash installer | macOS/Linux |
| `uninstall.ps1` | PowerShell uninstaller | Windows |
| `uninstall.sh` | Bash uninstaller | macOS/Linux |

Both installers are **identical in functionality** - choose whichever is more convenient for your system!

---

## 🔐 Safety & Privacy

✅ **Open Source** - See exactly what's installed
✅ **No Telemetry** - No tracking or data collection
✅ **Isolated** - Virtual environment keeps dependencies safe
✅ **Reversible** - Complete uninstall available
✅ **Community** - 860+ contributors, fully transparent

---

Happy coding with Denji! 🚀
