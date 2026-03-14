## ✨ Features

### 🎵 Procedural Audio Engine

* **Built-in Synthesis**: Includes 5 real-time synthesized tracks (Brown, Pink, and White noise, Rain on Glass, and Deep Space Hum) designed for deep work.
* **Custom Library**: Supports local file playback (MP3, FLAC, WAV) and YouTube audio streaming via `yt-dlp`.
* **Adaptive Visualizer**: A live spectrum visualizer reacts to the frequency profile of the current audio.

### 🗓️ Productivity & System Views

* **Dashboard (View 1)**: A central hub displaying your clock, system status, and a persistent todo list.
* **News & Stocks (View 9)**: New in v3, this view provides real-time RSS news and stock market tracking.
* **Focus Tool**: A Pomodoro timer with customizable modes like **Coding**, **Reading**, and **Deep Work**.
* **Calendar**: Day, Week, and Month views with support for Google and Apple Calendar (ICS) sync.

### 📡 Real-Time Monitoring & Media

* **Device Tracking**: Scans and displays actually connected Bluetooth and USB hardware, including battery percentages for supported peripherals.
* **Video Playback**: Stream YouTube videos or play local files directly via `mpv` or `ffplay`.
* **Neofetch**: An animated Pac-Man logo paired with detailed system specs, including GPU and kernel info.

---

## 📊 Views (Navigate with `←` / `→`)

| # | View | Description |
| --- | --- | --- |
| 1 | **Dashboard** | Your central command. Manage your current projects, like finalizing **Triket** logic or updating your **portfolio build**. |
| 2 | **Clock + Music** | Immersive clock and now-playing panel with a large visualizer. |
| 3 | **Focus** | Pomodoro timer with work/break phases. |
| 4 | **Neofetch** | Animated TUI system information panel. |
| 5 | **Network** | Bandwidth monitoring and real device discovery. |
| 6 | **Library** | Management for built-in, local, and YouTube-sourced audio. |
| 7 | **Calendar** | Full-screen interactive calendar with event management. |
| 8 | **Video** | Separate-window video player for local or streamed content. |
| 9 | **News & Stocks** | Localized news and market data based on your region. |

---

## 🎮 Controls

### Global Keys

* `Space`: Play / Pause music.
* `←` / `→`: Switch between views.
* `z` / `x`: Previous / Next track.
* `q`: Quit application (automatically saves your todos and library).

### News & Stocks (View 9)

* `1` / `2`: Toggle between News and Stocks tabs.
* `C`: Change your country/region (updates both RSS feeds and stock tickers).
* `a` / `d`: Add or remove tickers from your stock watchlist.
* `r`: Force a manual refresh of news and market data.

### Calendar (View 7)

* `1` / `2` / `3` / `4`: Switch view modes (Day, Week, Month, Year).
* `a` / `d`: Add a new local event or delete the selected one.
* `G`: Sync from an external ICS URL (Google/Apple).

---

## 🚀 Installation & Setup

1. **Clone and Run**:
```bash
git clone https://github.com/your-username/terminal-standby.git
cd terminal-standby
python main.py

```


2. **Dependencies**: The app will attempt to auto-install `windows-curses` and `sounddevice` on first run. For the full experience, install `psutil` and `yt-dlp` via pip.
3. **Localization**: On first launch of View 9, you will be prompted to select your country. This sets up defaults for news sources and market data.

---

## 📁 Persistence

The application stores your data in your home directory:

* `~/.terminal_standby_todos.json`: Your task list, including your current development goals.
* `~/.terminal_standby_settings.json`: Your region and UI preferences.
* `~/.terminal_standby_watchlist.json`: Your custom stock tickers.
* `~/.terminal_standby_cal.json`: Manually added calendar events.
