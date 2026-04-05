# TARS AI Assistant System

## Overview
Denji has been transformed into a TARS-inspired AI assistant from the movie *Interstellar*, featuring geometric UI, voice control, personality-driven responses, and adjustable humor levels.

## Features

### 🎨 TARS-Inspired UI
- **Geometric Interface**: Clean, technical design with cube-like segments and percentage displays
- **Status Indicators**: Visual indicators for voice, system state, and activity
- **Data Visualization**: Spectrum waves, percentage bars, and real-time metrics
- **Compact & Responsive**: Adapts to terminal size with full-width and compact layouts

### 🎤 Voice Control
- **Speech Recognition** (`[v]`): Speak commands naturally
- **Text-to-Speech**: TARS responds with synthesized voice
- **Smart Command Parsing**: "Play music" → automatically prefixed as "Denji play music"
- **Status Feedback**: Real-time listening/processing indicators

### 😄 Adjustable Personality
- **Humor Slider** (`[+]`/`[-]`): Adjust TARS's wit level (0-100%)
  - **0%**: Deadpan, factual responses
  - **50%**: Balanced, professional with hints of personality
  - **100%**: Maximum sarcasm, witty commentary on everything
- **Context-Aware Responses**: Personality adapts to what you're doing (system info, news, network, etc.)
- **Dynamic Generation**: Each response is generated based on current humor level

### 📊 System Integration
TARS integrates with all existing Denji functionality:
- **Music Control**: Play, pause, skip tracks with voice
- **Focus Mode**: Start Pomodoro sessions
- **Calendar**: Navigate and manage events
- **Network**: View connection status with TARS commentary
- **System Overview**: Check CPU, RAM, and other metrics
- **News & Markets**: Get updates with personality-colored commentary

## Quick Start

### Installation
```bash
pip install -e .
```

### Launch
```bash
denji
```

### Voice Commands
Try these voice commands (say them naturally):
```
"Play music"
"Pause"
"Next track"
"Start focus mode"
"Open calendar"
"Show network status"
"System status"
"Open video"
"Show news"
```

## Controls

| Key | Action |
|-----|--------|
| `[v]` | Voice input (speak a command) |
| `[t]` | Type a command |
| `[+]` | Increase humor level (+5%) |
| `[-]` | Decrease humor level (-5%) |
| `[space]` | Play/pause music |
| `[z]/[x]` | Previous/next track |
| `[←]/[→]` | Navigate views |
| `[1-6]` | Quick action buttons |
| `[c]` | Toggle camera on/off |
| `[q]` | Quit app |

## Humor Levels

### 0-25% (Deadpan Mode)
```
Status: "CPU utilization at 75%. Core temperatures rising."
Command: "Affirmative. Processing."
Network: "Network operational. Download speed: 45.2 Mbps."
```

### 50% (Balanced Mode)
```
Status: "Your CPU's running warm. Maybe give it a break?"
Command: "Got it. Running that now."
Network: "Decent connection at 45.2 Mbps. Adequate."
```

### 75-100% (Sarcasm Mode)
```
Status: "CPU at 75%. That's... ambitious. Most humans run slower."
Command: "Oh, so NOW you want my help. Noted."
Network: "Man, 45.2 Mbps? That's... optimistic. But I'll make it work."
```

## Voice System

### Requirements
- **Speech Recognition**: `SpeechRecognition` library with Google API (free, internet required for listening)
- **Microphone**: Working audio input device
- **Text-to-Speech**: `pyttsx3` (works offline)

### How It Works
1. Press `[v]` to activate listening mode
2. Speak your command (e.g., "Play music" or "Show calendar")
3. TARS recognizes and confirms with synthesized voice
4. Command executes and response is spoken

### Fallback
If speech recognition fails or isn't available:
- Listen mode switches to text input
- You can type the command instead
- System will still respond with personality

## UI Sections

### Personality Panel
- Shows TARS face with current mood (idle, listening, processing, speaking)
- Humor level percentage bar (0-100%)
- Real-time personality adjustments

### Voice Control Panel
- Microphone status (Ready/Listening/Error/Offline)
- Text-to-Speech status (Ready/Speaking/Offline)
- Listening indicator (● active, ○ idle)

### User Input
- Displays your last command
- Shows TARS's response

### System Metrics
- CPU and RAM usage with percentage bars
- Currently playing track
- Network status
- Other real-time metrics

## Architecture

### Core Modules
- **`tars_ui.py`**: Geometric UI renderer with TARSUIRenderer class
- **`personality.py`**: PersonalityEngine for humor and response generation
- **`voice.py`**: VoiceEngine for speech recognition and TTS
- **`main.py`**: Integration layer with views and controls

### Key Classes
- `TARSUIRenderer`: Renders geometric boxes, percentage bars, status indicators
- `PersonalityEngine`: Generates context-aware responses with humor adjustment
- `VoiceEngine`: Manages microphone input and speaker output

## Troubleshooting

### Voice not working
1. Check microphone is connected and enabled
2. Run `python -c "import speech_recognition; print('SR available')"` 
3. Ensure internet connection (for Google API)
4. Check TTS: `python -c "import pyttsx3; print('TTS available')"`

### No audio output
1. Check speakers/headphones are connected
2. Volume is not muted
3. pyttsx3 is installed: `pip install pyttsx3`
4. On Windows Defender: Grant microphone permission to Python

### Terminal too small
- TARS UI gracefully degrades at <72x24 terminal size
- Switch to compact mode automatically
- Expand terminal window for full experience

## Future Enhancements
- [ ] Custom humor profiles (save/load)
- [ ] Voice command learning (custom commands)
- [ ] Gesture recognition with camera  
- [ ] Multi-language support
- [ ] Conversation history
- [ ] TARS avatar animation

## Credits
Inspired by TARS from *Interstellar* (2014)  
Built with Python curses, pyttsx3, and SpeechRecognition
