# 🖥️ Terminal StandBy

> An Apple-style standby mode for your terminal — ambient music, live spectrum visualizer, system stats, focus tools, real device monitoring, and a full calendar. All in one beautiful TUI.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Version](https://img.shields.io/badge/Version-v4-blueviolet)
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
- **Smart backend detection** — prefers `sounddevice` (gapless, zero subprocess) with auto-install on first run, falls back to `ffplay`, `afplay`, `mpv`, `aplay`, or `winsound`

### 📊 Views (navigate with `←` / `→`)

| # | View | Description |
|---|------|-------------|
| 1 | **Dashboard** | System overview, todos, pomodoro timer, spectrum visualizer |
| 2 | **Clock + Music** | Full-screen clock, now-playing panel, spectrum visualizer |
| 3 | **Focus** | Pomodoro timer with work/break phases and focus modes |
| 4 | **Neofetch** | System info panel — OS, CPU, GPU, RAM, uptime, and more |
| 5 | **Network** | Live bandwidth stats, real connected device list with battery % |
| 6 | **Library** | Browse, add, and manage your music library |
| 7 | **Calendar** ⭐ new | Day, Week, and Month views with Google & Apple Calendar sync |

### 🗓️ Calendar View (new in v4)
A full calendar built into the terminal:
- **Three view modes** — Day, Week, and Month, toggled with `1` / `2` / `3`
- **Google Calendar sync** — paste your secret ICS URL and hit `G` to sync
- **Apple Calendar sync** — export your `.ics` file to `~/.terminal_standby.ics`
- **Add events manually** — step-through form for date, time, and title
- **Delete events** — remove local events with a confirmation prompt
- **Today indicator** — current hour highlighted with a live `▶` marker in Day view
- Events are colour-coded: upcoming in cyan, selected in amber, past events dimmed

### 📡 Real Device Monitoring
The Network view scans and displays **actually connected** devices — not built-in or virtual ones:
- **Bluetooth** — AirPods, keyboards, mice, phones (with battery % via GATT where available)
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

## 🗓️ Setting Up Calendar Sync

### Google Calendar
1. Open Google Calendar → **Settings** → select your calendar
2. Scroll to **Secret address in iCal format** and copy the URL
3. In Terminal StandBy, navigate to the **Calendar** view
4. Press `G` and paste the URL, then press `Enter` to sync

### Apple Calendar
1. Open Apple Calendar → **File → Export…**
2. Save the `.ics` file to `~/.terminal_standby.ics`
3. Navigate to the **Calendar** view and press `G` to load it

Events sync on demand — press `G` at any time to refresh.

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

### Calendar View
| Key | Action |
|-----|--------|
| `1` / `2` / `3` | Switch Day / Week / Month view |
| `j` / `k` | Navigate events or days |
| `a` | Add a new event |
| `d` | Delete selected event |
| `G` | Sync from Google / Apple Calendar (ICS) |
| `t` | Jump to today |

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
├── main.py                            # Main application (single-file)
├── ~/.terminal_standby_music.json     # Saved music library (auto-created)
├── ~/.terminal_standby_cache/         # Downloaded YouTube audio cache
├── ~/.terminal_standby.ics            # Apple/Google Calendar ICS file
└── ~/.terminal_standby_events.json    # Manually added local events
```

---

## 🔧 Audio Backend Priority

Terminal StandBy auto-detects and uses the best available backend:

1. `sounddevice` ← gapless PCM streaming via PortAudio, auto-installs
2. `ffplay` ← best for file playback (all platforms)
3. `afplay` ← macOS native
4. `mpv` / `mplayer` ← cross-platform
5. `aplay` ← Linux/ALSA
6. `winsound` / `powershell` ← Windows fallback

Install [FFmpeg](https://ffmpeg.org/download.html) alongside `sounddevice` for the best experience across both noise streaming and local file playback.

---

## 🚧 Roadmap

### Coming in v5
- [ ] **Spotify integration** — connect your Spotify account and control playback from the terminal
- [ ] **In-terminal video playback** — play videos directly inside the TUI

### Known Issues
- [ ] Brown Noise and Pink Noise volume levels can be uncomfortably loud — softening pass in progress
- [ ] Bluetooth battery % not always retrievable depending on OS/driver support

---

## 🤝 Contributing

Pull requests are welcome! If you're fixing a bug or adding a feature, please open an issue first to discuss what you'd like to change.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">Made with ☕ and 🎧 for terminal lovers everywhere</p>
