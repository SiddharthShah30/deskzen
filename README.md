# 🖥️ Terminal StandBy

> An Apple-style standby mode for your terminal — ambient music, live spectrum visualizer, system stats, focus tools, and real device monitoring. All in one beautiful TUI.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Version](https://img.shields.io/badge/Version-v3-blueviolet)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### 🎵 Audio Engine
- **5 built-in ambient tracks** — synthesized in real-time, zero downloads needed:
  - 🟤 **Brown Noise** — deep bass rumble for deep work & coding
  - 🌸 **Pink Noise** — balanced 1/f hiss for reading & focus
  - ⬜ **White Noise** — flat static for blocking distractions
  - 🌧️ **Rain on Glass** — soft rain texture with droplet pops
  - 🌌 **Deep Space Hum** — low-frequency drone for meditation
- **Custom track support** — add local audio files or YouTube URLs via `yt-dlp`
- **Shuffle, Repeat, Prev/Next** controls available from every view
- **Smart backend detection** — now prefers `sounddevice` (gapless, zero subprocess) with auto-install on first run, falls back to `ffplay`, `afplay`, `mpv`, `aplay`, or `winsound`

### 📊 Views (navigate with `←` / `→`)

| # | View | Description |
|---|------|-------------|
| 1 | **Dashboard** | System overview, todos, pomodoro timer, spectrum visualizer |
| 2 | **Clock + Music** | Full-screen clock, now-playing panel, spectrum visualizer |
| 3 | **Focus** | Pomodoro timer with work/break phases and focus modes |
| 4 | **Neofetch** | System info panel — OS, CPU, GPU, RAM, uptime, and more |
| 5 | **Network** | Live bandwidth stats, real connected device list with battery % |
| 6 | **Library** | Browse, add, and manage your music library |

### 📡 Real Device Monitoring (v3)
The Network view now scans and displays **actually connected** devices — not built-in or virtual ones:
- **Bluetooth** — AirPods, keyboards, mice, phones (with battery % where available via GATT)
- **USB** — external drives, hubs, USB-C docks (labelled `[USB]` / `[USB-C]`)
- **Controllers** — Xbox, PlayStation, and generic gamepads (`[CTRL]`)
- **Phones** — Android (ADB) and iPhone detected as `[PHONE]`
- **Audio / HID** — external audio interfaces, cameras, and peripherals
- Battery percentages shown inline in the Battery & Power panel for all BT devices that expose them

### 🌈 Other Highlights
- Live **CAVA-style spectrum visualizer** reacts to the current ambient genre
- **Pomodoro timer** with Work / Break phases (25 min / 5 min)
- Persistent **todo list** saved between sessions
- Full **256-color** terminal UI with clean box-drawing characters
- Minimum terminal size guard (72×24) with a graceful warning
- Cross-platform: Windows, macOS, Linux

---

## 📋 Requirements

- **Python 3.8+**
- Audio backend — the app will auto-install `sounddevice` on first run. Alternatively, install any of:
  - `ffplay` (part of [FFmpeg](https://ffmpeg.org/) — best for file playback)
  - `afplay` (macOS built-in)
  - `mpv` or `mplayer`
  - `aplay` (Linux/ALSA)
  - `winsound` / `powershell` (Windows fallback)

### Optional but recommended
```
pip install psutil        # real CPU, RAM, battery, and network stats
pip install sounddevice   # best audio backend — gapless, auto-installed on first run
pip install yt-dlp        # add YouTube tracks to your library
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

> **Windows users:** `windows-curses` will be installed automatically on first launch if it's missing. `sounddevice` is also auto-installed in the background on first run for the best audio experience.

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

1. `sounddevice` ← **new in v3**, gapless PCM streaming via PortAudio, auto-installs
2. `ffplay` ← best for file playback (all platforms)
3. `afplay` ← macOS native
4. `mpv` / `mplayer` ← cross-platform
5. `aplay` ← Linux/ALSA
6. `winsound` / `powershell` ← Windows fallback

Install [FFmpeg](https://ffmpeg.org/download.html) alongside `sounddevice` for the best experience across both noise streaming and local file playback.

---

## 🐛 Known Issues & Roadmap

### v3 → v4 planned fixes
- [ ] Brown Noise and Pink Noise volume levels can be uncomfortably loud — softening pass needed
- [ ] Bluetooth battery % not always retrievable depending on OS/driver support
- [ ] Calendar integration not yet implemented (see below)

### 🗓️ Upcoming: Calendar View (v4)
A dedicated Calendar screen is planned with:
- Google Calendar and Apple Calendar sync
- Daily, Weekly, and Monthly view toggle
- Inline event display within the TUI

---

## 🤝 Contributing

Pull requests are welcome! If you're fixing a bug or adding a feature, please open an issue first to discuss what you'd like to change.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">Made with ☕ and 🎧 for terminal lovers everywhere</p>
