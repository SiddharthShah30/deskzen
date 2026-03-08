# 🖥️ Terminal StandBy

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### 🎵 Audio Engine
- **5 built-in ambient tracks** — synthesized in real-time, no downloads needed:
  - 🟤 **Brown Noise** — deep bass rumble for deep work & coding
  - 🌸 **Pink Noise** — balanced 1/f hiss for reading & focus
  - ⬜ **White Noise** — flat static for blocking distractions
  - 🌧️ **Rain on Glass** — soft rain texture with droplet pops
  - 🌌 **Deep Space Hum** — low-frequency drone for meditation
- **Custom track support** — add local audio files or YouTube URLs via `yt-dlp`
- **Shuffle, Repeat, Prev/Next** controls across all views
- Auto-detects best available audio backend (`ffplay`, `afplay`, `mpv`, `aplay`, `winsound`)

### 📊 Views (navigate with `←` / `→`)

| # | View | Description |
|---|------|-------------|
| 1 | **Dashboard** | System overview, todos, pomodoro timer |
| 2 | **Clock** | Full-screen clock with live spectrum visualizer |
| 3 | **Focus** | Pomodoro timer with work/break phases and focus modes |
| 4 | **Neofetch** | System info panel (OS, CPU, RAM, uptime, and more) |
| 5 | **Network** | Live network stats — bandwidth, IP, hostname |
| 6 | **Library** | Browse, add, and manage your music library |

### 🌈 Other Highlights
- Live **spectrum visualizer** reacts to the current ambient genre
- **Pomodoro timer** with Work / Break phases (25 min / 5 min)
- Persistent **todo list** saved between sessions
- Full **256-color** terminal UI with clean box-drawing characters
- Minimum terminal size check with graceful warning
- Cross-platform: Windows, macOS, Linux

---

## 📋 Requirements

- **Python 3.8+**
- One of the following audio backends (at least one should already be on your system):
  - `ffplay` (part of [FFmpeg](https://ffmpeg.org/) — recommended)
  - `afplay` (macOS built-in)
  - `mpv` or `mplayer`
  - `aplay` (Linux/ALSA)
  - `winsound` / `powershell` (Windows fallback)

### Optional but recommended
```
pip install psutil      # real CPU, RAM, battery, and network stats
pip install yt-dlp      # add YouTube tracks to your library
pip install windows-curses  # Windows only — auto-installed on first run
```

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/your-username/terminal-standby.git
cd terminal-standby

# Install optional dependencies
pip install psutil yt-dlp

# Run it!
python main.py
```

> **Windows users:** `windows-curses` will be installed automatically on first launch if it's missing.

---

## 🎮 Controls

### Global (works in every view)
| Key | Action |
|-----|--------|
| `←` / `h` | Previous view |
| `→` / `l` / `Tab` | Next view |
| `Space` | Play / Pause music |
| `z` | Previous track |
| `x` | Next track |
| `s` | Toggle shuffle |
| `R` | Toggle repeat |
| `q` | Quit |

### Dashboard View
| Key | Action |
|-----|--------|
| `↑` / `k` | Move todo cursor up |
| `↓` / `j` | Move todo cursor down |
| `a` | Add new todo item |
| `d` | Delete selected todo |
| `Space` | Toggle todo complete |
| `p` | Start / pause pomodoro |
| `r` | Reset pomodoro |

### Focus View
| Key | Action |
|-----|--------|
| `p` | Start / pause timer |
| `r` | Reset timer |
| `s` | Switch Work ↔ Break |
| `f` | Cycle focus mode |

### Library View
| Key | Action |
|-----|--------|
| `↑` / `k` & `↓` / `j` | Navigate tracks |
| `Enter` | Play selected track |
| `Y` | Add YouTube URL |
| `F` | Add local file path |
| `D` | Delete selected track |

---

## 📁 File Structure

```
terminal-standby/
├── main.py                          # Main application (single-file)
└── ~/.terminal_standby_music.json   # Saved user library (auto-created)
└── ~/.terminal_standby_cache/       # Downloaded YouTube audio cache
```

---

## 🔧 Audio Backend Priority

Terminal StandBy auto-detects and uses the best available backend:

1. `ffplay` ← best for streaming PCM (all platforms)
2. `afplay` ← macOS native
3. `mpv` / `mplayer` ← cross-platform
4. `aplay` ← Linux/ALSA
5. `winsound` / `powershell` ← Windows fallback

Install [FFmpeg](https://ffmpeg.org/download.html) for the best experience on all platforms.

---

## 🐛 Known Issues (v1 → v2 roadmap)

- [ ] Built-in noise tracks (Brown, Pink, White, Rain, Space) may not play correctly on some backends — under investigation
- [ ] `AttributeError: _pcm_cache` in Clock view when streaming noise tracks
- [ ] Bluetooth device detection shows system devices instead of the actively connected device; battery % not yet pulled
- [ ] USB devices (OTG, USB-C hubs, controllers, phones) not yet shown in device panel

---

## 🤝 Contributing

Pull requests are welcome! If you're fixing a bug or adding a feature, please open an issue first to discuss what you'd like to change.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">Made with ☕ and 🎧 for terminal lovers everywhere</p>
