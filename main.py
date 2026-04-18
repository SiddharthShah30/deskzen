#!/usr/bin/env python3
"""
Terminal StandBy v3
Apple-style standby for your terminal.
Real synthesized music · Live spectrum visualizer · Neofetch panel for windows & calendar events · Customizable settings · Cross-platform support
"""

# ─── cross-platform curses ───────────────────────────────────────────────────
import sys, platform, subprocess

if platform.system() == "Windows":
    try:
        import curses
    except ModuleNotFoundError:
        print("Installing windows-curses…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "windows-curses"])
        import curses
else:
    import curses

import time, threading, socket, os, datetime, random, json, math, struct, shutil, atexit, hashlib, importlib
from typing import Any, cast

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

pyttsx3: Any = None
sr: Any = None
cv2: Any = None

try:
    pyttsx3 = importlib.import_module("pyttsx3")
    HAS_TTS = True
except Exception:
    pyttsx3 = None
    HAS_TTS = False

try:
    sr = importlib.import_module("speech_recognition")
    HAS_SR = True
except Exception:
    sr = None
    HAS_SR = False

try:
    cv2 = importlib.import_module("cv2")
    HAS_CV2 = True
except Exception:
    cv2 = None
    HAS_CV2 = False

# ─── TARS AI Assistant System ────────────────────────────────────────────────
try:
    from denji_standby.tars_ui import TARSUIRenderer
    HAS_TARS_UI = True
except ImportError:
    HAS_TARS_UI = False

try:
    from denji_standby.personality import get_personality_engine, set_global_humor
    HAS_PERSONALITY = True
except ImportError:
    HAS_PERSONALITY = False

try:
    from denji_standby.voice import get_voice_engine
    HAS_VOICE_ENGINE = True
except ImportError:
    HAS_VOICE_ENGINE = False

try:
    from denji_ai import get_ai_engine
    HAS_AI_ENGINE = True
except ImportError:
    HAS_AI_ENGINE = False

# ══════════════════════════════════════════════════════════════════════════════
#  COLOURS
# ══════════════════════════════════════════════════════════════════════════════
P_DIM   = 1;  P_MID  = 2;  P_HI   = 3
P_GREEN = 4;  P_AMBER= 5;  P_RED  = 6
P_BLUE  = 7;  P_CYAN = 8;  P_PINK = 9;  P_BOX = 10

def init_colors():
    curses.start_color(); curses.use_default_colors()
    curses.init_pair(P_DIM,   242, -1); curses.init_pair(P_MID,   249, -1)
    curses.init_pair(P_HI,    255, -1); curses.init_pair(P_GREEN,  70, -1)
    curses.init_pair(P_AMBER, 214, -1); curses.init_pair(P_RED,   203, -1)
    curses.init_pair(P_BLUE,   75, -1); curses.init_pair(P_CYAN,   81, -1)
    curses.init_pair(P_PINK,  170, -1); curses.init_pair(P_BOX,   237, -1)

def cp(p, bold=False):
    a = curses.color_pair(p)
    if bold: a |= curses.A_BOLD
    return a

def trim_text(text, width):
    return text if len(text) <= width else text[:max(0, width - 1)] + "…"

def clear_line(win, y, x=0, width=None, attr=0):
    H, W = win.getmaxyx()
    if y < 0 or y >= H:
        return
    if width is None:
        width = W - x
    if width <= 0:
        return
    put(win, y, x, " " * max(0, width), attr)

def chip(win, y, x, text, fg=P_HI, fill_attr=0, bold=True):
    label = f" {text} "
    put(win, y, x, label, cp(fg, bold=bold) | fill_attr)

def divider(win, y, width, x=0, attr=0):
    put(win, y, x, "─" * max(0, width), attr or cp(P_BOX))

# ══════════════════════════════════════════════════════════════════════════════
#  DRAW HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def put(win, y, x, s, attr=0):
    H, W = win.getmaxyx()
    if y < 0 or y >= H or x < 0 or x >= W: return
    s = s[:max(0, W - x - 1)]
    if not s: return
    try: win.addstr(y, x, s, attr)
    except curses.error: pass

def box(win, y, x, h, w, title=""):
    a = cp(P_BOX)
    try:
        win.attron(a)
        win.addch(y,     x,     curses.ACS_ULCORNER)
        win.addch(y,     x+w-1, curses.ACS_URCORNER)
        win.addch(y+h-1, x,     curses.ACS_LLCORNER)
        win.addch(y+h-1, x+w-1, curses.ACS_LRCORNER)
        for i in range(1, w-1):
            win.addch(y,     x+i, curses.ACS_HLINE)
            win.addch(y+h-1, x+i, curses.ACS_HLINE)
        for i in range(1, h-1):
            win.addch(y+i, x,     curses.ACS_VLINE)
            win.addch(y+i, x+w-1, curses.ACS_VLINE)
        win.attroff(a)
    except curses.error: pass
    if title:
        put(win, y, x+2, f" {title} ", cp(P_DIM))

def hbar(win, y, x, w, pct, col=P_HI):
    pct = max(0, min(100, pct))
    f   = int(w * pct / 100)
    put(win, y, x,   "█"*f,       cp(col))
    put(win, y, x+f, "░"*(w-f),   cp(P_DIM))

def centre(win, y, s, attr=0):
    _, W = win.getmaxyx()
    put(win, y, max(0,(W-len(s))//2), s, attr)

def kbfmt(k):
    return f"{k/1024:.1f}MB/s" if k > 1024 else f"{k:.0f}KB/s"

# ══════════════════════════════════════════════════════════════════════════════
#  PAC-MAN LOGO ANIMATION
# ══════════════════════════════════════════════════════════════════════════════

# Pac-Man open / closed mouth frames (5 rows tall, 7 cols wide)
# ══════════════════════════════════════════════════════════════════════════════
#  ANIMATIONS: Pac-Man, Anime, Logo, Bouncing
# ══════════════════════════════════════════════════════════════════════════════

_PAC_OPEN = [
    " ████ ",
    "██████",
    "███   ",
    "██████",
    " ████ ",
]
_PAC_CLOSED = [
    " ████ ",
    "██████",
    "██████",
    "██████",
    " ████ ",
]

# Ghost (5 rows, 6 cols)
_GHOST = [
    " ████ ",
    "██████",
    "██ ██ ",   # eyes as spaces
    "██████",
    "█ ██ █",   # wavy bottom
]

# Starfield animation - scrolling stars (beautiful space effect)
_STARFIELD_FRAMES = [
    [
        "   ✦  ★  ✧     ✦",
        "  ✧    ★   ✦    ",
        "    ★  ✧  ✦  ★  ",
        " ★   ✦    ✧    ★",
        "✦  ✧   ★    ✦   ",
        "  ✧  ✦   ★  ✧   ",
        "★    ✦  ✧   ★   ",
    ],
    [
        "  ✦    ★  ✧     ",
        " ✧      ★   ✦   ",
        "   ★   ✧  ✦  ★  ",
        "★    ✦     ✧    ★",
        " ✦  ✧   ★    ✦  ",
        "   ✧  ✦   ★  ✧  ",
        "  ★    ✦  ✧   ★ ",
    ],
    [
        "✦    ★  ✧      ✦",
        "✧      ★   ✦    ",
        "  ★   ✧  ✦  ★   ",
        "    ✦     ✧    ★",
        "  ✦  ✧   ★    ✦ ",
        "    ✧  ✦   ★  ✧ ",
        "    ★    ✦  ✧   ★",
    ],
]

# 3D Spinning cube (rotating perspective)
_CUBE_FRAMES = [
    [
        "   ┌─────┐",
        "  ╱       ╱│",
        " ┌─────────┐ │ │",
        " │      │ │ │ ╰",
        " │      │ ╱  ",
        " ╰─────────╯    ",
    ],
    [
        "    ╱─────╱",
        "   ╱       ╱ ",
        "  ┌────────┐   ",
        "  │      │  ",
        "  │      │  ",
        "  ╰────────╯  ",
    ],
    [
        "   ┌─────┐ ",
        "   │ ╱──╱ │ ",
        "   │╱   ╱ │ ",
        "   ┌─────────┐ ",
        "   │      │ ",
        "   ╰────────╯ ",
    ],
]

# Ocean wave animation
_WAVE_FRAMES = [
    [
        "     ≈≈≈      ",
        "   ≈≈≈≈≈≈≈   ",
        "  ≈≈≈≈≈≈≈≈≈  ",
        " ≈≈≈≈ ≈ ≈≈≈≈≈ ",
    ],
    [
        "    ≈≈≈≈     ",
        "   ≈≈≈≈≈≈≈   ",
        "  ≈≈≈  ≈≈≈≈  ",
        " ≈≈≈≈≈≈≈≈≈≈≈ ",
    ],
    [
        "   ≈≈≈≈≈    ",
        "  ≈≈≈≈≈≈≈≈  ",
        " ≈≈≈ ≈≈ ≈≈≈ ",
        "≈≈≈≈≈≈≈≈≈≈≈≈ ",
    ],
]

# Anime girl frames (dancing, 8 rows, ~12 cols wide)
_ANIME_FRAMES = [
    [  # Frame 1: neutral
        "   ╔═╗   ",
        "   ║▔▔╗  ",
        "  ╔╣◕◕║╗ ",
        "  ║╚□╩╝║ ",
        "  ║ ╲╱ ║ ",
        " ╔╡ │ │ ║ ",
        " ║│ │ │╔╝ ",
        " ╚══════╝ ",
    ],
    [  # Frame 2: left lean
        "  ╔═╗    ",
        "  ║▔▔╗   ",
        " ╔╣◕◕║╗  ",
        " ║╚□╩╝║  ",
        " ║╲╱  ║  ",
        "╔╡ │ │║  ",
        "║│╱│ │╝  ",
        "╚════════ ",
    ],
    [  # Frame 3: right lean
        "    ╔═╗  ",
        "   ╔║▔▔╗ ",
        "  ║╣◕◕║╗ ",
        "  ║╚□╩╝║ ",
        "  ║  ╲╱║ ",
        "  ║│ │ │╡╗",
        "  ╚│ │ │║ ",
        " ════════╝",
    ],
]

# System logo spinning (circle, 5 rows)
_LOGO_SPIN = [
    "  ◇    ",
    "  ◆    ",
    "  ●    ",
    "  ◆    ",
    "  ◇    ",
]

# Bouncing ball (simple)
_BOUNCE_FRAMES = [
    "●      ",
    " ●     ",
    "  ●    ",
    "   ●   ",
    "    ●  ",
    "     ● ",
    "      ●",
]

# The track width matches LOGO_W = 26, minus 2 padding = 24 usable chars
_TRACK_W = 22   # dots track width (chars)
_DOT     = "·"
_PELLET  = "●"

class NeofetchState:
    animation_mode = "pacman"  # pacman, anime, logo, bounce

NFS = NeofetchState()

def draw_animated_logo(win, y, x, t):
    """Pac-Man eats dots across the logo area. Returns height used."""
    W_LOGO = 24   # total logo column width available

    # --- animation state derived from time ---
    speed   = 4.0                          # chars per second
    cycle   = _TRACK_W / speed            # seconds for one full pass
    pos_f   = (t * speed) % _TRACK_W      # pacman x position (float, 0..TRACK_W)
    pos     = int(pos_f)
    mouth_open = int(t * 8) % 2 == 0      # mouth flaps 4 Hz

    # ghost lags behind pacman by 6 chars (wraps)
    ghost_pos = int((pos_f - 7) % _TRACK_W)

    # --- choose pac frame ---
    pac_frame  = _PAC_OPEN if mouth_open else _PAC_CLOSED

    # --- title rows ---
    put(win, y,   x, "  TERMINAL STANDBY  v3", cp(P_DIM))
    put(win, y+1, x, "  " + "─" * (W_LOGO - 4), cp(P_BOX))

    # --- pac-man rows (5 rows) ---
    PAC_Y = y + 2
    for row in range(5):
        # build the track line
        track = list(" " * _TRACK_W)

        # place dots — only ahead of pacman
        for col in range(_TRACK_W):
            is_pellet = (col % 7 == 3)
            if col > pos + 6:          # not yet eaten
                track[col] = _PELLET if is_pellet else _DOT

        # place ghost (overwrite track chars in ghost columns)
        # ghost is 6 wide, drawn only if it fits
        gx = ghost_pos
        if 0 <= gx < _TRACK_W:
            ghost_line = _GHOST[row]
            for ci, ch in enumerate(ghost_line):
                ti = gx + ci
                if 0 <= ti < _TRACK_W:
                    track[ti] = ch

        # place pac-man (7 wide, drawn last so it wins)
        pac_line = pac_frame[row]
        for ci, ch in enumerate(pac_line):
            ti = pos + ci
            if 0 <= ti < _TRACK_W:
                track[ti] = ch

        track_str = "".join(track)

        # draw: leading indent, then track
        put(win, PAC_Y + row, x + 1, track_str, cp(P_AMBER, bold=True))

        # ghost eyes — bright overlay
        for ci, ch in enumerate(_GHOST[row]):
            ti = ghost_pos + ci
            if 0 <= ti < _TRACK_W and ch == " " and row == 2:
                # these spaces are the eyes — make them cyan
                put(win, PAC_Y + row, x + 1 + ti, "●", cp(P_CYAN, bold=True))

    return PAC_Y - y + 5   # total rows used


def draw_starfield_logo(win, y, x, t):
    """Scrolling starfield animation. Returns height used."""
    frame_idx = int(t * 2) % len(_STARFIELD_FRAMES)
    frame = _STARFIELD_FRAMES[frame_idx]

    put(win, y, x, "  TERMINAL STANDBY  v3", cp(P_DIM))
    put(win, y+1, x, "  " + "─" * 20, cp(P_BOX))

    for i, line in enumerate(frame):
        put(win, y + 2 + i, x + 1, line, cp(P_CYAN, bold=True))

    return y - y + len(frame) + 2


def draw_cube_anim(win, y, x, t):
    """3D spinning cube animation. Returns height used."""
    frame_idx = int(t * 2) % len(_CUBE_FRAMES)
    frame = _CUBE_FRAMES[frame_idx]

    put(win, y, x, "  TERMINAL STANDBY  v3", cp(P_DIM))
    put(win, y+1, x, "  " + "─" * 20, cp(P_BOX))

    for i, line in enumerate(frame):
        put(win, y + 2 + i, x + 1, line, cp(P_BLUE, bold=True))

    return y - y + len(frame) + 2


def draw_wave_anim(win, y, x, t):
    """Ocean wave animation. Returns height used."""
    frame_idx = int(t * 3) % len(_WAVE_FRAMES)
    frame = _WAVE_FRAMES[frame_idx]

    put(win, y, x, "  TERMINAL STANDBY  v3", cp(P_DIM))
    put(win, y+1, x, "  " + "─" * 20, cp(P_BOX))

    for i, line in enumerate(frame):
        put(win, y + 2 + i, x, line, cp(P_GREEN, bold=True))

    return y - y + len(frame) + 2


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO ENGINE  –  procedural synth → ffplay / afplay / Windows WAVE
# ══════════════════════════════════════════════════════════════════════════════
SR    = 44100
CHUNK = 2048

def _sin(f, t):  return math.sin(2*math.pi*f*t)

def _saw(f, t, nh=6):
    s = 0.0
    for h in range(1, nh+1): s += _sin(f*h, t)/h
    return s * (2/math.pi)

def _sqr(f, t, nh=6):
    s = 0.0
    for h in range(0, nh):
        k = 2*h+1
        s += _sin(f*k, t)/k
    return s * (4/math.pi)

def _tri(f, t, nh=5):
    s = 0.0
    for h in range(0, nh):
        k = 2*h+1
        s += ((-1)**h)*_sin(f*k, t)/(k*k)
    return s * (8/(math.pi**2))

def env(i, n, a_frac=0.05, r_frac=0.15):
    at = int(n*a_frac); rel = int(n*r_frac)
    if i < at:   return i/max(1,at)
    if i > n-rel:return (n-i)/max(1,rel)
    return 1.0

def midi(n):   return 440.0 * 2**((n-69)/12)


# ══════════════════════════════════════════════════════════════════════════════
#  MUSIC LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
import array as _array

LIBRARY_FILE = os.path.join(os.path.expanduser("~"), ".terminal_standby_music.json")

# ══════════════════════════════════════════════════════════════════════════════
#  CALENDAR ENGINE
# ══════════════════════════════════════════════════════════════════════════════
CAL_FILE  = os.path.join(os.path.expanduser("~"), ".terminal_standby_cal.json")
CAL_ICS   = os.path.join(os.path.expanduser("~"), ".terminal_standby.ics")
CAL_ICS_DIR = os.path.join(os.path.expanduser("~"), ".terminal_standby_ics")
CAL_SRC_FILE = os.path.join(os.path.expanduser("~"), ".terminal_standby_cal_sources.json")
_CAL_LOCK = threading.Lock()
_CAL_EVENTS = []
_CAL_STATUS = ""


def _parse_ics_date(val):
    val = val.split(";")[-1].split(":")[-1].strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _parse_ics(text):
    events = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    unfolded = []
    for line in lines:
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    i, in_ev = 0, False
    start = end = title = None
    while i < len(unfolded):
        line = unfolded[i]
        if line.strip() == "BEGIN:VEVENT":
            in_ev = True; start = end = title = None
        elif line.strip() == "END:VEVENT" and in_ev:
            if start and title:
                events.append((start, end or start, title))
            in_ev = False
        elif in_ev:
            if line.startswith("DTSTART"):
                start = _parse_ics_date(line)
            elif line.startswith("DTEND"):
                end   = _parse_ics_date(line)
            elif line.startswith("SUMMARY"):
                title = line.split(":", 1)[-1].strip()[:50]
        i += 1
    return sorted(events, key=lambda e: e[0])


def _source_id(src):
    return hashlib.sha1(src.encode("utf-8", errors="ignore")).hexdigest()[:12]


def _label_for_source(src):
    s = src.strip()
    if s.lower().startswith(("http://", "https://")):
        try:
            from urllib.parse import urlparse
            p = urlparse(s)
            host = p.netloc or "ical"
            tail = (p.path.rsplit("/", 1)[-1] or "feed.ics")[:24]
            return f"{host}/{tail}"[:42]
        except Exception:
            return s[:42]
    return os.path.basename(s)[:42] or s[:42]


def _load_ics_sources():
    try:
        with open(CAL_SRC_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            clean = []
            for it in data:
                if not isinstance(it, dict):
                    continue
                src = str(it.get("source", "")).strip()
                sid = str(it.get("id", _source_id(src))).strip()
                if not src:
                    continue
                path = it.get("path") or os.path.join(CAL_ICS_DIR, f"{sid}.ics")
                clean.append({
                    "id": sid,
                    "source": src,
                    "label": it.get("label") or _label_for_source(src),
                    "path": path,
                })
            return clean
    except Exception:
        pass
    return []


def _save_ics_sources(srcs):
    try:
        with open(CAL_SRC_FILE, "w", encoding="utf-8") as f:
            json.dump(srcs, f, indent=2)
    except Exception:
        pass


def _ensure_ics_sources_migrated():
    os.makedirs(CAL_ICS_DIR, exist_ok=True)
    if os.path.exists(CAL_SRC_FILE):
        return _load_ics_sources()
    srcs = _load_ics_sources()
    if srcs:
        return srcs
    try:
        if os.path.exists(CAL_ICS) and os.path.getsize(CAL_ICS) > 0:
            sid = "legacy"
            target = os.path.join(CAL_ICS_DIR, f"{sid}.ics")
            try:
                shutil.copyfile(CAL_ICS, target)
            except Exception:
                target = CAL_ICS
            srcs = [{
                "id": sid,
                "source": CAL_ICS,
                "label": "Legacy iCal",
                "path": target,
            }]
            _save_ics_sources(srcs)
    except Exception:
        pass
    return srcs


def _read_ics_source(source):
    s = source.strip()
    if s.lower().startswith(("http://", "https://")):
        import urllib.request
        req = urllib.request.Request(s, headers={"User-Agent": "TerminalStandBy/3"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    with open(s, encoding="utf-8", errors="replace") as f:
        return f.read()


def get_connected_ics_sources():
    return _ensure_ics_sources_migrated()


def get_connected_ics_count():
    return len(get_connected_ics_sources())


def load_calendar_events():
    _ensure_ics_sources_migrated()
    evs = []
    try:
        with open(CAL_FILE) as f:
            for e in json.load(f):
                dt_str = e.get("dt","")
                for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        dt = datetime.datetime.strptime(dt_str, fmt); break
                    except: dt = None
                if dt: evs.append((dt, dt, e.get("title","Event")[:50]))
    except Exception: pass
    for src in _load_ics_sources():
        p = src.get("path", "")
        if not p or not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                evs += _parse_ics(f.read())
        except Exception:
            pass
    return sorted(set(evs), key=lambda e: e[0])


def save_local_events(local_evs):
    try:
        with open(CAL_FILE, "w") as f:
            json.dump(local_evs, f, indent=2)
    except Exception: pass


def refresh_calendar():
    global _CAL_EVENTS, _CAL_STATUS
    evs = load_calendar_events()
    with _CAL_LOCK:
        _CAL_EVENTS = evs
    _CAL_STATUS = f"Loaded {len(evs)} events"


def fetch_ics_url(url, label=None):
    global _CAL_STATUS
    try:
        _CAL_STATUS = "Fetching calendar..."
        source = url.strip()
        data = _read_ics_source(source)
        if "BEGIN:VCALENDAR" not in data:
            _CAL_STATUS = "ERROR: Not a valid ICS file"
            return False, "Not a valid ICS"
        os.makedirs(CAL_ICS_DIR, exist_ok=True)
        srcs = _ensure_ics_sources_migrated()
        sid = _source_id(source)
        out = os.path.join(CAL_ICS_DIR, f"{sid}.ics")
        with open(out, "w", encoding="utf-8") as f:
            f.write(data)
        custom_label = (label or "").strip()
        updated = False
        for s in srcs:
            if s.get("id") == sid or s.get("source") == source:
                s["id"] = sid
                s["source"] = source
                s["label"] = custom_label or s.get("label") or _label_for_source(source)
                s["path"] = out
                updated = True
                break
        if not updated:
            label = custom_label or _label_for_source(source)
            srcs.append({"id": sid, "source": source, "label": label, "path": out})
        _save_ics_sources(srcs)
        refresh_calendar()
        _CAL_STATUS = f"Connected {len(srcs)} calendars · Synced {len(_CAL_EVENTS)} events"
        return True, f"Synced {len(_CAL_EVENTS)} events"
    except Exception as e:
        _CAL_STATUS = f"ERROR: {e}"
        return False, str(e)


def has_connected_ics():
    return get_connected_ics_count() > 0


def disconnect_ics_calendar(source_idx=None, source_id=None):
    global _CAL_STATUS
    try:
        srcs = _ensure_ics_sources_migrated()
        if not srcs:
            _CAL_STATUS = "No connected calendar"
            return False, _CAL_STATUS

        pick = None
        if source_id:
            for s in srcs:
                if s.get("id") == source_id:
                    pick = s
                    break
        elif source_idx is not None and 0 <= source_idx < len(srcs):
            pick = srcs[source_idx]
        else:
            pick = srcs[0]

        if not pick:
            _CAL_STATUS = "No matching calendar source"
            return False, _CAL_STATUS

        new_srcs = [s for s in srcs if s.get("id") != pick.get("id")]
        _save_ics_sources(new_srcs)

        p = pick.get("path", "")
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

        # Remove legacy singleton ICS too, otherwise migration can revive it.
        if pick.get("id") == "legacy" or pick.get("source") == CAL_ICS:
            try:
                if os.path.exists(CAL_ICS):
                    os.remove(CAL_ICS)
            except Exception:
                pass

        refresh_calendar()
        _CAL_STATUS = f"Disconnected: {pick.get('label', 'calendar')}"
        return True, _CAL_STATUS
    except Exception as e:
        _CAL_STATUS = f"ERROR: {e}"
        return False, str(e)


def get_next_event():
    def _add_months(dt, months):
        y = dt.year + (dt.month - 1 + months) // 12
        m = (dt.month - 1 + months) % 12 + 1
        import calendar as _c
        d = min(dt.day, _c.monthrange(y, m)[1])
        return dt.replace(year=y, month=m, day=d)

    def _fmt_remaining(start, now):
        if start <= now:
            return "ongoing"

        months = (start.year - now.year) * 12 + (start.month - now.month)
        anchor = _add_months(now, months)
        if anchor > start:
            months -= 1
            anchor = _add_months(now, months)

        delta = start - anchor
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        parts = []
        if months > 0:
            parts.append(f"{months}mo")
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")

        if not parts:
            if minutes > 0:
                parts.append(f"{minutes}m")
            else:
                parts.append("<1m")

        return "in " + " ".join(parts)

    now = datetime.datetime.now()
    with _CAL_LOCK:
        evs = list(_CAL_EVENTS)
    for start, end, title in evs:
        if start > now:
            ts = f"{start.strftime('%H:%M')}  {title}"
            remaining = _fmt_remaining(start, now)
            return ts[:40], remaining
    for start, end, title in evs:
        if start.date() == now.date() and start <= now:
            return f"{start.strftime('%H:%M')}  {title}"[:40], "ongoing"
    return "No events today", ""


threading.Thread(target=refresh_calendar, daemon=True).start()


CACHE_DIR = os.path.join(os.path.expanduser("~"), ".terminal_standby_cache")
SR = 44100

BUILTIN_TRACKS = [
    {
        "name":     "Brown Noise",
        "artist":   "Focus Aid",
        "source":   "builtin",
        "genre":    "brown",
        "duration": 0,
        "bpm":      60,
        "desc":     "Deep rumble · coding & deep work",
    },
    {
        "name":     "Pink Noise",
        "artist":   "Focus Aid",
        "source":   "builtin",
        "genre":    "pink",
        "duration": 0,
        "bpm":      60,
        "desc":     "Balanced hiss · reading & focus",
    },
    {
        "name":     "White Noise",
        "artist":   "Focus Aid",
        "source":   "builtin",
        "genre":    "white",
        "duration": 0,
        "bpm":      60,
        "desc":     "Bright static · blocking distractions",
    },
    {
        "name":     "Rain on Glass",
        "artist":   "Focus Aid",
        "source":   "builtin",
        "genre":    "rain",
        "duration": 0,
        "bpm":      60,
        "desc":     "Soft rain texture · relaxed focus",
    },
    {
        "name":     "Deep Space Hum",
        "artist":   "Focus Aid",
        "source":   "builtin",
        "genre":    "space",
        "duration": 0,
        "bpm":      40,
        "desc":     "Low frequency drone · meditation",
    },
]


# ── Noise generators ──────────────────────────────────────────────────────────

def _gen_brown(n, state):
    b1 = state.get('b1', 0.0)
    b2 = state.get('b2', 0.0)
    if not state.get('_warmed'):
        for _ in range(8192):
            w  = random.gauss(0, 1.0)
            b1 = b1 * 0.998 + w * 0.002
            b2 = b2 * 0.992 + b1 * 0.008
        state['_warmed'] = True
    out = _array.array('h')
    for _ in range(n):
        w  = random.gauss(0, 1.0)
        b1 = b1 * 0.998 + w * 0.002
        b2 = b2 * 0.992 + b1 * 0.008
        v  = max(-32767, min(32767, int(b2 * 22000)))
        out.append(v)
    state['b1'] = b1
    state['b2'] = b2
    return out.tobytes()

def _gen_pink(n, state):
    b    = state.get('b', [0.0]*7)
    prev = state.get('p', 0.0)
    out  = _array.array('h')
    for _ in range(n):
        w = random.gauss(0, 1.0)
        b[0] = 0.99886*b[0] + w*0.0555179
        b[1] = 0.99332*b[1] + w*0.0750759
        b[2] = 0.96900*b[2] + w*0.1538520
        b[3] = 0.86650*b[3] + w*0.3104856
        b[4] = 0.55000*b[4] + w*0.5329522
        b[5] = -0.7616*b[5] - w*0.0168980
        pink = (b[0]+b[1]+b[2]+b[3]+b[4]+b[5]+b[6]+w*0.5362) * 0.11
        b[6] = w * 0.115926
        prev = prev * 0.85 + pink * 0.15
        v = max(-32767, min(32767, int(prev * 18000)))
        out.append(v)
    state['b'] = b
    state['p'] = prev
    return out.tobytes()

def _gen_white(n, _state):
    out = _array.array('h')
    for _ in range(n):
        v = max(-32767, min(32767, int(random.gauss(0, 1.0) * 10000)))
        out.append(v)
    return out.tobytes()

def _gen_rain(n, state):
    out  = _array.array('h')
    last = state.get('b', 0.0)
    drop_countdown = state.get('dc', 0)
    drop_amp       = state.get('da', 0.0)
    for i in range(n):
        white = random.gauss(0, 1.0)
        last  = last * 0.95 + white * 0.05
        rain  = last * 0.6
        if drop_countdown <= 0:
            drop_amp       = random.uniform(0.2, 0.9)
            drop_countdown = random.randint(SR//20, SR//3)
        else:
            drop_countdown -= 1
        drop  = drop_amp * math.exp(-drop_countdown / (SR * 0.002))
        v = max(-32767, min(32767, int((rain + drop * 0.4) * 18000)))
        out.append(v)
    state['b']  = last
    state['dc'] = drop_countdown
    state['da'] = drop_amp
    return out.tobytes()

def _gen_space(n, state):
    out   = _array.array('h')
    t_off = state.get('t', 0)
    last  = state.get('b', 0.0)
    for i in range(n):
        t     = (t_off + i) / SR
        drone = (0.5 * math.sin(2*math.pi*60*t)
               + 0.3 * math.sin(2*math.pi*60.3*t)
               + 0.15* math.sin(2*math.pi*90*t)
               + 0.1 * math.sin(2*math.pi*120*t))
        white = random.gauss(0, 1.0)
        last  = last * 0.999 + white * 0.001
        mix   = drone * 0.7 + last * 0.3
        v = max(-32767, min(32767, int(mix * 14000)))
        out.append(v)
    state['t'] = t_off + n
    state['b'] = last
    return out.tobytes()

_GENERATORS = {
    "brown": _gen_brown,
    "pink":  _gen_pink,
    "white": _gen_white,
    "rain":  _gen_rain,
    "space": _gen_space,
}


# ── Library persistence ───────────────────────────────────────────────────────

def load_library():
    try:
        with open(LIBRARY_FILE) as f:
            user = json.load(f)
    except Exception:
        user = []
    return list(BUILTIN_TRACKS) + user

def save_library(tracks):
    user = [t for t in tracks if t.get("source") != "builtin"]
    try:
        os.makedirs(os.path.dirname(LIBRARY_FILE), exist_ok=True)
        with open(LIBRARY_FILE, "w") as f:
            json.dump(user, f, indent=2)
    except Exception:
        pass

def get_audio_info(path):
    try:
        r = subprocess.run(
            ["ffprobe","-v","quiet","-print_format","json",
             "-show_format","-show_streams", path],
            capture_output=True, text=True, timeout=10)
        data = json.loads(r.stdout)
        fmt  = data.get("format", {})
        tags = fmt.get("tags", {})
        dur  = float(fmt.get("duration", 0))
        title  = (tags.get("title") or tags.get("Title") or
                  os.path.splitext(os.path.basename(path))[0])[:40]
        artist = (tags.get("artist") or tags.get("Artist") or
                  tags.get("album_artist") or "Unknown")[:30]
        return title, artist, dur
    except Exception:
        name = os.path.splitext(os.path.basename(path))[0]
        return name[:40], "Unknown", 0.0

def yt_dlp_available():
    try: import yt_dlp; return True
    except ImportError: return shutil.which("yt-dlp") is not None

def install_yt_dlp():
    try:
        subprocess.check_call([sys.executable,"-m","pip","install","yt-dlp","-q"], timeout=90)
        return True
    except Exception:
        return False

def resolve_youtube(url):
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        import yt_dlp
        ydl_opts: Any = {
            "format":         "bestaudio/best",
            "outtmpl":        os.path.join(CACHE_DIR, "%(id)s.%(ext)s"),
            "quiet":          True,
            "no_warnings":    True,
            "postprocessors": [{"key":"FFmpegExtractAudio",
                                "preferredcodec":"mp3",
                                "preferredquality":"192"}],
        }
        with yt_dlp.YoutubeDL(cast(Any, ydl_opts)) as ydl:
            info = ydl.extract_info(url, download=True) or {}
            if not isinstance(info, dict):
                return None
            title  = (info.get("title") or "Unknown")[:40]
            artist = (info.get("uploader") or info.get("channel") or "YouTube")[:30]
            vid_id = info.get("id","unknown")
            path   = os.path.join(CACHE_DIR, f"{vid_id}.mp3")
            dur    = float(info.get("duration") or 0)
            if os.path.exists(path):
                return title, artist, path, dur
    except Exception:
        pass
    if shutil.which("yt-dlp"):
        try:
            out_tmpl = os.path.join(CACHE_DIR, "%(id)s.%(ext)s")
            r = subprocess.run(
                ["yt-dlp","-x","--audio-format","mp3","--audio-quality","192K",
                 "-o", out_tmpl, "--print","id", "--print","title",
                 "--print","uploader", "--print","duration", url],
                capture_output=True, text=True, timeout=180)
            lines = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
            if lines:
                vid_id = lines[0]
                title  = lines[1] if len(lines)>1 else "Unknown"
                artist = lines[2] if len(lines)>2 else "YouTube"
                dur    = float(lines[3]) if len(lines)>3 else 0.0
                path   = os.path.join(CACHE_DIR, f"{vid_id}.mp3")
                if os.path.exists(path):
                    return title[:40], artist[:30], path, dur
        except Exception:
            pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class AudioEngine:
    CHUNK = SR // 8

    def __init__(self):
        self.library    = load_library()
        self.track_idx  = 0
        self.playing    = False
        self.elapsed    = 0.0
        self.shuffle    = False
        self.repeat     = False
        self._lock      = threading.Lock()
        self._wall      = time.time()
        self._play_gen  = 0
        self._proc      = None
        self._active_pids = set()
        self.status_msg = ""
        self._spec_t    = 0.0
        self._backend   = self._detect()
        if self._backend != "sounddevice":
            threading.Thread(target=self._try_install_sd, daemon=True).start()

    def _track_proc(self, proc):
        if not proc:
            return
        with self._lock:
            self._proc = proc
            try:
                self._active_pids.add(int(proc.pid))
            except Exception:
                pass

    def _untrack_proc(self, proc):
        with self._lock:
            if self._proc is proc:
                self._proc = None
            try:
                self._active_pids.discard(int(proc.pid))
            except Exception:
                pass

    def _try_install_sd(self):
        try:
            import sounddevice
            self._backend = "sounddevice"
            return
        except ImportError:
            pass
        try:
            self.status_msg = "Installing audio engine (one-time)..."
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "sounddevice", "-q"],
                timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import sounddevice
            self._backend   = "sounddevice"
            self.status_msg = ""
        except Exception:
            self.status_msg = ""

    def _detect(self):
        try:
            import sounddevice
            return "sounddevice"
        except Exception:
            pass
        for cmd in ("ffplay", "afplay", "mpv", "mplayer", "aplay"):
            if shutil.which(cmd):
                return cmd
        if platform.system() == "Windows":
            for p in [
                os.path.join(os.environ.get("LOCALAPPDATA",""),  "ffmpeg","bin","ffplay.exe"),
                os.path.join(os.environ.get("USERPROFILE",""),   "ffmpeg","bin","ffplay.exe"),
                "C:/ffmpeg/bin/ffplay.exe",
                "C:/Program Files/ffmpeg/bin/ffplay.exe",
            ]:
                if os.path.isfile(p):
                    return p
            try:
                import winsound
                return "winsound"
            except ImportError:
                pass
        return None

    @staticmethod
    def _ensure_sounddevice():
        try:
            import sounddevice
            return True
        except Exception:
            pass
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "sounddevice", "-q"],
                timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import sounddevice
            return True
        except Exception:
            return False

    def get_spectrum(self, n=32):
        if not self.playing:
            return [0.0]*n
        trk   = self.current
        genre = trk.get("genre","")
        t     = self.elapsed
        out   = []
        for b in range(n):
            frac = b / max(1, n-1)
            if genre == "brown":
                v = math.exp(-frac * 5.0) * (0.7 + 0.3*math.sin(t*1.3+b*0.5))
            elif genre == "pink":
                v = (1.0-frac*0.7) * (0.5 + 0.4*math.sin(t*0.9+b*0.3))
            elif genre == "white":
                v = 0.5 + 0.4*math.sin(t*2.1*frac+b)
            elif genre == "rain":
                base = math.exp(-((frac-0.35)**2)/0.08)
                drop = 0.6*math.exp(-((frac-0.8)**2)/0.02)*abs(math.sin(t*7.3))
                v = base*0.6 + drop
            elif genre == "space":
                v = math.exp(-frac*8)*(0.8+0.2*math.sin(t*0.3+frac*3))
                v += 0.15*math.exp(-((frac-0.1)**2)/0.01)*abs(math.sin(t*0.7))
            else:
                bpm  = trk.get("bpm", 90)
                beat = 60.0 / bpm
                kick = math.exp(-(t % beat)/beat*8)*0.8
                v = (0.4+0.4*kick)*math.exp(-frac*3)
                v += 0.2*abs(math.sin(t*frac*2+b*0.5))
            v += random.uniform(-0.04, 0.04)
            out.append(min(1.0, max(0.0, v)))
        return out

    def _new_gen(self):
        with self._lock:
            self._play_gen += 1
            return self._play_gen

    def _spawn(self):
        with self._lock:
            gen   = self._play_gen
            idx   = self.track_idx
            start = self.elapsed
        threading.Thread(target=self._play_thread,
                         args=(gen, idx, start), daemon=True).start()

    def _alive(self, gen):
        with self._lock:
            return gen == self._play_gen

    def _play_thread(self, gen, idx, start_sec):
        trk = self.library[idx] if idx < len(self.library) else BUILTIN_TRACKS[0]
        if trk.get("source") == "builtin":
            self._play_builtin(gen, trk, start_sec)
        else:
            self._play_file(gen, trk["source"], start_sec, trk.get("duration", 0))
        if not self._alive(gen):
            return
        with self._lock:
            trk2 = self.library[self.track_idx] if self.track_idx < len(self.library) else {}
            is_inf = (trk2.get("duration") or 0) == 0
        if is_inf:
            if self.playing:
                with self._lock:
                    self.elapsed = 0.0
                    self._wall   = time.time()
                self._spawn()
        else:
            with self._lock:
                if self.repeat:
                    self.elapsed = 0.0
                elif self.shuffle:
                    self.track_idx = random.randint(0, len(self.library)-1)
                    self.elapsed   = 0.0
                else:
                    self.track_idx = (self.track_idx+1) % len(self.library)
                    self.elapsed   = 0.0
                self._wall = time.time()
            if self.playing:
                self._spawn()

    def _play_builtin(self, gen, trk, start_sec):
        genre = trk.get("genre", "brown")
        genfn = _GENERATORS.get(genre, _gen_brown)
        state = {}
        skip = int(start_sec * SR / self.CHUNK)
        for _ in range(skip):
            if not self._alive(gen): return
            genfn(self.CHUNK, state)

        b = self._backend or ""
        if b == "sounddevice":
            self._stream_sounddevice(gen, genfn, state)
        elif b in ("ffplay","aplay") or (os.path.isfile(b) and "ffplay" in b.lower()):
            self._stream_pipe(gen, genfn, state)
        else:
            self._stream_wav_segments(gen, genfn, state)

    def _stream_sounddevice(self, gen, genfn, state):
        try:
            import sounddevice as sd
        except ImportError:
            self._stream_pipe(gen, genfn, state)
            return
        try:
            with sd.RawOutputStream(samplerate=SR, channels=1,
                                    dtype='int16', blocksize=self.CHUNK) as stream:
                while self._alive(gen):
                    chunk = genfn(self.CHUNK, state)
                    stream.write(chunk)
        except Exception as e:
            err = str(e).lower()
            if "invalid device" in err or "no default" in err or "device unavailable" in err:
                self._stream_pipe(gen, genfn, state)
            elif self._alive(gen):
                self._stream_pipe(gen, genfn, state)

    def _stream_pipe(self, gen, genfn, state):
        b = self._backend or ""
        ffplay_bin = None
        if b == "ffplay" or (os.path.isfile(b) and "ffplay" in b.lower()):
            ffplay_bin = b
        elif b == "afplay":
            ffplay_bin = shutil.which("ffplay")
        if ffplay_bin:
            cmd = [ffplay_bin, "-f","s16le","-ar",str(SR),"-ac","1",
                   "-nodisp","-loglevel","quiet","-autoexit","-"]
        elif b == "aplay":
            cmd = ["aplay","-f","S16_LE","-r",str(SR),"-c","1","--quiet"]
        else:
            self._stream_wav_segments(gen, genfn, state)
            return
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            self._track_proc(proc)
            while self._alive(gen):
                try:
                    pipe = proc.stdin
                    if pipe is None:
                        break
                    pipe.write(genfn(self.CHUNK, state))
                    pipe.flush()
                except (BrokenPipeError, OSError):
                    break
                time.sleep(self.CHUNK / SR * 0.5)
        except Exception:
            pass
        finally:
            try:
                pipe = proc.stdin
                if pipe is not None:
                    pipe.close()
            except:
                pass
            try: proc.wait(timeout=2)
            except: proc.terminate()
            self._untrack_proc(proc)

    def _stream_wav_segments(self, gen, genfn, state):
        import tempfile, wave as wv
        SEG  = 30
        SR_W = 22050 if self._backend == "winsound" else SR
        dec  = SR // SR_W

        while self._alive(gen):
            raw = genfn(SEG * SR, state)
            if dec > 1:
                import array as _a
                s = _a.array('h', raw)
                raw = _a.array('h', [s[i] for i in range(0, len(s), dec)]).tobytes()

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                with wv.open(tmp.name, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR_W)
                    wf.writeframes(raw)
            except Exception:
                try: os.unlink(tmp.name)
                except: pass
                time.sleep(0.5)
                continue

            try:
                b = self._backend
                if b == "afplay":
                    proc = subprocess.Popen(["afplay", tmp.name],
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
                    self._track_proc(proc)
                    while proc.poll() is None:
                        if not self._alive(gen): proc.terminate(); return
                        time.sleep(0.05)
                elif b == "winsound":
                    import winsound
                    done = threading.Event()
                    wav  = tmp.name
                    def _play(p=wav, e=done):
                        try: winsound.PlaySound(p, winsound.SND_FILENAME)
                        except: pass
                        finally: e.set()
                    threading.Thread(target=_play, daemon=True).start()
                    while not done.wait(0.1):
                        if not self._alive(gen):
                            try: winsound.PlaySound(None, winsound.SND_PURGE)
                            except: pass
                            done.wait(1.0)
                            return
                else:
                    time.sleep(SEG)
            finally:
                try: os.unlink(tmp.name)
                except: pass

    def _play_file(self, gen, path, start_sec, duration):
        b  = self._backend or ""
        ss = str(int(start_sec))

        ffplay_bin = None
        if b == "ffplay" or (os.path.isfile(b) and "ffplay" in b.lower()):
            ffplay_bin = b
        elif b == "sounddevice":
            ffplay_bin = shutil.which("ffplay")

        try:
            if ffplay_bin:
                cmd = [ffplay_bin, "-nodisp","-loglevel","quiet","-ss",ss, path]
            elif b == "afplay":
                cmd = ["afplay", path]
            elif b in ("mpv","mplayer"):
                cmd = [b, "--no-video" if b=="mpv" else "-nogui",
                       "--really-quiet" if b=="mpv" else "-really-quiet",
                       f"--start={ss}" if b=="mpv" else "-ss", path]
            elif b == "aplay":
                cmd = ["ffplay","-nodisp","-loglevel","quiet","-ss",ss, path]
            elif b == "winsound":
                self._play_win_winsound(gen, path, duration - start_sec); return
            elif shutil.which("powershell"):
                self._play_win_ps(gen, path); return
            else:
                return

            proc = subprocess.Popen(cmd,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            self._track_proc(proc)
            while proc.poll() is None:
                if not self._alive(gen): proc.terminate(); break
                time.sleep(0.05)
            self._untrack_proc(proc)
        except Exception:
            pass

    def _play_win_winsound(self, gen, path, remaining):
        import winsound, tempfile, wave as wv
        wav_path = path; cleanup = False
        if not path.lower().endswith(".wav"):
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg:
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                wav_path = tmp.name; tmp.close(); cleanup = True
                try:
                    subprocess.run([ffmpeg,"-y","-i",path,"-ar","22050",
                                    "-ac","1","-f","wav", wav_path],
                                   capture_output=True, timeout=30)
                except Exception:
                    try: os.unlink(wav_path)
                    except: pass
                    return
            else:
                return
        try:
            done = threading.Event()
            def _pl(p=wav_path, e=done):
                try: winsound.PlaySound(p, winsound.SND_FILENAME)
                except: pass
                finally: e.set()
            threading.Thread(target=_pl, daemon=True).start()
            while not done.wait(0.1):
                if not self._alive(gen):
                    try: winsound.PlaySound(None, winsound.SND_PURGE)
                    except: pass
                    done.wait(1.0); return
        finally:
            if cleanup:
                try: os.unlink(wav_path)
                except: pass

    def _play_win_ps(self, gen, path):
        try:
            uri = path.replace("\\", "/")
            script = (
                "Add-Type -AssemblyName presentationCore;"
                "$m=[System.Windows.Media.MediaPlayer]::new();"
                "$m.Open([Uri]::new('" + uri + "'));$m.Play();"
                "Start-Sleep -Seconds 3600"
            )
            proc = subprocess.Popen(
                ["powershell","-NoProfile","-NonInteractive","-Command",script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._track_proc(proc)
            while proc.poll() is None:
                if not self._alive(gen): proc.terminate(); break
                time.sleep(0.1)
            self._untrack_proc(proc)
        except Exception:
            pass

    def _kill(self):
        self._new_gen()
        with self._lock:
            proc = self._proc
            self._proc = None
            pids = list(self._active_pids)
            self._active_pids.clear()
        if proc and getattr(proc, "pid", None):
            if int(proc.pid) not in pids:
                pids.append(int(proc.pid))

        if platform.system() == "Windows":
            for pid in pids:
                try:
                    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                                   capture_output=True, timeout=5)
                except Exception:
                    pass
        else:
            for pid in pids:
                try:
                    os.kill(pid, 15)
                except Exception:
                    pass
        if platform.system() == "Windows":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except: pass

    def toggle_play(self):
        with self._lock:
            self.playing = not self.playing
            self._wall   = time.time()
        if not self.playing:
            self._kill()
        else:
            self._spawn()

    def next_track(self):
        self._kill()
        with self._lock:
            n = len(self.library)
            self.track_idx = (random.randint(0,n-1) if self.shuffle
                              else (self.track_idx+1) % n)
            self.elapsed = 0.0
            self._wall   = time.time()
        if self.playing:
            self._spawn()

    def prev_track(self):
        self._kill()
        with self._lock:
            n = len(self.library)
            self.track_idx = (self.track_idx-1) % n
            self.elapsed = 0.0
            self._wall   = time.time()
        if self.playing:
            self._spawn()

    def play_index(self, idx):
        self._kill()
        with self._lock:
            self.track_idx = idx % len(self.library)
            self.elapsed   = 0.0
            self._wall     = time.time()
            self.playing   = True
        self._spawn()

    def add_file(self, path):
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return False, "File not found"
        title, artist, dur = get_audio_info(path)
        entry = {"name":title,"artist":artist,"source":path,
                 "duration":dur,"bpm":90}
        self.library.append(entry)
        save_library(self.library)
        return True, f"Added: {title}"

    def add_youtube(self, url):
        def _worker():
            self.status_msg = "Checking yt-dlp..."
            if not yt_dlp_available():
                self.status_msg = "Installing yt-dlp (one-time setup)..."
                if not install_yt_dlp():
                    self.status_msg = "ERROR: pip install yt-dlp failed — try manually"
                    return
            self.status_msg = "Downloading audio from YouTube..."
            result = resolve_youtube(url)
            if result is None:
                self.status_msg = "ERROR: Download failed — check URL & internet"
                return
            title, artist, path, dur = result
            entry = {"name":title,"artist":artist,"source":path,
                     "duration":dur,"bpm":90}
            self.library.append(entry)
            save_library(self.library)
            self.status_msg = f"Added: {title[:35]}"
        threading.Thread(target=_worker, daemon=True).start()

    def remove_track(self, idx):
        if idx < len(BUILTIN_TRACKS):
            return False, "Cannot remove built-in tracks"
        if idx >= len(self.library):
            return False, "Invalid index"
        name = self.library[idx]["name"]
        self.library.pop(idx)
        if self.track_idx >= len(self.library):
            self.track_idx = max(0, len(self.library)-1)
        save_library(self.library)
        return True, f"Removed: {name}"

    def tick(self):
        now = time.time()
        with self._lock:
            dt         = now - self._wall
            self._wall = now
            if not self.playing:
                return
            trk = self.library[self.track_idx]
            dur = float(trk.get("duration") or 0)
            if dur > 0:
                self.elapsed = min(self.elapsed + dt, dur)
            else:
                self.elapsed += dt

    @property
    def current(self):
        if not self.library:
            return BUILTIN_TRACKS[0]
        return self.library[self.track_idx]




# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO PLAYER
# ══════════════════════════════════════════════════════════════════════════════
class VideoPlayer:
    def __init__(self):
        self.playing     = False
        self.title       = ""
        self.status      = ""
        self.in_terminal = False
        self.prefer_ascii = False
        self.ascii_mode   = False
        self._proc       = None
        self._lock       = threading.Lock()
        self._renderer   = None
        self._installing = False
        self._tct_checked = False
        self._tct_supported = False
        self._ascii_frame = []
        self._ascii_lock  = threading.Lock()
        self._ascii_stop  = threading.Event()
        self._ascii_thread = None
        self._ascii_cols  = 90
        self._ascii_rows  = 26
        threading.Thread(target=self._setup, daemon=True).start()

    def set_ascii_viewport(self, cols, rows):
        with self._ascii_lock:
            # Cap preview size so fullscreen terminals do not produce oversized ASCII frames.
            self._ascii_cols = max(24, min(168, int(cols)))
            self._ascii_rows = max(8, min(56, int(rows)))

    def get_ascii_frame(self):
        with self._ascii_lock:
            return list(self._ascii_frame)

    def _ascii_available(self):
        try:
            import cv2  # noqa: F401
            return True
        except Exception:
            return False

    def _play_ascii(self, source, title=""):
        if not self._ascii_available():
            self.status = "ASCII mode needs OpenCV: pip install opencv-python"
            self.playing = False
            return False

        self._ascii_stop.clear()
        self.ascii_mode = True
        self.title = title or os.path.basename(source)[:40]
        self.status = f"playing ASCII (no audio) — {self.title}"

        def _runner():
            try:
                import cv2
                chars = " .:-=+*#%@"
                cap = cv2.VideoCapture(source)
                if not cap or not cap.isOpened():
                    self.status = "ASCII: could not open source"
                    self.playing = False
                    self.ascii_mode = False
                    return

                fps = cap.get(cv2.CAP_PROP_FPS)
                if not fps or fps <= 0 or fps > 120:
                    fps = 24.0
                delay = 1.0 / fps

                with self._lock:
                    self.playing = True

                while not self._ascii_stop.is_set():
                    ok, frame = cap.read()
                    if not ok:
                        break

                    with self._ascii_lock:
                        cols = self._ascii_cols
                        rows = self._ascii_rows

                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    src_h, src_w = gray.shape[:2]
                    src_aspect = src_w / max(1, src_h)
                    # Typical terminal glyph cells are taller than wide.
                    char_aspect = 0.5

                    target_w = max(24, cols)
                    target_h = max(8, int(target_w / max(0.1, src_aspect * char_aspect)))
                    if target_h > rows:
                        target_h = max(8, rows)
                        target_w = max(24, int(src_aspect * target_h * char_aspect))

                    target_w = min(target_w, cols)
                    target_h = min(target_h, rows)
                    small = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)

                    lines = []
                    for r in small:
                        line = "".join(chars[min(len(chars)-1, int(px * (len(chars)-1) / 255))] for px in r)
                        lines.append(line)

                    with self._ascii_lock:
                        self._ascii_frame = lines

                    time.sleep(delay)

                cap.release()
                if self._ascii_stop.is_set():
                    self.status = "stopped"
                else:
                    self.status = f"finished — {self.title}"
            except Exception as e:
                self.status = f"ASCII error: {str(e)[:50]}"
            finally:
                with self._lock:
                    self.playing = False
                self.ascii_mode = False
                with self._ascii_lock:
                    self._ascii_frame = []

        self._ascii_thread = threading.Thread(target=_runner, daemon=True)
        self._ascii_thread.start()
        return True

    def _setup(self):
        r = self._find_mpv()
        if r:
            self._renderer = r
            self.status = ""
            return
        fp = self._find_ffplay()
        if fp:
            self._renderer = fp
            self.status = "using ffplay (install mpv for better quality)"
            return
        self._auto_install_mpv()

    def _re_detect(self):
        r = self._find_mpv() or self._find_ffplay()
        if r:
            self._renderer = r
            self.status = ""

    def _find_mpv(self):
        p = shutil.which("mpv")
        if p: return p
        if platform.system() == "Windows":
            for candidate in [
                r"C:\Program Files\MPV Player\mpv.exe",
                r"C:\Program Files (x86)\MPV Player\mpv.exe",
                os.path.join(os.environ.get("LOCALAPPDATA",""), "Programs","mpv","mpv.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA",""), "mpv","mpv.exe"),
                r"C:\mpv\mpv.exe",
                r"C:\Program Files\mpv\mpv.exe",
                r"C:\Program Files (x86)\mpv\mpv.exe",
            ]:
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _check_tct_support(self, mpv_path):
        if self._tct_checked:
            return self._tct_supported
        try:
            r = subprocess.run([mpv_path, "--vo=help"],
                               capture_output=True, text=True, timeout=5)
            txt = ((r.stdout or "") + "\n" + (r.stderr or "")).lower()
            self._tct_supported = "tct" in txt
        except Exception:
            self._tct_supported = False
        self._tct_checked = True
        return self._tct_supported

    def _find_ffplay(self):
        p = shutil.which("ffplay")
        if p: return p
        if platform.system() == "Windows":
            local = os.environ.get("LOCALAPPDATA","")
            user  = os.environ.get("USERPROFILE","")
            for candidate in [
                os.path.join(local,  "ffmpeg", "bin", "ffplay.exe"),
                os.path.join(user,   "ffmpeg", "bin", "ffplay.exe"),
                r"C:\ffmpeg\bin\ffplay.exe",
                r"C:\Program Files\ffmpeg\bin\ffplay.exe",
                r"C:\Program Files (x86)\ffmpeg\bin\ffplay.exe",
                os.path.join(local, "Programs", "ffmpeg", "bin", "ffplay.exe"),
            ]:
                if os.path.isfile(candidate): return candidate
        return None

    def _auto_install_mpv(self):
        sys_name = platform.system()
        self._installing = True
        self.status = "installing mpv..."
        try:
            if sys_name == "Windows":
                if shutil.which("winget"):
                    subprocess.run(
                        ["winget", "install", "--id", "mpv.mpv",
                         "--silent", "--accept-package-agreements",
                         "--accept-source-agreements"],
                        capture_output=True, timeout=120)
                    r = self._find_mpv()
                    if r:
                        self._renderer = r
                        self.status = "mpv installed"
                        return
                self._download_mpv_windows()
            elif sys_name == "Darwin":
                if shutil.which("brew"):
                    subprocess.run(["brew", "install", "mpv"],
                                   capture_output=True, timeout=180)
                    r = self._find_mpv()
                    if r:
                        self._renderer = r
                        self.status = "mpv installed via brew"
                        return
            elif sys_name == "Linux":
                for mgr, cmd in [
                    ("apt-get",  ["sudo","apt-get","install","-y","mpv"]),
                    ("dnf",      ["sudo","dnf","install","-y","mpv"]),
                    ("pacman",   ["sudo","pacman","-S","--noconfirm","mpv"]),
                    ("zypper",   ["sudo","zypper","install","-y","mpv"]),
                ]:
                    if shutil.which(mgr):
                        subprocess.run(cmd, capture_output=True, timeout=120)
                        r = self._find_mpv()
                        if r:
                            self._renderer = r
                            self.status = f"mpv installed via {mgr}"
                            return
                        break
        except Exception as e:
            self.status = f"auto-install failed: {e} — install mpv manually"
        finally:
            self._installing = False
        if not self._renderer:
            fp = self._find_ffplay()
            if fp:
                self._renderer = fp
                self.status = "mpv unavailable — using ffplay"
            else:
                self.status = "no player found — install mpv manually"

    def _download_mpv_windows(self):
        try:
            import urllib.request, zipfile, io
            self.status = "finding latest mpv release..."
            api_url2 = "https://api.github.com/repos/zhongfly/mpv-winbuild/releases/latest"
            try:
                req = urllib.request.Request(api_url2,
                    headers={"User-Agent": "terminal-standby/1"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                asset_url = None
                for asset in data.get("assets", []):
                    n = asset.get("name","")
                    if "x86_64" in n and n.endswith(".zip") and "mpv" in n:
                        asset_url = asset["browser_download_url"]
                        break
            except Exception:
                asset_url = None

            if not asset_url:
                self.status = "visit mpv.io/installation to install mpv manually"
                return

            self.status = "downloading mpv (~15 MB)..."
            req = urllib.request.Request(asset_url,
                headers={"User-Agent": "terminal-standby/1"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                zip_data = resp.read()

            install_dir = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "mpv")
            os.makedirs(install_dir, exist_ok=True)
            self.status = "extracting mpv..."
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                for member in zf.namelist():
                    if member.endswith("mpv.exe") or member.endswith("mpv.com"):
                        basename = os.path.basename(member)
                        dest = os.path.join(install_dir, basename)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            dst.write(src.read())

            mpv_exe = os.path.join(install_dir, 'mpv.exe')
            if os.path.isfile(mpv_exe):
                self._renderer = mpv_exe
                self.status = "mpv installed to " + install_dir
            else:
                self.status = "extraction done but mpv.exe not found — install manually"
        except Exception as e:
            self.status = f"download failed: {e} — visit mpv.io/installation"

    def _ensure_ytdlp(self):
        try:
            import yt_dlp
            return True
        except ImportError:
            pass
        try:
            self.status = "installing yt-dlp..."
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "yt-dlp", "-q"],
                timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import yt_dlp
            return True
        except Exception:
            return False

    def play(self, source, title=""):
        self.stop()
        self.title  = title or os.path.basename(source)[:40]
        self.status = "loading..."

        def _run():
            for _ in range(80):
                if self._renderer or not self._installing: break
                time.sleep(0.1)
            renderer = self._renderer
            if not renderer:
                self.status = ("still installing player..." if self._installing
                               else "no player found — see VIDEO view for install help")
                self.playing = False
                return
            try:
                term_mode = bool(self.in_terminal)
                # Terminal rendering needs mpv. If we're on ffplay, try to switch.
                if term_mode and renderer:
                    base = os.path.basename(renderer).lower()
                    if "mpv" not in base:
                        mpv = self._find_mpv()
                        if mpv:
                            self._renderer = mpv
                            renderer = mpv
                        else:
                            if not self._installing:
                                threading.Thread(target=self._auto_install_mpv, daemon=True).start()
                            self.status = "terminal mode needs mpv; installing/looking for mpv..."
                            self.playing = False
                            return
                is_mpv = "mpv" in os.path.basename(renderer).lower()
                if is_mpv:
                    if term_mode:
                        if self.prefer_ascii:
                            if self._play_ascii(source, self.title):
                                return
                        if not self._check_tct_support(renderer):
                            if self._play_ascii(source, self.title):
                                self.status = f"ASCII fallback (mpv tct unavailable) — {self.title}"
                                return
                            self.status = "terminal mode unsupported: mpv build has no vo=tct"
                            self.playing = False
                            return
                        cmd = [renderer, "--no-config", "--vo=tct", "--force-window=no",
                               "--really-quiet", source]
                    elif platform.system() == "Windows":
                        cmd = [renderer, "--really-quiet", source]
                    else:
                        cmd = [renderer, "--vo=tct", "--really-quiet", source]
                else:
                    if term_mode:
                        if self._play_ascii(source, self.title):
                            self.status = f"ASCII fallback (ffplay cannot render in terminal) — {self.title}"
                            return
                        self.status = "terminal mode requires mpv (ffplay cannot render in this terminal)"
                        self.playing = False
                        return
                    ffplay_path = renderer if os.path.isfile(renderer) else shutil.which(renderer) or renderer
                    cmd = [ffplay_path, "-loglevel", "quiet", "-autoexit", source]

                self.status = f"launching player..."
                # In terminal mode we must inherit stdout/stderr so tct frames are visible.
                if term_mode:
                    proc = subprocess.Popen(cmd)
                else:
                    proc = subprocess.Popen(cmd,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
                with self._lock:
                    self._proc   = proc
                    self.playing = True
                    self.status  = f"playing — {self.title}"
                proc.wait()
                with self._lock:
                    self.playing = False
                    self._proc   = None
                    self.status  = f"finished — {self.title}"
                    self.title   = ""
            except FileNotFoundError:
                self.status  = f"player executable not found: {renderer}"
                self._renderer = None
                threading.Thread(target=self._setup, daemon=True).start()
            except Exception as e:
                self.status  = f"error: {e}"
                self.playing = False

        threading.Thread(target=_run, daemon=True).start()

    def play_youtube(self, url):
        if not self._renderer and not self._installing:
            threading.Thread(target=self._setup, daemon=True).start()

        self.status = "fetching stream info..."

        def _stream():
            try:
                if not self._ensure_ytdlp():
                    self.status = "yt-dlp unavailable — pip install yt-dlp"
                    return

                import yt_dlp

                ydl_opts: Any = {
                    "quiet":       True,
                    "no_warnings": True,
                    "format":      "best[height<=480]/bestvideo[height<=480]+bestaudio/best",
                    "noplaylist":  True,
                }
                with yt_dlp.YoutubeDL(cast(Any, ydl_opts)) as ydl:
                    info = ydl.extract_info(url, download=False) or {}

                if not isinstance(info, dict):
                    self.status = "could not parse video info"
                    return

                if not info:
                    self.status = "could not fetch video info"
                    return

                title      = (info.get("title") or "YouTube Video")[:40]
                stream_url = info.get("url") or info.get("manifest_url", "")

                if not stream_url and info.get("formats"):
                    fmts = list(info.get("formats") or [])
                    good = [f for f in fmts
                            if f.get("acodec","none") != "none"
                            and (f.get("height") or 999) <= 480]
                    if not good:
                        good = [f for f in fmts if f.get("acodec","none") != "none"]
                    if not good:
                        good = fmts
                    best = sorted(good, key=lambda f: f.get("height") or 0)[-1]
                    stream_url = best.get("url","")

                if not stream_url:
                    self.status = "no playable stream URL found"
                    return

                self.play(stream_url, title)

            except Exception as e:
                err = str(e)
                if "WinError" in err or "FileNotFoundError" in err:
                    self.status = "yt-dlp internal error — try: pip install -U yt-dlp"
                elif "Sign in" in err or "bot" in err.lower():
                    self.status = "YouTube blocked request — try again or use a file"
                elif "unavailable" in err.lower():
                    self.status = "video unavailable in your region"
                else:
                    self.status = f"error: {err[:60]}"

        threading.Thread(target=_stream, daemon=True).start()

    def stop(self):
        self._ascii_stop.set()
        with self._lock:
            proc = self._proc
            self._proc   = None
            self.playing = False
        if proc:
            try:
                if platform.system() == "Windows":
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   capture_output=True, timeout=5)
                else:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except Exception:
                        proc.kill()
            except Exception:
                pass
        self.ascii_mode = False
        with self._ascii_lock:
            self._ascii_frame = []
        self.title = ""
        self.status = ""

    def toggle_terminal_mode(self):
        self.in_terminal = not self.in_terminal
        if self.in_terminal:
            mpv = self._find_mpv()
            if mpv:
                self._renderer = mpv
                self.status = "terminal mode enabled (mpv)"
            else:
                if not self._installing:
                    threading.Thread(target=self._auto_install_mpv, daemon=True).start()
                self.status = "terminal mode enabled; searching/installing mpv..."
        elif self.status.startswith("terminal mode"):
            self.status = ""
        return self.in_terminal

    def toggle_ascii_preference(self):
        self.prefer_ascii = not self.prefer_ascii
        return self.prefer_ascii

    def has_renderer(self): return self._renderer is not None
    def renderer_name(self):
        if self._installing: return "installing..."
        if not self._renderer: return "none"
        return os.path.basename(self._renderer)


VIDEO = VideoPlayer()
atexit.register(VIDEO.stop)
AUDIO = AudioEngine()
atexit.register(AUDIO._kill)

# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM DATA  –  FIXED VERSION
# ══════════════════════════════════════════════════════════════════════════════
class SysData:
    def __init__(self):
        self._lock     = threading.Lock()
        self.bat_pct   = 100;  self.bat_plug  = True
        self.cpu       = 0.0;  self.mem_pct   = 0.0
        self.mem_used  = 0.0;  self.mem_total = 0.0
        self.disk_pct  = 0.0;  self.net_dn    = 0.0;  self.net_up = 0.0
        self.hostname  = socket.gethostname()
        self.os_str    = self._os()
        self.kernel    = self._kernel()
        self.cpu_name  = self._cpu()
        self.gpu_name  = self._gpu()
        self.uptime    = 0
        self.ssid      = self._ssid()
        self.local_ip  = self._local_ip()
        self.cpu_cores = os.cpu_count() or 1
        self.shell     = self._shell()
        self.de_wm     = self._de_wm()
        self.resolution = "N/A"
        self._pnet     = None
        self._boot     = psutil.boot_time() if HAS_PSUTIL else time.time()
        self.devices       = []
        self._dev_last     = 0.0
        self._dev_scanning = False
        # Package count + resolution cached separately (slow)
        self.pkg_count = "…"
        threading.Thread(target=self._fetch_pkg_count, daemon=True).start()
        threading.Thread(target=self._fetch_resolution, daemon=True).start()

    @staticmethod
    def _os():
        s = platform.system()
        if s == "Darwin":
            v = platform.mac_ver()[0]; return f"macOS {v}"
        if s == "Windows":
            # Detect Windows 10 vs 11 + edition (Home/Pro/etc.) from registry
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                build    = int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
                edition  = winreg.QueryValueEx(key, "EditionID")[0]          # "Core" = Home
                ubr      = winreg.QueryValueEx(key, "UBR")[0]                # update build rev
                winreg.CloseKey(key)
                ver   = "11" if build >= 22000 else "10"
                # EditionID: "Core"=Home, "Professional"=Pro, "Enterprise", etc.
                ed    = {"Core": "Home", "CoreN": "Home N",
                         "Professional": "Pro", "ProfessionalN": "Pro N",
                         "Enterprise": "Enterprise",
                         "Education": "Education"}.get(edition, edition)
                return f"Windows {ver} {ed} (Build {build}.{ubr})"
            except Exception:
                pass
            try:
                build = int(platform.version().split(".")[-1])
                major = int(platform.version().split(".")[0])
                if major >= 10 and build >= 22000:
                    return "Windows 11"
                elif major >= 10:
                    return "Windows 10"
                else:
                    return f"Windows {major}"
            except Exception:
                return "Windows"
        # Linux: read from /etc/os-release
        try:
            for fpath in ["/etc/os-release", "/etc/lsb-release"]:
                if os.path.exists(fpath):
                    with open(fpath) as f:
                        for line in f:
                            if line.startswith("PRETTY_NAME="):
                                return line.split("=",1)[1].strip().strip('"')[:28]
        except Exception:
            pass
        return f"Linux {platform.release()[:20]}"

    @staticmethod
    def _kernel():
        s = platform.system()
        if s == "Windows":
            # Show full NT version: e.g. "NT 10.0.22621"
            try:
                import winreg
                key   = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                build = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
                ubr   = winreg.QueryValueEx(key, "UBR")[0]
                winreg.CloseKey(key)
                return f"NT 10.0.{build}.{ubr}"
            except Exception:
                pass
            return f"NT {platform.version()}"[:26]
        if s == "Darwin":
            return f"Darwin {platform.release()}"[:26]
        return platform.release()[:26]

    @staticmethod
    def _cpu():
        try:
            if platform.system() == "Darwin":
                r = subprocess.run(["sysctl","-n","machdep.cpu.brand_string"],
                                   capture_output=True, text=True, timeout=2)
                v = r.stdout.strip()
                if v: return v[:36]
            if platform.system() == "Linux":
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":",1)[1].strip()[:36]
            if platform.system() == "Windows":
                # Try PowerShell first (works on Win11 where wmic is deprecated)
                try:
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         "(Get-CimInstance Win32_Processor).Name"],
                        capture_output=True, text=True, timeout=4)
                    v = r.stdout.strip()
                    if v: return v[:40]
                except Exception:
                    pass
                # Fallback: wmic (works on Win10)
                try:
                    r = subprocess.run(["wmic","cpu","get","name","/value"],
                                       capture_output=True, text=True, timeout=3)
                    for line in r.stdout.splitlines():
                        if "Name=" in line:
                            return line.split("=",1)[1].strip()[:40]
                except Exception:
                    pass
        except Exception:
            pass
        return platform.processor()[:36] or "Unknown CPU"

    @staticmethod
    def _gpu():
        try:
            if platform.system() == "Darwin":
                r = subprocess.run(["system_profiler","SPDisplaysDataType"],
                                   capture_output=True, text=True, timeout=4)
                for line in r.stdout.splitlines():
                    if "Chipset Model" in line or "Chip" in line:
                        return line.split(":",1)[1].strip()[:40]

            if platform.system() == "Linux":
                gpus = []

                # 1) nvidia-smi — most reliable for NVIDIA cards
                try:
                    r = subprocess.run(
                        ["nvidia-smi", "--query-gpu=name",
                         "--format=csv,noheader"],
                        capture_output=True, text=True, timeout=4)
                    if r.returncode == 0:
                        for name in r.stdout.strip().splitlines():
                            name = name.strip()
                            if name and name not in gpus:
                                gpus.append(name[:36])
                except Exception:
                    pass

                # 2) lspci — catches Intel iGPU and any card nvidia-smi missed
                try:
                    r = subprocess.run(["lspci", "-mm"],
                                       capture_output=True, text=True, timeout=3)
                    for line in r.stdout.splitlines():
                        upper = line.upper()
                        if "VGA" in upper or "3D" in upper or "DISPLAY" in upper:
                            # lspci -mm format: addr "class" "vendor" "device" …
                            # Pull quoted fields for vendor + device
                            import re as _re
                            fields = _re.findall(r'"([^"]*)"', line)
                            if len(fields) >= 3:
                                vendor = fields[1].strip()
                                device = fields[2].strip()
                                # Skip generic/sub-device entries
                                if device and device not in ("", "Device"):
                                    name = f"{vendor} {device}".strip()[:36]
                                    # Avoid duplicating an already-found NVIDIA entry
                                    already = any(
                                        "nvidia" in g.lower() and "nvidia" in name.lower()
                                        for g in gpus)
                                    if not already and name not in gpus:
                                        gpus.append(name)
                            else:
                                # Fallback: last colon-separated field
                                raw = line.split(":",2)[-1].strip()[:36]
                                if raw and raw not in gpus:
                                    gpus.append(raw)
                except Exception:
                    pass

                # 3) /sys DRM nodes — last resort (no lspci available)
                if not gpus:
                    try:
                        drm = "/sys/class/drm"
                        seen = set()
                        for entry in sorted(os.listdir(drm)):
                            vendor_f = os.path.join(drm, entry, "device", "vendor")
                            device_f = os.path.join(drm, entry, "device", "device")
                            if os.path.exists(vendor_f) and os.path.exists(device_f):
                                vid = open(vendor_f).read().strip()
                                did = open(device_f).read().strip()
                                key = (vid, did)
                                if key not in seen:
                                    seen.add(key)
                                    label = f"GPU {vid}:{did}"
                                    gpus.append(label)
                    except Exception:
                        pass

                if gpus:
                    return " / ".join(gpus)

            if platform.system() == "Windows":
                gpus = []

                # 1) nvidia-smi — most accurate name for NVIDIA cards
                try:
                    r = subprocess.run(
                        ["nvidia-smi", "--query-gpu=name",
                         "--format=csv,noheader"],
                        capture_output=True, text=True, timeout=4)
                    if r.returncode == 0:
                        for name in r.stdout.strip().splitlines():
                            name = name.strip()
                            if name and name not in gpus:
                                gpus.append(name[:38])
                except Exception:
                    pass

                # 2) PowerShell CIM (Win10/11, works where wmic is deprecated)
                try:
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         "(Get-CimInstance Win32_VideoController).Name -join '|'"],
                        capture_output=True, text=True, timeout=5)
                    if r.returncode == 0:
                        for name in r.stdout.strip().split("|"):
                            name = name.strip()
                            if not name:
                                continue
                            # Skip Microsoft Basic Display / Remote Desktop adapters
                            nl = name.lower()
                            if any(x in nl for x in ("microsoft basic", "remote desktop",
                                                      "hyper-v", "virtual")):
                                continue
                            # Don't duplicate an NVIDIA entry already from nvidia-smi
                            already = any(
                                "nvidia" in g.lower() and "nvidia" in nl
                                for g in gpus)
                            if not already and name not in gpus:
                                gpus.append(name[:38])
                except Exception:
                    pass

                # 3) wmic fallback (Win10)
                if not gpus:
                    try:
                        r = subprocess.run(
                            ["wmic","path","win32_VideoController","get","name","/value"],
                            capture_output=True, text=True, timeout=4)
                        for line in r.stdout.splitlines():
                            if "Name=" in line:
                                name = line.split("=",1)[1].strip()[:38]
                                if name and name not in gpus:
                                    gpus.append(name)
                    except Exception:
                        pass

                if gpus:
                    return " / ".join(gpus)

        except Exception:
            pass
        return "N/A"

    @staticmethod
    def _ssid():
        try:
            if platform.system() == "Darwin":
                r = subprocess.run(["/System/Library/PrivateFrameworks/"
                                    "Apple80211.framework/Versions/Current/"
                                    "Resources/airport","-I"],
                                   capture_output=True, text=True, timeout=2)
                for line in r.stdout.splitlines():
                    if " SSID:" in line and "BSSID" not in line:
                        return line.split(":",1)[1].strip()
            if platform.system() == "Linux":
                r = subprocess.run(["iwgetid","-r"],
                                   capture_output=True, text=True, timeout=2)
                v = r.stdout.strip()
                if v: return v
                # Fallback: nmcli
                r2 = subprocess.run(
                    ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                    capture_output=True, text=True, timeout=2)
                for line in r2.stdout.splitlines():
                    if line.startswith("yes:"):
                        return line.split(":",1)[1].strip()
            if platform.system() == "Windows":
                r = subprocess.run(["netsh","wlan","show","interfaces"],
                                   capture_output=True, text=True, timeout=2)
                for line in r.stdout.splitlines():
                    if "SSID" in line and "BSSID" not in line:
                        return line.split(":",1)[1].strip()
        except Exception:
            pass
        return "N/A"

    @staticmethod
    def _local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def _shell():
        sys_name = platform.system()
        if sys_name == "Windows":
            # Check if running inside PowerShell
            ppid_name = ""
            try:
                if HAS_PSUTIL:
                    import psutil as _ps
                    p = _ps.Process(os.getpid())
                    ppid_name = _ps.Process(p.ppid()).name().lower()
            except Exception:
                pass
            if "powershell" in ppid_name or "pwsh" in ppid_name:
                # Get version
                try:
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                        capture_output=True, text=True, timeout=3)
                    v = r.stdout.strip()
                    return f"PowerShell {v}" if v else "PowerShell"
                except Exception:
                    return "PowerShell"
            if "cmd" in ppid_name:
                return "cmd.exe"
            return os.environ.get("COMSPEC", "cmd.exe").split("\\")[-1]
        # Unix
        shell_path = os.environ.get("SHELL", "")
        if shell_path:
            name = shell_path.split("/")[-1]
            try:
                r = subprocess.run([shell_path, "--version"],
                                   capture_output=True, text=True, timeout=2)
                first = r.stdout.splitlines()[0] if r.stdout else ""
                # Extract version number
                import re
                m = re.search(r"[\d]+\.[\d]+[\.\d]*", first)
                if m:
                    return f"{name} {m.group()}"
            except Exception:
                pass
            return name
        return "unknown"

    @staticmethod
    def _de_wm():
        sys_name = platform.system()
        if sys_name == "Windows":
            # Windows always uses DWM (Desktop Window Manager)
            return "DWM"
        if sys_name == "Darwin":
            return "Quartz Compositor"
        # Linux – check common env vars
        de = (os.environ.get("XDG_CURRENT_DESKTOP") or
              os.environ.get("DESKTOP_SESSION") or
              os.environ.get("GDMSESSION") or "")
        wm = os.environ.get("WINDOW_MANAGER", "")
        if de and wm:
            return f"{de} / {wm}"
        if de:
            return de
        if wm:
            return wm
        # Try wmctrl
        try:
            r = subprocess.run(["wmctrl", "-m"], capture_output=True, text=True, timeout=2)
            for line in r.stdout.splitlines():
                if line.startswith("Name:"):
                    return line.split(":",1)[1].strip()
        except Exception:
            pass
        return "N/A"

    def _fetch_resolution(self):
        """Fetch screen resolution in background."""
        res = "N/A"
        try:
            sys_name = platform.system()
            if sys_name == "Windows":
                # 1) ctypes — most reliable, works on Win10 and Win11
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    # Call SetProcessDPIAware so we get physical pixels, not scaled
                    try:
                        ctypes.windll.shcore.SetProcessDpiAwareness(2)
                    except Exception:
                        try: user32.SetProcessDPIAware()
                        except Exception: pass
                    w = user32.GetSystemMetrics(0)   # SM_CXSCREEN
                    h = user32.GetSystemMetrics(1)   # SM_CYSCREEN
                    if w > 0 and h > 0:
                        res = f"{w}x{h}"
                except Exception:
                    pass

                # 2) PowerShell via .NET Screen class
                if res == "N/A":
                    try:
                        ps = ("[System.Windows.Forms.Screen]::PrimaryScreen.Bounds |"
                              " ForEach-Object { $_.Width.ToString()+'x'+$_.Height.ToString() }")
                        r2 = subprocess.run(
                            ["powershell", "-NoProfile", "-Command", ps],
                            capture_output=True, text=True, timeout=5)
                        v = r2.stdout.strip()
                        if "x" in v:
                            res = v
                    except Exception:
                        pass

                # 3) wmic desktopmonitor (Win10 fallback)
                if res == "N/A":
                    try:
                        r = subprocess.run(
                            ["wmic", "desktopmonitor", "get",
                             "ScreenWidth,ScreenHeight", "/value"],
                            capture_output=True, text=True, timeout=5)
                        w = h = ""
                        for line in r.stdout.splitlines():
                            line = line.strip()
                            if line.startswith("ScreenWidth="):
                                w = line.split("=",1)[1].strip()
                            elif line.startswith("ScreenHeight="):
                                h = line.split("=",1)[1].strip()
                        if w and h and w != "0":
                            res = f"{w}x{h}"
                    except Exception:
                        pass
            elif sys_name == "Darwin":
                r = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True, text=True, timeout=5)
                for line in r.stdout.splitlines():
                    if "Resolution" in line:
                        res = line.split(":",1)[1].strip().split(" @")[0]
                        break
            else:
                # Linux: Wayland first, then X11 (xrandr / xdpyinfo), then tkinter
                import re as _re

                # --- Wayland paths ---
                if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE","").lower() == "wayland":

                    # wlr-randr (wlroots compositors: Sway, Hyprland, etc.)
                    try:
                        r = subprocess.run(["wlr-randr"],
                                           capture_output=True, text=True, timeout=3)
                        if r.returncode == 0:
                            for line in r.stdout.splitlines():
                                m = _re.search(r'(\d{3,}x\d{3,})', line)
                                if m:
                                    res = m.group(1); break
                    except Exception:
                        pass

                    # kscreen-doctor (KDE/KWin)
                    if res == "N/A":
                        try:
                            r = subprocess.run(["kscreen-doctor", "-o"],
                                               capture_output=True, text=True, timeout=3)
                            if r.returncode == 0:
                                for line in r.stdout.splitlines():
                                    m = _re.search(r'(\d{3,}x\d{3,})', line)
                                    if m:
                                        res = m.group(1); break
                        except Exception:
                            pass

                    # gnome-randr / mutter (GNOME on Wayland)
                    if res == "N/A":
                        try:
                            r = subprocess.run(["gnome-randr"],
                                               capture_output=True, text=True, timeout=3)
                            if r.returncode == 0:
                                for line in r.stdout.splitlines():
                                    m = _re.search(r'(\d{3,}x\d{3,})', line)
                                    if m:
                                        res = m.group(1); break
                        except Exception:
                            pass

                    # /sys/class/drm — kernel always knows the mode
                    if res == "N/A":
                        try:
                            drm_base = "/sys/class/drm"
                            for card in sorted(os.listdir(drm_base)):
                                modes_path = os.path.join(drm_base, card, "modes")
                                if os.path.exists(modes_path):
                                    with open(modes_path) as mf:
                                        first = mf.readline().strip()
                                    if first:
                                        res = first; break
                        except Exception:
                            pass

                # --- X11 paths ---
                if res == "N/A":
                    try:
                        r = subprocess.run(["xrandr","--current"],
                                           capture_output=True, text=True, timeout=3)
                        for line in r.stdout.splitlines():
                            if " connected" in line:
                                m = _re.search(r'(\d{3,}x\d{3,})', line)
                                if m:
                                    res = m.group(1); break
                    except Exception:
                        pass

                if res == "N/A":
                    try:
                        r = subprocess.run(["xdpyinfo"],
                                           capture_output=True, text=True, timeout=3)
                        for line in r.stdout.splitlines():
                            if "dimensions:" in line:
                                res = line.split()[1]; break
                    except Exception:
                        pass

                # --- tkinter fallback (works on both X11 and some Wayland via XWayland) ---
                if res == "N/A":
                    try:
                        import tkinter as _tk
                        _root = _tk.Tk()
                        _root.withdraw()
                        w = _root.winfo_screenwidth()
                        h = _root.winfo_screenheight()
                        _root.destroy()
                        if w > 0 and h > 0:
                            res = f"{w}x{h}"
                    except Exception:
                        pass
        except Exception:
            pass
        with self._lock:
            self.resolution = res

    def _fetch_pkg_count(self):
        """Fetch package count in background so it doesn't slow startup."""
        count = "N/A"
        try:
            sys_name = platform.system()
            if sys_name == "Darwin":
                r = subprocess.run(["brew","list","--formula"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    count = f"{len(r.stdout.strip().splitlines())} (brew)"
            if sys_name == "Windows":
                counts = []
                # winget (fast with --disable-interactivity)
                try:
                    r = subprocess.run(
                        ["winget", "list", "--disable-interactivity",
                         "--accept-source-agreements"],
                        capture_output=True, text=True, timeout=10)
                    if r.returncode == 0:
                        # Skip header lines (contain dashes separator) and blanks
                        lines = [l for l in r.stdout.splitlines()
                                 if l.strip() and not l.startswith("-")
                                 and not all(c in "- \t" for c in l)]
                        # First line is usually the header row "Name  Id  Version…"
                        pkg_lines = lines[1:] if lines else []
                        if pkg_lines:
                            counts.append(f"{len(pkg_lines)} (winget)")
                except Exception:
                    pass
                # scoop (if installed)
                try:
                    r = subprocess.run(["scoop", "list"],
                                       capture_output=True, text=True, timeout=8,
                                       shell=True)
                    if r.returncode == 0:
                        lines = [l for l in r.stdout.splitlines()
                                 if l.strip() and not l.startswith(" Name")]
                        if lines:
                            counts.append(f"{len(lines)} (scoop)")
                except Exception:
                    pass
                # chocolatey (if installed)
                try:
                    r = subprocess.run(["choco", "list", "--local-only", "--limit-output"],
                                       capture_output=True, text=True, timeout=8)
                    if r.returncode == 0:
                        lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
                        if lines:
                            # Last line is summary "N packages installed"
                            try:
                                n = int(lines[-1].split()[0])
                                counts.append(f"{n} (choco)")
                            except Exception:
                                counts.append(f"{len(lines)} (choco)")
                except Exception:
                    pass
                if counts:
                    count = ", ".join(counts)
            elif sys_name == "Linux":
                for cmd, flag in [
                    ("dpkg-query", ["-l"]),
                    ("rpm",        ["-qa"]),
                    ("pacman",     ["-Q"]),
                    ("apk",        ["list", "--installed"]),
                ]:
                    if shutil.which(cmd):
                        r = subprocess.run([cmd] + flag,
                                           capture_output=True, text=True, timeout=5)
                        if r.returncode == 0:
                            lines = [l for l in r.stdout.strip().splitlines()
                                     if l and not l.startswith("Desired")]
                            count = f"{len(lines)} ({cmd})"
                            break
        except Exception:
            pass
        with self._lock:
            self.pkg_count = count

    @staticmethod
    def _scan_devices():
        devs = []
        sys_name = platform.system()

        if sys_name == "Windows":
            _SKIP = {
                "avrcp","pbap","pan","hfp","hsp","gatt","sdp","rfcomm","obex",
                "map","nap","pse","panu","service","profile","gateway","push",
                "network","generic","personal area","headset audio","handsfree",
                "audio sink","advanced audio","attribute","object push","a2dp",
                "bnep","dip","streaming","enumerator","radio","adapter","hands-f",
            }
            _JUNK = {
                "hid-compliant","usb input device","usb root","host controller",
                "composite","hub","microsoft","realtek","intel","generic usb",
                "portable device control","system control","consumer contr",
                "vendor-defined","unknown device",
            }
            bt_names = {}
            seen_names = set()
            try:
                ps_bt = (
                    "$skip=@('avrcp','pbap','hfp','hsp','gatt','sdp','rfcomm',"
                    "'obex','map','nap','pse','panu','service','profile','gateway',"
                    "'push','network','personal area','headset audio','handsfree',"
                    "'audio sink','advanced audio','attribute','object push','a2dp',"
                    "'bnep','streaming','enumerator','radio','adapter','hands-f');"
                    "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |"
                    " ForEach-Object {"
                    "  $conn=(Get-PnpDeviceProperty -InstanceId $_.InstanceId"
                    "   -KeyName '{83DA6326-97A6-4088-9453-A1923F573B29} 15'"
                    "   -ErrorAction SilentlyContinue).Data;"
                    "  if($conn -eq $true){"
                    "    $nl=$_.FriendlyName.ToLower();"
                    "    $bad=$false;"
                    "    foreach($s in $skip){if($nl.Contains($s)){$bad=$true;break}}"
                    "    if(-not $bad){"
                    "      Write-Output ($_.FriendlyName+'|'+$_.InstanceId)"
                    "    }"
                    "  }"
                    "}"
                )
                r_bt = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_bt],
                    capture_output=True, text=True, timeout=10)
                for line in r_bt.stdout.strip().splitlines():
                    line = line.strip()
                    if "|" not in line: continue
                    name, iid = line.split("|", 1)
                    name = name.strip(); iid = iid.strip()
                    if not name: continue
                    nl  = name.lower()
                    if any(x in nl for x in _SKIP): continue
                    if any(x in nl for x in _JUNK): continue
                    key = " ".join(nl.split()[:2])
                    if key in seen_names: continue
                    seen_names.add(key)
                    entry = {"name": name[:30], "type": "BT",
                             "connected": True, "battery": None, "_iid": iid}
                    devs.append(entry)
                    bt_names[key] = entry
            except Exception: pass

        elif sys_name == "Darwin":
            try:
                r = subprocess.run(
                    ["system_profiler","SPBluetoothDataType","-json"],
                    capture_output=True, text=True, timeout=5)
                data = json.loads(r.stdout)
                bt_data = data.get("SPBluetoothDataType",[{}])[0]
                connected = bt_data.get("device_connected", [])
                for entry in connected:
                    for name, info in entry.items():
                        bat = None
                        bat_str = str(info.get("device_batteryLevelMain",""))
                        if bat_str.replace("%","").isdigit():
                            bat = int(bat_str.replace("%",""))
                        devs.append({"name":name[:28],"type":"BT",
                                     "connected":True,"battery":bat})
            except Exception: pass
            try:
                r = subprocess.run(
                    ["system_profiler","SPUSBDataType","-json"],
                    capture_output=True, text=True, timeout=5)
                data = json.loads(r.stdout)
                def _walk_usb(items):
                    for item in items:
                        for k,v in item.items():
                            if isinstance(v, dict):
                                name = v.get("_name","")
                                if name and "hub" not in name.lower():
                                    devs.append({"name":name[:28],"type":"USB",
                                                 "connected":True,"battery":None})
                                _walk_usb(v.get("_items",[]))
                _walk_usb(data.get("SPUSBDataType",[]))
            except Exception: pass

        else:
            try:
                r = subprocess.run(["bluetoothctl","devices","Connected"],
                                   capture_output=True, text=True, timeout=3)
                for line in r.stdout.splitlines():
                    parts = line.split(None, 2)
                    if len(parts) >= 3 and parts[0]=="Device":
                        devs.append({"name":parts[2][:28],"type":"BT",
                                     "connected":True,"battery":None})
            except Exception: pass
            try:
                r = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=3)
                for line in r.stdout.splitlines():
                    if ":" in line:
                        name = line.split(":",1)[1].strip().split("ID")[0].strip()
                        if name and "Hub" not in name and "root" not in name.lower():
                            devs.append({"name":name[:28],"type":"USB",
                                         "connected":True,"battery":None})
            except Exception: pass

        return devs[:16]

    def poll(self):
        if not HAS_PSUTIL: return
        with self._lock:
            try:
                b = psutil.sensors_battery()
                if b: self.bat_pct,self.bat_plug = int(b.percent),b.power_plugged
            except Exception: pass
            try: self.cpu = psutil.cpu_percent(interval=None)
            except Exception: pass
            try:
                m = psutil.virtual_memory()
                self.mem_pct  = m.percent
                self.mem_used  = m.used / 1e9
                self.mem_total = m.total / 1e9
            except Exception: pass
            try:
                p = "/" if platform.system() != "Windows" else "C:\\"
                self.disk_pct = psutil.disk_usage(p).percent
            except Exception: pass
            try:
                n = psutil.net_io_counters()
                if self._pnet:
                    self.net_dn = (n.bytes_recv - self._pnet.bytes_recv) / 1024 / 2
                    self.net_up = (n.bytes_sent - self._pnet.bytes_sent) / 1024 / 2
                self._pnet = n
            except Exception: pass
            try: self.uptime = int(time.time() - self._boot)
            except Exception: pass
        if time.time() - self._dev_last > 8 and not self._dev_scanning:
            self._dev_last     = time.time()
            self._dev_scanning = True
            def _bg_scan(self=self):
                try:
                    result = self._scan_devices()
                    with self._lock:
                        self.devices = result
                finally:
                    self._dev_scanning = False
            threading.Thread(target=_bg_scan, daemon=True).start()

    def snap(self):
        with self._lock:
            return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

SD = SysData()
def _poll_loop():
    while True: SD.poll(); time.sleep(2)
threading.Thread(target=_poll_loop, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
#  TODO PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════
TODO_FILE = os.path.join(os.path.expanduser("~"), ".terminal_standby_todos.json")

def load_todos():
    try:
        with open(TODO_FILE) as f:
            data = json.load(f)
            return [[bool(x[0]), str(x[1])] for x in data]
    except:
        return [[False,"Finalize Triket logic"],[False,"Update portfolio build"],[False,"Weekly review"]]

def save_todos(todos):
    try:
        with open(TODO_FILE,"w") as f: json.dump(todos,f,indent=2)
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  BIG DIGIT FONT
# ══════════════════════════════════════════════════════════════════════════════
_D = {
  '0':["▄███▄","█   █","█   █","█   █","▀███▀"],
  '1':["  █  ","  █  ","  █  ","  █  ","  █  "],
  '2':["████ ","    █","▄███▀","█    ","█████"],
  '3':["████ ","    █"," ███ ","    █","████ "],
  '4':["█  █ ","█  █ ","█████","   █ ","   █ "],
  '5':[" ████","█    ","████ ","    █","████ "],
  '6':["▄███▄","█    ","████ ","█   █","▀███▀"],
  '7':["█████","   █ ","  █  "," █   ","█    "],
  '8':["▄███▄","█   █","▄███▄","█   █","▀███▀"],
  '9':["▄███▄","█   █","▀████","    █","▄███▀"],
  ':':[" ██  "," ██  ","     "," ██  "," ██  "],
}

def big_time(win, y, x, s, col=P_HI):
    cx = x
    for ch in s:
        rows = _D.get(ch, [" "*5]*5)
        for r, row in enumerate(rows):
            put(win, y+r, cx, row, cp(col, bold=True))
        cx += len(rows[0]) + 1

def btw(s): return sum(len(_D.get(c,["     "])[0])+1 for c in s)-1

# ══════════════════════════════════════════════════════════════════════════════
#  CAVA-STYLE SPECTRUM VISUALIZER
# ══════════════════════════════════════════════════════════════════════════════
_VCHR = " ▁▂▃▄▅▆▇█"

def draw_spectrum(win, y, x, h, w, spectrum, col_low=P_CYAN, col_mid=P_BLUE, col_hi=P_PINK):
    n_bars = min(len(spectrum), w // 2)
    if n_bars < 1: return

    for b in range(n_bars):
        amp   = spectrum[b]
        total = h * 8
        val   = int(amp * total)

        bx = x + b * (w // n_bars)
        for row in range(h):
            row_y = y + h - 1 - row
            row_units_start = row * 8
            row_units_end   = row_units_start + 8
            if val <= row_units_start:
                ch = " "
            elif val >= row_units_end:
                ch = "█"
            else:
                lvl = val - row_units_start
                ch  = _VCHR[lvl]

            frac = (h - 1 - row) / max(1, h-1)
            if frac < 0.4:    col = col_low
            elif frac < 0.75: col = col_mid
            else:              col = col_hi

            put(win, row_y, bx,   ch, cp(col, bold=(frac>0.6)))
            put(win, row_y, bx+1, ch, cp(col, bold=(frac>0.6)))

# ══════════════════════════════════════════════════════════════════════════════
#  APP STATE
# ══════════════════════════════════════════════════════════════════════════════
VIEWS = ["DASHBOARD","MUSIC + LIBRARY","FOCUS","NEOFETCH","NETWORK","CALENDAR","VIDEO","NEWS & MARKET HUB","NEWS & STOCKS","ETF · CRYPTO"]
ALL_VIEW_NAMES = VIEWS

HUB_VIEW_IDX = 7
NEWS_STOCKS_VIEW_IDX = 8
ETF_CRYPTO_VIEW_IDX = 9
SHORTCUT_ONLY_VIEWS = {NEWS_STOCKS_VIEW_IDX, ETF_CRYPTO_VIEW_IDX}
NAV_CYCLE_VIEWS = [0, 1, 2, 3, 4, 5, 6, HUB_VIEW_IDX]


def _cycle_view(cur, step):
    """Cycle through primary views only; shortcut-only views are excluded."""
    if cur not in NAV_CYCLE_VIEWS:
        cur = HUB_VIEW_IDX
    pos = NAV_CYCLE_VIEWS.index(cur)
    return NAV_CYCLE_VIEWS[(pos + step) % len(NAV_CYCLE_VIEWS)]

class State:
    def __init__(self):
        self.view       = 0
        self.return_view: int | None = None
        self.todos      = load_todos()
        self.todo_cur   = 0
        self.todo_add   = False
        self.todo_buf   = ""
        self.pomo_total = 25*60.0
        self.pomo_secs  = 25*60.0
        self.pomo_run   = False
        self.pomo_done  = 0
        self.pomo_phase = "WORK"
        self._pw        = time.time()
        self.focus_modes= ["DEEP WORK","READING","CODING","REVIEW","WRITING"]
        self.focus_idx  = 0
        self.cal_mode  = "week"
        self.cal_date  = datetime.datetime.now().date()
        self.cal_add   = False
        self.cal_buf   = ""
        self._spec_smooth = [0.0]*32
        self._anim_t   = 0.0   # animation time counter


class DenjiState:
    def __init__(self):
        self.input_mode = False
        self.input_buf = ""
        self.user_text = ""
        self.response_text = "Ready for your command."
        self.mood = "idle"          # idle | listening | processing | speaking | happy | sad
        self.mood_until = 0.0
        self.stage_queue = []
        self.last_action = "Waiting for your command"
        self.mic_status = "Ready" if HAS_SR else "Offline"
        self.tts_status = "Ready" if HAS_TTS else "Offline"
        self.speech_output_enabled = True
        self.camera_enabled = False
        self.camera_status = "Ready" if HAS_CV2 else "Offline"
        self.face_seen = False
        self.face_last_seen = 0.0
        self.user_away_secs = 0.0
        self.face_x = 0.0            # normalized [-1, 1], from camera center
        self.face_y = 0.0            # normalized [-1, 1], from camera center
        self.eye_x = 0               # tui eye offset x
        self.eye_y = 0               # tui eye offset y
        self.camera_error = ""
        self._camera_stop = threading.Event()
        self._camera_thread: Any = None
        # ─── TARS System Fields ─────────────────────────────────────
        self.humor_level = 50.0           # 0-100: TARS humor adjustment
        self.voice_enabled = HAS_VOICE_ENGINE
        self.listening = False
        self.voice_engine = None
        self.personality = get_personality_engine(50.0) if HAS_PERSONALITY else None
        self.tars_mode = True             # Toggle between standard and TARS UI
        self.last_voiced_command = ""
        self.voice_timeout = 0.0
        self.boot_status = "BOOT"
        self.boot_note = "Starting systems"
        # ─── AI Brain Fields ────────────────────────────────────────
        self.ai_engine = get_ai_engine() if HAS_AI_ENGINE else None
        self.ai_thinking = False
        self.ai_last_input = ""
        self.ai_last_output = ""


_DENJI_BOOT_LOCK = threading.Lock()
_DENJI_BOOT_DONE = False


def denji_startup_boot():
    """One-time startup warmup that never blocks or crashes app launch."""
    global _DENJI_BOOT_DONE
    if _DENJI_BOOT_DONE:
        return
    with _DENJI_BOOT_LOCK:
        if _DENJI_BOOT_DONE:
            return
        try:
            DS.boot_status = "INIT"
            DS.boot_note = "Calibrating personality core"
            if HAS_PERSONALITY and DS.personality is None:
                DS.personality = get_personality_engine(DS.humor_level)

            if HAS_AI_ENGINE:
                try:
                    ai_module = importlib.import_module("denji_ai")
                    DS.ai_engine = ai_module.get_ai_engine()
                except Exception:
                    _refresh_ai_engine()

            DS.boot_note = "Warming voice channels"
            if HAS_VOICE_ENGINE and DS.voice_enabled and DS.voice_engine is None:
                try:
                    DS.voice_engine = get_voice_engine()
                    st = DS.voice_engine.get_status()
                    DS.mic_status = st.get("sr", DS.mic_status)
                    DS.tts_status = st.get("tts", DS.tts_status)
                except Exception:
                    DS.voice_enabled = False
                    DS.mic_status = "Offline"
                    DS.tts_status = "Offline"

            DS.boot_status = "READY"
            DS.boot_note = "All systems online"
        except Exception:
            DS.boot_status = "SAFE"
            DS.boot_note = "Booted in safe mode"
        _DENJI_BOOT_DONE = True


_DENJI_TTS_LOCK = threading.Lock()
_DENJI_TTS_ENGINE = None


def _denji_speak_worker(text):
    global _DENJI_TTS_ENGINE
    if not HAS_TTS:
        DS.tts_status = "Offline"
        return
    try:
        with _DENJI_TTS_LOCK:
            if _DENJI_TTS_ENGINE is None:
                _DENJI_TTS_ENGINE = pyttsx3.init()
            DS.tts_status = "Speaking"
            _DENJI_TTS_ENGINE.say(text)
            _DENJI_TTS_ENGINE.runAndWait()
            DS.tts_status = "Ready"
    except Exception:
        DS.tts_status = "Error"


def denji_speak(text):
    if not DS.speech_output_enabled:
        DS.tts_status = "Muted"
        return
    if DS.voice_engine is not None:
        try:
            DS.voice_engine.speak(text, wait=False)
            return
        except Exception:
            pass
    if not HAS_TTS:
        return
    threading.Thread(target=lambda t=text: _denji_speak_worker(t), daemon=True).start()


def _tars_reply(core_text: str, personality_response: str = "") -> str:
    """Blend informative text with personality tone so text and speech stay aligned."""
    core = (core_text or "").strip()
    flair = (personality_response or "").strip()
    if not flair:
        return core
    if not core:
        return flair
    return f"{flair} {core}"


def _refresh_ai_engine():
    """Reload the AI module so the live process sees the current backend state."""
    if not HAS_AI_ENGINE:
        return None
    try:
        fresh_module = importlib.import_module("denji_ai")
        DS.ai_engine = fresh_module.get_ai_engine()
    except Exception:
        try:
            DS.ai_engine = get_ai_engine()
        except Exception:
            pass
    return DS.ai_engine


def denji_toggle_speech_output():
    """Toggle spoken output while keeping text replies active."""
    DS.speech_output_enabled = not DS.speech_output_enabled
    if DS.speech_output_enabled:
        DS.tts_status = "Ready" if HAS_TTS else "Offline"
        DS.last_action = "Speech output enabled"
    else:
        DS.tts_status = "Muted"
        DS.last_action = "Speech output muted"


def _denji_camera_loop():
    if not HAS_CV2:
        DS.camera_status = "Offline"
        return

    cap = None
    face_cascade = None
    try:
        if platform.system() == "Windows" and hasattr(cv2, "CAP_DSHOW"):
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap or not cap.isOpened():
                cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(0)
        if not cap or not cap.isOpened():
            DS.camera_status = "Unavailable"
            return

        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if os.path.exists(cascade_path):
            face_cascade = cv2.CascadeClassifier(cascade_path)

        DS.camera_status = "Active"
        while not DS._camera_stop.is_set():
            ok, frame = cap.read()
            if not ok or frame is None:
                DS.face_seen = False
                time.sleep(0.08)
                continue

            seen = False
            if face_cascade is not None and not face_cascade.empty():
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))
                seen = len(faces) > 0
                if seen:
                    # Track the largest detected face so eye movement feels stable.
                    fx, fy, fw, fh = sorted(faces, key=lambda f: (f[2] * f[3]), reverse=True)[0]
                    h, w = gray.shape[:2]
                    cx = fx + fw / 2.0
                    cy = fy + fh / 2.0
                    nx = ((cx / max(1.0, float(w))) - 0.5) * 2.0
                    ny = ((cy / max(1.0, float(h))) - 0.5) * 2.0
                    DS.face_x = max(-1.0, min(1.0, nx))
                    DS.face_y = max(-1.0, min(1.0, ny))
                    DS.eye_x = int(round(DS.face_x * 1.5))
                    DS.eye_y = int(round(DS.face_y * 1.0))
                    DS.face_last_seen = time.time()
            DS.face_seen = seen
            time.sleep(0.08)
    except Exception as e:
        DS.camera_error = str(e)
        DS.camera_status = "Error"
    finally:
        DS.camera_enabled = False
        DS.face_seen = False
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def denji_toggle_camera():
    if not HAS_CV2:
        DS.response_text = "Camera module not installed"
        DS.last_action = "Install opencv-python for camera"
        DS.camera_status = "Offline"
        return

    if DS.camera_enabled:
        DS._camera_stop.set()
        DS.camera_enabled = False
        DS.camera_status = "Stopped"
        DS.last_action = "Camera stopped"
        return

    DS._camera_stop = threading.Event()
    DS.camera_enabled = True
    DS.camera_status = "Starting"
    DS.camera_error = ""
    DS._camera_thread = threading.Thread(target=_denji_camera_loop, daemon=True)
    DS._camera_thread.start()
    DS.last_action = "Camera started"


def _denji_listen_worker():
    try:
        DS.listening = True
        DS.mic_status = "Listening"
        engine = DS.voice_engine or (get_voice_engine() if HAS_VOICE_ENGINE else None)
        if engine is None:
            DS.mic_status = "Offline"
            DS.response_text = "Voice engine unavailable"
            DS.last_action = "Voice engine missing"
            return

        text = engine.listen(timeout=6.0, on_audio_received=lambda msg: setattr(DS, "mic_status", msg.replace("...", "")))
        DS.mic_status = "Ready"
        if text.strip():
            cmd = text.strip()
            if not cmd.lower().startswith("denji"):
                cmd = f"Denji {cmd}"
            denji_submit_command(cmd)
    except Exception:
        DS.mic_status = "Ready" if (HAS_SR or HAS_VOICE_ENGINE) else "Offline"
        DS.response_text = "I could not catch that. Try typing command with T."
        DS.last_action = "Voice listen timeout/failure"
    finally:
        DS.listening = False


def denji_listen_once():
    if not (HAS_SR or HAS_VOICE_ENGINE):
        DS.input_mode = True
        DS.input_buf = ""
        DS.mood = "listening"
        DS.mood_until = time.time() + 0.5
        DS.stage_queue = [("idle", 0.0)]
        return
    if DS.voice_engine is None and HAS_VOICE_ENGINE:
        try:
            DS.voice_engine = get_voice_engine()
        except Exception:
            pass
    DS.mood = "listening"
    DS.mood_until = time.time() + 0.7
    DS.stage_queue = [("processing", 0.6), ("idle", 0.0)]
    threading.Thread(target=_denji_listen_worker, daemon=True).start()


def denji_shutdown():
    if DS.camera_enabled:
        DS._camera_stop.set()
        DS.camera_enabled = False
    DS.camera_status = "Stopped" if HAS_CV2 else "Offline"


def denji_face(mood):
    if mood == "speaking":
        return "( ^‿^ )"
    if mood == "processing":
        return "( -_- )"
    if mood == "listening":
        return "( •_• )"
    if mood == "happy":
        return "( ^_^ )"
    if mood == "sad":
        return "( ;_; )"

    # Idle: eyes look toward tracked user position.
    eye_set = ["o", "O", "0"]
    idx = 0
    if DS.eye_x >= 1:
        idx = 1
    elif DS.eye_x <= -1:
        idx = 2
    e = eye_set[idx]
    return f"( {e}_{e} )"


def denji_submit_command(cmd):
    raw = (cmd or "").strip()
    if not raw:
        return

    c = raw.lower()
    if c.startswith("denji "):
        c = c[6:].strip()

    DS.user_text = raw
    DS.mood = "listening"
    DS.mood_until = time.time() + 0.55
    DS.stage_queue = [("processing", 0.85), ("speaking", 1.4), ("idle", 0.0)]

    if HAS_AI_ENGINE:
        try:
            ai_module = importlib.import_module("denji_ai")
            DS.ai_engine = ai_module.get_ai_engine()
        except Exception:
            _refresh_ai_engine()

    # Get personality response based on humor level
    personality_response = ""
    if HAS_PERSONALITY and DS.personality:
        personality_response = DS.personality.generate_acknowledgment(c)

    command_handled = False

    if c in ("test", "ai test", "test ai", "tars"):
        # Quick TARS personality test
        DS.user_text = raw
        if HAS_AI_ENGINE and DS.ai_engine:
            DS.ai_last_input = "Quick TARS personality check"
            DS.mood = "processing"
            try:
                response = DS.ai_engine.get_response("What can you do?", DS.mood, DS.humor_level)
                DS.ai_last_output = response
                backend = (DS.ai_engine.last_backend or "TARS").upper()
                DS.response_text = f"[{backend}] {response}"
                DS.mood = "speaking"
                DS.last_action = "Ran TARS personality test"
                denji_speak(DS.response_text)
            except Exception as err:
                DS.response_text = f"Neural error: {str(err)[:40]}"
                DS.mood = "idle"
                denji_speak(DS.response_text)
        else:
            DS.response_text = _tars_reply("TARS system ready", personality_response)
            DS.last_action = "TARS test"
            denji_speak(DS.response_text)
        return
    
    if "play" in c and "music" in c:
        if not AUDIO.playing:
            AUDIO.toggle_play()
        DS.response_text = _tars_reply("Playing your music", personality_response)
        DS.last_action = "Music playback started"
        command_handled = True
    elif "pause" in c and "music" in c:
        if AUDIO.playing:
            AUDIO.toggle_play()
        DS.response_text = _tars_reply("Pausing your music", personality_response)
        DS.last_action = "Music playback paused"
        command_handled = True
    elif "next" in c and ("track" in c or "song" in c or "music" in c):
        AUDIO.next_track()
        DS.response_text = _tars_reply("Skipping to the next track", personality_response)
        DS.last_action = "Advanced to next track"
        command_handled = True
    elif "focus" in c:
        ST.pomo_run = True
        ST._pw = time.time()
        DS.response_text = _tars_reply("Starting focus mode", personality_response)
        DS.last_action = "Pomodoro session started"
        command_handled = True
    elif "calendar" in c:
        ST.view = 5
        DS.response_text = _tars_reply("Opening your calendar", personality_response)
        DS.last_action = "Switched to calendar view"
        command_handled = True
    elif "network" in c:
        ST.view = 4
        DS.response_text = _tars_reply("Opening network overview", personality_response)
        DS.last_action = "Switched to network view"
        command_handled = True
    elif "video" in c:
        ST.view = 6
        DS.response_text = _tars_reply("Opening video panel", personality_response)
        DS.last_action = "Switched to video view"
        command_handled = True
    elif "news" in c:
        ST.view = HUB_VIEW_IDX
        DS.response_text = _tars_reply("Opening news and market hub", personality_response)
        DS.last_action = "Switched to news hub"
        command_handled = True
    elif "system" in c and "snapshot" in c:
        ST.view = 3
        DS.response_text = _tars_reply("Opening system overview", personality_response)
        DS.last_action = "Switched to neofetch view"
        command_handled = True
    
    # If command not handled by system, route to AI engine
    if not command_handled:
        # Force AI engine initialization (always try to use it)
        try:
            if not DS.ai_engine and HAS_AI_ENGINE:
                DS.ai_engine = get_ai_engine()
        except Exception:
            pass
        
        # Use AI engine if available, otherwise use TARS fallback
        if DS.ai_engine:
            DS.ai_last_input = raw
            DS.mood = "processing"
            try:
                response = DS.ai_engine.get_response(raw, DS.mood, DS.humor_level)
                DS.ai_last_output = response
                backend = (DS.ai_engine.last_backend or "TARS").upper()
                DS.response_text = f"[{backend}] {response}"
                DS.mood = "speaking"
                denji_speak(DS.response_text)
            except Exception as err:
                DS.response_text = f"Neural error: {str(err)[:40]}"
                DS.mood = "idle"
                denji_speak(DS.response_text)
        else:
            # Genuine fallback (should rarely happen)
            DS.response_text = _tars_reply("I got that. Tell me what to run next.", personality_response)
            DS.last_action = "Command understood, waiting for exact action"
            denji_speak(DS.response_text)
    else:
        denji_speak(DS.response_text)


def denji_tick():
    if DS.mood_until <= 0:
        return
    now = time.time()
    if now < DS.mood_until:
        return

    if DS.stage_queue:
        nxt, dur = DS.stage_queue.pop(0)
        DS.mood = nxt
        DS.mood_until = (now + dur) if dur > 0 else 0.0
    else:
        # Presence-based idle mood after active animation pipeline finishes.
        if DS.camera_enabled and HAS_CV2:
            away = now - DS.face_last_seen if DS.face_last_seen else 999.0
            DS.user_away_secs = max(0.0, away)
            if away <= 1.8:
                DS.mood = "happy"
            elif away >= 3.8:
                DS.mood = "sad"
            else:
                DS.mood = "idle"
        else:
            DS.mood = "idle"
        DS.mood_until = 0.0

ST = State()
DS = DenjiState()

# ══════════════════════════════════════════════════════════════════════════════
#  TICK
# ══════════════════════════════════════════════════════════════════════════════
def tick():
    now = time.time()
    AUDIO.tick()

    # Advance animation time
    ST._anim_t += 0.05
    denji_tick()

    if ST.pomo_run:
        dt = now - ST._pw
        ST.pomo_secs = max(0.0, ST.pomo_secs - dt)
        if ST.pomo_secs <= 0:
            ST.pomo_run = False
            if ST.pomo_phase == "WORK":
                ST.pomo_done  += 1
                ST.pomo_phase  = "BREAK"
                ST.pomo_total  = 5*60.0
                ST.pomo_secs   = 5*60.0
            else:
                ST.pomo_phase  = "WORK"
                ST.pomo_total  = 25*60.0
                ST.pomo_secs   = 25*60.0
    ST._pw = now

    raw = AUDIO.get_spectrum(32)
    ST._spec_smooth = [0.6*s + 0.4*r for s,r in zip(ST._spec_smooth, raw)]

def ios_style_clock(now):
    """Render iOS-style digital clock with large digits and clean design."""
    hour = now.hour
    minute = now.minute
    second = now.second
    ampm = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 if hour % 12 != 0 else 12
    
    # Format time with leading zeros
    time_str = f"{display_hour:02d}:{minute:02d}:{second:02d}"
    date_str = now.strftime("%A, %B %d, %Y")
    
    return {
        "time": time_str,
        "ampm": ampm,
        "date": date_str,
        "hour_24": f"{hour:02d}:{minute:02d}:{second:02d}"
    }


def ascii_clock_lines(time_text):
    """Render a large ASCII clock from HH:MM:SS text."""
    glyphs = {
        "0": [" __ ", "|  |", "|  |", "|  |", "|__|"],
        "1": ["    ", "   |", "   |", "   |", "   |"],
        "2": [" __ ", "   |", " __|", "|   ", "|__ "],
        "3": [" __ ", "   |", " __|", "   |", " __|"],
        "4": ["    ", "|  |", "|__|", "   |", "   |"],
        "5": [" __ ", "|   ", "|__ ", "   |", " __|"],
        "6": [" __ ", "|   ", "|__ ", "|  |", "|__|"],
        "7": [" __ ", "   |", "   |", "   |", "   |"],
        "8": [" __ ", "|  |", "|__|", "|  |", "|__|"],
        "9": [" __ ", "|  |", "|__|", "   |", " __|"],
        ":": ["    ", " .. ", "    ", " .. ", "    "],
        " ": ["    ", "    ", "    ", "    ", "    "],
    }
    rows = ["", "", "", "", ""]
    for ch in time_text:
        g = glyphs.get(ch, glyphs[" "])
        for i in range(5):
            rows[i] += g[i] + " "
    return rows

def next_event():
    return get_next_event()

# ══════════════════════════════════════════════════════════════════════════════
#  TARS DASHBOARD (AI Assistant Interface)
# ══════════════════════════════════════════════════════════════════════════════
def v_tars_dashboard(win, W, H):
    """TARS-inspired geometric AI dashboard"""
    if not HAS_TARS_UI or not DS.tars_mode:
        return v_dashboard(win, W, H)  # Fallback to standard dashboard
    
    # Helper to clip text
    def _clip(s, n):
        return s if len(s) <= n else s[:max(1, n-1)] + "..."

    def _wrap(s, width, limit=3):
        words = (s or "").split()
        if not words or width <= 1:
            return [""]
        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if len(candidate) <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
                if len(lines) >= limit:
                    break
        if len(lines) < limit and current:
            lines.append(current)
        return lines[:limit]
    
    now = datetime.datetime.now()
    sd = SD.snap()

    if W < 96 or H < 24:
        box(win, 1, 0, H - 2, W - 1, "D E N J I   C O R E")
        centre(win, 3, denji_face(DS.mood), cp(P_CYAN, bold=True))
        centre(win, 5, f"STATE {DS.mood.upper()}  |  BOOT {DS.boot_status}", cp(P_MID, bold=True))
        if HAS_AI_ENGINE and DS.ai_engine:
            centre(win, 6, _clip(DS.ai_engine.get_backend_status(), W - 6), cp(P_BLUE))
        blink = "_" if int(time.time() * 2) % 2 == 0 else " "
        if DS.input_mode:
            centre(win, 7, _clip(f"COMMAND > {DS.input_buf}{blink}", W - 6), cp(P_CYAN, bold=True))
            centre(win, 8, "ENTER submit  ESC cancel", cp(P_DIM))
        elif ST.todo_add:
            centre(win, 7, _clip(f"NEW TODO > {ST.todo_buf}{blink}", W - 6), cp(P_AMBER, bold=True))
            centre(win, 8, "ENTER add  ESC cancel", cp(P_DIM))
        else:
            centre(win, 7, _clip(f"INPUT  {DS.user_text}", W - 6), cp(P_HI))
            centre(win, 8, _clip(f"OUTPUT {DS.response_text}", W - 6), cp(P_GREEN))
        centre(win, 10, f"HUMOR {int(DS.humor_level):3d}%", cp(P_PINK, bold=True))
        hbar(win, 11, max(2, (W - 30) // 2), min(26, W - 4), DS.humor_level, P_PINK)
        todo_count = len(ST.todos)
        todo_done = sum(1 for done, _ in ST.todos if done)
        centre(win, 13, f"TODOS {todo_done}/{todo_count}", cp(P_AMBER, bold=True))
        if ST.todos:
            first_todo = ST.todos[0][1]
            centre(win, 14, _clip(f"1. {first_todo}", W - 6), cp(P_DIM))
        voice_label = "VOICE LISTENING" if DS.listening else "VOICE READY" if DS.voice_enabled else "VOICE OFFLINE"
        centre(win, H - 3, voice_label, cp(P_CYAN if DS.voice_enabled else P_DIM, bold=True))
        put(win, H - 1, 0, " type any key/t  test TARS  v voice  m mute  o todo  + - humor  c camera  left/right views  esc cancel  q quit ", cp(P_DIM))
        return

    # Cinematic sci-fi header band
    scan = int(time.time() * 2.7) % max(1, W - 10)
    put(win, 0, 0, "=" * (W - 1), cp(P_BOX))
    put(win, 1, 2, "DENJI // SYNTHETIC COMMAND BRIDGE", cp(P_CYAN, bold=True))
    put(win, 1, max(2, W - 26), now.strftime("%H:%M:%S  %d %b %Y"), cp(P_DIM))
    put(win, 2, 0, "-" * scan, cp(P_BLUE))
    put(win, 2, scan, ">>>", cp(P_PINK, bold=True))
    put(win, 2, scan + 3, "-" * max(0, W - scan - 4), cp(P_BLUE))

    # Main geometry
    top = 3
    body_h = H - 7
    left_w = max(26, W // 5)
    right_w = max(30, W // 3)
    center_w = max(26, W - left_w - right_w - 2)
    left_x = 0
    center_x = left_w + 1
    right_x = center_x + center_w + 1

    box(win, top, left_x, body_h, left_w, "SHIP TELEMETRY")
    box(win, top, center_x, body_h, center_w, "NEURAL CORE")
    box(win, top, right_x, body_h, right_w, "MISSION CHANNEL")

    # Left: telemetry stack
    cpu_pct = float(sd.get("cpu", 0))
    mem_pct = float(sd.get("memory", 0))
    hum_pct = float(DS.humor_level)
    away_pct = min(100.0, DS.user_away_secs * 4.0)

    put(win, top + 2, left_x + 2, "CPU", cp(P_DIM));   hbar(win, top + 3, left_x + 2, left_w - 4, cpu_pct, P_BLUE)
    put(win, top + 5, left_x + 2, "RAM", cp(P_DIM));   hbar(win, top + 6, left_x + 2, left_w - 4, mem_pct, P_CYAN)
    put(win, top + 8, left_x + 2, "HUMOR", cp(P_DIM)); hbar(win, top + 9, left_x + 2, left_w - 4, hum_pct, P_PINK)
    put(win, top + 11, left_x + 2, "IDLE DRIFT", cp(P_DIM)); hbar(win, top + 12, left_x + 2, left_w - 4, away_pct, P_AMBER)

    voice_line = f"MIC {DS.mic_status:<8}  TTS {DS.tts_status:<8}"
    cam_line = f"CAM {'ON' if DS.camera_enabled else 'OFF'}  FACE {'LOCK' if DS.face_seen else 'SEARCH'}"
    net_name = sd.get("ssid", "N/A")
    net_dn = sd.get("net_dn", 0.0)
    net_up = sd.get("net_up", 0.0)
    put(win, top + body_h - 6, left_x + 2, _clip(voice_line, left_w - 4), cp(P_MID))
    put(win, top + body_h - 5, left_x + 2, _clip(cam_line, left_w - 4), cp(P_MID))
    put(win, top + body_h - 4, left_x + 2, _clip(f"NET {net_name}", left_w - 4), cp(P_CYAN))
    put(win, top + body_h - 3, left_x + 2, _clip(f"DOWN {kbfmt(net_dn)}  UP {kbfmt(net_up)}", left_w - 4), cp(P_CYAN))
    put(win, top + body_h - 2, left_x + 2, _clip(f"BOOT {DS.boot_status} // {DS.boot_note}", left_w - 4), cp(P_GREEN if DS.boot_status == "READY" else P_AMBER, bold=True))

    # Center: neural core and AI interaction
    core_face = denji_face(DS.mood)
    centre(win, top + 2, core_face, cp(P_CYAN, bold=True))
    centre(win, top + 3, f"STATE :: {DS.mood.upper()}", cp(P_HI, bold=True))
    centre(win, top + 4, "NEURAL CORE // AI BRAIN", cp(P_DIM))

    pulse = "|" * (1 + int((math.sin(time.time() * 4.0) + 1.0) * 6.0))
    centre(win, top + 5, f"[{pulse:<13}]", cp(P_BLUE, bold=True))
    if HAS_AI_ENGINE and DS.ai_engine:
        put(win, top + 6, center_x + 2, _clip(DS.ai_engine.get_backend_status(), center_w - 4), cp(P_BLUE))

    # AI conversation display
    centre(win, top + 7, "─" * max(5, center_w - 6), cp(P_BOX))
    
    if HAS_AI_ENGINE and DS.ai_engine:
        conv_lines = DS.ai_engine.get_conversation_display(max_lines=min(8, max(4, body_h - top - 12)))
        for i, line in enumerate(conv_lines):
            y = top + 8 + i
            if y < top + body_h - 5:
                # Alternate colors for readability
                is_user = line.startswith("YOU >")
                color = P_HI if is_user else P_GREEN
                put(win, y, center_x + 2, _clip(line, center_w - 4), cp(color))

    # Keep latest output always visible even while typing/todo input.
    put(win, top + body_h - 5, center_x + 2, _clip(f"OUTPUT > {DS.response_text}", center_w - 4), cp(P_GREEN))
    
    # Current input/composer line
    if DS.input_mode:
        blink = "_" if int(time.time() * 2) % 2 == 0 else " "
        composer = f"COMMAND > {DS.input_buf}{blink}"
        hint = "ENTER submit  ESC cancel"
        put(win, top + body_h - 3, center_x + 2, _clip(composer, center_w - 4), cp(P_CYAN, bold=True))
        put(win, top + body_h - 2, center_x + 2, _clip(hint, center_w - 4), cp(P_DIM))
    elif ST.todo_add:
        blink = "_" if int(time.time() * 2) % 2 == 0 else " "
        composer = f"NEW TODO > {ST.todo_buf}{blink}"
        hint = "ENTER add  ESC cancel"
        put(win, top + body_h - 3, center_x + 2, _clip(composer, center_w - 4), cp(P_AMBER, bold=True))
        put(win, top + body_h - 2, center_x + 2, _clip(hint, center_w - 4), cp(P_DIM))
    else:
        input_display = f"INPUT > {DS.user_text[:max(0,center_w-10)]}"
        put(win, top + body_h - 3, center_x + 2, _clip(input_display, center_w - 4), cp(P_CYAN, bold=True))
        if DS.mood == "speaking":
            spec = ST._spec_smooth[:max(8, center_w - 6)]
            bars = ""
            for v in spec:
                lvl = max(0, min(7, int(v * 8)))
                bars += "._-:=+*#"[lvl]
            put(win, top + body_h - 2, center_x + 2, _clip(bars, center_w - 4), cp(P_PINK, bold=True))
        else:
            put(win, top + body_h - 2, center_x + 2, _clip("PROCESSING // READY FOR INPUT", center_w - 4), cp(P_DIM))

    # Right: mission/news/track stack
    items = get_news_items()
    head_1 = items[0].get("title", "No headline") if items else "No headline"
    head_2 = items[1].get("title", "No update") if len(items) > 1 else "No update"
    track = AUDIO.current.get("name", "No track") if AUDIO.current else "No track"
    right_text_w = max(10, right_w - 4)

    put(win, top + 2, right_x + 2, "NOW PLAYING", cp(P_DIM))
    for i, line in enumerate(_wrap(track, right_text_w, limit=2)):
        put(win, top + 3 + i, right_x + 2, line, cp(P_PINK, bold=True))
    put(win, top + 5, right_x + 2, f"AUDIO {'LIVE' if AUDIO.playing else 'PAUSED'}", cp(P_GREEN if AUDIO.playing else P_AMBER, bold=True))
    put(win, top + 6, right_x + 2, "─" * max(0, right_text_w), cp(P_BOX))

    put(win, top + 7, right_x + 2, "GLOBAL FEED", cp(P_DIM))
    feed_lines = _wrap(head_1, right_text_w, limit=2) + _wrap(head_2, right_text_w, limit=2)
    for i, line in enumerate(feed_lines[:4]):
        put(win, top + 8 + i, right_x + 2, line, cp(P_HI if i < 2 else P_MID))
    put(win, top + 12, right_x + 2, "─" * max(0, right_text_w), cp(P_BOX))

    put(win, top + 13, right_x + 2, "TODO LIST", cp(P_DIM))
    todo_count = len(ST.todos)
    todo_done = sum(1 for done, _ in ST.todos if done)
    put(win, top + 14, right_x + 2, f"{todo_done}/{todo_count} completed", cp(P_AMBER, bold=True))
    put(win, top + 15, right_x + 2, "─" * max(0, right_text_w), cp(P_BOX))
    for i, item in enumerate(ST.todos[:max(5, body_h - top - 19)]):
        done, title = item
        mark = "✓" if done else "○"
        line = _clip(f"{mark} {title}", right_text_w - 2)
        put(win, top + 16 + i, right_x + 2, line, cp(P_GREEN if done else P_HI))

    # Footer command rail
    put(win, H - 3, 0, "=" * (W - 1), cp(P_BOX))
    rail = " type any key/t | v voice | m mute | o todo | + - humor | c camera | z/x track | left/right view | esc cancel | q quit "
    put(win, H - 2, max(0, (W - len(rail)) // 2), rail, cp(P_DIM))
    put(win, H - 1, max(0, (W - 40) // 2), "DENJI SYNTHETIC INTERFACE // LIVE", cp(P_CYAN, bold=True))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 1 — DASHBOARD (REVAMPED)
# ══════════════════════════════════════════════════════════════════════════════
def v_dashboard(win, W, H):
    now = datetime.datetime.now()
    sd  = SD.snap()
    clock_data = ios_style_clock(now)

    def _clip(s, n):
        return s if len(s) <= n else s[:max(1, n-1)] + "..."  

    def _marquee(msg, w, speed=4.0):
        if w <= 1:
            return ""
        txt = (msg or "").strip()
        if len(txt) <= w:
            return txt
        pad = "   "
        loop = txt + pad
        off = int(time.time() * speed) % len(loop)
        view = (loop + loop)[off:off + w]
        return view

    # Fallback for very small terminals - still show all panels, just stacked
    if W < 100 or H < 26:
        box(win, 1, 0, H - 2, W - 1, "COMMAND CENTER")
        face = denji_face(DS.mood)
        centre(win, 2, face, cp(P_CYAN, bold=True))
        centre(win, 3, f"State: {DS.mood.upper()}", cp(P_MID))
        centre(win, 4, _clip(f'User: "{DS.user_text}"', W - 4), cp(P_DIM))
        centre(win, 5, _clip(f'Denji: "{DS.response_text}"', W - 4), cp(P_GREEN))
        track = AUDIO.current.get("name", "No track") if AUDIO.current else "No track"
        put(win, 7, 1, _clip(f"♫ {track}", W - 2), cp(P_HI))
        put(win, 8, 1, _clip(f"Mic: {DS.mic_status}  Cam: {DS.camera_status}  Face: {'✓' if DS.face_seen else '✗'}", W - 2), cp(P_DIM))
        prompt = DS.input_buf if DS.input_mode else "type or [v]oice"
        put(win, H - 3, 1, _clip(f"> {prompt}", W - 2), cp(P_AMBER, bold=True))
        put(win, H - 1, 0, " [t]ype  [v]oice  [c]amera  [space]play  [←→]views  [q]uit ", cp(P_DIM))
        return

    # ═══════════════════════════════════════════════════════════════════════════
    #  MAIN 3-COLUMN LAYOUT (30% | 40% | 30%)
    # ═══════════════════════════════════════════════════════════════════════════
    top_y = 1
    footer_y = H - 1
    content_h = footer_y - top_y

    left_w = max(30, W // 4)
    right_w = max(30, W // 4)
    mid_w = W - 1 - left_w - right_w
    left_x, mid_x, right_x = 0, left_w, left_w + mid_w

    # Calculate panel heights (2 rows for top, 1 row for bottom)
    row1_h = max(13, (content_h - 1) // 2)
    row2_h = max(8, content_h - row1_h - 1)
    
    first_y = top_y
    second_y = first_y + row1_h

    # ═══════════════════════════════════════════════════════════════════════════
    #  ROW 1: CLOCK & EVENTS | DENJI | NEWS & MARKET
    # ═══════════════════════════════════════════════════════════════════════════

    # LEFT: ASCII DIGITAL CLOCK
    clock_h = max(9, row1_h // 2)
    box(win, first_y, left_x, clock_h, left_w, "CLOCK")
    ascii_time = clock_data["hour_24"]
    rows = ascii_clock_lines(ascii_time)
    clock_inner_w = max(1, left_w - 2)
    for i, row in enumerate(rows):
        if i >= max(0, clock_h - 3):
            break
        row_txt = row.rstrip()
        if len(row_txt) > clock_inner_w:
            row_txt = row_txt[:clock_inner_w]
        row_x = left_x + max(1, (left_w - len(row_txt)) // 2)
        put(win, first_y + 1 + i, row_x, row_txt, cp(P_HI, bold=True))
    date_short = now.strftime("%a %d %b %Y")
    date_txt = date_short if len(date_short) <= left_w - 2 else date_short[:left_w - 2]
    date_x = left_x + max(1, (left_w - len(date_txt)) // 2)
    put(win, first_y + clock_h - 2, date_x, date_txt, cp(P_DIM))

    # LEFT: UPCOMING EVENTS
    events_h = max(6, row1_h - clock_h - 1)
    box(win, first_y + clock_h, left_x, events_h, left_w, "SCHEDULE")
    evtitle, evtime = next_event()
    e_msg = f"{evtitle} @ {evtime}"
    put(win, first_y + clock_h + 1, left_x + 1, _clip(_marquee(e_msg, left_w - 4), left_w - 4), cp(P_HI))
    put(win, first_y + clock_h + 2, left_x + 1, _clip("Upcoming schedule", left_w - 4), cp(P_DIM))

    # CENTER: DENJI (FULL HEIGHT, ROW 1)
    box(win, first_y, mid_x, row1_h, mid_w, "COMMAND CENTER")
    face = denji_face(DS.mood)
    centre(win, first_y + 2, face, cp(P_CYAN, bold=True) | curses.A_BOLD)
    centre(win, first_y + 3, f"{DS.mood.upper():^{max(10, mid_w - 8)}}", cp(P_GREEN if DS.mood == "happy" else P_AMBER if DS.mood == "sad" else P_MID, bold=True))
    centre(win, first_y + 5, f"Attention: {DS.eye_x:+2d},{DS.eye_y:+2d}  Face {'seen' if DS.face_seen else 'idle'}", cp(P_DIM))
    centre(win, first_y + 6, "Assistant status", cp(P_DIM))
    
    if DS.mood == "speaking":
        vy = first_y + row1_h - 3
        spec = ST._spec_smooth[:max(6, (mid_w - 4) // 2)]
        vis = ""
        for v in spec:
            lvl = max(1, min(8, int(v * 8) + 1))
            vis += "▁▂▃▄▅▆▇█"[lvl - 1]
        centre(win, vy, vis, cp(P_BLUE, bold=True))

    # RIGHT: TOP NEWS
    news_h = max(7, row1_h // 2 - 1)
    box(win, first_y, right_x, news_h, right_w, "NEWS")
    items = get_news_items()
    top_news = items[0].get("title", "No news") if items else "No news"
    put(win, first_y + 1, right_x + 1, _clip(_marquee(top_news, right_w - 4), right_w - 4), cp(P_HI))
    put(win, first_y + 2, right_x + 1, _clip("Latest headlines", right_w - 4), cp(P_DIM))

    # RIGHT: MARKET CONDITION
    market_h = max(6, row1_h - news_h - 1)
    box(win, first_y + news_h, right_x, market_h, right_w, "MARKET")
    put(win, first_y + news_h + 1, right_x + 1, _clip("Stock & crypto data", right_w - 4), cp(P_DIM))
    put(win, first_y + news_h + 2, right_x + 1, _clip("Market status", right_w - 4), cp(P_DIM))

    # ═══════════════════════════════════════════════════════════════════════════
    #  ROW 2: MUSIC | CHAT | LIVE STATUS
    # ═══════════════════════════════════════════════════════════════════════════

    # LEFT: MUSIC PLAYER
    box(win, second_y, left_x, row2_h, left_w, "MUSIC")
    track = AUDIO.current.get("name", "No track") if AUDIO.current else "No track"
    put(win, second_y + 1, left_x + 1, _clip(f"Track: {track}", left_w - 4), cp(P_HI))
    put(win, second_y + 2, left_x + 1,
        _clip(f"State: {'PLAY' if AUDIO.playing else 'PAUSE'}", left_w - 4),
        cp(P_GREEN if AUDIO.playing else P_AMBER))

    # CENTER: CHAT
    box(win, second_y, mid_x, row2_h, mid_w, "INPUT")
    centre(win, second_y + 1, _clip(f'User: "{DS.user_text}"', max(8, mid_w - 6)), cp(P_DIM))
    centre(win, second_y + 2, _clip(f'Denji: "{DS.response_text}"', max(8, mid_w - 6)), cp(P_GREEN))
    prompt = DS.input_buf if DS.input_mode else "[t] type or [v] voice"
    put(win, second_y + 3, mid_x + 1, _clip(f"> {prompt}", mid_w - 4), cp(P_AMBER, bold=True))

    # RIGHT: LIVE STATUS
    box(win, second_y, right_x, row2_h, right_w, "LIVE STATUS")
    put(win, second_y + 1, right_x + 1, _clip(f"Mic: {DS.mic_status}", right_w - 4), cp(P_MID))
    put(win, second_y + 2, right_x + 1, _clip(f"Cam: {DS.camera_status}", right_w - 4), cp(P_MID))
    put(win, second_y + 3, right_x + 1, _clip(f"Voice: {DS.tts_status}", right_w - 4), cp(P_MID))

    # ═══════════════════════════════════════════════════════════════════════════
    #  FOOTER
    # ═══════════════════════════════════════════════════════════════════════════
    put(win, H - 1, 0,
        " t type  v voice  c camera  space play  z/x track  1-6 quick  ←/→ views  q quit ",
        cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 2 — CLOCK + MUSIC
# ══════════════════════════════════════════════════════════════════════════════
def v_clock(win, W, H):
    lib = AUDIO.library
    n = len(lib)

    if W < 90 or H < 24:
        box(win, 1, 0, H - 2, W - 1, "MUSIC")
        td = AUDIO.current if lib else {"name": "No track", "artist": "-", "duration": 0}
        centre(win, 3, td.get("name", "No track")[:max(8, W - 8)], cp(P_HI, bold=True))
        centre(win, 5, td.get("artist", "")[:max(8, W - 8)], cp(P_DIM))
        st = "Playing" if AUDIO.playing else "Paused"
        centre(win, 7, f"State: {st}", cp(P_GREEN if AUDIO.playing else P_AMBER))
        if H > 13:
            draw_spectrum(win, 9, 2, max(2, H - 14), max(4, W - 4), ST._spec_smooth)
        put(win, H - 1, 0, " [space] play/pause  [z/x] prev/next  [<- ->] views  [q] quit ", cp(P_DIM))
        return

    put(win, 1, 2, "MUSIC DASHBOARD", cp(P_HI, bold=True) | curses.A_BOLD)
    put(win, 2, 0, "─" * W, cp(P_BOX))

    top_y = 3
    shortcuts_h = 4
    sc_y = H - shortcuts_h
    usable_h = max(14, sc_y - top_y - 1)
    top_h = max(9, int(usable_h * 0.62))
    bottom_y = top_y + top_h + 1
    bottom_h = max(6, sc_y - bottom_y)

    # Top full-width: library
    box(win, top_y, 1, top_h, W - 2, "LIBRARY")
    tabs = [("ALL", "all"), ("BUILT-IN", "builtin"), ("YOUTUBE", "youtube"), ("FILES", "file")]
    tx = 3
    for label, key in tabs:
        active = (LS.filter == key)
        attr = (cp(P_CYAN, bold=True) | curses.A_REVERSE) if active else cp(P_DIM)
        pill = f" {label} "
        put(win, top_y + 1, tx, pill, attr)
        tx += len(pill) + 1

    idxs = _lib_filtered_indices()
    fn = len(idxs)
    put(win, top_y + 1, W - 18, f"{fn}/{n} shown", cp(P_DIM))
    put(win, top_y + 2, 2, "─" * (W - 4), cp(P_BOX))
    put(win, top_y + 3, 3, "SRC", cp(P_DIM, bold=True))
    put(win, top_y + 3, 9, "TITLE", cp(P_DIM, bold=True))
    put(win, top_y + 3, W - 14, "LENGTH", cp(P_DIM, bold=True))
    put(win, top_y + 4, 2, "─" * (W - 4), cp(P_BOX))

    rows = max(1, top_h - 7)
    if fn > 0:
        if LS.cursor not in idxs:
            LS.cursor = idxs[0]
        cpos = idxs.index(LS.cursor)
        start = max(0, min(cpos - rows // 2, max(0, fn - rows)))
        vis = idxs[start:start + rows]
    else:
        vis = []

    for i, ri in enumerate(vis):
        trk = lib[ri]
        ry = top_y + 5 + i
        sel = (ri == LS.cursor)
        now = (ri == AUDIO.track_idx)
        src = trk.get("source", "")
        src_icon = "B" if src == "builtin" else "Y" if ("youtube" in src or "youtu.be" in src) else "F"
        durv = trk.get("duration", 0) or 0
        lens = f"{int(durv)//60}:{int(durv)%60:02d}" if durv > 0 else "live"
        attr = cp(P_CYAN) | curses.A_REVERSE if sel else cp(P_GREEN if now else P_MID)
        if sel:
            put(win, ry, 2, " " * (W - 4), attr)
        put(win, ry, 3, src_icon, attr)
        put(win, ry, 5, "▶" if now else "•", cp(P_GREEN if now else P_DIM))
        put(win, ry, 9, trk.get("name", "")[:max(8, W - 25)], attr)
        put(win, ry, W - 14, lens[:10], attr)

    if fn == 0:
        centre(win, top_y + top_h // 2, "No tracks in this filter", cp(P_DIM))

    # Bottom split: left player, right spectrum
    left_w = W // 2
    right_x = left_w
    right_w = W - right_x

    box(win, bottom_y, 1, bottom_h, left_w - 1, "PLAYER")
    td = AUDIO.current if lib else {"name": "No track", "artist": "-", "duration": 0}
    dur = float(td.get("duration") or 0)
    with AUDIO._lock:
        elapsed = float(AUDIO.elapsed)
    if dur > 0:
        elapsed = min(elapsed, dur)
        pct = int(elapsed / dur * 100)
    else:
        pct = int((elapsed % 60) / 60 * 100)
    em, es = divmod(int(elapsed), 60)
    dm, ds2 = divmod(int(dur), 60) if dur > 0 else (0, 0)

    inner_w = max(16, left_w - 8)
    name_w = max(8, inner_w - 26)
    name_txt = td.get("name", "")[:name_w]
    put(win, bottom_y + 1, 3, name_txt, cp(P_HI, bold=True))

    chip_x = 3 + len(name_txt) + 2
    rep_chip = " R "
    shf_chip = " S "
    rep_attr = (cp(P_CYAN, bold=True) | curses.A_REVERSE) if AUDIO.repeat else cp(P_DIM)
    shf_attr = (cp(P_CYAN, bold=True) | curses.A_REVERSE) if AUDIO.shuffle else cp(P_DIM)
    if chip_x < left_w - 10:
        put(win, bottom_y + 1, chip_x, rep_chip, rep_attr)
        put(win, bottom_y + 1, chip_x + len(rep_chip) + 1, shf_chip, shf_attr)

    put(win, bottom_y + 2, 3, td.get("artist", "")[:max(8, left_w - 8)], cp(P_DIM))
    hbar(win, bottom_y + 3, 3, max(8, left_w - 8), pct, P_CYAN)
    put(win, bottom_y + 4, 3, f"{em}:{es:02d}", cp(P_DIM))
    put(win, bottom_y + 4, max(4, left_w - 9), f"{dm}:{ds2:02d}" if dur > 0 else "live", cp(P_DIM))

    play_chip = " Play/Pause (Space) "
    play_attr = cp(P_GREEN, bold=True) if AUDIO.playing else cp(P_AMBER, bold=True)
    put(win, bottom_y + 5, 3, play_chip, play_attr | curses.A_REVERSE)
    put(win, bottom_y + 6, 3, "Prev (Z)  Next (X)   Repeat (R)  Shuffle (S)", cp(P_DIM))

    box(win, bottom_y, right_x, bottom_h, right_w, "SPECTRUM")
    spec_h = max(1, bottom_h - 2)
    draw_spectrum(win, bottom_y + 1, right_x + 1, spec_h, right_w - 2, ST._spec_smooth)

    # Bottom input/confirm panel for LS modes
    if LS.mode in ("add_url", "add_file", "confirm_del"):
        oy = max(3, H // 2 - 3)
        ow = min(W - 6, 86)
        ox = (W - ow) // 2
        if LS.mode == "confirm_del":
            box(win, oy, ox, 4, ow, "REMOVE TRACK")
            trk = lib[LS.cursor] if 0 <= LS.cursor < len(lib) else {}
            centre(win, oy + 1,
                   f"Remove '{trk.get('name','?')[:40]}' ?  Y=yes  N/Esc=cancel",
                   cp(P_RED, bold=True))
        else:
            title = "ADD YOUTUBE" if LS.mode == "add_url" else "ADD LOCAL FILE"
            box(win, oy, ox, 6, ow, title)
            put(win, oy + 1, ox + 2, "Paste and press Enter", cp(P_DIM))
            blink = "_" if int(time.time() * 2) % 2 else " "
            disp = LS.buf if len(LS.buf) <= ow - 8 else "..." + LS.buf[-(ow - 11):]
            put(win, oy + 2, ox + 2, (disp + blink)[:ow-4], cp(P_AMBER, bold=True))
            put(win, oy + 4, ox + 2, "Esc to cancel", cp(P_DIM))

    box(win, sc_y, 1, shortcuts_h, W - 2, "SHORTCUTS")

    if W >= 140:
        line1 = "Library: 1/2/3/4 filter | j/k browse | Enter play | Y add URL | F add file | D remove"
        line2 = "Player: Space play/pause | Z/X prev-next | R repeat | S shuffle | Left/Right switch views"
    elif W >= 115:
        line1 = "Library: 1/2/3/4 filter | j/k browse | Enter play | Y URL | F file | D remove"
        line2 = "Player: Space play/pause | Z/X prev-next | R repeat | S shuffle | ←/→ views"
    else:
        line1 = "Library: 1-4 filter | j/k | Enter | Y/F add | D remove"
        line2 = "Player: Space | Z/X | R repeat | S shuffle | ←/→ views"

    centre(win, sc_y + 1, line1[:W-6], cp(P_DIM))
    centre(win, sc_y + 2, line2[:W-6], cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 3 — FOCUS / POMODORO
# ══════════════════════════════════════════════════════════════════════════════
def v_focus(win, W, H):
    fm   = ST.focus_modes[ST.focus_idx]
    pc   = P_RED if ST.pomo_phase=="WORK" else P_GREEN

    centre(win, 1, f"FOCUS MODE  ·  {fm}", cp(P_HI,bold=True)|curses.A_BOLD)

    pm=int(ST.pomo_secs)//60; ps=int(ST.pomo_secs)%60
    pct=1.0-ST.pomo_secs/max(1,ST.pomo_total)
    aw=min(W-10,52); filled=int(pct*aw)
    centre(win, 3, "╺"+"━"*filled+"╌"*(aw-filled)+"╸", cp(pc))

    ts = f"{pm:02d}:{ps:02d}"
    big_time(win, 5, max(0,(W-btw(ts))//2), ts, pc)

    phase_s="[*] WORK" if ST.pomo_phase=="WORK" else "[~] BREAK"
    centre(win,11,phase_s,cp(pc))
    dots=" ".join("◉" if i<ST.pomo_done else "○" for i in range(8))
    centre(win,12,dots,cp(P_DIM))

    cw=min(W-6,48); cx=(W-cw)//2; cy=14
    box(win,cy,cx,10,cw,"CONTROLS")
    rl="||  PAUSE" if ST.pomo_run else "▶  START"
    rc=P_AMBER if ST.pomo_run else P_GREEN
    def ctrl(r,l,h,col=P_MID): put(win,cy+r,cx+3,f"{l:<22}",cp(col)); put(win,cy+r,cx+25,h,cp(P_DIM))
    ctrl(1,rl,"[p]",rc)
    ctrl(2,"↺  RESET TIMER","[r]")
    ctrl(3,">|  SKIP PHASE","[s]")
    ctrl(4,f"[>]  MODE: {fm[:14]}","[f]")
    ctrl(5,f"Sessions: {ST.pomo_done}  ({ST.pomo_done*25} min)","")

    gw=min(W-8,52); gx=(W-gw)//2; gy=cy+11
    gp=min(100,ST.pomo_done*25*100//120)
    put(win,gy,gx,f"Daily goal: {ST.pomo_done*25}/120 min  ({gp}%)",cp(P_DIM))
    hbar(win,gy+1,gx,gw,gp,P_GREEN)

    vy=gy+3
    vis_h=max(2,H-vy-3)
    if vy+vis_h+1<H:
        box(win,vy,2,vis_h+2,W-4,"MUSIC")
        draw_spectrum(win,vy+1,3,vis_h,W-6,ST._spec_smooth)

    put(win,H-1,0," p start/pause  r reset  s skip  f mode  ←/→ views  q quit ",cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  OS DETECTION & ASCII LOGOS
# ══════════════════════════════════════════════════════════════════════════════

def draw_windows_logo(win, y, x):
    """Draw stylized Windows 11 logo in ASCII."""
    logo = [
        "  ╔════╗  ╔════╗",
        "  ║ ▄▄ ║  ║ ▄▄ ║",
        "  ║▄▄▄▄║  ║▄▄▄▄║",
        "  ╚════╝  ╚════╝",
        "  ╔════╗  ╔════╗",
        "  ║ ▄▄ ║  ║ ▄▄ ║",
        "  ║▄▄▄▄║  ║▄▄▄▄║",
        "  ╚════╝  ╚════╝",
    ]
    for i, line in enumerate(logo):
        if y + i < win.getmaxyx()[0]:
            put(win, y + i, x, line, cp(P_CYAN, bold=True))
    return len(logo)

def draw_linux_logo(win, y, x):
    """Draw Tux penguin (Linux logo) in ASCII."""
    logo = [
        "    ▄▀▀▀▀▀●",
        "   █  ○ ○ ●",
        "   ▀▄   ᴒ█",
        "     ▀█▄●▀",
        "     ▄█▀▀",
        "    ██▀▀█",
        "    ██  █",
    ]
    for i, line in enumerate(logo):
        if y + i < win.getmaxyx()[0]:
            put(win, y + i, x, line, cp(P_AMBER, bold=True))
    return len(logo)

def draw_system_logo(win, y, x):
    """Draw appropriate OS logo based on system detected."""
    if platform.system() == "Windows":
        return draw_windows_logo(win, y, x)
    else:
        return draw_linux_logo(win, y, x)

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 4 — NEOFETCH
# ══════════════════════════════════════════════════════════════════════════════

def v_neofetch(win, W, H):
    sd       = SD.snap()

    # ── Layout ────────────────────────────────────────────────────────────
    _, main_w, _, _ = _responsive_layout(W)
    frame_w = min(max(78, main_w - 4), 122)
    frame_x = max(1, (main_w - frame_w) // 2)
    frame_y = 1
    frame_h = max(14, H - 5)

    box(win, frame_y, frame_x, frame_h, frame_w, "SYSTEM OVERVIEW")

    AX     = frame_x + 2                # logo left edge
    AY     = frame_y + 1                # logo top
    LOGO_W = min(26, max(22, frame_w // 4))
    IX     = AX + LOGO_W + 2            # info column starts here
    KEY_W  = 11         # width of key label field
    VAL_X  = IX + KEY_W

    # Pac-Man only
    logo_h = draw_animated_logo(win, AY, AX, ST._anim_t)

    # ── Collect all values ────────────────────────────────────────────────
    uh, rem   = divmod(sd.get("uptime", 0), 3600)
    um        = rem // 60
    mem_used  = sd.get("mem_used",  0.0)
    mem_total = sd.get("mem_total", 8.0)
    cpu_val   = sd.get("cpu",       0.0)
    disk_pct  = sd.get("disk_pct",  0.0)
    bat_pct   = sd.get("bat_pct",   100)
    bat_plug  = sd.get("bat_plug",  True)
    net_dn    = sd.get("net_dn",    0.0)
    net_up    = sd.get("net_up",    0.0)
    user      = os.environ.get("USER", os.environ.get("USERNAME", "user"))
    # Terminal emulator detection
    if platform.system() == "Windows":
        if os.environ.get("WT_SESSION"):
            term_emu = "Windows Terminal"
        elif os.environ.get("TERM_PROGRAM"):
            term_emu = os.environ["TERM_PROGRAM"]
        elif os.environ.get("ConEmuPID"):
            term_emu = "ConEmu"
        elif os.environ.get("CMDER_ROOT"):
            term_emu = "Cmder"
        elif os.environ.get("ALACRITTY_SOCKET"):
            term_emu = "Alacritty"
        elif os.environ.get("TERM") == "xterm-256color":
            term_emu = os.environ.get("TERM", "xterm-256color")
        else:
            term_emu = "conhost"
    else:
        term_emu = (os.environ.get("TERM_PROGRAM") or
                    os.environ.get("TERM") or "unknown")

    uptime_s = f"{uh}h {um:02d}m" if uh else f"{um}m"
    mem_s    = f"{mem_used:.0f} MiB / {mem_total*1024:.0f} MiB"

    # Build info rows — (key, value) pairs
    info = [
        ("OS",         sd.get("os_str",     platform.system())),
        ("Host",       sd.get("hostname",   socket.gethostname())),
        ("Kernel",     sd.get("kernel",     platform.release())),
        ("Uptime",     uptime_s),
        ("Packages",   sd.get("pkg_count",  "…")),
        ("Shell",      sd.get("shell",      os.environ.get("SHELL","?").split("/")[-1])),
        ("Resolution", sd.get("resolution", "N/A")),
        ("DE / WM",    sd.get("de_wm",      "N/A")),
        ("Terminal",   term_emu),
        ("CPU",        sd.get("cpu_name",   "N/A")),
        ("GPU",        sd.get("gpu_name",   "N/A")),
        ("Memory",     mem_s),
        ("Disk",       f"{disk_pct:.0f}% used"),
        ("Battery",    f"{bat_pct}%  {'charging' if bat_plug else 'on battery'}"),
        ("Local IP",   sd.get("local_ip",   "N/A")),
        ("WiFi",       sd.get("ssid",       "N/A")),
        ("Cores",      str(sd.get("cpu_cores", os.cpu_count() or 1))),
    ]

    # ── user@host header ──────────────────────────────────────────────────
    host      = sd.get("hostname", socket.gethostname())
    user_host = f"{user}@{host}"
    max_info_w = max(1, (frame_x + frame_w - 2) - VAL_X)

    put(win, AY,   IX, user_host[:max_info_w], cp(P_HI, bold=True))
    put(win, AY+1, IX, "─" * min(len(user_host), max_info_w), cp(P_BOX))

    # ── info rows ─────────────────────────────────────────────────────────
    for i, (k, v) in enumerate(info):
        ry = AY + 2 + i
        if ry >= H - 6:
            break
        put(win, ry, IX,    f"{k:<{KEY_W}}", cp(P_CYAN, bold=True))
        put(win, ry, VAL_X, str(v)[:max_info_w], cp(P_HI))

    # ── colour swatches (like neofetch) ───────────────────────────────────
    info_rows_drawn = min(len(info), H - 6 - AY - 2)
    pal_y = AY + 2 + info_rows_drawn + 1
    if pal_y + 2 < H - 4:
        palettes = [P_RED, P_GREEN, P_AMBER, P_CYAN, P_BLUE, P_PINK, P_HI, P_DIM]
        put(win, pal_y, IX, "".join("██" for _ in palettes),
            cp(P_HI))
        for i, c in enumerate(palettes):
            put(win, pal_y,   IX + i*2, "██", cp(c))
        for i, c in enumerate(palettes):
            put(win, pal_y+1, IX + i*2, "██", cp(c, bold=True))

    # ── live resource bars (full width, below everything) ─────────────────
    bar_top = max(AY + logo_h + 1, pal_y + 3)
    bar_h   = 8
    bw      = max(24, frame_w - 12)
    if bar_top + bar_h < min(H - 2, frame_y + frame_h):
        box(win, bar_top, frame_x + 2, bar_h, frame_w - 4, "LIVE RESOURCES")
        res_rows = [
            ("CPU  ", int(cpu_val),                              P_CYAN),
            ("MEM  ", int(mem_used / max(mem_total, 0.1) * 100), P_BLUE),
            ("DISK ", int(disk_pct),                             P_AMBER),
            ("BAT  ", bat_pct,  P_GREEN if bat_pct > 40 else P_RED),
            ("NET↓ ", min(100, int(net_dn / 500 * 100)),         P_GREEN),
            ("NET↑ ", min(100, int(net_up / 200 * 100)),         P_PINK),
        ]
        for i, (lbl, pct, col) in enumerate(res_rows):
            ry = bar_top + 1 + i
            if ry >= H - 2: break
            bar_x = frame_x + 4
            put(win, ry, bar_x, lbl, cp(P_DIM))
            hbar(win, ry, bar_x + 5, bw, pct, col)
            put(win, ry, bar_x + 6 + bw, f"{pct:3d}%", cp(col))

    put(win, H-1, 0,
        " system overview  ·  ←/→ views  ·  q quit ",
        cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 5 — NETWORK + DEVICES
# ══════════════════════════════════════════════════════════════════════════════
def v_network(win, W, H):
    sd  = SD.snap()
    hw  = W//2-1

    box(win,1,0,14,hw,"NETWORK")
    rows=[("SSID",sd.get("ssid","N/A")),("LOCAL IP",sd.get("local_ip","N/A")),
          ("HOST",sd.get("hostname","N/A")),("↓ RECV",kbfmt(sd.get("net_dn",0))),
          ("↑ SEND",kbfmt(sd.get("net_up",0))),("CPU",f"{sd.get('cpu',0):.1f}%"),
          ("MEM",f"{sd.get('mem_pct',0):.1f}%"),("DISK",f"{sd.get('disk_pct',0):.0f}%")]
    for i,(k,v) in enumerate(rows):
        put(win,2+i,2,f"{k:<9}",cp(P_DIM)); put(win,2+i,11,v[:hw-14],cp(P_HI))

    net_dn = sd.get("net_dn", 0); net_up = sd.get("net_up", 0)
    put(win,10,2,"DOWN",cp(P_DIM)); hbar(win,10,7,hw-10,min(100,int(net_dn/1000*100)),P_GREEN)
    put(win,11,2,"UP  ",cp(P_DIM)); hbar(win,11,7,hw-10,min(100,int(net_up/500*100)), P_BLUE)
    put(win,12,2,"CPU ",cp(P_DIM)); hbar(win,12,7,hw-10,int(sd.get("cpu",0)),P_CYAN)

    rx=hw+1; rw=W-rx-1
    devices = SD.devices
    _tc = {"BT":P_CYAN,"USB":P_BLUE,"CTRL":P_PINK,"PHONE":P_GREEN,
            "AUDIO":P_AMBER,"KBD":P_DIM,"HID":P_DIM,"CAM":P_DIM,
            "STOR":P_MID,"MTP":P_GREEN,"USB-C":P_BLUE}

    max_rows = min(len(devices), (14-2))
    box(win,1,rx,max(6, max_rows*2+2),rw,
        f"CONNECTED DEVICES ({len(devices)})" if devices else "CONNECTED DEVICES")

    if not devices:
        put(win,3,rx+2,"No devices found",cp(P_DIM))
        put(win,4,rx+2,"(scanning...)" if SD._dev_last==0 else "(none connected)",cp(P_DIM))
    else:
        for i, dev in enumerate(devices[:max_rows]):
            ry  = 2 + i
            bat = dev.get("battery")
            dtype = dev.get("type","")
            if bat is not None:
                bc      = P_GREEN if bat>40 else (P_AMBER if bat>15 else P_RED)
                right_s = f"{bat}%"
                right_c = cp(bc, bold=True)
            elif dtype != "BT":
                right_s = f"[{dtype}]"
                right_c = cp(_tc.get(dtype, P_DIM))
            else:
                right_s = ""
                right_c = 0
            name_w = rw - len(right_s) - 4
            put(win, ry, rx+2, dev["name"][:name_w], cp(P_HI))
            if right_s:
                put(win, ry, rx+rw-len(right_s)-2, right_s, right_c)

    bat=sd.get("bat_pct",100); plug=sd.get("bat_plug",True)
    bc=P_GREEN if bat>40 else (P_AMBER if bat>15 else P_RED)
    n_devs   = min(len(SD.devices), 14)
    bat_y    = max(16, 3 + n_devs + 2)
    box(win,bat_y,0,7,W-1,"BATTERY & POWER")
    put(win,bat_y+1,2,f"{'+ CHARGING' if plug else '  ON BATTERY'}  {bat}%  system",cp(bc,bold=True))
    hbar(win,bat_y+2,2,W-5,bat,bc)
    put(win,bat_y+3,2,"charging" if plug else f"~{int(bat*1.5)} min remaining",cp(P_DIM))
    bt_bats = [(d["name"][:14],d["battery"]) for d in SD.devices
               if d.get("battery") is not None]
    if bt_bats:
        bx = 2
        for dname,dbat in bt_bats[:4]:
            dbc = P_GREEN if dbat>40 else (P_AMBER if dbat>15 else P_RED)
            s = f"{dname}: {dbat}%  "
            put(win,bat_y+4,bx,s,cp(dbc))
            bx += len(s)
    else:
        put(win,bat_y+4,2,f"cpu {sd.get('cpu',0):.0f}%  mem {sd.get('mem_pct',0):.0f}%  disk {sd.get('disk_pct',0):.0f}%",cp(P_DIM))

    vy=24; vis_h=max(2,H-vy-3)
    if vy+vis_h+1<H:
        box(win,vy,0,vis_h+2,W-1,"SPECTRUM")
        draw_spectrum(win,vy+1,1,vis_h,W-3,ST._spec_smooth)

    put(win,H-1,0," real-time data  ·  ←/→ views  ·  q quit ",cp(P_DIM))


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 6 — MUSIC LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
class LibState:
    cursor   = 0
    filter   = "all"
    mode     = "browse"
    buf      = ""
    msg      = ""
    msg_time = 0.0

LS = LibState()


def _lib_matches_filter(trk, fkey):
    src = trk.get("source", "")
    is_builtin = (src == "builtin")
    is_youtube = (not is_builtin) and ("youtube" in src or "youtu.be" in src)
    if fkey == "builtin":
        return is_builtin
    if fkey == "youtube":
        return is_youtube
    if fkey == "file":
        return (not is_builtin) and (not is_youtube)
    return True


def _lib_filtered_indices():
    lib = AUDIO.library
    return [i for i, trk in enumerate(lib) if _lib_matches_filter(trk, LS.filter)]

# ══════════════════════════════════════════════════════════════════════════════
#  CHROME
# ══════════════════════════════════════════════════════════════════════════════
def draw_topbar(win, W):
    now = datetime.datetime.now(); sd = SD.snap()
    ts = now.strftime("%H:%M:%S")
    ds = now.strftime("%a %d %b")
    bat = sd.get("bat_pct", 100); plug = sd.get("bat_plug", True)
    bc = P_GREEN if bat > 40 else (P_AMBER if bat > 15 else P_RED)

    clear_line(win, 0, 0, W, cp(P_BOX))
    divider(win, 0, W, 0, cp(P_BOX))

    brand = " DENJI STANDBY "
    put(win, 0, 1, brand, cp(P_CYAN, bold=True))

    if ST.view == 0 and ST.pomo_run:
        pm = int(ST.pomo_secs) // 60
        ps = int(ST.pomo_secs) % 60
        center_text = f"FOCUS {ST.pomo_phase} {pm:02d}:{ps:02d}"
    else:
        center_text = ALL_VIEW_NAMES[ST.view] if 0 <= ST.view < len(ALL_VIEW_NAMES) else "UNKNOWN VIEW"
    put(win, 0, max(1, (W - len(center_text)) // 2), center_text, cp(P_HI, bold=True))

    status_text = f"{ts}  {ds}"
    if AUDIO.playing and AUDIO.current:
        status_text = f"{status_text}  •  {AUDIO.current.get('name', '')[:18]}"
    right_text = f"{'+' if plug else ' '} {bat:>3}%  CPU {sd.get('cpu', 0):>4.0f}%  MEM {sd.get('mem_pct', 0):>4.0f}%"
    right_x = max(20, W - len(right_text) - 2)
    put(win, 0, right_x - len(status_text) - 2, trim_text(status_text, max(0, right_x - 3)), cp(P_DIM))
    put(win, 0, W - len(right_text) - 1, right_text, cp(bc, bold=True))

def draw_navbar(win, W, H):
    active_view = ST.view if ST.view in NAV_CYCLE_VIEWS else HUB_VIEW_IDX
    labels = ["Home", "Music", "Focus", "System", "Net", "Cal", "Video", "Hub"]
    segments = []
    for idx, view_idx in enumerate(NAV_CYCLE_VIEWS):
        label = labels[idx]
        segments.append(f"{label}" if view_idx != active_view else f"[{label}]")
    nav = "  ".join(segments)
    put(win, H - 2, 2, "←/→ navigate", cp(P_DIM))
    centre(win, H - 2, nav[:max(0, W - 24)], cp(P_DIM))
    put(win, H - 2, max(2, W - 15), "q quit", cp(P_DIM))


def draw_footer(win, W, H):
    """Unified bottom menu bar for all views."""
    hints = {
        0: "t type  v voice  c camera  space play  z/x track  1-6 quick",
        1: "1-4 filter  j/k browse  enter play  y URL  f file  d remove",
        2: "p start/pause  r reset  s skip  f mode",
        3: "system overview only  ←/→ views  q quit",
        4: "network, battery, devices, and spectrum  ←/→ views  q quit",
        5: "day/week/month/year  1-4 modes  a add  G connect  D disconnect  r refresh",
        6: "o file  y YouTube  s stop  t terminal/window  a ASCII  k force stop",
        7: "1 news  2 stocks  3 markets  r refresh",
        8: "1 news  2 stocks  j/k scroll  enter open  C country  r refresh",
        9: "1-4 sections  j/k scroll  a add  d remove  r refresh",
    }

    divider(win, H - 3, W, 0, cp(P_BOX))
    clear_line(win, H - 1, 0, W, cp(P_BOX))
    put(win, H - 1, 1, "q quit", cp(P_HI, bold=True))
    put(win, H - 1, max(1, W - 18), "←/→ switch view", cp(P_DIM))

    msg = hints.get(ST.view, "Use arrow keys to navigate views.")
    room = W - 24
    if room > 16:
        put(win, H - 1, max(12, (W - len(msg)) // 2), trim_text(msg, room), cp(P_DIM))


def _responsive_layout(W):
    """Return (main_x, main_w, rail_x, rail_w) for balanced fullscreen layout."""
    max_main_w = 136

    if W < 132:
        return 0, W, None, 0

    rail_w = min(40, max(34, W // 4))
    avail_main = W - rail_w - 1
    main_w = min(avail_main, max_main_w)

    if main_w < 84:
        # Fallback: centered single pane with no side rail.
        main_w = min(W, max_main_w)
        main_x = max(0, (W - main_w) // 2)
        return main_x, main_w, None, 0

    total_w = main_w + 1 + rail_w
    main_x = max(0, (W - total_w) // 2)
    rail_x = main_x + main_w + 1
    return main_x, main_w, rail_x, rail_w


def _view_hint_lines():
    hints = {
        0: ["Dashboard: quick command surface", "t type, v voice, c camera", "space toggles music"],
        1: ["Library: 1-4 filter views", "j/k move selection, enter plays", "y add URL, f add file, d remove"],
        2: ["Focus: pomodoro workflow", "p start/pause, r reset, s skip", "f cycles focus modes"],
        3: ["System overview: hardware + OS", "Animated logo and live resource bars", "No extra actions on this page"],
        4: ["Network: bandwidth + devices", "Tracks Bluetooth, USB, and battery", "No dedicated actions on this page"],
        5: ["Calendar: day/week/month/year", "1-4 change view, a add event", "G connect ICS, D disconnect, r refresh"],
        6: ["Video: local + YouTube playback", "o open file, y open URL, s stop", "t changes terminal/window mode, a ASCII"],
        7: ["Hub: jump to news tools", "1 news, 2 stocks, 3 markets", "r refreshes everything"],
        8: ["News & Stocks: split tabs", "1/2 tabs, C change country", "j/k scroll, enter open, r refresh"],
        9: ["ETF / Crypto / Forex / Commodities", "1-4 sections, j/k scroll", "a add symbol, d remove, r refresh"],
    }
    return hints.get(ST.view, ["Use left/right arrows to navigate views", "Press Q to quit", "Live data updates continuously"])


def draw_side_rail(win, x, w, H):
    """Extra wide-screen content rail shared across all views."""
    if w < 24:
        return

    now = datetime.datetime.now()
    sd = SD.snap()
    bat = sd.get("bat_pct", 100)
    bat_col = P_GREEN if bat > 40 else (P_AMBER if bat > 15 else P_RED)

    try:
        for y in range(1, H - 1):
            put(win, y, x - 1, "│", cp(P_BOX))
    except Exception:
        pass

    y = 1
    h1 = min(10, max(7, H // 5))
    if y + h1 < H - 2:
        box(win, y, x, h1, w, "SYSTEM")
        put(win, y + 1, x + 2, now.strftime("%A"), cp(P_HI, bold=True))
        put(win, y + 2, x + 2, now.strftime("%d %b %Y  %H:%M"), cp(P_DIM))
        divider(win, y + 3, w - 4, x + 2, cp(P_BOX))
        put(win, y + 4, x + 2, f"CPU  {sd.get('cpu', 0):5.1f}%", cp(P_DIM))
        put(win, y + 5, x + 2, f"MEM  {sd.get('mem_pct', 0):5.1f}%", cp(P_DIM))
        put(win, y + 6, x + 2, f"DSK  {sd.get('disk_pct', 0):5.1f}%", cp(P_DIM))
        put(win, y + 7, x + 2, f"BAT  {bat:5.1f}%", cp(bat_col, bold=True))
    y += h1

    h2 = min(10, max(7, H // 5))
    if y + h2 < H - 2:
        box(win, y, x, h2, w, "NOW PLAYING")
        if AUDIO.playing:
            td = AUDIO.current
            put(win, y + 1, x + 2, "ACTIVE", cp(P_GREEN, bold=True))
            put(win, y + 2, x + 2, trim_text(td.get("name", "Track"), w - 4), cp(P_HI))
            put(win, y + 3, x + 2, trim_text(td.get("artist", ""), w - 4), cp(P_DIM))
            dur = int(td.get("duration", 0) or 0)
            el = int(AUDIO.elapsed)
            put(win, y + 5, x + 2, f"{el // 60:02d}:{el % 60:02d} / {dur // 60:02d}:{dur % 60:02d}", cp(P_DIM))
            bw = max(8, w - 4)
            pct = int((el / max(1, dur)) * 100) if dur > 0 else 0
            hbar(win, y + 6, x + 2, bw - 2, pct, P_CYAN)
        else:
            put(win, y + 2, x + 2, "No music playing", cp(P_DIM))
            put(win, y + 4, x + 2, "Space toggles playback", cp(P_DIM))
            put(win, y + 5, x + 2, "Z/X move tracks", cp(P_DIM))
    y += h2

    h3 = max(6, H - y - 2)
    if h3 >= 6:
        box(win, y, x, h3, w, "VIEW HELP")
        vn = ALL_VIEW_NAMES[ST.view] if 0 <= ST.view < len(ALL_VIEW_NAMES) else "UNKNOWN"
        put(win, y + 1, x + 2, trim_text(vn, w - 4), cp(P_CYAN, bold=True))
        lines = _view_hint_lines()
        for i, line in enumerate(lines[:max(1, h3 - 4)]):
            put(win, y + 3 + i, x + 2, trim_text(line, w - 4), cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  TEXT INPUT HELPER
# ══════════════════════════════════════════════════════════════════════════════
def _text_input(buf, k):
    if k in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
        return buf[:-1]
    if k == 23:
        parts = buf.rstrip().rsplit(None, 1)
        return parts[0] + " " if len(parts) > 1 else ""
    if k == 21:
        return ""
    if k < 32 or k > 0x10FFFF:
        return buf
    try:
        return buf + chr(k)
    except (ValueError, OverflowError):
        return buf


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 7 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
class CalState:
    mode      = "week"
    date      = datetime.datetime.now().date()
    add_mode  = False
    add_step  = 0
    add_date  = datetime.datetime.now().date()
    add_hour  = 9
    add_min   = 0
    add_title = ""
    del_mode  = False
    del_idx   = -1
    cur_ev    = 0
    ics_mode  = False
    ics_buf   = ""
    ics_step  = 0
    ics_name_buf = ""
    ics_sel_mode = False
    ics_sel_idx = 0
    msg       = ""
    msg_time  = 0.0
    local_evs = []

CS = CalState()
try:
    with open(CAL_FILE) as _f:
        CS.local_evs = json.load(_f)
except Exception:
    CS.local_evs = []


def _evs_for_day(d):
    with _CAL_LOCK:
        evs = list(_CAL_EVENTS)
    return [(s, e, t) for s, e, t in evs if s.date() == d]


def _evs_for_week(d):
    monday = d - datetime.timedelta(days=d.weekday())
    week   = [monday + datetime.timedelta(days=i) for i in range(7)]
    with _CAL_LOCK:
        evs = list(_CAL_EVENTS)
    result = {day: [] for day in week}
    for s, e, t in evs:
        if s.date() in result:
            result[s.date()].append((s, t))
    return week, result


def _evs_for_month(d):
    import calendar as _cal
    first = d.replace(day=1)
    days_in = _cal.monthrange(d.year, d.month)[1]
    all_days = [first + datetime.timedelta(days=i) for i in range(days_in)]
    start_pad = first.weekday()
    end_pad   = (7 - (days_in + start_pad) % 7) % 7
    grid = ([None]*start_pad + all_days +
            [first + datetime.timedelta(days=days_in+i) for i in range(end_pad)])
    weeks = [grid[i:i+7] for i in range(0, len(grid), 7)]
    with _CAL_LOCK:
        evs = list(_CAL_EVENTS)
    ev_map = {}
    for s, e, t in evs:
        if s.year == d.year and s.month == d.month:
            ev_map.setdefault(s.date(), []).append(t)
    return weeks, ev_map


def _cal_draw_header(win, W, H, now, today):
    """Apple Calendar-style header: month/year left, nav arrows, view tabs right."""
    # ── Month / Year ──────────────────────────────────────────────────────────
    month_lbl = CS.date.strftime("%B")
    year_lbl  = CS.date.strftime("%Y")
    put(win, 0, 2, month_lbl, cp(P_HI, bold=True))
    put(win, 0, 2 + len(month_lbl) + 1, year_lbl, cp(P_DIM))

    # ── Today button ──────────────────────────────────────────────────────────
    today_lbl = " Today "
    today_x   = len(month_lbl) + len(year_lbl) + 6
    today_col = cp(P_CYAN) if CS.date != today else cp(P_DIM)
    put(win, 0, today_x, today_lbl, today_col)

    # ── View-mode tabs (pill style with brackets) ─────────────────────────────
    tabs     = [("Day","1"), ("Week","2"), ("Month","3"), ("Year","4")]
    tab_str  = ""
    tab_pos  = []
    for name, key in tabs:
        tab_pos.append((len(tab_str), name))
        tab_str += f" {name} "
    tx = W - len(tab_str) - 3

    n_conn = get_connected_ics_count()
    conn = f"iCal {n_conn}" if n_conn else "iCal 0"
    conn_col = cp(P_GREEN, bold=True) if n_conn else cp(P_DIM)
    conn_x = max(today_x + len(today_lbl) + 1, tx - len(conn) - 2)
    put(win, 0, conn_x, conn, conn_col)

    put(win, 0, tx - 1, "[", cp(P_BOX))
    for off, name in tab_pos:
        active = (CS.mode == name.lower())
        attr   = cp(P_CYAN, bold=True) | curses.A_REVERSE if active else cp(P_DIM)
        put(win, 0, tx + off, f" {name} ", attr)
    put(win, 0, tx + len(tab_str), "]", cp(P_BOX))

    # ── Separator ─────────────────────────────────────────────────────────────
    put(win, 1, 0, "─" * W, cp(P_BOX))


def _cal_draw_overlay(win, W, H):
    """Shared add/delete/ics overlay panels."""
    blink = "▌" if int(time.time() * 2) % 2 else " "
    ow = min(W - 8, 60); ox = (W - ow) // 2; oy = max(2, H // 2 - 6)

    # clear overlay area
    for r in range(oy, min(oy + 13, H)):
        try: win.move(r, ox); win.clrtoeol()
        except: pass

    # rounded-corner box
    box(win, oy, ox, 12, ow)

    if CS.add_mode:
        step  = CS.add_step
        title = "  ✦ New Event"
        put(win, oy,     ox + 2, title, cp(P_CYAN, bold=True))
        put(win, oy + 1, ox + 1, "─" * (ow - 2), cp(P_BOX))

        # Step labels with active highlight
        d_str  = (CS.add_date or CS.date).strftime("%A, %d %B %Y")
        t_str  = f"{CS.add_hour:02d}:{CS.add_min:02d}"
        t_buf  = CS.add_title

        def _field(row, label, value, active, hint=""):
            lattr = cp(P_AMBER, bold=True) if active else cp(P_DIM)
            vattr = (cp(P_HI, bold=True) | curses.A_UNDERLINE) if active else cp(P_MID)
            put(win, row, ox + 3, f"{label:<8}", lattr)
            put(win, row, ox + 12, value + (blink if active else ""), vattr)
            if active and hint:
                put(win, row + 1, ox + 12, hint, cp(P_DIM))

        _field(oy + 3, "Date",  d_str, step == 0, "← → day  Shift+←→ month  Enter ▶")
        _field(oy + 5, "Time",  t_str, step == 1, "↑ ↓ hour  ← → minute  Enter ▶")
        _field(oy + 7, "Title", t_buf, step == 2)

        put(win, oy + 10, ox + 1, "─" * (ow - 2), cp(P_BOX))
        save_lbl = "Enter · Save" if step == 2 else "Enter · Next"
        put(win, oy + 11, ox + 3, save_lbl, cp(P_GREEN if step == 2 else P_DIM))
        put(win, oy + 11, ox + 20, "Esc · Cancel", cp(P_DIM))

    elif CS.ics_mode:
        n_conn = get_connected_ics_count()
        put(win, oy,     ox + 2, "  ⟳ Connect Calendar", cp(P_CYAN, bold=True))
        put(win, oy + 1, ox + 1, "─" * (ow - 2), cp(P_BOX))
        put(win, oy + 3, ox + 3, "Google: Settings → Secret address in iCal format", cp(P_DIM))
        put(win, oy + 4, ox + 3, "Apple:  File → Export → ~/.terminal_standby.ics", cp(P_DIM))
        put(win, oy + 6, ox + 3, "URL / path:", cp(P_DIM if CS.ics_step != 0 else P_CYAN))
        put(win, oy + 7, ox + 3, f"{CS.ics_buf}{blink if CS.ics_step == 0 else ''}", cp(P_HI, bold=True))
        put(win, oy + 8, ox + 3, "Name:", cp(P_DIM if CS.ics_step != 1 else P_CYAN))
        put(win, oy + 9, ox + 3, f"{CS.ics_name_buf}{blink if CS.ics_step == 1 else ''}", cp(P_HI, bold=True))
        put(win, oy + 10, ox + 1, "─" * (ow - 2), cp(P_BOX))
        action = "Enter · Next" if CS.ics_step == 0 else "Enter · Connect"
        put(win, oy + 11, ox + 3, f"Connected: {n_conn}   {action}   D · Choose Disconnect   Esc · Cancel", cp(P_DIM))

    elif CS.ics_sel_mode:
        srcs = get_connected_ics_sources()
        n = len(srcs)
        put(win, oy,     ox + 2, "  ⛓ Connected Calendars", cp(P_CYAN, bold=True))
        put(win, oy + 1, ox + 1, "─" * (ow - 2), cp(P_BOX))
        if n == 0:
            put(win, oy + 4, ox + 3, "No connected iCal sources", cp(P_DIM))
        else:
            CS.ics_sel_idx = max(0, min(CS.ics_sel_idx, n - 1))
            max_rows = 5
            start = 0
            if CS.ics_sel_idx >= max_rows:
                start = CS.ics_sel_idx - max_rows + 1
            for i in range(start, min(n, start + max_rows)):
                row = oy + 3 + (i - start)
                lab = srcs[i].get("label", srcs[i].get("source", ""))
                prefix = "▶" if i == CS.ics_sel_idx else " "
                attr = cp(P_HI, bold=True) if i == CS.ics_sel_idx else cp(P_MID)
                put(win, row, ox + 3, f"{prefix} {i+1}. {lab}"[:ow-6], attr)
        put(win, oy + 9, ox + 1, "─" * (ow - 2), cp(P_BOX))
        put(win, oy + 10, ox + 3, "↑/↓ · Select   Enter · Disconnect   Esc · Cancel", cp(P_DIM))

    elif CS.del_mode:
        ev = CS.local_evs[CS.del_idx] if 0 <= CS.del_idx < len(CS.local_evs) else None
        put(win, oy,     ox + 2, "  ✕ Delete Event", cp(P_RED, bold=True))
        put(win, oy + 1, ox + 1, "─" * (ow - 2), cp(P_BOX))
        if ev:
            put(win, oy + 3, ox + 3, ev.get("title", "?")[: ow - 6], cp(P_HI, bold=True))
            put(win, oy + 4, ox + 3, ev.get("dt",    "")[: ow - 6], cp(P_DIM))
        put(win, oy + 6, ox + 1, "─" * (ow - 2), cp(P_BOX))
        put(win, oy + 7, ox + 3, "y · Confirm Delete    n / Esc · Cancel", cp(P_DIM))


def _cal_view_day(win, W, H, now, today, CY, CH):
    """Apple-Calendar day view: left time gutter, events in right panel, now-line."""
    evs      = _evs_for_day(CS.date)
    is_today = (CS.date == today)

    # ── Day label ─────────────────────────────────────────────────────────────
    dow   = CS.date.strftime("%A").upper()
    dnum  = CS.date.strftime("%d")
    drest = CS.date.strftime("%B %Y")
    if is_today:
        put(win, CY, 2, dow, cp(P_DIM))
        put(win, CY, 2 + len(dow) + 1, dnum, cp(P_AMBER, bold=True) | curses.A_REVERSE)
        put(win, CY, 2 + len(dow) + 1 + len(dnum) + 1, drest, cp(P_DIM))
        put(win, CY, 2 + len(dow) + 1 + len(dnum) + 1 + len(drest) + 2,
            "— today", cp(P_AMBER))
    else:
        lbl = f"{dow}  {dnum}  {drest}"
        put(win, CY, 2, lbl, cp(P_MID))

    # ── Layout ────────────────────────────────────────────────────────────────
    FIRST_H, LAST_H = 0, 23
    n_hours   = LAST_H - FIRST_H + 1
    body_h    = CH - 2
    slot_h    = max(1, body_h // n_hours)
    GUTTER    = 6          # "HH:MM" width
    EV_X      = GUTTER + 2
    EV_W      = W - EV_X - 2

    # vertical gutter rule
    for r in range(CY + 1, CY + CH):
        try: win.addch(r, GUTTER + 1, curses.ACS_VLINE, cp(P_BOX))
        except: pass

    now_y = None
    for hi, hour in enumerate(range(FIRST_H, LAST_H + 1)):
        hy = CY + 1 + hi * slot_h
        if hy >= CY + CH: break

        is_now_hour = is_today and now.hour == hour
        hcol = P_AMBER if is_now_hour else P_DIM

        # show time label every 2 hours or if slot_h > 1
        if slot_h >= 2 or hour % 2 == 0:
            put(win, hy, 0, f"{hour:02d}:00", cp(hcol))

        # half-hour tick
        if slot_h >= 2:
            half_y = hy + slot_h // 2
            if half_y < CY + CH:
                put(win, half_y, 2, f"{hour:02d}:30", cp(P_BOX))
                put(win, half_y, GUTTER + 2, "╌" * min(20, EV_W), cp(P_BOX))

        # hour rule
        put(win, hy, GUTTER + 2, "─" * min(EV_W, W - GUTTER - 3), cp(P_BOX))

        # now indicator
        if is_now_hour and slot_h >= 1:
            frac   = (now.minute * 60 + now.second) / 3600
            now_y  = hy + int(frac * slot_h)
            now_y  = min(now_y, CY + CH - 1)
            indicator = "▶" + "─" * min(EV_W - 1, W - EV_X - 3)
            put(win, now_y, GUTTER + 1, indicator, cp(P_RED, bold=True))

        # events for this hour
        hour_evs = [(s, e, t) for s, e, t in evs if s.hour == hour]
        for ei, (s, e, t) in enumerate(hour_evs):
            ey = hy + ei
            if ey >= CY + CH: break
            g_idx = evs.index((s, e, t))
            sel   = (g_idx == CS.cur_ev)
            past  = s < now
            ecol  = P_AMBER if sel else (P_DIM if past else P_CYAN)
            is_local = any(
                lev.get("title") == t and
                lev.get("dt", "").startswith(s.strftime("%Y-%m-%d"))
                for lev in CS.local_evs
            )
            # event pill
            marker  = "●" if is_local else "○"
            time_s  = s.strftime("%H:%M")
            ev_text = f" {marker} {time_s}  {t}"[:EV_W]
            if sel:
                # draw full-width highlight bar
                put(win, ey, EV_X, " " * min(EV_W, W - EV_X - 1),
                    cp(P_CYAN) | curses.A_REVERSE)
                put(win, ey, EV_X, ev_text, cp(P_HI, bold=True) | curses.A_REVERSE)
                put(win, ey, GUTTER + 1, "▶", cp(P_AMBER, bold=True))
            else:
                put(win, ey, EV_X, ev_text, cp(ecol, bold=(not past)))

    if not evs:
        centre(win, CY + CH // 2,     "No events scheduled", cp(P_DIM))
        centre(win, CY + CH // 2 + 1, "press  a  to add", cp(P_DIM))


def _cal_view_week(win, W, H, now, today, CY, CH):
    """Apple-like week view with cleaner grid and right-side agenda rail."""
    week, ev_map = _evs_for_week(CS.date)

    rail_w = 0
    if W >= 110:
        rail_w = 26
    grid_w = W - rail_w

    GUTTER = 6
    n_cols = 7
    col_w = max(5, (grid_w - GUTTER - 1) // n_cols)
    grid_end_x = GUTTER + 1 + n_cols * col_w

    FIRST_H, LAST_H = 8, 21
    n_hours = LAST_H - FIRST_H + 1
    body_h = CH - 4
    slot_h = max(1, body_h // n_hours)

    for i, d in enumerate(week):
        x = GUTTER + 1 + i * col_w
        dow = d.strftime("%a").upper()
        num = str(d.day)
        if d == today:
            put(win, CY, x, dow, cp(P_DIM))
            put(win, CY + 1, x, f"[{num}]", cp(P_AMBER, bold=True))
        elif d == CS.date:
            put(win, CY, x, dow, cp(P_DIM))
            put(win, CY + 1, x, num, cp(P_CYAN, bold=True) | curses.A_UNDERLINE)
        else:
            put(win, CY, x, dow, cp(P_DIM if d.weekday() < 5 else P_BOX))
            put(win, CY + 1, x, num, cp(P_MID if d.weekday() < 5 else P_BOX))

    put(win, CY + 2, GUTTER + 1, "─" * max(1, grid_end_x - (GUTTER + 1)), cp(P_BOX))

    for hi, hour in enumerate(range(FIRST_H, LAST_H + 1)):
        hy = CY + 3 + hi * slot_h
        if hy >= CY + CH:
            break
        hcol = P_AMBER if (now.date() in week and now.hour == hour) else P_DIM
        if hour % 2 == 0 or slot_h >= 2:
            put(win, hy, 0, f"{hour:02d}:00", cp(hcol))
            put(win, hy, GUTTER + 1, "╌" * max(1, grid_end_x - (GUTTER + 1)), cp(P_BOX))
        else:
            put(win, hy, GUTTER, "┆", cp(P_BOX))

    for i in range(1, n_cols):
        x = GUTTER + i * col_w
        for r in range(CY + 2, CY + CH):
            try:
                win.addch(r, x, curses.ACS_VLINE, cp(P_BOX))
            except Exception:
                pass

    if now.date() in week and FIRST_H <= now.hour <= LAST_H:
        day_idx = week.index(now.date())
        frac = (now.hour - FIRST_H + now.minute / 60.0) / n_hours
        now_y = CY + 3 + int(frac * body_h)
        now_y = max(CY + 3, min(now_y, CY + CH - 1))
        nx = GUTTER + 1 + day_idx * col_w
        put(win, now_y, nx, "▶" + "─" * max(1, col_w - 2), cp(P_RED, bold=True))

    for i, d in enumerate(week):
        x = GUTTER + 1 + i * col_w
        day_events = sorted(ev_map.get(d, []), key=lambda it: it[0])
        used_rows = set()
        for s, t in day_events[:18]:
            frac = (s.hour - FIRST_H + s.minute / 60.0) / n_hours
            ey = CY + 3 + int(frac * body_h)
            ey = max(CY + 3, min(ey, CY + CH - 1))
            while ey in used_rows and ey < CY + CH - 1:
                ey += 1
            used_rows.add(ey)

            past = s < now
            if past:
                attr = cp(P_DIM)
            elif d == today:
                attr = cp(P_HI, bold=True)
            else:
                attr = cp(P_CYAN)
            txt = f"{s.strftime('%H:%M')} {t}"[: max(1, col_w - 1)]
            put(win, ey, x, txt, attr)

    if rail_w:
        rx = grid_end_x + 1
        for r in range(CY, CY + CH):
            try:
                win.addch(r, rx - 1, curses.ACS_VLINE, cp(P_BOX))
            except Exception:
                pass

        put(win, CY, rx + 1, "AGENDA", cp(P_CYAN, bold=True))
        put(win, CY + 1, rx + 1, CS.date.strftime("%a %d %b"), cp(P_DIM))

        devs = sorted(_evs_for_day(CS.date), key=lambda ev: ev[0])
        y = CY + 3
        if not devs:
            put(win, y, rx + 1, "No events", cp(P_DIM))
        else:
            for s, e, t in devs[: max(1, CH - 6)]:
                is_local = any(
                    lev.get("title") == t and
                    lev.get("dt", "").startswith(s.strftime("%Y-%m-%d"))
                    for lev in CS.local_evs
                )
                marker = "●" if is_local else "○"
                line = f"{marker} {s.strftime('%H:%M')} {t}"[: max(1, rail_w - 4)]
                attr = cp(P_DIM if s < now else P_HI, bold=(s >= now))
                put(win, y, rx + 1, line, attr)
                y += 1
                if y >= CY + CH - 2:
                    break

        n_conn = get_connected_ics_count()
        src = f"{n_conn} connected" if n_conn else "Not connected"
        scol = cp(P_GREEN) if n_conn else cp(P_DIM)
        put(win, CY + CH - 2, rx + 1, f"iCal: {src}", scol)


def _cal_view_month(win, W, H, now, today, CY, CH):
    """Apple-Calendar month grid with event dots and first-event preview."""
    weeks, ev_map = _evs_for_month(CS.date)
    col_w     = (W - 1) // 7
    n_weeks   = len(weeks)
    row_h     = max(3, (CH - 3) // max(1, n_weeks))
    day_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    # ── Day-of-week header ────────────────────────────────────────────────────
    for i, dn in enumerate(day_names):
        wknd = (i >= 5)
        col  = P_BOX if wknd else P_DIM
        put(win, CY, 1 + i * col_w, dn, cp(col))
    put(win, CY + 1, 0, "─" * W, cp(P_BOX))

    # ── Week rows ─────────────────────────────────────────────────────────────
    for wi, week in enumerate(weeks):
        wy = CY + 2 + wi * row_h

        # horizontal week rule (below each row except last)
        if wi > 0:
            put(win, wy - 1, 0, "─" * W, cp(P_BOX))

        for di, d in enumerate(week):
            x = 1 + di * col_w
            if d is None:
                continue

            in_month = (d.month == CS.date.month)
            is_t     = (d == today)
            is_sel   = (d == CS.date)
            evs_day  = ev_map.get(d, [])
            n_ev     = len(evs_day)
            wknd     = (di >= 5)

            # date number
            num = str(d.day)
            if is_t:
                # Apple-style: white circle around today
                lbl = f"[{num}]"
                put(win, wy, x, lbl, cp(P_AMBER, bold=True))
            elif is_sel:
                put(win, wy, x, num, cp(P_CYAN, bold=True) | curses.A_UNDERLINE)
            elif not in_month:
                put(win, wy, x, num, cp(P_BOX))
            elif wknd:
                put(win, wy, x, num, cp(P_DIM))
            else:
                put(win, wy, x, num, cp(P_MID))

            # event dots row
            if n_ev and row_h >= 2:
                past  = (d < today)
                dcol  = P_DIM if past else (P_RED if is_t else P_GREEN)
                # coloured dot per event (up to col_w-3)
                dots  = ("●" * min(n_ev, 3)).ljust(3)
                put(win, wy + 1, x, dots[: col_w - 2], cp(dcol, bold=(not past)))

            # first event title preview
            if row_h >= 3 and evs_day:
                preview = evs_day[0][: col_w - 1]
                pcol    = P_DIM if d < today else P_MID
                put(win, wy + 2, x, preview, cp(pcol))

        # vertical column dividers
        for ci in range(1, 7):
            cx = ci * col_w
            for r in range(wy, min(wy + row_h, CY + CH)):
                try: win.addch(r, cx, curses.ACS_VLINE, cp(P_BOX))
                except: pass


def _cal_view_year(win, W, H, now, today, CY, CH):
    """Compact 4×3 mini-month year overview."""
    import calendar as _cal
    year   = CS.date.year
    cols   = 4
    rows   = 3
    # each mini-month: 7 chars/col × 7 cols = ~22 wide + 2 padding
    cell_w = max(22, (W - 2) // cols)
    cell_h = max(10, (CH - 1) // rows)

    with _CAL_LOCK:
        evs_all = list(_CAL_EVENTS)

    for mi in range(12):
        month  = mi + 1
        gr     = mi // cols
        gc     = mi % cols
        ox     = 1 + gc * cell_w
        oy     = CY + gr * cell_h

        m_name = datetime.date(year, month, 1).strftime("%b").upper()
        is_cur = (month == CS.date.month and year == CS.date.year)
        hlbl   = cp(P_CYAN, bold=True) if is_cur else cp(P_DIM, bold=True)
        put(win, oy, ox, m_name, hlbl)

        # mini day-of-week row
        dnames = "Mo Tu We Th Fr Sa Su"
        put(win, oy + 1, ox, dnames[:cell_w - 1], cp(P_BOX))

        # event count per day
        ev_days = set()
        for s, e, t in evs_all:
            if s.year == year and s.month == month:
                ev_days.add(s.day)
        # also local events
        for lev in CS.local_evs:
            try:
                dt = datetime.datetime.strptime(lev["dt"][:10], "%Y-%m-%d")
                if dt.year == year and dt.month == month:
                    ev_days.add(dt.day)
            except Exception:
                pass

        # calendar weeks
        first_day = datetime.date(year, month, 1)
        days_in   = _cal.monthrange(year, month)[1]
        pad       = first_day.weekday()          # Mon=0
        cal_cells = [None] * pad + list(range(1, days_in + 1))
        while len(cal_cells) % 7: cal_cells.append(None)
        cal_weeks = [cal_cells[i:i+7] for i in range(0, len(cal_cells), 7)]

        for wi, wk in enumerate(cal_weeks):
            wy = oy + 2 + wi
            if wy >= oy + cell_h: break
            for di, day in enumerate(wk):
                if day is None:
                    continue
                dx   = ox + di * 3
                d_obj = datetime.date(year, month, day)
                is_t  = (d_obj == today)
                is_s  = (d_obj == CS.date)
                has_ev= day in ev_days

                num = f"{day:2d}"
                if is_t:
                    put(win, wy, dx, num, cp(P_AMBER, bold=True) | curses.A_REVERSE)
                elif is_s:
                    put(win, wy, dx, num, cp(P_CYAN, bold=True) | curses.A_UNDERLINE)
                elif has_ev:
                    put(win, wy, dx, num, cp(P_GREEN))
                elif di >= 5:
                    put(win, wy, dx, num, cp(P_BOX))
                else:
                    put(win, wy, dx, num, cp(P_DIM))


def v_calendar(win, W, H):
    now   = datetime.datetime.now()
    today = now.date()

    if CS.msg and time.time() - CS.msg_time > 4:
        CS.msg = ""

    # ── Shared header ─────────────────────────────────────────────────────────
    _cal_draw_header(win, W, H, now, today)

    # ── Status / hint bar ─────────────────────────────────────────────────────
    hint = " j/k nav  a add  D disconnect  G connect  t today  1/2/3/4 views "
    if CS.msg:
        hcol = P_RED if "ERROR" in CS.msg else P_GREEN
        put(win, H - 1, 0, (" " + CS.msg)[: W], cp(hcol, bold=True))
    else:
        put(win, H - 1, 0, hint[: W], cp(P_DIM))

    CY = 2    # content start row
    CH = H - 3

    # ── Overlay panels take priority ──────────────────────────────────────────
    if CS.add_mode or CS.ics_mode or CS.del_mode or CS.ics_sel_mode:
        _cal_draw_overlay(win, W, H)
        return

    # ── View dispatch ─────────────────────────────────────────────────────────
    if CS.mode == "day":
        _cal_view_day(win, W, H, now, today, CY, CH)
    elif CS.mode == "week":
        _cal_view_week(win, W, H, now, today, CY, CH)
    elif CS.mode == "month":
        _cal_view_month(win, W, H, now, today, CY, CH)
    elif CS.mode == "year":
        _cal_view_year(win, W, H, now, today, CY, CH)

    # ── No-events nudge ───────────────────────────────────────────────────────
    with _CAL_LOCK:
        n_total = len(_CAL_EVENTS)
    if n_total == 0 and not CS.add_mode and not CS.ics_mode:
        centre(win, H - 2,
               "no events · press G to connect Google / Apple Calendar",
               cp(P_DIM))


def _handle_cal_input(k):
    if CS.add_mode:
        step = CS.add_step

        if step == 0:
            if k in (10, 13):
                CS.add_step = 1
            elif k == 27:
                CS.add_mode = False
            elif k == curses.KEY_RIGHT:
                CS.add_date = CS.add_date + datetime.timedelta(days=1)
            elif k == curses.KEY_LEFT:
                CS.add_date = CS.add_date - datetime.timedelta(days=1)
            elif k == curses.KEY_SR or k == 337:
                import calendar as _c
                y, m = CS.add_date.year, CS.add_date.month
                m += 1
                if m > 12: m, y = 1, y+1
                d = min(CS.add_date.day, _c.monthrange(y,m)[1])
                CS.add_date = CS.add_date.replace(year=y, month=m, day=d)
            elif k == curses.KEY_SF or k == 336:
                import calendar as _c
                y, m = CS.add_date.year, CS.add_date.month
                m -= 1
                if m < 1: m, y = 12, y-1
                d = min(CS.add_date.day, _c.monthrange(y,m)[1])
                CS.add_date = CS.add_date.replace(year=y, month=m, day=d)

        elif step == 1:
            if k in (10, 13):
                CS.add_step = 2
            elif k == 27:
                CS.add_mode = False
            elif k in (curses.KEY_UP, ord('k')):
                CS.add_hour = (CS.add_hour + 1) % 24
            elif k in (curses.KEY_DOWN, ord('j')):
                CS.add_hour = (CS.add_hour - 1) % 24
            elif k == curses.KEY_RIGHT:
                CS.add_min = (CS.add_min + 5) % 60
            elif k == curses.KEY_LEFT:
                CS.add_min = (CS.add_min - 5) % 60

        elif step == 2:
            if k in (10, 13):
                title = CS.add_title.strip() or "Event"
                dt_str = f"{CS.add_date.strftime('%Y-%m-%d')} {CS.add_hour:02d}:{CS.add_min:02d}"
                CS.local_evs.append({"dt": dt_str, "title": title})
                save_local_events(CS.local_evs)
                threading.Thread(target=refresh_calendar, daemon=True).start()
                CS.msg = f"Added: {title}"; CS.msg_time = time.time()
                CS.add_mode = False
            elif k == 27:
                CS.add_mode = False
            elif k in (curses.KEY_BACKSPACE, 127, 8):
                CS.add_title = CS.add_title[:-1]
            elif 32 <= k <= 126:
                CS.add_title += chr(k)

    elif CS.del_mode:
        if k in (ord('y'), ord('Y')):
            if 0 <= CS.del_idx < len(CS.local_evs):
                title = CS.local_evs[CS.del_idx].get("title","Event")
                CS.local_evs.pop(CS.del_idx)
                save_local_events(CS.local_evs)
                threading.Thread(target=refresh_calendar, daemon=True).start()
                CS.msg = f"Deleted: {title}"; CS.msg_time = time.time()
                CS.cur_ev = max(0, CS.cur_ev - 1)
            CS.del_mode = False; CS.del_idx = -1
        elif k in (ord('n'), ord('N'), 27):
            CS.del_mode = False; CS.del_idx = -1

    elif CS.ics_mode:
        if k == ord('D'):
            CS.ics_mode = False
            CS.ics_step = 0
            CS.ics_name_buf = ""
            CS.ics_sel_mode = True
            CS.ics_sel_idx = 0
            return
        if k in (10, 13):
            if CS.ics_step == 0:
                if CS.ics_buf.strip():
                    CS.ics_step = 1
                else:
                    CS.msg = "Enter URL/path first"; CS.msg_time = time.time()
            else:
                url = CS.ics_buf.strip()
                if url:
                    name = CS.ics_name_buf.strip()
                    def _sync(u=url, n=name):
                        ok, msg = fetch_ics_url(u, n)
                        CS.msg = msg; CS.msg_time = time.time()
                    threading.Thread(target=_sync, daemon=True).start()
                CS.ics_mode = False
                CS.ics_buf = ""
                CS.ics_step = 0
                CS.ics_name_buf = ""
        elif k == 27:
            CS.ics_mode = False
            CS.ics_buf = ""
            CS.ics_step = 0
            CS.ics_name_buf = ""
        elif k in (curses.KEY_BACKSPACE, 127, 8):
            if CS.ics_step == 0:
                CS.ics_buf = CS.ics_buf[:-1]
            else:
                CS.ics_name_buf = CS.ics_name_buf[:-1]
        elif 32 <= k <= 126:
            if CS.ics_step == 0:
                CS.ics_buf += chr(k)
            else:
                CS.ics_name_buf += chr(k)

    elif CS.ics_sel_mode:
        srcs = get_connected_ics_sources()
        if k in (27, ord('n'), ord('N')):
            CS.ics_sel_mode = False
        elif k in (curses.KEY_UP, ord('k')) and srcs:
            CS.ics_sel_idx = (CS.ics_sel_idx - 1) % len(srcs)
        elif k in (curses.KEY_DOWN, ord('j')) and srcs:
            CS.ics_sel_idx = (CS.ics_sel_idx + 1) % len(srcs)
        elif k in (10, 13):
            if srcs:
                ok, msg = disconnect_ics_calendar(source_idx=CS.ics_sel_idx)
                CS.msg = msg; CS.msg_time = time.time()
                CS.ics_sel_idx = 0
            else:
                CS.msg = "No connected calendar"; CS.msg_time = time.time()
            CS.ics_sel_mode = False


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 9 — VIDEO PLAYER
# ══════════════════════════════════════════════════════════════════════════════
class VidState:
    mode = "browse"
    buf  = ""
    msg  = ""
    msg_time = 0.0

VS = VidState()

def v_video(win, W, H):
    if VS.msg and time.time() - VS.msg_time > 5:
        VS.msg = ""

    def _trim(txt, n):
        return txt if len(txt) <= n else txt[:max(0, n-1)] + "…"

    put(win, 0, 2, "VIDEO PLAYER", cp(P_CYAN, bold=True))
    rname = VIDEO.renderer_name()
    ready = VIDEO.has_renderer()
    rcol = P_GREEN if ready else P_RED
    put(win, 0, max(2, W-28), f"ENGINE: {_trim(rname.upper(), 20)}", cp(rcol, bold=True))
    mode_txt = "TERMINAL" if VIDEO.in_terminal else "WINDOW"
    mode_col = P_CYAN if VIDEO.in_terminal else P_DIM
    put(win, 0, max(2, W-45), f"MODE: {mode_txt}", cp(mode_col, bold=True))
    ascii_txt = "ASCII" if VIDEO.prefer_ascii else "AUTO"
    put(win, 0, max(2, W-58), f"RENDER: {ascii_txt}", cp(P_DIM, bold=True))
    put(win, 1, 0, "─"*W, cp(P_BOX))

    wide_mode = W >= 140
    content_w = min(max(40, W - 4), 170)
    content_x = max(2, (W - content_w) // 2)

    hero_y = 2
    hero_h = 12 if H >= 42 else 10
    hero_w = content_w
    box(win, hero_y, content_x, hero_h, hero_w, "PLAYBACK")

    if VIDEO.playing:
        state = "NOW PLAYING"
        state_col = P_GREEN
        primary = VIDEO.title or "Untitled"
        secondary = ("Rendering ASCII in terminal. Press S to stop."
                     if VIDEO.ascii_mode else
                     "Rendering inside terminal. Press S to stop."
                     if VIDEO.in_terminal else
                     "Playing in a separate window. Press S to stop.")
    elif not ready:
        state = "PLAYER SETUP"
        state_col = P_AMBER
        primary = "No renderer found. Trying auto-install in background."
        secondary = "If needed: winget install mpv   or   brew install mpv"
    elif VIDEO._installing:
        state = "INSTALLING"
        state_col = P_AMBER
        primary = "Setting up mpv for better playback quality."
        secondary = "You can still try ffplay fallback if available."
    else:
        state = "READY"
        state_col = P_GREEN
        primary = "Choose a source to start watching."
        secondary = "Y for YouTube URL, O for local video file."

    put(win, hero_y+1, content_x+2, f"[{state}]", cp(state_col, bold=True))
    put(win, hero_y+1, content_x+18, f"Renderer: {_trim(rname, hero_w-24)}", cp(P_DIM))
    put(win, hero_y+3, content_x+2, _trim(primary, hero_w-4), cp(P_HI, bold=True))
    put(win, hero_y+4, content_x+2, _trim(secondary, hero_w-4), cp(P_DIM))

    status_txt = VIDEO.status.strip()
    if status_txt:
        err = ("error" in status_txt.lower() or "failed" in status_txt.lower()
               or "not found" in status_txt.lower())
        put(win, hero_y+6, content_x+2, _trim("Status: " + status_txt, hero_w-4), cp(P_RED if err else P_CYAN))

    put(win, hero_y+8, content_x+2, "Flow: 1) Pick source  2) Paste path/URL  3) Enter to launch", cp(P_DIM))
    if hero_h >= 12:
        put(win, hero_y+9, content_x+2,
            _trim(f"Runtime: {'PLAYING' if VIDEO.playing else 'IDLE'}  |  Mode: {mode_txt}  |  Render: {ascii_txt}", hero_w-4),
            cp(P_DIM))
        put(win, hero_y+10, content_x+2,
            _trim("Fullscreen tip: this view expands with extra actions/help panels on wide terminals.", hero_w-4),
            cp(P_DIM))

    act_y = hero_y + hero_h
    act_h = max(6, H - act_y - 3)
    if act_h >= 6:
        if VIDEO.playing and VIDEO.ascii_mode:
            if wide_mode and hero_w >= 96:
                prev_w = max(54, int(hero_w * 0.68))
                info_x = content_x + prev_w
                info_w = hero_w - prev_w

                box(win, act_y, content_x, act_h, prev_w, "ASCII PREVIEW")
                drawable_h = max(1, act_h - 2)
                drawable_w = max(8, prev_w - 2)
                VIDEO.set_ascii_viewport(drawable_w, drawable_h)
                lines = VIDEO.get_ascii_frame()
                shown_h = min(drawable_h, len(lines))
                y_off = max(0, (drawable_h - shown_h) // 2)
                for i in range(shown_h):
                    line = lines[i][:drawable_w]
                    x_off = max(0, (drawable_w - len(line)) // 2)
                    put(win, act_y + 1 + y_off + i, content_x + 1 + x_off, line, cp(P_HI))

                box(win, act_y, info_x, act_h, info_w, "ASCII DETAILS")
                put(win, act_y+1, info_x+2, "Renderer: OpenCV ASCII", cp(P_HI, bold=True))
                put(win, act_y+2, info_x+2, "Audio: Off in ASCII mode", cp(P_DIM))
                put(win, act_y+3, info_x+2, f"Viewport: up to {VIDEO._ascii_cols}x{VIDEO._ascii_rows}", cp(P_DIM))
                put(win, act_y+4, info_x+2, "S stop  |  T switch mode  |  A toggle ASCII", cp(P_DIM))
                put(win, act_y+6, info_x+2, "If frame looks dense:", cp(P_HI, bold=True))
                put(win, act_y+7, info_x+2, "1) Reduce terminal zoom", cp(P_DIM))
                put(win, act_y+8, info_x+2, "2) Shrink window width", cp(P_DIM))
                put(win, act_y+9, info_x+2, "3) Use WINDOW mode for native playback", cp(P_DIM))
            else:
                box(win, act_y, content_x, act_h, hero_w, "ASCII PREVIEW")
                drawable_h = max(1, act_h - 2)
                drawable_w = max(8, hero_w - 2)
                VIDEO.set_ascii_viewport(drawable_w, drawable_h)
                lines = VIDEO.get_ascii_frame()
                shown_h = min(drawable_h, len(lines))
                y_off = max(0, (drawable_h - shown_h) // 2)
                for i in range(shown_h):
                    line = lines[i][:drawable_w]
                    x_off = max(0, (drawable_w - len(line)) // 2)
                    put(win, act_y + 1 + y_off + i, content_x + 1 + x_off, line, cp(P_HI))
        else:
            box(win, act_y, content_x, act_h, hero_w, "QUICK ACTIONS")
            if wide_mode and hero_w >= 108:
                c1 = content_x + 2
                c2 = content_x + hero_w // 3
                c3 = content_x + (hero_w * 2) // 3

                put(win, act_y+1, c1, "Y  YouTube URL", cp(P_HI, bold=True))
                put(win, act_y+2, c1, "O  Open local file", cp(P_HI, bold=True))
                put(win, act_y+3, c1, "S  Stop playback", cp(P_HI, bold=True))
                put(win, act_y+4, c1, "T  Toggle terminal/window mode", cp(P_HI, bold=True))
                put(win, act_y+5, c1, "A  Toggle ASCII renderer", cp(P_HI, bold=True))
                put(win, act_y+6, c1, "K  Force kill stuck players", cp(P_HI, bold=True))

                put(win, act_y+1, c2, "Supports: mp4 mkv mov avi webm", cp(P_DIM))
                put(win, act_y+2, c2, "YouTube: youtube.com or youtu.be links", cp(P_DIM))
                put(win, act_y+3, c2, "Tip: use absolute paths for local files", cp(P_DIM))
                put(win, act_y+4, c2, "Windows: tct may fail; ASCII fallback", cp(P_DIM))
                put(win, act_y+5, c2, "ASCII is terminal-only and no-audio", cp(P_DIM))

                put(win, act_y+1, c3, "CURRENT", cp(P_HI, bold=True))
                put(win, act_y+2, c3, f"Engine: {_trim(rname, max(8, hero_w//3 - 10))}", cp(P_DIM))
                put(win, act_y+3, c3, f"Mode: {mode_txt}", cp(P_DIM))
                put(win, act_y+4, c3, f"Render: {ascii_txt}", cp(P_DIM))
                put(win, act_y+5, c3, f"State: {state}", cp(P_DIM))
                if VIDEO.status:
                    put(win, act_y+6, c3, _trim("Status: " + VIDEO.status, max(16, hero_w//3 - 4)), cp(P_DIM))
            else:
                put(win, act_y+1, content_x+2, "Y  YouTube URL", cp(P_HI, bold=True))
                put(win, act_y+2, content_x+2, "O  Open local file", cp(P_HI, bold=True))
                put(win, act_y+3, content_x+2, "S  Stop playback", cp(P_HI, bold=True))
                put(win, act_y+4, content_x+2, "T  Toggle terminal/window mode", cp(P_HI, bold=True))
                put(win, act_y+5, content_x+2, "A  Toggle ASCII renderer", cp(P_HI, bold=True))
                right_x = content_x + hero_w // 2
                put(win, act_y+1, right_x, "Supports: mp4 mkv mov avi webm", cp(P_DIM))
                put(win, act_y+2, right_x, "YouTube: youtube.com or youtu.be links", cp(P_DIM))
                put(win, act_y+3, right_x, "Tip: use absolute paths for local files", cp(P_DIM))
                put(win, act_y+4, right_x, "Windows: tct may fail, ASCII fallback is used", cp(P_DIM))
                put(win, act_y+5, right_x, "ASCII playback is terminal-only and no-audio", cp(P_DIM))

    blink = "▌" if int(time.time()*2)%2 else " "
    if VS.mode in ("add_url", "add_file"):
        ow = min(W-8, 76); ox = (W-ow)//2; oy = H//2 - 4
        box(win, oy, ox, 9, ow, "INPUT")
        for r in range(oy+1, oy+8):
            try: win.move(r, ox); win.clrtoeol()
            except: pass
        label = "play youtube url" if VS.mode == "add_url" else "open video file"
        put(win, oy+1, ox+2, label.upper(),     cp(P_CYAN, bold=True))
        put(win, oy+2, ox+2, "─"*(ow-4),       cp(P_BOX))
        if VS.mode == "add_url":
            put(win, oy+3, ox+2, "youtube.com/watch?v=...  or  youtu.be/...", cp(P_DIM))
        else:
            put(win, oy+3, ox+2, "full path to video file  (mp4 mkv avi mov webm)", cp(P_DIM))
        put(win, oy+5, ox+2, _trim(f"{VS.buf}{blink}", ow-4), cp(P_HI, bold=True))
        put(win, oy+6, ox+2, "─"*(ow-4), cp(P_BOX))
        put(win, oy+7, ox+2, "enter = play    esc = cancel", cp(P_DIM))

    if VS.msg:
        mcol = P_RED if "error" in VS.msg.lower() else P_GREEN
        put(win, H-2, 2, VS.msg[:W-4], cp(mcol, bold=True))

    put(win, H-1, 0,
        " O open file  Y YouTube  S stop  T terminal/window  A ascii  K force-stop ",
        cp(P_DIM))


# ══════════════════════════════════════════════════════════════════════════════
#  INPUT HANDLER
# ══════════════════════════════════════════════════════════════════════════════
def _handle_mouse():
    """Translate a curses mouse event into app actions."""
    try:
        _, mx, my, _, bstate = curses.getmouse()
    except curses.error:
        return

    v = ST.view

    # ── Scroll wheel (Button4 = up, Button5 = down) ───────────────────
    if bstate & curses.BUTTON4_PRESSED:
        return
    if bstate & curses.BUTTON5_PRESSED:
        return

    # ── Only handle left-button click/press from here ─────────────────
    if not (bstate & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED |
                      curses.BUTTON1_RELEASED)):
        return

    # ── Tab bar row (row 1) ───────────────────────────────────────────
    if my == 1:
        pass

    # ── News tab: click a headline row ───────────────────────────────
    if NSS.tab == 0:
        item_idx = NSS.news_row_map.get(my, -1)
        if item_idx < 0:
            return
        items = get_news_items()
        if item_idx >= len(items):
            return
        url = items[item_idx].get("url", "")
        if NSS.news_cursor == item_idx:
            # already selected → open URL
            if url:
                _open_url(url)
        else:
            # first click → highlight
            NSS.news_cursor = item_idx

    # ── Stocks tab: click a ticker row ───────────────────────────────
    elif NSS.tab == 1:
        # Sub-tab bar click (row 3: MARKET / PORTFOLIO)
        if my == 3:
            for x0, x1, sidx in NSS.stock_sub_regions:
                if x0 <= mx < x1:
                    NSS.stock_screen = sidx
                    return
        # Portfolio row click
        if NSS.stock_screen == 1:
            wl = load_stock_watchlist()
            for base in (9, 7):
                rel = my - base
                if 0 <= rel < len(wl):
                    NSS.stock_cur = rel
                    return


def _force_stop_all_media():
    """Emergency kill switch for stuck audio/video playback."""
    try:
        VIDEO.stop()
    except Exception:
        pass
    try:
        AUDIO._kill()
    except Exception:
        pass
    if platform.system() == "Windows":
        for exe in ("mpv.exe", "ffplay.exe", "mplayer.exe", "aplay.exe"):
            try:
                subprocess.run(["taskkill", "/IM", exe, "/T", "/F"],
                               capture_output=True, timeout=3)
            except Exception:
                pass
    VS.msg = "FORCE STOPPED all media"
    VS.msg_time = time.time()


def handle_key(k):
    if k == curses.KEY_MOUSE:
        _handle_mouse()
        return
    v = ST.view

    # Check if ANY input mode is active - if so, ONLY handle input-specific keys
    # This prevents shortcuts from interfering with text input
    input_mode_active = (DS.input_mode or ST.todo_add or 
                         (v == 5 and (CS.add_mode or CS.ics_mode or CS.del_mode or CS.ics_sel_mode)) or 
                         (v == 1 and LS.mode in ("add_url", "add_file")) or 
                         (v == 6 and VS.mode in ("add_url", "add_file")) or
                         (v == 8 and NSS.stock_input) or
                         (v == 9 and ECS.input_mode))

    if v == 0 and DS.input_mode:
        if k in (10, 13):
            denji_submit_command(DS.input_buf)
            DS.input_mode = False
            DS.input_buf = ""
        elif k == 27:
            DS.input_mode = False
            DS.input_buf = ""
        else:
            DS.input_buf = _text_input(DS.input_buf, k)
        return

    if ST.todo_add:
        if k in (10, 13):
            t = ST.todo_buf.strip()
            if t:
                ST.todos.append([False, t])
                ST.todo_cur = len(ST.todos) - 1
                save_todos(ST.todos)
            ST.todo_add = False
            ST.todo_buf = ""
        elif k == 27:
            ST.todo_add = False
            ST.todo_buf = ""
        else:
            ST.todo_buf = _text_input(ST.todo_buf, k)
        return

    if v == 5 and (CS.add_mode or CS.ics_mode or CS.del_mode or CS.ics_sel_mode):
        _handle_cal_input(k)
        return

    if v == 1 and LS.mode in ("add_url", "add_file"):
        if k in (10, 13):
            t = LS.buf.strip()
            if t:
                if LS.mode == "add_url":
                    AUDIO.add_youtube(t)
                else:
                    ok, msg = AUDIO.add_file(t)
                    LS.msg = msg; LS.msg_time = time.time()
            LS.mode = "browse"; LS.buf = ""
        elif k == 27:
            LS.mode = "browse"; LS.buf = ""
        else:
            LS.buf = _text_input(LS.buf, k)
        return

    if v == 6 and VS.mode in ("add_url", "add_file"):
        if k in (10, 13):
            src = VS.buf.strip()
            if src:
                if VS.mode == "add_url":
                    VIDEO.play_youtube(src)
                    VS.msg = "loading stream..."; VS.msg_time = time.time()
                else:
                    if os.path.exists(src):
                        VIDEO.play(src)
                        VS.msg = f"playing: {os.path.basename(src)[:30]}"
                    else:
                        VS.msg = "file not found"; VS.msg_time = time.time()
            VS.mode = "browse"; VS.buf = ""
        elif k == 27:
            VS.mode = "browse"; VS.buf = ""
        elif k in (curses.KEY_BACKSPACE, 127, 8):
            VS.buf = VS.buf[:-1]
        elif 32 <= k <= 126:
            VS.buf += chr(k)
        return

    # Crypto/ETF ticker input - protect it completely
    if v == 9 and ECS.input_mode:
        if k in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
            ECS.input_buf = ECS.input_buf[:-1]
        elif k == 27:
            ECS.input_mode = False; ECS.input_buf = ""
        elif k in (10, 13):
            sym = ECS.input_buf.upper().strip()
            ECS.input_mode = False; ECS.input_buf = ""
            if sym and sym not in [s.upper() for s in ECS.custom]:
                ECS.custom.append(sym)
                _save_ec_custom()
                threading.Thread(target=lambda s=sym: _fetch_and_cache_ec(s), daemon=True).start()
                ECS.msg = f"Added {sym}"; ECS.msg_time = time.time()
            elif sym:
                ECS.msg = f"{sym} already added"; ECS.msg_time = time.time()
        elif 32 <= k <= 126 and len(ECS.input_buf) < 14:
            ECS.input_buf += chr(k)
        return

    # Portfolio stock ticker input - protect it completely
    if v == 8 and NSS.stock_input:
        if k in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
            NSS.stock_buf = NSS.stock_buf[:-1]
        elif k == 27:
            NSS.stock_input = False
            NSS.stock_buf = ""
        elif k in (10, 13):
            sym = NSS.stock_buf.upper().strip()
            NSS.stock_input = False
            NSS.stock_buf = ""
            if sym:
                wl = load_stock_watchlist()
                if sym not in [s.upper() for s in wl]:
                    wl.append(sym)
                    save_stock_watchlist(wl)
                    threading.Thread(target=lambda s=sym: fetch_stocks_bg([s]), daemon=True).start()
                    NSS.msg = f"Added {sym} — fetching…"
                    NSS.msg_time = time.time()
                else:
                    NSS.msg = f"{sym} already in portfolio"
                    NSS.msg_time = time.time()
        elif 32 <= k <= 126 and len(NSS.stock_buf) < 12:
            NSS.stock_buf += chr(k)
        return

    # Navigation shortcuts (only when NOT in input mode)
    if not input_mode_active:
        if k in (curses.KEY_RIGHT, ord('l'), ord('L'), 9):
            if v in SHORTCUT_ONLY_VIEWS:
                return
            ST.view = _cycle_view(v, +1); return
        if k in (curses.KEY_LEFT, ord('h'), ord('H')):
            if v in SHORTCUT_ONLY_VIEWS:
                return
            ST.view = _cycle_view(v, -1); return

    # Global shortcuts (only when NOT in input mode)
    if not input_mode_active:
        # Home view direct typing: start command mode on printable key without requiring 't'.
        reserved_home_keys = {
            ord('q'), ord('Q'), ord('t'), ord('T'), ord('/'), ord('v'), ord('V'),
            ord('o'), ord('O'), ord('c'), ord('C'), ord('m'), ord('M'), ord('+'), ord('='), ord('-'),
            ord('_'), ord('z'), ord('Z'), ord('x'), ord('X'), ord(' '), ord('h'),
            ord('H'), ord('l'), ord('L'), ord('1'), ord('2'), ord('3'), ord('4'),
            ord('5'), ord('6')
        }
        if v == 0 and 32 <= k <= 126 and k not in reserved_home_keys:
            DS.input_mode = True
            DS.input_buf = chr(k)
            return
        if k == 27:
            # Page-wise back behavior: only return from shortcut-only pages
            # to the page they were opened from. Otherwise ESC is local/no-op.
            if v in SHORTCUT_ONLY_VIEWS and ST.return_view is not None:
                ST.view = ST.return_view
                ST.return_view = None
            return
        if k in (11, ord('K')):
            _force_stop_all_media()
            return
        if k == ord(' ') and v != 0: AUDIO.toggle_play(); return
        if v == 0 and k in (ord('t'), ord('T'), ord('/')):
            DS.input_mode = True
            if not DS.input_buf:
                DS.input_buf = ""
            return
        if v == 0 and k in (ord('o'), ord('O')):
            ST.todo_add = True
            ST.todo_buf = ""
            return
        if v == 0 and k in (ord('v'), ord('V')):
            denji_listen_once()
            return
        if v == 0 and k in (ord('m'), ord('M')):
            denji_toggle_speech_output()
            return
        if v == 0 and k in (ord('+'), ord('=')):
            DS.humor_level = min(100, DS.humor_level + 5)
            if HAS_PERSONALITY:
                set_global_humor(DS.humor_level)
            return
        if v == 0 and k in (ord('-'), ord('_')):
            DS.humor_level = max(0, DS.humor_level - 5)
            if HAS_PERSONALITY:
                set_global_humor(DS.humor_level)
            return
        if v == 0 and k in (ord('c'), ord('C')):
            denji_toggle_camera()
            return
        if k in (ord('z'), ord('Z')):             AUDIO.prev_track();  return
        if k in (ord('x'), ord('X')):             AUDIO.next_track();  return
        if k in (ord('s'), ord('S')) and v != 2: AUDIO.shuffle = not AUDIO.shuffle; return
        if k == ord('R'):             AUDIO.repeat = not AUDIO.repeat;   return

    # Skip view-specific shortcuts if in input mode
    if not input_mode_active:
        if v == 0:
            if k in (ord('1'),):
                denji_submit_command("Denji play music")
            elif k in (ord('2'),):
                denji_submit_command("Denji focus mode")
            elif k in (ord('3'),):
                denji_submit_command("Denji open calendar")
            elif k in (ord('4'),):
                denji_submit_command("Denji open video")
            elif k in (ord('5'),):
                denji_submit_command("Denji show news")
            elif k in (ord('6'),):
                denji_submit_command("Denji system snapshot")
            elif k == ord(' '):
                AUDIO.toggle_play()
                DS.response_text = "Toggled music playback"
                DS.last_action = "Music toggle"

        elif v == 2:
            if k == ord('p'):   ST.pomo_run = not ST.pomo_run; ST._pw = time.time()
            elif k == ord('r'): ST.pomo_run = False; ST.pomo_secs = ST.pomo_total; ST._pw = time.time()
            elif k == ord('s'):
                ST.pomo_run   = False
                ST.pomo_phase = "BREAK" if ST.pomo_phase == "WORK" else "WORK"
                ST.pomo_total = 5*60.0 if ST.pomo_phase == "BREAK" else 25*60.0
                ST.pomo_secs  = ST.pomo_total; ST._pw = time.time()
            elif k == ord('f'): ST.focus_idx = (ST.focus_idx+1) % len(ST.focus_modes)

        elif v == 1:
            if LS.mode == "browse":
                idxs = _lib_filtered_indices()
                if k == ord('1'):
                    LS.filter = "all"
                    idxs = _lib_filtered_indices()
                    if idxs: LS.cursor = idxs[0]
                elif k == ord('2'):
                    LS.filter = "builtin"
                    idxs = _lib_filtered_indices()
                    if idxs: LS.cursor = idxs[0]
                elif k == ord('3'):
                    LS.filter = "youtube"
                    idxs = _lib_filtered_indices()
                    if idxs: LS.cursor = idxs[0]
                elif k == ord('4'):
                    LS.filter = "file"
                    idxs = _lib_filtered_indices()
                    if idxs: LS.cursor = idxs[0]
                elif k in (curses.KEY_UP, ord('k')):
                    if idxs:
                        if LS.cursor not in idxs:
                            LS.cursor = idxs[0]
                        else:
                            pos = idxs.index(LS.cursor)
                            LS.cursor = idxs[(pos - 1) % len(idxs)]
                elif k in (curses.KEY_DOWN, ord('j')):
                    if idxs:
                        if LS.cursor not in idxs:
                            LS.cursor = idxs[0]
                        else:
                            pos = idxs.index(LS.cursor)
                            LS.cursor = idxs[(pos + 1) % len(idxs)]
                elif k in (10, 13):
                    if idxs:
                        if LS.cursor not in idxs:
                            LS.cursor = idxs[0]
                        AUDIO.play_index(LS.cursor)
                elif k == ord('Y'): LS.mode = "add_url";  LS.buf = ""
                elif k == ord('F'): LS.mode = "add_file"; LS.buf = ""
                elif k == ord('D'):
                    if idxs and LS.cursor not in idxs:
                        LS.cursor = idxs[0]
                    if idxs and LS.cursor >= len(BUILTIN_TRACKS):
                        LS.mode = "confirm_del"
                    else:
                        LS.msg = "Cannot remove built-in tracks" if idxs else "No tracks in this filter"
                        LS.msg_time = time.time()
            elif LS.mode == "confirm_del":
                if k in (ord('y'), ord('Y')):
                    ok, msg = AUDIO.remove_track(LS.cursor)
                    LS.msg = msg; LS.msg_time = time.time()
                    idxs = _lib_filtered_indices()
                    if idxs:
                        LS.cursor = idxs[min(len(idxs)-1, 0)]
                    else:
                        LS.cursor = 0
                    LS.mode   = "browse"
                elif k in (ord('n'), ord('N'), 27):
                    LS.mode = "browse"

        elif v == 3:
            NFS.animation_mode = "pacman"

        elif v == 4:
            # Network view shortcuts can go here
            pass

        elif v == 5:
            if k == ord('1'):   CS.mode = "day"
            elif k == ord('2'): CS.mode = "week"
            elif k == ord('3'): CS.mode = "month"
            elif k == ord('4'): CS.mode = "year"
            elif k in (ord('j'), curses.KEY_DOWN):
                if CS.mode == "day":
                    evs = _evs_for_day(CS.date)
                    if evs: CS.cur_ev = (CS.cur_ev + 1) % len(evs)
                    else:   CS.date += datetime.timedelta(days=1)
                elif CS.mode == "week":
                    CS.date += datetime.timedelta(days=7)
                elif CS.mode == "month":
                    CS.date += datetime.timedelta(days=28)
                elif CS.mode == "year":
                    CS.date = CS.date.replace(year=CS.date.year + 1)
            elif k in (ord('k'), curses.KEY_UP):
                if CS.mode == "day":
                    evs = _evs_for_day(CS.date)
                    if evs: CS.cur_ev = (CS.cur_ev - 1) % len(evs)
                    else:   CS.date -= datetime.timedelta(days=1)
                elif CS.mode == "week":
                    CS.date -= datetime.timedelta(days=7)
                elif CS.mode == "month":
                    CS.date -= datetime.timedelta(days=28)
                elif CS.mode == "year":
                    CS.date = CS.date.replace(year=CS.date.year - 1)
            elif k in (curses.KEY_RIGHT, curses.KEY_LEFT) and CS.mode != "day":
                CS.date += datetime.timedelta(days=1 if k==curses.KEY_RIGHT else -1)
            elif k == ord('t'):
                CS.date = datetime.datetime.now().date(); CS.cur_ev = 0
            elif k == ord('a'):
                CS.add_mode = True; CS.add_step = 0
                CS.add_date = CS.date; CS.add_hour = 9
                CS.add_min  = 0;       CS.add_title = ""
            elif k == ord('G'):
                CS.ics_mode = True; CS.ics_buf = ""; CS.ics_step = 0; CS.ics_name_buf = ""
            elif k == ord('D'):
                if get_connected_ics_count() == 0:
                    CS.msg = "No connected calendar"; CS.msg_time = time.time()
                else:
                    CS.ics_sel_mode = True
                    CS.ics_sel_idx = 0
            elif k == ord('r'):
                threading.Thread(target=refresh_calendar, daemon=True).start()
                CS.msg = "Refreshing..."; CS.msg_time = time.time()

        elif v == 6:
            if k in (ord('y'), ord('Y')):   VS.mode = "add_url";  VS.buf = ""
            elif k in (ord('o'), ord('O')): VS.mode = "add_file"; VS.buf = ""
            elif k in (ord('s'), ord('S')):
                VIDEO.stop()
                VS.msg = "stopped"; VS.msg_time = time.time()
            elif k in (ord('t'), ord('T')):
                now_term = VIDEO.toggle_terminal_mode()
                VS.msg = ("video mode: terminal" if now_term else "video mode: popup window")
                VS.msg_time = time.time()
            elif k in (ord('a'), ord('A')):
                now_ascii = VIDEO.toggle_ascii_preference()
                VS.msg = ("renderer: ASCII preferred" if now_ascii else "renderer: auto (mpv/tct first)")
                VS.msg_time = time.time()

        elif v == HUB_VIEW_IDX:
            # Shortcut-only child pages are entered from the hub.
            if k == ord('1'):
                NSS.tab = 0
                ST.return_view = HUB_VIEW_IDX
                ST.view = NEWS_STOCKS_VIEW_IDX
            elif k == ord('2'):
                NSS.tab = 1
                ST.return_view = HUB_VIEW_IDX
                ST.view = NEWS_STOCKS_VIEW_IDX
            elif k == ord('3'):
                ST.return_view = HUB_VIEW_IDX
                ST.view = ETF_CRYPTO_VIEW_IDX
            elif k == ord('r'):
                _news_last = 0.0
                _stocks_last = 0.0
                _market_last = 0.0
                _etf_last = 0.0
                _crypto_last = 0.0
                threading.Thread(target=fetch_news_bg, daemon=True).start()
                threading.Thread(target=lambda: fetch_stocks_bg(load_stock_watchlist()), daemon=True).start()
                threading.Thread(target=fetch_market_bg, daemon=True).start()
                threading.Thread(target=fetch_etf_bg, daemon=True).start()
                threading.Thread(target=fetch_crypto_bg, daemon=True).start()

        elif v == NEWS_STOCKS_VIEW_IDX:
            # News & Stocks shortcuts
            _handle_news_stocks_key(k)

        elif v == ETF_CRYPTO_VIEW_IDX:
            # ETF/Crypto shortcuts
            if k == ord('1'):   ECS.screen = 0; ECS.cursor = 0
            elif k == ord('2'): ECS.screen = 1; ECS.cursor = 0
            elif k == ord('3'): ECS.screen = 2; ECS.cursor = 0
            elif k == ord('4'): ECS.screen = 3; ECS.cursor = 0
            elif k in (ord('j'), curses.KEY_DOWN):
                ECS.cursor += 1
            elif k in (ord('k'), curses.KEY_UP):
                ECS.cursor = max(0, ECS.cursor - 1)
            elif k == ord('a'):
                ECS.input_mode = True; ECS.input_buf = ""
            elif k == ord('d') and ECS.custom:
                if ECS.cursor < len(ECS.custom):
                    ECS.custom.pop(ECS.cursor)
                    _save_ec_custom()
                    ECS.msg = "Removed"; ECS.msg_time = time.time()
            elif k == ord('r'):
                threading.Thread(target=fetch_etf_bg, daemon=True).start()
                threading.Thread(target=fetch_crypto_bg, daemon=True).start()
                ECS.msg = "Refreshing..."; ECS.msg_time = time.time()


# ══════════════════════════════════════════════════════════════════════════════
#  NEWS & STOCKS ENGINE
# ══════════════════════════════════════════════════════════════════════════════
import urllib.request as _ureq
import html as _html


def _open_url(url):
    """Open URL in the default browser. Non-blocking — runs in a daemon thread.
    Also writes the URL to ~/.ts_last_url.txt as a fallback the user can copy.
    """
    if not url:
        return
    # Always write to file so user can find it even if browser fails
    try:
        with open(os.path.expanduser("~/.ts_last_url.txt"), "w") as _f:
            _f.write(url + "\n")
    except Exception:
        pass
    def _do_open():
        opened = False
        # Try platform-native opener first (never blocks curses)
        try:
            sys_name = platform.system()
            if sys_name == "Darwin":
                r = subprocess.run(["open", url],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=5)
                opened = (r.returncode == 0)
            elif sys_name == "Windows":
                os.startfile(url)
                opened = True
            else:
                # Try xdg-open, then sensible-browser, then x-www-browser
                for cmd in ("xdg-open", "sensible-browser", "x-www-browser"):
                    if shutil.which(cmd):
                        r = subprocess.run([cmd, url],
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, timeout=5)
                        opened = (r.returncode == 0)
                        if opened:
                            break
        except Exception:
            pass
        if not opened:
            # Last resort: Python webbrowser module
            try:
                import webbrowser
                webbrowser.open_new_tab(url)
            except Exception:
                pass
    threading.Thread(target=_do_open, daemon=True).start()
    # Show confirmation in NSS message bar
    NSS.msg = f"Opening: {url[:60]}"
    NSS.msg_time = time.time()

NEWS_FILE      = os.path.join(os.path.expanduser("~"), ".terminal_standby_news.json")
STOCKS_FILE    = os.path.join(os.path.expanduser("~"), ".terminal_standby_stocks.json")
SETTINGS_FILE  = os.path.join(os.path.expanduser("~"), ".terminal_standby_settings.json")

_NEWS_LOCK   = threading.Lock()
_STOCKS_LOCK = threading.Lock()

_news_items    = []   # list of {"title":str, "source":str, "time":str, "country":str}
_stock_data    = {}   # symbol -> {"price":float, "change":float, "pct":float, "name":str}
_news_status   = "Loading news…"
_stocks_status = "Loading stocks…"
_news_last     = 0.0
_stocks_last   = 0.0

# ── Currency rate cache ────────────────────────────────────────────────────────
_currency_rates  = {}   # "FROM/TO" -> float rate
_currency_lock   = threading.Lock()
_currency_last   = 0.0
CURRENCY_REFRESH = 1800  # 30 min

NEWS_REFRESH_SECS   = 3600   # 1 hour
STOCKS_REFRESH_SECS = 300    # 5 minutes

# ── Country database ──────────────────────────────────────────────────────────
# Each entry: code, flag, display name, [RSS feeds], [default stock tickers]
COUNTRY_DB = {
    "US": {
        "flag": "🇺🇸", "name": "United States",
        "feeds": [
            ("Reuters",    "https://feeds.reuters.com/reuters/topNews"),
            ("AP News",    "https://feeds.apnews.com/rss/apf-topnews"),
            ("CNN",        "https://rss.cnn.com/rss/cnn_topstories.rss"),
            ("NPR",        "https://feeds.npr.org/1001/rss.xml"),
        ],
        "stocks": ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA", "META"],
        "currency": "USD",
    },
    "GB": {
        "flag": "🇬🇧", "name": "United Kingdom",
        "feeds": [
            ("BBC News",   "https://feeds.bbci.co.uk/news/rss.xml"),
            ("Guardian",   "https://www.theguardian.com/uk/rss"),
            ("Sky News",   "https://feeds.skynews.com/feeds/rss/home.xml"),
        ],
        "stocks": ["BARC.L", "HSBA.L", "BP.L", "VOD.L", "GSK.L", "AZN.L"],
        "currency": "GBP",
    },
    "IN": {
        "flag": "🇮🇳", "name": "India",
        "feeds": [
            ("Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
            ("Hindu",          "https://www.thehindu.com/news/feeder/default.rss"),
            ("NDTV",           "https://feeds.feedburner.com/NDTV-TopStories"),
            ("India Today",    "https://www.indiatoday.in/rss/1206578"),
            ("Economic Times", "https://economictimes.indiatimes.com/rssfeedsdefault.cms"),
        ],
        "stocks": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "WIPRO.NS", "ICICIBANK.NS"],
        "currency": "INR",
    },
    "DE": {
        "flag": "🇩🇪", "name": "Germany",
        "feeds": [
            ("DW",        "https://rss.dw.com/rdf/rss-en-all"),
            ("Spiegel",   "https://www.spiegel.de/schlagzeilen/index.rss"),
            ("Reuters DE","https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["SAP.DE", "BMW.DE", "SIE.DE", "ALV.DE", "DTE.DE", "VOW3.DE"],
        "currency": "EUR",
    },
    "FR": {
        "flag": "🇫🇷", "name": "France",
        "feeds": [
            ("France 24", "https://www.france24.com/en/rss"),
            ("Le Monde",  "https://www.lemonde.fr/rss/une.xml"),
            ("Reuters",   "https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["MC.PA", "OR.PA", "TTE.PA", "SAN.PA", "AIR.PA", "BNP.PA"],
        "currency": "EUR",
    },
    "JP": {
        "flag": "🇯🇵", "name": "Japan",
        "feeds": [
            ("Japan Times", "https://www.japantimes.co.jp/feed/"),
            ("NHK World",   "https://www3.nhk.or.jp/nhkworld/en/news/feeds/"),
            ("Reuters",     "https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["7203.T", "6758.T", "9984.T", "8306.T", "6861.T", "9432.T"],
        "currency": "JPY",
    },
    "AU": {
        "flag": "🇦🇺", "name": "Australia",
        "feeds": [
            ("ABC AU",    "https://www.abc.net.au/news/feed/51120/rss.xml"),
            ("SMH",       "https://www.smh.com.au/rss/feed.xml"),
            ("Reuters",   "https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["CBA.AX", "BHP.AX", "ANZ.AX", "WBC.AX", "CSL.AX", "NAB.AX"],
        "currency": "AUD",
    },
    "CA": {
        "flag": "🇨🇦", "name": "Canada",
        "feeds": [
            ("CBC",        "https://www.cbc.ca/cmlink/rss-topstories"),
            ("Globe Mail", "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/canada/"),
            ("Reuters",    "https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["SHOP.TO", "RY.TO", "TD.TO", "BNS.TO", "ENB.TO", "CNR.TO"],
        "currency": "CAD",
    },
    "SG": {
        "flag": "🇸🇬", "name": "Singapore",
        "feeds": [
            ("CNA",          "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml"),
            ("Straits Times","https://www.straitstimes.com/news/singapore/rss.xml"),
            ("Reuters",      "https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["D05.SI", "O39.SI", "U11.SI", "Z74.SI", "C6L.SI", "G13.SI"],
        "currency": "SGD",
    },
    "BR": {
        "flag": "🇧🇷", "name": "Brazil",
        "feeds": [
            ("Folha",     "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml"),
            ("Reuters",   "https://feeds.reuters.com/reuters/topNews"),
            ("Al Jazeera","https://www.aljazeera.com/xml/rss/all.xml"),
        ],
        "stocks": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA"],
        "currency": "BRL",
    },
    "ZA": {
        "flag": "🇿🇦", "name": "South Africa",
        "feeds": [
            ("News24",    "https://feeds.news24.com/articles/news24/TopStories/rss"),
            ("Reuters",   "https://feeds.reuters.com/reuters/topNews"),
            ("Al Jazeera","https://www.aljazeera.com/xml/rss/all.xml"),
        ],
        "stocks": ["NPN.JO", "AGL.JO", "SOL.JO", "FSR.JO", "SBK.JO"],
        "currency": "ZAR",
    },
    "AE": {
        "flag": "🇦🇪", "name": "UAE",
        "feeds": [
            ("Gulf News",  "https://gulfnews.com/rss"),
            ("Khaleej",    "https://www.khaleejtimes.com/rss"),
            ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ],
        "stocks": ["FAB.AD", "ENBD.DU", "EMAAR.DU", "DIB.DU", "ETISALAT.AD"],
        "currency": "AED",
    },
    "NG": {
        "flag": "🇳🇬", "name": "Nigeria",
        "feeds": [
            ("Punch",      "https://punchng.com/feed/"),
            ("Vanguard",   "https://www.vanguardngr.com/feed/"),
            ("Reuters",    "https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["DANGCEM.LG", "GTCO.LG", "MTNN.LG", "ZENITHBANK.LG"],
        "currency": "NGN",
    },
    "KR": {
        "flag": "🇰🇷", "name": "South Korea",
        "feeds": [
            ("Korea Herald","https://www.koreaherald.com/rss/"),
            ("Yonhap",      "https://en.yna.co.kr/RSS/news.xml"),
            ("Reuters",     "https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["005930.KS", "000660.KS", "035420.KS", "005380.KS"],
        "currency": "KRW",
    },
    "CN": {
        "flag": "🇨🇳", "name": "China",
        "feeds": [
            ("CGTN",      "https://www.cgtn.com/subscribe/rss/section/news.xml"),
            ("Xinhua",    "https://english.news.cn/rss/world.xml"),
            ("Reuters",   "https://feeds.reuters.com/reuters/topNews"),
        ],
        "stocks": ["BABA", "JD", "PDD", "BIDU", "NIO", "XPEV"],
        "currency": "CNY",
    },
    "MX": {
        "flag": "🇲🇽", "name": "Mexico",
        "feeds": [
            ("El Universal","https://www.eluniversal.com.mx/rss.xml"),
            ("Reuters",     "https://feeds.reuters.com/reuters/topNews"),
            ("Al Jazeera",  "https://www.aljazeera.com/xml/rss/all.xml"),
        ],
        "stocks": ["AMXL.MX", "FEMSAUBD.MX", "WALMEX.MX", "GFNORTEO.MX"],
        "currency": "MXN",
    },
    "GLOBAL": {
        "flag": "🌍", "name": "Global / International",
        "feeds": [
            ("Reuters",    "https://feeds.reuters.com/reuters/topNews"),
            ("BBC News",   "https://feeds.bbci.co.uk/news/rss.xml"),
            ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
            ("AP News",    "https://feeds.apnews.com/rss/apf-topnews"),
        ],
        "stocks": ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA"],
        "currency": "USD",
    },
}

COUNTRY_LIST = sorted(COUNTRY_DB.keys(), key=lambda c: (c == "GLOBAL", COUNTRY_DB[c]["name"]))


def load_user_settings():
    """Load persisted user settings (country, etc.)."""
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_user_settings(d):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass


def get_user_country():
    s = load_user_settings()
    return s.get("country", "")   # "" means not set yet


def set_user_country(code):
    s = load_user_settings()
    s["country"] = code
    # On first-run only: save home_currency from selected country as baseline.
    # This is overwritten once IP geolocation succeeds, but ensures the banner
    # works even if geolocation is unavailable.
    # IMPORTANT: we only write home_currency if NOT already set — changing the
    # viewed country later must NOT overwrite the user's real home currency.
    if not s.get("home_currency"):
        info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
        s["home_currency"] = info.get("currency", "USD")
        global _home_currency_cache
        _home_currency_cache = s["home_currency"]
    save_user_settings(s)
    # Re-seed watchlist with country defaults if watchlist was never customised
    wl_path = os.path.join(os.path.expanduser("~"), ".terminal_standby_watchlist.json")
    if not os.path.exists(wl_path):
        info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
        save_stock_watchlist(info["stocks"][:])


def get_active_feeds():
    code = get_user_country() or "GLOBAL"
    info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    return info["feeds"]

def _strip_tags(s):
    """Remove XML/HTML tags from a string."""
    import re
    return re.sub(r'<[^>]+>', '', s).strip()


def _fetch_rss(url, source, limit=7):
    """Fetch one RSS/Atom feed, return list of article dicts.
    Handles both <item> (RSS) and <entry> (Atom) formats."""
    import re
    USER_AGENTS = [
        "Mozilla/5.0 (compatible; TerminalStandBy/3; +https://github.com)",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Feedfetcher-Google; (+http://www.google.com/feedfetcher.html)",
    ]
    raw = None
    for ua in USER_AGENTS:
        try:
            req = _ureq.Request(url, headers={"User-Agent": ua,
                                               "Accept": "application/rss+xml, application/xml, text/xml, */*"})
            with _ureq.urlopen(req, timeout=12) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            break
        except Exception:
            continue
    if not raw:
        return []

    items = []

    # Try RSS <item> blocks first
    blocks = re.findall(r'<item[^>]*>(.*?)</item>', raw, re.DOTALL)

    # Fall back to Atom <entry> blocks
    if not blocks:
        blocks = re.findall(r'<entry[^>]*>(.*?)</entry>', raw, re.DOTALL)

    for block in blocks[:limit]:
        # title — strip CDATA and tags
        title_m = re.search(r'<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', block, re.DOTALL)
        # pubDate (RSS) or published/updated (Atom)
        date_m  = (re.search(r'<pubDate[^>]*>(.*?)</pubDate>', block, re.DOTALL) or
                   re.search(r'<published[^>]*>(.*?)</published>', block, re.DOTALL) or
                   re.search(r'<updated[^>]*>(.*?)</updated>', block, re.DOTALL))

        title = _html.unescape(_strip_tags(title_m.group(1))) if title_m else ""
        pub   = date_m.group(1).strip()[:40] if date_m else ""

        # Parse relative time
        ts = ""
        for parser in (
            lambda p: __import__('email.utils', fromlist=['parsedate_to_datetime'])
                      .parsedate_to_datetime(p),
            lambda p: datetime.datetime.fromisoformat(p.replace("Z", "+00:00")),
        ):
            try:
                dt   = parser(pub)
                # normalise to UTC-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                now  = datetime.datetime.now(datetime.timezone.utc)
                diff = now - dt
                secs = diff.total_seconds()
                if secs < 3600:
                    ts = f"{int(secs // 60)}m ago"
                elif secs < 86400:
                    ts = f"{int(secs // 3600)}h ago"
                else:
                    ts = dt.strftime("%b %d")
                break
            except Exception:
                continue
        if not ts:
            ts = pub[:12]

        # Extract article URL — prefer <guid> (canonical) over <link> (may be feed redirect)
        url = ""
        _lm_guid = re.search(r'<guid[^>]*>(https?://[^\s<]+)</guid>', block, re.DOTALL)
        _lm_link = re.search(r'<link[^>]*>\s*(https?://[^\s<]+)', block, re.DOTALL)
        _lm_href = re.search(r'<link[^>]+href=["\']([^"\'>\s]+)["\']', block, re.DOTALL)
        for _lm in (_lm_guid, _lm_link, _lm_href):
            if _lm:
                _u = _lm.group(1).strip()
                # skip feed-redirect URLs (contain /~r/ or feedburner etc.)
                if _u and '/~r/' not in _u and 'feedburner' not in _u and 'feedproxy' not in _u:
                    url = _u
                    break
        if not url and _lm_guid:  # fallback: use guid even if it looks like a feed url
            url = _lm_guid.group(1).strip()

        title = title.strip()
        if title and len(title) > 4:
            items.append({"title": title, "source": source, "time": ts, "url": url})

    return items


def _fetch_currency_rate(from_cur, to_cur):
    """Fetch exchange rate from_cur -> to_cur via Yahoo Finance.
    Returns float rate or None on failure."""
    if from_cur == to_cur:
        return 1.0
    try:
        symbol = f"{from_cur}{to_cur}=X"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        req = _ureq.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with _ureq.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        meta  = data["chart"]["result"][0]["meta"]
        rate  = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
        return rate if rate > 0 else None
    except Exception:
        return None


def fetch_currency_bg(from_cur, to_cur):
    """Background: fetch and cache currency rate."""
    global _currency_rates, _currency_last
    key  = f"{from_cur}/{to_cur}"
    rate = _fetch_currency_rate(from_cur, to_cur)
    if rate:
        with _currency_lock:
            _currency_rates[key] = rate
        _currency_last = time.time()


def get_currency_rate(from_cur, to_cur):
    """Return cached rate or None."""
    if from_cur == to_cur:
        return 1.0
    key = f"{from_cur}/{to_cur}"
    with _currency_lock:
        return _currency_rates.get(key)


_home_currency_cache = ""  # in-memory cache, populated once per session

def get_home_currency():
    """Return the user's physical home currency.

    Priority order:
    1. 'home_currency' in settings file (set at first-run, never overwritten)
    2. IP geolocation via ipapi.co (tried once, result cached to settings)
    3. USD as safe fallback

    This is intentionally SEPARATE from the viewed/selected country currency.
    If a user in India selects 'US' to watch US news/stocks, home_cur=INR
    and view_cur=USD, so we show 1 USD = 86.xx INR.
    """
    global _home_currency_cache
    if _home_currency_cache:
        return _home_currency_cache

    settings = load_user_settings()

    # 1. Already stored in settings
    stored = settings.get("home_currency", "")
    if stored and len(stored) == 3:
        _home_currency_cache = stored.upper()
        return _home_currency_cache

    # 2. Try IP geolocation
    try:
        req = _ureq.Request(
            "https://ipapi.co/json/",
            headers={"User-Agent": "Mozilla/5.0 (compatible; TerminalStandBy/3)"},
        )
        with _ureq.urlopen(req, timeout=6) as resp:
            geo = json.loads(resp.read().decode())
        currency = geo.get("currency", "")
        if currency and len(currency) == 3:
            _home_currency_cache = currency.upper()
            settings["home_currency"] = _home_currency_cache
            save_user_settings(settings)
            return _home_currency_cache
    except Exception:
        pass

    # 3. Hard fallback — do NOT use selected country here
    #    Leave home_currency unset so next session tries geolocation again
    return "USD"


def fetch_news_bg():
    """Background thread: fetch country-specific RSS feeds, merge, save."""
    global _news_items, _news_status, _news_last
    _news_status = "Fetching news…"
    feeds    = get_active_feeds()
    all_items = []
    for source, url in feeds:
        items = _fetch_rss(url, source, limit=7)
        all_items.extend(items)
    if all_items:
        with _NEWS_LOCK:
            _news_items = all_items
        try:
            with open(NEWS_FILE, "w") as f:
                json.dump(all_items, f, indent=2)
        except Exception:
            pass
        code = get_user_country() or "GLOBAL"
        flag = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])["flag"]
        _news_status = f"{flag}  Updated  {datetime.datetime.now().strftime('%H:%M')}"
    else:
        try:
            with open(NEWS_FILE) as f:
                cached = json.load(f)
            with _NEWS_LOCK:
                _news_items = cached
            _news_status = "Cached"
        except Exception:
            _news_status = "No news (check internet)"
    _news_last = time.time()


def get_news_items():
    with _NEWS_LOCK:
        return list(_news_items)


def _fetch_stock_price(symbol):
    """Fetch stock price via Yahoo Finance unofficial JSON endpoint.
    Returns dict with price data, or None if failed.
    Automatically tries common exchange suffixes for ambiguous symbols.
    """
    # Attempt 1: Try the symbol as-is
    def _try_fetch(sym):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=2d"
            req = _ureq.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            })
            with _ureq.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if not data.get("chart") or not data["chart"].get("result"):
                return None
            meta   = data["chart"]["result"][0]["meta"]
            if meta.get("regularMarketPrice") is None and meta.get("previousClose") is None:
                return None
            price  = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
            prev   = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
            change = price - prev
            pct    = (change / prev * 100) if prev else 0.0
            name   = meta.get("longName") or meta.get("shortName") or sym
            return {"price": price, "change": change, "pct": pct, "name": name[:28]}
        except Exception:
            return None
    
    # Try original symbol
    result = _try_fetch(symbol)
    if result:
        return result
    
    # If symbol has no dot, try common Indian exchange suffixes
    if "." not in symbol:
        for suffix in [".NS", ".BO", ".NU"]:
            result = _try_fetch(symbol + suffix)
            if result:
                return result
    
    return None


def fetch_stocks_bg(symbols):
    """Background thread: fetch all watched symbols."""
    global _stock_data, _stocks_status, _stocks_last
    _stocks_status = "Fetching prices…"
    new_data = {}
    failed = []
    for sym in symbols:
        result = _fetch_stock_price(sym.upper())
        if result:
            new_data[sym.upper()] = result
        else:
            failed.append(sym.upper())
    if new_data:
        with _STOCKS_LOCK:
            _stock_data.update(new_data)
        try:
            combined = {}
            with _STOCKS_LOCK:
                combined = dict(_stock_data)
            with open(STOCKS_FILE, "w") as f:
                json.dump(combined, f, indent=2)
        except Exception:
            pass
        if failed:
            _stocks_status = f"Updated {len(new_data)} — {len(failed)} invalid"
        else:
            _stocks_status = f"Updated  {datetime.datetime.now().strftime('%H:%M')}"
    else:
        if symbols:
            _stocks_status = f"Failed: Invalid symbol(s). Try with exchange suffix (e.g., OLECTRA.NS)"
        else:
            _stocks_status = "No data (check internet)"
    _stocks_last = time.time()


# ── Per-country market symbols for the MARKET trending screen ─────────────
MARKET_SYMBOLS = {
    "US":     ["AAPL","MSFT","NVDA","GOOGL","AMZN","TSLA","META","BRK-B","JPM","V","NFLX","AMD"],
    "IN":     ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","WIPRO.NS","BAJFINANCE.NS",
               "ICICIBANK.NS","HINDUNILVR.NS","SBIN.NS","ADANIENT.NS","LT.NS","MARUTI.NS"],
    "GB":     ["BARC.L","HSBA.L","BP.L","VOD.L","GSK.L","AZN.L","SHEL.L","LLOY.L","RIO.L","BT-A.L"],
    "DE":     ["SAP.DE","BMW.DE","SIE.DE","ALV.DE","DTE.DE","VOW3.DE","BAS.DE","MRK.DE","BAYN.DE"],
    "FR":     ["MC.PA","OR.PA","TTE.PA","SAN.PA","AIR.PA","BNP.PA","SU.PA","DG.PA","CAP.PA"],
    "JP":     ["7203.T","9984.T","6758.T","8306.T","6861.T","9432.T","4063.T","6367.T","7974.T"],
    "AU":     ["CBA.AX","BHP.AX","ANZ.AX","WBC.AX","CSL.AX","NAB.AX","WDS.AX","MQG.AX","RIO.AX"],
    "CA":     ["SHOP.TO","RY.TO","TD.TO","BNS.TO","ENB.TO","CNR.TO","BMO.TO","MFC.TO","CP.TO"],
    "CN":     ["BABA","JD","PDD","BIDU","NIO","XPEV","TCEHY","NTES","LI","VIPS"],
    "KR":     ["005930.KS","000660.KS","035420.KS","005380.KS","051910.KS","055550.KS"],
    "SG":     ["D05.SI","O39.SI","U11.SI","Z74.SI","C6L.SI","G13.SI","S68.SI","Y92.SI"],
    "BR":     ["PETR4.SA","VALE3.SA","ITUB4.SA","BBDC4.SA","ABEV3.SA","WEGE3.SA","MGLU3.SA"],
    "ZA":     ["NPN.JO","AGL.JO","SOL.JO","FSR.JO","SBK.JO","MTN.JO","NED.JO","BID.JO"],
    "AE":     ["FAB.AD","ENBD.DU","EMAAR.DU","DIB.DU","ETISALAT.AD","ADCB.AD","ALDAR.AD"],
    "MX":     ["AMXL.MX","FEMSAUBD.MX","WALMEX.MX","GFNORTEO.MX","CEMEXCPO.MX","BIMBOA.MX"],
    "NG":     ["DANGCEM.LG","GTCO.LG","MTNN.LG","ZENITHBANK.LG"],
    "GLOBAL": ["AAPL","MSFT","NVDA","TSLA","AMZN","BABA","RELIANCE.NS","SAP.DE",
               "9984.T","SHOP.TO","BHP.AX","MC.PA","005930.KS","NESN.SW","TSM"],
}

# ETF/Crypto symbols for the dedicated ETF/Crypto view
ETF_SYMBOLS  = ["SPY","QQQ","VTI","IWM","EFA","VWO","GLD","SLV","USO","TLT",
                "VNQ","XLK","XLF","XLE","ARKK","SCHD","JEPI","BND","HYG","EMB"]
CRYPTO_SYMBOLS = ["BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD",
                  "DOGE-USD","AVAX-USD","DOT-USD","MATIC-USD","LINK-USD","UNI-USD",
                  "ATOM-USD","LTC-USD","TRX-USD","SHIB-USD"]
FOREX_SYMBOLS  = ["EURUSD=X","GBPUSD=X","USDJPY=X","USDINR=X","USDCNY=X",
                  "USDKRW=X","USDAUD=X","USDCAD=X","USDSGD=X","USDBRL=X"]
COMMODITY_SYMS = ["GC=F","CL=F","SI=F","NG=F","ZW=F","ZC=F","HG=F","PL=F"]


def get_market_symbols_for_country(code):
    """Return the right symbol list for the current viewed country."""
    if code in MARKET_SYMBOLS:
        return MARKET_SYMBOLS[code]
    return MARKET_SYMBOLS["GLOBAL"]

_market_data   = {}   # sym -> price info (same format as _stock_data)
_market_status = "Loading market data…"
_market_last   = 0.0
_MARKET_LOCK   = threading.Lock()
MARKET_REFRESH = 300  # 5 min


def fetch_market_bg(symbols=None):
    """Fetch market symbols for current country. symbols=None means auto from country."""
    global _market_data, _market_status, _market_last
    _market_status = "Fetching market data…"
    if symbols is None:
        code    = get_user_country() or "GLOBAL"
        symbols = get_market_symbols_for_country(code)
    fetched = {}
    for sym in symbols:
        result = _fetch_stock_price(sym)
        if result:
            fetched[sym.upper()] = result
    if fetched:
        with _MARKET_LOCK:
            _market_data = fetched
        _market_status = f"Updated {datetime.datetime.now().strftime('%H:%M')}"
    else:
        _market_status = "Market data unavailable"
    _market_last = time.time()


def get_market_data():
    with _MARKET_LOCK:
        return dict(_market_data)


def _market_refresh_loop():
    global _market_last
    while True:
        if time.time() - _market_last >= MARKET_REFRESH:
            fetch_market_bg()
        time.sleep(10)


# ── ETF / Crypto / Forex / Commodity data ────────────────────────────────────
_etf_data      = {}
_crypto_data   = {}
_etf_status    = "Loading…"
_crypto_status = "Loading…"
_etf_last      = 0.0
_crypto_last   = 0.0
_ETF_LOCK      = threading.Lock()
_CRYPTO_LOCK   = threading.Lock()
EC_REFRESH     = 300   # 5 min

def fetch_etf_bg():
    global _etf_data, _etf_status, _etf_last
    _etf_status = "Fetching ETFs…"
    d = {}
    for sym in ETF_SYMBOLS:
        r = _fetch_stock_price(sym)
        if r: d[sym] = r
    with _ETF_LOCK:
        _etf_data = d
    _etf_status = f"ETFs updated {datetime.datetime.now().strftime('%H:%M')}"
    _etf_last   = time.time()

def fetch_crypto_bg():
    global _crypto_data, _crypto_status, _crypto_last
    _crypto_status = "Fetching crypto…"
    d = {}
    for sym in CRYPTO_SYMBOLS + FOREX_SYMBOLS + COMMODITY_SYMS:
        r = _fetch_stock_price(sym)
        if r: d[sym] = r
    with _CRYPTO_LOCK:
        _crypto_data = d
    _crypto_status = f"Crypto updated {datetime.datetime.now().strftime('%H:%M')}"
    _crypto_last   = time.time()

def get_etf_data():
    with _ETF_LOCK: return dict(_etf_data)

def get_crypto_data():
    with _CRYPTO_LOCK: return dict(_crypto_data)

def _etf_crypto_refresh_loop():
    global _etf_last, _crypto_last
    while True:
        now = time.time()
        if now - _etf_last   >= EC_REFRESH: fetch_etf_bg()
        if now - _crypto_last >= EC_REFRESH: fetch_crypto_bg()
        time.sleep(15)


def load_stock_watchlist():
    """Load user's stock watchlist from disk."""
    path = os.path.join(os.path.expanduser("~"), ".terminal_standby_watchlist.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]


def save_stock_watchlist(lst):
    path = os.path.join(os.path.expanduser("~"), ".terminal_standby_watchlist.json")
    try:
        with open(path, "w") as f:
            json.dump(lst, f)
    except Exception:
        pass


def get_stock_data():
    with _STOCKS_LOCK:
        return dict(_stock_data)


# ─── Auto-refresh scheduler ────────────────────────────────────────────────
def _news_refresh_loop():
    """Auto-refresh news periodically. Uses short sleeps so manual refresh
    (which updates _news_last to 0) can trigger an immediate re-fetch."""
    global _news_last
    while True:
        now = time.time()
        if now - _news_last >= NEWS_REFRESH_SECS:
            fetch_news_bg()
        time.sleep(5)   # check every 5 s; manual refresh sets _news_last=0

def _stocks_refresh_loop():
    """Auto-refresh stocks periodically. Short sleep so watchlist changes
    and manual refreshes are picked up quickly."""
    global _stocks_last
    while True:
        wl  = load_stock_watchlist()
        now = time.time()
        if now - _stocks_last >= STOCKS_REFRESH_SECS:
            fetch_stocks_bg(wl)
        time.sleep(5)

def _currency_refresh_loop():
    """Periodically refresh viewed-country-currency -> home-currency exchange rate."""
    global _currency_last
    while True:
        now      = time.time()
        home_cur = get_home_currency()   # fast after first call (cached in memory)
        code     = get_user_country() or "GLOBAL"
        view_cur = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"]).get("currency", "USD")
        # Fetch whenever: due for refresh OR rate not yet in cache
        needs_fetch = (now - _currency_last >= CURRENCY_REFRESH or
                       (home_cur and view_cur and home_cur != view_cur and
                        get_currency_rate(view_cur, home_cur) is None))
        if home_cur and view_cur and home_cur != view_cur and needs_fetch:
            fetch_currency_bg(view_cur, home_cur)
        time.sleep(15)   # check every 15 s so new country triggers fast

# Load cached data immediately on startup
def _load_cached_news():
    global _news_items, _news_status
    try:
        with open(NEWS_FILE) as f:
            data = json.load(f)
        with _NEWS_LOCK:
            _news_items = data
        _news_status = "Cached"
    except Exception:
        pass

def _load_cached_stocks():
    global _stock_data, _stocks_status
    try:
        with open(STOCKS_FILE) as f:
            data = json.load(f)
        with _STOCKS_LOCK:
            _stock_data = data
        _stocks_status = "Cached"
    except Exception:
        pass

_load_cached_news()
_load_cached_stocks()
threading.Thread(target=_news_refresh_loop,       daemon=True).start()
threading.Thread(target=_stocks_refresh_loop,     daemon=True).start()
threading.Thread(target=_currency_refresh_loop,   daemon=True).start()
threading.Thread(target=_market_refresh_loop,     daemon=True).start()
threading.Thread(target=_etf_crypto_refresh_loop, daemon=True).start()
threading.Thread(target=get_home_currency,        daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 9 — NEWS & STOCKS
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#  CONSOLIDATED NEWS & MARKET HUB — Market Pulse + Top Mover + Headlines
# ══════════════════════════════════════════════════════════════════════════════
def v_news_market_hub(win, W, H):
    """Apple-inspired composition for the News & Market Hub."""
    news_items  = get_news_items()
    market_data = get_market_data()
    etf_data    = get_etf_data()
    crypto_data = get_crypto_data()
    stock_data  = get_stock_data()
    all_assets  = {**market_data, **etf_data, **crypto_data, **stock_data}

    code = get_user_country() or "GLOBAL"
    info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    flag = info["flag"]; cname = info["name"]
    country_cur = info.get("currency", "USD")

    # Build a country-specific symbol universe for dashboard cards.
    country_defaults = [s.upper() for s in info.get("stocks", [])]
    country_market   = [s.upper() for s in get_market_symbols_for_country(code)]
    country_universe = set(country_defaults + country_market)
    country_assets   = {sym: v for sym, v in all_assets.items() if sym.upper() in country_universe}

    # Currency symbol for country-wise display.
    cur_map = {
        "USD":"$","EUR":"€","GBP":"£","JPY":"¥","INR":"₹","CNY":"¥",
        "KRW":"₩","AUD":"A$","CAD":"C$","SGD":"S$","BRL":"R$",
        "ZAR":"R","AED":"د.إ","NGN":"₦","MXN":"$","HKD":"HK$",
    }
    cur_sym = cur_map.get(country_cur, country_cur + " ")

    if W < 92 or H < 28:
        centre(win, H // 2 - 1, "News & Market Hub looks best at 92x28+", cp(P_AMBER, bold=True))
        centre(win, H // 2, "Resize terminal for premium card layout", cp(P_DIM))
        put(win, H - 1, 2, "1 news  2 stocks  3 markets  r refresh  ←/→ views", cp(P_DIM))
        return

    put(win, 1, 0, "─" * W, cp(P_BOX))
    put(win, 2, 2, " NEWS & MARKET HUB ", cp(P_CYAN, bold=True) | curses.A_BOLD)
    put(win, 2, W - 35, f"{flag} {cname}  ·  live market board", cp(P_DIM))
    put(win, 3, 0, "─" * W, cp(P_BOX))

    gutter = 2
    frame_x = 1
    frame_w = W - 2
    top_y = 4
    top_h = 10
    left_w = (frame_w - gutter) // 2
    right_w = frame_w - gutter - left_w
    left_x = frame_x
    right_x = left_x + left_w + gutter

    bottom_y = top_y + top_h + 1
    bottom_h = H - bottom_y - 3

    _draw_cell_market_pulse(win, top_y, left_x, left_w, top_h,
                            country_assets, country_defaults, country_market,
                            cur_sym, cname)
    _draw_cell_top_mover(win, top_y, right_x, right_w, top_h, country_assets, cur_sym, cname)
    _draw_cell_headlines(win, bottom_y, frame_x, frame_w, bottom_h, news_items)

    put(win, H - 2, 0, "─" * W, cp(P_BOX))
    put(win, H - 1, 2,
        "1 news  2 stocks  3 markets  r refresh  esc back  q quit",
        cp(P_DIM))


def _draw_cell_market_pulse(win, y, x, w, h, country_assets, country_defaults, country_market, cur_sym, cname):
    """Cell A: compact pulse board with two anchors and momentum bars."""
    box(win, y, x, h, w, " MARKET PULSE ")

    preferred = [s for s in country_defaults if s in country_assets]
    picks = []
    for sym in preferred:
        info = country_assets.get(sym)
        if info:
            picks.append((sym, info))
        if len(picks) >= 2:
            break

    if len(picks) < 2:
        fallback = [(s, country_assets[s]) for s in country_market if s in country_assets]
        fallback.sort(key=lambda kv: abs(kv[1].get("pct", 0)), reverse=True)
        for sym, info in fallback:
            if sym not in [s for s, _ in picks]:
                picks.append((sym, info))
            if len(picks) >= 2:
                break

    if not picks:
        put(win, y + 3, x + 3, "Waiting for market feed...", cp(P_AMBER))
        return

    put(win, y + 1, x + 2, f"{cname} benchmarks", cp(P_DIM))
    row = y + 2
    for sym, info in picks[:2]:
        pct = info.get("pct", 0.0)
        price = info.get("price", 0.0)
        col = P_GREEN if pct > 0 else (P_RED if pct < 0 else P_MID)
        arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "•")
        label = f"{sym:<10} {cur_sym}{price:>8.2f} {arrow}{pct:+6.2f}%"
        put(win, row, x + 2, label[:w - 4], cp(col, bold=True))
        bar_w = max(8, w - 24)
        hbar(win, row, x + w - bar_w - 3, bar_w, min(100, abs(pct) * 11), col)
        row += 2

    up = sum(1 for _, i in country_assets.items() if i.get("pct", 0) > 0)
    dn = sum(1 for _, i in country_assets.items() if i.get("pct", 0) < 0)
    pulse = f"Breadth  {up:02d} up  /  {dn:02d} down"
    put(win, y + h - 2, x + 2, pulse[:w - 4], cp(P_CYAN))


def _draw_cell_top_mover(win, y, x, w, h, all_assets, cur_sym, cname):
    """Cell B: hero card for the strongest mover right now."""
    box(win, y, x, h, w, " TOP MOVER ")

    if not all_assets:
        put(win, y + 2, x + 3, f"No {cname} market data", cp(P_AMBER))
        return

    ranked = sorted(all_assets.items(), key=lambda kv: abs(kv[1].get("pct", 0)), reverse=True)
    sym, info = ranked[0]
    pct = info.get("pct", 0.0)
    chg = info.get("change", 0.0)
    px = info.get("price", 0.0)
    name = info.get("name", sym)

    col = P_GREEN if pct > 0 else (P_RED if pct < 0 else P_MID)
    mood = "Breakout" if pct > 0 else ("Selloff" if pct < 0 else "Flat")

    put(win, y + 1, x + 2, f"{cname} {mood.lower()} leader", cp(P_DIM))
    put(win, y + 2, x + 2, f"{sym}"[:w - 4], cp(P_HI, bold=True) | curses.A_BOLD)
    put(win, y + 3, x + 2, name[:w - 4], cp(P_MID))
    put(win, y + 5, x + 2, f"{cur_sym}{px:,.2f}", cp(P_HI, bold=True))
    put(win, y + 6, x + 2, f"{chg:+.2f}   ({pct:+.2f}%)", cp(col, bold=True))

    if len(ranked) > 1:
        s2, i2 = ranked[1]
        p2 = i2.get("pct", 0.0)
        c2 = P_GREEN if p2 > 0 else (P_RED if p2 < 0 else P_MID)
        put(win, y + h - 2, x + 2, f"Next: {s2} {p2:+.2f}%"[:w - 4], cp(c2))


def _draw_cell_headlines(win, y, x, w, h, news_items):
    """Cell C: stable base card with headline hero."""
    box(win, y, x, h, w, " HEADLINE OF THE MOMENT ")

    if not news_items:
        put(win, y + 2, x + 2, "No headlines yet. Check connection.", cp(P_AMBER))
        return

    top = news_items[0]
    title = (top.get("title") or "No title").strip()
    source = top.get("source", "Unknown")
    ts = top.get("time", "")
    url = top.get("url", "")

    title_1 = title[:w - 6]
    title_2 = title[w - 6:(w - 6) * 2]
    put(win, y + 2, x + 2, title_1, cp(P_HI, bold=True))
    if title_2:
        put(win, y + 3, x + 2, title_2, cp(P_HI, bold=True))

    meta = f"{source}  •  {ts}"
    put(win, y + 4, x + 2, meta[:w - 4], cp(P_CYAN))
    if url:
        put(win, y + 5, x + 2, "Press ENTER in News view to open full story", cp(P_DIM))

    row = y + 7
    put(win, row, x + 2, "More headlines", cp(P_DIM))
    row += 1
    for i in range(1, min(4, len(news_items))):
        if row >= y + h - 3:
            break
        item = news_items[i]
        line = f"• {(item.get('title') or '')[:w - 10]}"
        put(win, row, x + 3, line, cp(P_MID))
        row += 1

def v_news_stocks(win, W, H):
    # ── First-run country setup ───────────────────────────────────────────────
    if not get_user_country():
        _draw_country_setup(win, W, H)
        return

    items  = get_news_items()
    stocks = get_stock_data()
    wl     = load_stock_watchlist()

    # ── Tab bar ──────────────────────────────────────────────────────────────
    code = get_user_country()
    info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    flag = info["flag"]; cname = info["name"]

    tabs = [("  NEWS  ", 0), ("  STOCKS  ", 1)]
    tx = 2
    NSS.tab_regions = []   # rebuilt every frame
    for lbl, idx in tabs:
        active = (NSS.tab == idx)
        attr   = cp(P_CYAN, bold=True) | curses.A_REVERSE if active else cp(P_DIM)
        put(win, 1, tx, lbl, attr)
        # record hit region: columns tx..(tx+len(lbl)), row 1
        NSS.tab_regions.append((tx, tx + len(lbl), idx))
        tx += len(lbl) + 1

    country_lbl = f"  {flag} {cname} "
    put(win, 1, tx + 2, country_lbl, cp(P_AMBER))
    put(win, 1, tx + 2 + len(country_lbl) + 1, "C change country", cp(P_DIM))
    put(win, 2, 0, "─" * W, cp(P_BOX))

    if NSS.country_mode:
        _draw_country_overlay(win, W, H)
        return

    if NSS.tab == 0:
        _draw_news_tab(win, W, H, items)
    else:
        _draw_stocks_tab(win, W, H, stocks, wl)


def _draw_country_setup(win, W, H):
    """Full-screen first-run country picker."""
    centre(win, 1, "  TERMINAL STANDBY — FIRST TIME SETUP  ", cp(P_CYAN, bold=True) | curses.A_BOLD)
    centre(win, 2, "Select your country to get local news & stock defaults", cp(P_DIM))
    put(win, 3, 0, "─" * W, cp(P_BOX))

    list_h  = H - 8
    list_y  = 4
    n       = len(COUNTRY_LIST)
    NSS.country_cur = max(0, min(NSS.country_cur, n - 1))
    start   = max(0, NSS.country_cur - list_h // 2)
    start   = min(start, max(0, n - list_h))

    box(win, list_y - 1, (W - 44) // 2, list_h + 2, 44, "CHOOSE YOUR COUNTRY  [j/k]=nav  [ENTER]=select")

    for i, code in enumerate(COUNTRY_LIST[start:start + list_h]):
        ri   = start + i
        ry   = list_y + i
        sel  = (ri == NSS.country_cur)
        info = COUNTRY_DB[code]
        line = f"  {info['flag']}  {info['name']:<26}  [{code}]"
        attr = (cp(P_AMBER, bold=True) | curses.A_REVERSE) if sel else cp(P_MID)
        cx   = (W - 44) // 2 + 1
        put(win, ry, cx, " " * 42, attr)
        put(win, ry, cx, line[:42], attr)

    put(win, H - 2, 0, "─" * W, cp(P_BOX))
    put(win, H - 1, 0,
        " [j/k/↑↓] navigate  [ENTER] select country  [q] quit ",
        cp(P_DIM))


def _draw_country_overlay(win, W, H):
    """Country picker overlay (for changing country after setup)."""
    ow = min(W - 4, 50); ox = (W - ow) // 2; oy = 3
    oh = H - oy - 3
    # dim background hint
    put(win, oy - 1, 0, "─" * W, cp(P_BOX))
    box(win, oy, ox, oh, ow, f"CHANGE COUNTRY  [j/k]=nav  [ENTER]=select  [ESC]=cancel")

    n      = len(COUNTRY_LIST)
    list_h = oh - 2
    NSS.country_cur = max(0, min(NSS.country_cur, n - 1))
    start  = max(0, NSS.country_cur - list_h // 2)
    start  = min(start, max(0, n - list_h))

    for i, code in enumerate(COUNTRY_LIST[start:start + list_h]):
        ri   = start + i
        ry   = oy + 1 + i
        sel  = (ri == NSS.country_cur)
        info = COUNTRY_DB[code]
        line = f"  {info['flag']}  {info['name']:<24}  [{code:<6}]"
        attr = (cp(P_AMBER, bold=True) | curses.A_REVERSE) if sel else cp(P_MID)
        put(win, ry, ox + 1, " " * (ow - 2), attr)
        put(win, ry, ox + 1, line[:ow - 2], attr)

    put(win, H - 1, 0,
        " [j/k] navigate  [ENTER] confirm  [ESC] cancel  [←→] views ",
        cp(P_DIM))


def _draw_news_tab(win, W, H, items):
    code   = get_user_country() or "GLOBAL"
    c_info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    flag   = c_info["flag"]; cname = c_info["name"]
    put(win, 3, 2, f"[ {flag} {cname}  ·  {_news_status}  ·  refreshes hourly ]", cp(P_DIM))
    put(win, 4, 0, "─" * W, cp(P_BOX))

    if not items:
        centre(win, H // 2, "  No news items. Check internet connection.  ", cp(P_AMBER))
        put(win, H-1, 0,
            " [1] News  [2] Stocks  [j/k] scroll  [r] refresh  [←→] views ",
            cp(P_DIM))
        return

    content_h = H - 7
    max_scroll = max(0, len(items) * 3 - content_h)
    NSS.scroll = max(0, min(NSS.scroll, max_scroll))

    src_colors = {
        "Reuters": P_CYAN, "BBC News": P_RED, "AP News": P_AMBER,
        "Al Jazeera": P_GREEN, "Times of India": P_AMBER,
        "Hindu": P_GREEN, "NDTV": P_BLUE, "India Today": P_PINK,
    }

    # Rebuild row→item map every frame
    NSS.news_row_map = {}

    y      = 5
    offset = NSS.scroll

    for i, item in enumerate(items):
        title    = item.get("title", "")
        source   = item.get("source", "")
        ts       = item.get("time", "")
        url      = item.get("url", "")
        src_col  = src_colors.get(source, P_BLUE)
        selected = (i == NSS.news_cursor)

        # Each item = 3 rows: [0] title  [1] source+time  [2] blank
        for row_idx in range(3):
            if offset > 0:
                offset -= 1
                continue
            if y >= H - 2:
                break

            # Map title row AND source row to this item index for click detection
            if row_idx < 2:
                NSS.news_row_map[y] = i

            if row_idx == 0:
                # ── Title row ──
                bullet = "▶" if selected else "●"
                prefix = f"  {bullet} "
                title_display = (prefix + title)[:W - 2]
                if selected:
                    put(win, y, 0, " " * (W - 1), cp(P_AMBER))
                    put(win, y, 0, title_display, cp(P_AMBER, bold=True) | curses.A_REVERSE)
                else:
                    if i % 2 == 0:
                        put(win, y, 0, " " * (W - 1), cp(P_DIM))
                    put(win, y, 0, title_display, cp(P_HI, bold=True))

            elif row_idx == 1:
                # ── Source + time + url hint row ──
                link_hint = "  [ENTER/click again to open →]" if (selected and url) else (
                            "  🔗" if url else "")
                src_display = (f"    ╰ {source}  ·  {ts}{link_hint}")[:W - 2]
                if selected:
                    put(win, y, 0, " " * (W - 1), cp(P_AMBER))
                    put(win, y, 0, src_display, cp(P_CYAN))
                else:
                    if i % 2 == 0:
                        put(win, y, 0, " " * (W - 1), cp(P_DIM))
                    put(win, y, 0, src_display, cp(src_col))

            else:
                # ── Blank spacer row ──
                pass

            y += 1

        if y >= H - 2:
            break

    # Scroll bar
    if max_scroll > 0:
        bar_h = H - 7
        pct   = int(NSS.scroll / max_scroll * bar_h)
        for sy in range(5, H - 2):
            put(win, sy, W - 1, "│", cp(P_BOX))
        put(win, min(5 + pct, H - 3), W - 1, "█", cp(P_DIM))

    # Status bar — msg takes priority, then URL of selected item, then default hint
    if NSS.msg and time.time() - NSS.msg_time < 4.0:
        col = P_GREEN if "Opening" in NSS.msg else P_AMBER
        put(win, H-1, 0, f" {NSS.msg} "[:W], cp(col, bold=True))
    elif 0 <= NSS.news_cursor < len(items):
        sel_url = items[NSS.news_cursor].get("url", "")
        if sel_url:
            hint = f" ↵ ENTER / click to open  ·  {sel_url}"
            put(win, H-1, 0, hint[:W], cp(P_CYAN, bold=True))
        else:
            put(win, H-1, 0,
                " j/k move  enter open  esc deselect  r refresh  C country  q quit ",
                cp(P_DIM))
    else:
        put(win, H-1, 0,
            " j/k select  enter open  r refresh  C country  q quit ",
            cp(P_DIM))


def _draw_stocks_tab(win, W, H, stocks, watchlist):
    code     = get_user_country() or "GLOBAL"
    c_info   = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    flag     = c_info["flag"]; cname = c_info["name"]
    view_cur = c_info.get("currency", "USD")
    home_cur = get_home_currency()

    # Kick off currency fetch if needed
    if home_cur and view_cur and home_cur != view_cur:
        if get_currency_rate(view_cur, home_cur) is None:
            threading.Thread(target=lambda vc=view_cur, hc=home_cur:
                             fetch_currency_bg(vc, hc), daemon=True).start()

    # ── Sub-tab bar: MARKET | PORTFOLIO ───────────────────────────────────────
    sub_tabs = [("  MARKET  ", 0), ("  PORTFOLIO  ", 1)]
    NSS.stock_sub_regions = []
    tx = 2
    put(win, 3, 0, " " * W, cp(P_DIM))
    for lbl, idx in sub_tabs:
        active = (NSS.stock_screen == idx)
        attr   = cp(P_GREEN, bold=True) | curses.A_REVERSE if active else cp(P_DIM)
        put(win, 3, tx, lbl, attr)
        NSS.stock_sub_regions.append((tx, tx + len(lbl), idx))
        tx += len(lbl) + 1

    # Currency banner inline on row 3 right side
    if home_cur and view_cur and home_cur != view_cur:
        rate = get_currency_rate(view_cur, home_cur)
        if rate:
            cur_s = f"1 {view_cur} = {rate:.4f} {home_cur}  "
        else:
            cur_s = f"{view_cur}/{home_cur} loading…  "
        put(win, 3, W - len(cur_s) - 2, cur_s, cp(P_CYAN))

    put(win, 4, 0, "─" * W, cp(P_BOX))

    _CUR_SYM = {
        "USD":"$","EUR":"€","GBP":"£","JPY":"¥","INR":"₹","CNY":"¥",
        "KRW":"₩","AUD":"A$","CAD":"C$","SGD":"S$","BRL":"R$",
        "ZAR":"R","AED":"د.إ","NGN":"₦","MXN":"$","HKD":"HK$",
    }
    csym = _CUR_SYM.get(view_cur, view_cur + " ")

    if NSS.stock_screen == 0:
        _draw_market_screen(win, W, H, csym)
    else:
        _draw_portfolio_screen(win, W, H, stocks, watchlist, csym, view_cur, home_cur)


# ── Column layout helper ──────────────────────────────────────────────────────
def _stock_cols(W):
    C_SYM  = 2;  W_SYM  = 10
    C_NAME = C_SYM + W_SYM
    W_NAME = max(14, W - C_NAME - 34)
    C_PX   = C_NAME + W_NAME
    C_CHG  = C_PX  + 13
    C_PCT  = C_CHG + 11
    return C_SYM, W_SYM, C_NAME, W_NAME, C_PX, C_CHG, C_PCT


def _draw_stock_row(win, y, W, sym, info, csym, sel, cursor_col=P_AMBER):
    C_SYM, W_SYM, C_NAME, W_NAME, C_PX, C_CHG, C_PCT = _stock_cols(W)
    rev = curses.A_REVERSE if sel else 0
    if sel:
        put(win, y, 0, " " * (W - 1), cp(cursor_col) | rev)
    if info:
        price  = info["price"]; change = info["change"]; pct = info["pct"]
        name   = info.get("name", sym)
        arrow  = "▲" if change > 0 else ("▼" if change < 0 else "─")
        cc     = P_GREEN if change > 0 else (P_RED if change < 0 else P_MID)
        price_s  = f"{csym}{price:>9.2f}"
        change_s = f"{arrow}{abs(change):>7.2f}"
        pct_s    = f"{pct:>+6.2f}%"
    else:
        name = "loading…"; arrow = ""; cc = P_DIM
        price_s = "         ─"; change_s = "       ─"; pct_s = "      ─"

    sym_lbl = f" {'▶' if sel else ' '} {sym[:7]:<7}"
    put(win, y, C_SYM,  sym_lbl,                   cp(cursor_col if sel else P_CYAN, bold=True) | rev)
    put(win, y, C_NAME, name[:W_NAME],              cp(P_MID) | rev)
    put(win, y, C_PX,   price_s,                    cp(P_HI, bold=True) | rev)
    put(win, y, C_CHG,  f"  {change_s}",            cp(cc, bold=True) | rev)
    put(win, y, C_PCT,  f" {pct_s}",                cp(cc) | rev)


def _draw_stock_header(win, y, W):
    C_SYM, W_SYM, C_NAME, W_NAME, C_PX, C_CHG, C_PCT = _stock_cols(W)
    hdr = f"{'  SYMBOL':<{W_SYM+2}}{'NAME':<{W_NAME}}{'PRICE':>11}  {'CHANGE':>9}  {'%':>7}"
    put(win, y,   C_SYM, hdr[:W-4], cp(P_DIM))
    put(win, y+1, 0,     "─" * W,   cp(P_BOX))


# ── MARKET screen ─────────────────────────────────────────────────────────────
def _draw_market_screen(win, W, H, csym):
    data  = get_market_data()
    code  = get_user_country() or "GLOBAL"
    c_info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    flag  = c_info["flag"]; cname = c_info["name"]
    put(win, 5, 2, f"[ {flag} {cname}  ·  {_market_status}  ·  {len(data)} symbols  ·  5 min refresh ]", cp(P_DIM))
    put(win, 6, 0, "─" * W, cp(P_BOX))

    if not data:
        centre(win, H//2, "  Fetching market data…  ", cp(P_AMBER))
        put(win, H-1, 0, " [r] refresh  [m] market  [p] portfolio  [q] quit ", cp(P_DIM))
        return

    # Sort into gainers / losers / neutral
    rows = []
    for sym, info in data.items():
        rows.append((sym, info))
    rows.sort(key=lambda x: x[1]["pct"], reverse=True)

    gainers  = [(s, i) for s, i in rows if i["pct"] >  0.05]
    losers   = [(s, i) for s, i in rows if i["pct"] < -0.05]
    neutral  = [(s, i) for s, i in rows if -0.05 <= i["pct"] <= 0.05]

    # Sections: TOP GAINERS | TOP LOSERS | NEUTRAL
    # Each section up to 5 rows; header row + data rows
    SECTION_CAP = 5
    sections = [
        ("TOP GAINERS",  P_GREEN, gainers[:SECTION_CAP]),
        ("TOP LOSERS",   P_RED,   losers[-SECTION_CAP:][::-1]),   # worst first
        ("FLAT / MIXED", P_MID,   neutral[:SECTION_CAP]),
    ]

    y = 7
    _draw_stock_header(win, y, W)
    y += 2

    NSS.market_cur = max(0, min(NSS.market_cur, max(0, len(rows) - 1)))

    flat_list = []  # all drawn rows in order for cursor nav
    for sec_title, sec_col, sec_rows in sections:
        if not sec_rows:
            continue
        if y >= H - 4:
            break
        put(win, y, 2, f" {sec_title} ", cp(sec_col, bold=True) | curses.A_BOLD)
        y += 1
        for sym, info in sec_rows:
            if y >= H - 3:
                break
            flat_idx = len(flat_list)
            flat_list.append((sym, info))
            sel = (flat_idx == NSS.market_cur)
            _draw_stock_row(win, y, W, sym, info, csym, sel, cursor_col=sec_col)
            y += 1

    # bottom panel
    put(win, H-2, 0, "─" * W, cp(P_BOX))
    if 0 <= NSS.market_cur < len(flat_list):
        sym, info = flat_list[NSS.market_cur]
        pct = info["pct"]
        pc  = P_GREEN if pct > 0 else (P_RED if pct < 0 else P_MID)
        put(win, H-1, 0,
            f" ▶  {sym}  {info['name'][:30]}  {pct:+.2f}%   [r] refresh  [p] portfolio  [q] quit ",
            cp(pc, bold=True))
    else:
        put(win, H-1, 0,
            " [j/k] navigate  [r] refresh  [p] portfolio  [m] market  [q] quit ",
            cp(P_DIM))


# ── PORTFOLIO screen ──────────────────────────────────────────────────────────
def _draw_portfolio_screen(win, W, H, stocks, watchlist, csym, view_cur, home_cur):
    # Header stats
    total_val = 0.0
    total_chg = 0.0
    for sym in watchlist:
        info = stocks.get(sym.upper())
        if info:
            total_val += info["price"]
            total_chg += info["change"]

    rate     = get_currency_rate(view_cur, home_cur) if home_cur != view_cur else 1.0
    _CUR_SYM = {"USD":"$","EUR":"€","GBP":"£","JPY":"¥","INR":"₹","CNY":"¥",
                "KRW":"₩","AUD":"A$","CAD":"C$","SGD":"S$","BRL":"R$",
                "ZAR":"R","AED":"د.إ","NGN":"₦","MXN":"$","HKD":"HK$"}
    home_sym = _CUR_SYM.get(home_cur, home_cur + " ")

    chg_col = P_GREEN if total_chg >= 0 else P_RED
    put(win, 5, 2,
        f"[ {_stocks_status}  ·  {len(watchlist)} tickers ]",
        cp(P_DIM))

    if watchlist and rate and home_cur != view_cur:
        home_val = total_val * rate
        put(win, 5, W - 28,
            f"≈ {home_sym}{home_val:,.2f} {home_cur}",
            cp(P_CYAN))

    put(win, 6, 0, "─" * W, cp(P_BOX))

    if not watchlist:
        centre(win, H//2 - 1, "Your portfolio is empty", cp(P_DIM))
        centre(win, H//2,     "Press  [a]  to add a ticker", cp(P_AMBER))
        centre(win, H//2 + 1,
               "Works with: AAPL  INFY.NS  BTC-USD  ETH-USD  EURUSD=X  GC=F",
               cp(P_DIM))
        put(win, H-1, 0, " [a] add ticker  [m] market view  [q] quit ", cp(P_DIM))
        return

    _draw_stock_header(win, 7, W)
    y = 9
    NSS.stock_cur = max(0, min(NSS.stock_cur, max(0, len(watchlist) - 1)))

    for i, sym in enumerate(watchlist):
        if y >= H - 6:
            break
        sel  = (i == NSS.stock_cur)
        info = stocks.get(sym.upper())
        # Detect asset class from symbol for colour accent
        sym_up = sym.upper()
        if any(x in sym_up for x in ("BTC","ETH","SOL","BNB","XRP","DOGE","ADA","USDT","=X","CRYPTO")):
            accent = P_PINK   # crypto / forex
        elif "=F" in sym_up or sym_up in ("GLD","SLV","USO"):
            accent = P_AMBER  # commodities / ETFs
        elif any(sym_up.endswith(x) for x in (".NS",".BO",".DE",".PA",".TO",".AX",".SI",".HK",".T",".KS",".L",".JO",".SA",".MX",".AD",".DU")):
            accent = P_CYAN   # international
        else:
            accent = P_GREEN  # US / default equity

        _draw_stock_row(win, y, W, sym, info, csym, sel, cursor_col=accent)
        y += 1

    # ── Summary bar ──────────────────────────────────────────────────────────
    loaded = [stocks.get(s.upper()) for s in watchlist if stocks.get(s.upper())]
    if loaded:
        gainers_n = sum(1 for i in loaded if i["pct"] >  0.05)
        losers_n  = sum(1 for i in loaded if i["pct"] < -0.05)
        neut_n    = len(loaded) - gainers_n - losers_n
        summary   = f" ▲ {gainers_n} up   ▼ {losers_n} down   — {neut_n} flat "
        put(win, max(y + 1, H - 6), 0, "─" * W, cp(P_BOX))
        put(win, max(y + 2, H - 5), 2, summary, cp(chg_col, bold=True))

    # ── Input panel ──────────────────────────────────────────────────────────
    panel_y = H - 4
    put(win, panel_y, 0, "─" * W, cp(P_BOX))
    blink = "█" if int(time.time() * 2) % 2 else " "
    if NSS.stock_input:
        put(win, panel_y + 1, 2,
            "Add ticker (any market):  ", cp(P_DIM))
        put(win, panel_y + 1, 28,
            (NSS.stock_buf.upper() + blink)[:W - 31], cp(P_AMBER, bold=True))
        put(win, panel_y + 2, 2,
            "Stocks: AAPL  INFY.NS  RELIANCE.NS  SAP.DE  BABA    "
            "Crypto: BTC-USD  ETH-USD  SOL-USD    "
            "Forex: USDINR=X    ETF: SPY  QQQ", cp(P_DIM))
    else:
        if NSS.msg and time.time() - NSS.msg_time < 4:
            col = P_GREEN if any(w in NSS.msg for w in ("Added","Removed","Opening")) else P_RED
            put(win, panel_y + 1, 2, NSS.msg[:W-4], cp(col, bold=True))
        else:
            put(win, panel_y + 1, 2,
                f"[a] add   [d] remove   [r] refresh   [m] market view   "
                f"[D] reset defaults   {len(watchlist)} tickers",
                cp(P_DIM))

    put(win, H-1, 0,
        " [j/k] navigate  [a] add  [d] remove  [D] reset  [m] market  [r] refresh  [←→] views ",
        cp(P_DIM))


# ── Key handling for view 8 (News & Stocks) ──────────────────────────────────
def _handle_news_stocks_key(k):
    """Handle keypresses for the news/stocks view."""
    global _news_items, _news_last, _stocks_last, _currency_last, _market_last
    n_countries = len(COUNTRY_LIST)

    # ── First-run country setup (no country set yet) ──────────────────────────
    if not get_user_country():
        if k in (ord('j'), curses.KEY_DOWN):
            NSS.country_cur = min(n_countries - 1, NSS.country_cur + 1)
        elif k in (ord('k'), curses.KEY_UP):
            NSS.country_cur = max(0, NSS.country_cur - 1)
        elif k in (10, 13):
            code = COUNTRY_LIST[NSS.country_cur]
            set_user_country(code)
            # Immediately trigger fresh fetch for new country
            threading.Thread(target=fetch_news_bg,   daemon=True).start()
            threading.Thread(target=lambda: fetch_stocks_bg(load_stock_watchlist()), daemon=True).start()
            _currency_last = 0.0   # trigger currency fetch for new country
            NSS.msg = f"Country set to {COUNTRY_DB[code]['name']}"; NSS.msg_time = time.time()
        return

    # ── Country overlay open ──────────────────────────────────────────────────
    if NSS.country_mode:
        if k in (ord('j'), curses.KEY_DOWN):
            NSS.country_cur = min(n_countries - 1, NSS.country_cur + 1)
        elif k in (ord('k'), curses.KEY_UP):
            NSS.country_cur = max(0, NSS.country_cur - 1)
        elif k in (10, 13):
            code = COUNTRY_LIST[NSS.country_cur]
            old  = get_user_country()
            set_user_country(code)
            NSS.country_mode = False
            if code != old:
                # Wipe cached news so new country feeds load fresh
                with _NEWS_LOCK:
                    _news_items = []
                threading.Thread(target=fetch_news_bg,   daemon=True).start()
                threading.Thread(target=lambda: fetch_stocks_bg(load_stock_watchlist()), daemon=True).start()
                threading.Thread(target=fetch_market_bg, daemon=True).start()
                # Refresh currency rate for new country
                _currency_last = 0.0
                _market_last   = 0.0
            NSS.msg = f"Switched to {COUNTRY_DB[code]['name']}"; NSS.msg_time = time.time()
        elif k == 27:  # ESC
            NSS.country_mode = False
        return

    # ── Normal tab navigation ─────────────────────────────────────────────────
    if k == ord('1'):
        NSS.tab = 0; return
    if k == ord('2'):
        NSS.tab = 1; return
    if k == ord('C'):
        NSS.country_mode = True
        # pre-position cursor on current country
        code = get_user_country()
        try: NSS.country_cur = COUNTRY_LIST.index(code)
        except ValueError: NSS.country_cur = 0
        return
    if k == ord('r'):
        if NSS.tab == 0:
            _news_last = 0.0
            threading.Thread(target=fetch_news_bg, daemon=True).start()
        elif NSS.stock_screen == 0:
            _market_last = 0.0
            threading.Thread(target=fetch_market_bg, daemon=True).start()
        else:
            _stocks_last = 0.0
            threading.Thread(target=lambda: fetch_stocks_bg(load_stock_watchlist()), daemon=True).start()
        return

    if NSS.tab == 0:  # ── news tab ──────────────────────────────────────────
        items   = get_news_items()
        n_items = len(items)
        if k in (ord('j'), curses.KEY_DOWN):
            # j always moves selection down; auto-enter cursor mode at item 0
            if NSS.news_cursor < 0:
                NSS.news_cursor = 0
            else:
                NSS.news_cursor = min(n_items - 1, NSS.news_cursor + 1)
            # keep selected item visible
            NSS.scroll = NSS.news_cursor * 3
        elif k in (ord('k'), curses.KEY_UP):
            if NSS.news_cursor <= 0:
                NSS.news_cursor = 0
                NSS.scroll = 0
            else:
                NSS.news_cursor -= 1
                NSS.scroll = NSS.news_cursor * 3
        elif k == 27:   # ESC — deselect, back to free scroll
            NSS.news_cursor = -1
        elif k in (10, 13):  # ENTER — open URL
            if 0 <= NSS.news_cursor < n_items:
                url = items[NSS.news_cursor].get("url", "")
                if url:
                    _open_url(url)
                else:
                    NSS.msg = "No link for this item"; NSS.msg_time = time.time()

    elif NSS.tab == 1:  # ── stocks tab ────────────────────────────────────────
        # m / p switch between Market and Portfolio sub-screens
        if k == ord('m'):
            NSS.stock_screen = 0; return
        if k == ord('p'):
            NSS.stock_screen = 1; return

        if NSS.stock_screen == 0:
            # ── MARKET screen navigation ──────────────────────────────────────
            market = get_market_data()
            n_mkt  = len(market)
            if k in (ord('j'), curses.KEY_DOWN):
                NSS.market_cur = min(max(0, n_mkt - 1), NSS.market_cur + 1)
            elif k in (ord('k'), curses.KEY_UP):
                NSS.market_cur = max(0, NSS.market_cur - 1)
            elif k == ord('r'):
                _market_last   = 0.0
                threading.Thread(target=fetch_market_bg, daemon=True).start()
                NSS.msg = "Refreshing market data…"; NSS.msg_time = time.time()
            return

        # ── PORTFOLIO screen ─────────────────────────────────────────────────
        if NSS.stock_input:
            if k in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
                NSS.stock_buf = NSS.stock_buf[:-1]
            elif k == 27:
                NSS.stock_input = False
                NSS.stock_buf   = ""
            elif k in (10, 13):
                sym = NSS.stock_buf.upper().strip()
                NSS.stock_input = False
                NSS.stock_buf   = ""
                if sym:
                    wl = load_stock_watchlist()
                    if sym not in [s.upper() for s in wl]:
                        wl.append(sym)
                        save_stock_watchlist(wl)
                        threading.Thread(target=lambda s=sym: fetch_stocks_bg([s]),
                                         daemon=True).start()
                        NSS.msg      = f"Added {sym} — fetching…"
                        NSS.msg_time = time.time()
                    else:
                        NSS.msg      = f"{sym} already in portfolio"
                        NSS.msg_time = time.time()
            elif 32 <= k <= 126:
                if len(NSS.stock_buf) < 12:
                    NSS.stock_buf += chr(k)
        else:
            wl = load_stock_watchlist()
            n  = len(wl)
            if k in (ord('j'), curses.KEY_DOWN):
                NSS.stock_cur = min(max(0, n - 1), NSS.stock_cur + 1)
            elif k in (ord('k'), curses.KEY_UP):
                NSS.stock_cur = max(0, NSS.stock_cur - 1)
            elif k == ord('a'):
                NSS.stock_input = True
                NSS.stock_buf   = ""
                NSS.stock_screen = 1  # ensure we're on portfolio screen
            elif k == ord('d') and wl:
                idx = max(0, min(NSS.stock_cur, n - 1))
                removed = wl.pop(idx)
                save_stock_watchlist(wl)
                NSS.stock_cur = max(0, min(idx, len(wl) - 1))
                NSS.msg       = f"Removed {removed}"
                NSS.msg_time  = time.time()
            elif k == ord('D'):
                code     = get_user_country() or "GLOBAL"
                info     = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
                defaults = info["stocks"][:]
                save_stock_watchlist(defaults)
                NSS.stock_cur = 0
                threading.Thread(target=lambda: fetch_stocks_bg(defaults), daemon=True).start()
                NSS.msg      = f"Reset to {info['name']} defaults"
                NSS.msg_time = time.time()


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 10 — ETF · CRYPTO · FOREX · COMMODITIES
# ══════════════════════════════════════════════════════════════════════════════

class EtfCryptoState:
    def __init__(self):
        self.screen     = 0      # 0=crypto  1=etf  2=forex  3=commodities
        self.cursor     = 0
        self.input_mode = False
        self.input_buf  = ""
        self.custom     = []     # user-added custom symbols for this view
        self.msg        = ""
        self.msg_time   = 0.0
        self.sub_regions = []    # mouse hit regions for sub-tabs
        self.show_modal = False   # Show etf/crypto as overlay

ECS = EtfCryptoState()

# Load custom EC symbols from settings
def _load_ec_custom():
    s = load_user_settings()
    ECS.custom = s.get("ec_custom", [])

def _save_ec_custom():
    s = load_user_settings()
    s["ec_custom"] = ECS.custom
    save_user_settings(s)

_load_ec_custom()

_CUR_SYM_MAP = {
    "USD":"$","EUR":"€","GBP":"£","JPY":"¥","INR":"₹","CNY":"¥",
    "KRW":"₩","AUD":"A$","CAD":"C$","SGD":"S$","BRL":"R$",
    "ZAR":"R","AED":"د.إ","NGN":"₦","MXN":"$","HKD":"HK$",
}

def _ec_sub_header(win, W, H):
    """Draw the 4 sub-tab buttons for the ETF/Crypto view."""
    sub_tabs = [
        ("  CRYPTO  ",    0),
        ("  ETF  ",       1),
        ("  FOREX  ",     2),
        ("  COMMODITIES  ", 3),
    ]
    ECS.sub_regions = []
    tx = 2
    put(win, 1, 0, " " * W, cp(P_DIM))
    for lbl, idx in sub_tabs:
        active = (ECS.screen == idx)
        attr   = cp(P_PINK, bold=True) | curses.A_REVERSE if active else cp(P_DIM)
        put(win, 1, tx, lbl, attr)
        ECS.sub_regions.append((tx, tx + len(lbl), idx))
        tx += len(lbl) + 1
    put(win, 1, tx + 2, "[a] add custom  [d] remove  [r] refresh", cp(P_DIM))
    put(win, 2, 0, "─" * W, cp(P_BOX))


def _ec_draw_section(win, W, H, title, symbols, data, title_col, y_start):
    """Draw one labelled section of symbols. Returns next y."""
    y = y_start
    if not symbols:
        return y
    put(win, y, 2, f" {title} ", cp(title_col, bold=True) | curses.A_BOLD)
    y += 1

    C_SYM, W_SYM, C_NAME, W_NAME, C_PX, C_CHG, C_PCT = _stock_cols(W)
    for i, sym in enumerate(symbols):
        if y >= H - 3:
            break
        info = data.get(sym.upper())
        abs_i = y  # use row as rough index
        sel   = (ECS.cursor == y_start + i + 1)  # offset by section header
        _draw_stock_row(win, y, W, sym, info, "$", sel, cursor_col=title_col)
        y += 1
    return y


def _build_ec_flat_list():
    """Return flat list of (sym, section) for the current screen."""
    screen = ECS.screen
    crypto_d = get_crypto_data()
    etf_d    = get_etf_data()
    custom   = ECS.custom

    if screen == 0:  # crypto
        base = CRYPTO_SYMBOLS[:]
        extras = [s for s in custom if s.endswith("-USD") or "USD" in s.upper()]
        return [(s, "crypto") for s in base + extras]
    elif screen == 1:  # ETF
        base = ETF_SYMBOLS[:]
        extras = [s for s in custom if not s.endswith("-USD") and "=" not in s and "=F" not in s]
        return [(s, "etf") for s in base + extras]
    elif screen == 2:  # forex
        base = FOREX_SYMBOLS[:]
        extras = [s for s in custom if "=X" in s]
        return [(s, "forex") for s in base + extras]
    else:  # commodities
        base = COMMODITY_SYMS[:]
        extras = [s for s in custom if "=F" in s]
        return [(s, "commod") for s in base + extras]


def v_etf_crypto(win, W, H):
    _ec_sub_header(win, W, H)

    crypto_d = get_crypto_data()
    etf_d    = get_etf_data()
    all_data = {**crypto_d, **etf_d}

    screen    = ECS.screen
    flat_list = _build_ec_flat_list()
    n         = len(flat_list)
    ECS.cursor = max(0, min(ECS.cursor, max(0, n - 1)))

    # Status row
    if screen == 0:
        status = _crypto_status
    elif screen == 1:
        status = _etf_status
    else:
        status = _crypto_status  # forex & commod share crypto_data
    put(win, 3, 2, f"[ {status}  ·  {n} symbols ]", cp(P_DIM))
    put(win, 4, 0, "─" * W, cp(P_BOX))

    if not all_data and not flat_list:
        centre(win, H//2, "  Fetching data…  ", cp(P_AMBER))
        put(win, H-1, 0, " [r] refresh  [←→] views  [q] quit ", cp(P_DIM))
        return

    # Header
    _draw_stock_header(win, 5, W)

    y = 7
    home_cur = get_home_currency()
    home_sym = _CUR_SYM_MAP.get(home_cur, home_cur + " ")

    # Group gainers / losers / neutral within the section
    loaded = [(sym, all_data.get(sym.upper())) for sym, _ in flat_list]
    gainers = [(s, i) for s, i in loaded if i and i["pct"] >  0.1]
    losers  = [(s, i) for s, i in loaded if i and i["pct"] < -0.1]
    neutral = [(s, i) for s, i in loaded if i and -0.1 <= i["pct"] <= 0.1]
    loading = [(s, i) for s, i in loaded if not i]

    flat_ordered = (
        [("🚀 TOP GAINERS", None)] +
        sorted(gainers, key=lambda x: x[1]["pct"], reverse=True)[:8] +
        [("💥 TOP LOSERS",  None)] +
        sorted(losers,  key=lambda x: x[1]["pct"])[:8] +
        [("😐 STABLE",      None)] +
        neutral[:8]
    )
    if loading:
        flat_ordered += [("⏳ LOADING", None)] + loading[:5]

    cursor_map = {}  # row → (sym, info)
    row_idx    = 0

    for item in flat_ordered:
        if y >= H - 3:
            break
        sym, info = item
        if info is None:
            # section header
            col = (P_GREEN if "GAINER" in sym else
                   P_RED   if "LOSER"  in sym else
                   P_AMBER if "LOAD"   in sym else P_MID)
            put(win, y, 2, f" {sym} ", cp(col, bold=True) | curses.A_BOLD)
            y += 1
            continue

        sel = (ECS.cursor == row_idx)
        cursor_map[row_idx] = (sym, info)

        # pick currency symbol from symbol name
        if "=X" in sym.upper():
            csym = ""   # forex pairs are ratios
        elif "-USD" in sym.upper() or screen == 0:
            csym = "$"
        else:
            csym = "$"

        _draw_stock_row(win, y, W, sym, info, csym, sel, cursor_col=P_PINK if screen==0 else P_CYAN)

        # Show home currency equivalent on the right if different
        if sel and home_cur != "USD" and info:
            rate = get_currency_rate("USD", home_cur)
            if rate:
                eq = info["price"] * rate
                eq_s = f"≈ {home_sym}{eq:,.2f}"
                put(win, y, W - len(eq_s) - 2, eq_s, cp(P_CYAN))

        y += 1
        row_idx += 1

    # Scroll bar
    if n > H - 10:
        pct = int(ECS.cursor / max(1, n-1) * (H - 10))
        for sy in range(7, H - 2):
            put(win, sy, W - 1, "│", cp(P_BOX))
        put(win, min(7 + pct, H - 3), W - 1, "█", cp(P_DIM))

    # Bottom panel
    put(win, H-2, 0, "─" * W, cp(P_BOX))
    blink = "█" if int(time.time()*2)%2 else " "
    if ECS.input_mode:
        put(win, H-1, 0,
            f" Add symbol: {ECS.input_buf.upper()}{blink}  "
            "  (ENTER confirm  ESC cancel)  "
            "e.g. BTC-USD  ETH-USD  SPY  EURUSD=X  GC=F",
            cp(P_AMBER, bold=True))
    elif ECS.msg and time.time() - ECS.msg_time < 4:
        col = P_GREEN if any(w in ECS.msg for w in ("Added","Removed")) else P_RED
        put(win, H-1, 0, f" {ECS.msg} "[:W], cp(col, bold=True))
    elif 0 <= ECS.cursor < len(cursor_map):
        sym, info = cursor_map.get(ECS.cursor, (None, None))
        if info:
            pct = info["pct"]
            pc  = P_GREEN if pct > 0 else (P_RED if pct < 0 else P_MID)
            put(win, H-1, 0,
                f" ▶  {sym}  {info['name'][:28]}  {pct:+.2f}%  "
                "  [a] add  [d] remove  [r] refresh  [q] quit",
                cp(pc, bold=True))
        else:
            put(win, H-1, 0,
                " [j/k/scroll] navigate  [a] add symbol  [d] remove  [r] refresh  [q] quit ",
                cp(P_DIM))
    else:
        put(win, H-1, 0,
            " [j/k/scroll] navigate  [a] add symbol  [d] remove  [r] refresh  [q] quit ",
            cp(P_DIM))


def _handle_etf_crypto_key(k):
    global _etf_last, _crypto_last
    flat = _build_ec_flat_list()
    n    = len(flat)

    # Handle input mode first - check for input before any shortcuts
    if ECS.input_mode:
        if k in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
            ECS.input_buf = ECS.input_buf[:-1]
        elif k == 27:
            ECS.input_mode = False; ECS.input_buf = ""
        elif k in (10, 13):
            sym = ECS.input_buf.upper().strip()
            ECS.input_mode = False; ECS.input_buf = ""
            if sym and sym not in [s.upper() for s in ECS.custom]:
                ECS.custom.append(sym)
                _save_ec_custom()
                threading.Thread(target=lambda s=sym: _fetch_and_cache_ec(s), daemon=True).start()
                ECS.msg = f"Added {sym}"; ECS.msg_time = time.time()
            elif sym:
                ECS.msg = f"{sym} already added"; ECS.msg_time = time.time()
        elif 32 <= k <= 126 and len(ECS.input_buf) < 14:
            ECS.input_buf += chr(k)
        return

    # Sub-tab switching (only when NOT in input mode)
    if k == ord('1') or k == ord('c'): ECS.screen = 0; ECS.cursor = 0; return
    if k == ord('2') or k == ord('e'): ECS.screen = 1; ECS.cursor = 0; return
    if k == ord('3') or k == ord('f'): ECS.screen = 2; ECS.cursor = 0; return
    if k == ord('4') or k == ord('o'): ECS.screen = 3; ECS.cursor = 0; return

    if k in (ord('j'), curses.KEY_DOWN):
        ECS.cursor = min(max(0, n-1), ECS.cursor + 1)
    elif k in (ord('k'), curses.KEY_UP):
        ECS.cursor = max(0, ECS.cursor - 1)
    elif k == ord('a'):
        ECS.input_mode = True; ECS.input_buf = ""
    elif k == ord('d'):
        if ECS.custom:
            # remove the custom symbol nearest cursor
            if ECS.cursor < len(ECS.custom):
                removed = ECS.custom.pop(ECS.cursor)
                _save_ec_custom()
                ECS.cursor = max(0, ECS.cursor - 1)
                ECS.msg = f"Removed {removed}"; ECS.msg_time = time.time()
    elif k == ord('r'):
        _etf_last = 0.0; _crypto_last = 0.0
        threading.Thread(target=fetch_etf_bg,    daemon=True).start()
        threading.Thread(target=fetch_crypto_bg, daemon=True).start()
        ECS.msg = "Refreshing…"; ECS.msg_time = time.time()


def _fetch_and_cache_ec(sym):
    """Fetch a single custom symbol and store it in both etf and crypto caches."""
    result = _fetch_stock_price(sym)
    if result:
        with _ETF_LOCK:
            _etf_data[sym.upper()] = result
        with _CRYPTO_LOCK:
            _crypto_data[sym.upper()] = result


# ══════════════════════════════════════════════════════════════════════════════
#  APP STATE
# ══════════════════════════════════════════════════════════════════════════════
class NewsStocksState:
    def __init__(self):
        self.scroll        = 0
        self.tab           = 0        # 0=news  1=stocks
        self.stock_screen  = 0        # 0=market/trending  1=portfolio
        self.stock_input   = False    # adding ticker in portfolio
        self.stock_buf     = ""
        self.stock_cur     = 0        # cursor in portfolio list
        self.market_cur    = 0        # cursor in market trending list
        self.country_cur   = 0
        self.country_mode  = False
        self.msg           = ""
        self.msg_time      = 0.0
        # mouse / keyboard item selection
        self.news_row_map  = {}
        self.tab_regions   = []
        self.stock_sub_regions = []  # [(x0,x1,screen_idx)] for M/P sub-tabs
        self.news_cursor   = -1

NSS = NewsStocksState()

# Initialise country_cur to match saved country
def _init_nss_country():
    code = get_user_country()
    if code and code in COUNTRY_LIST:
        try:
            NSS.country_cur = COUNTRY_LIST.index(code)
        except ValueError:
            NSS.country_cur = 0

_init_nss_country()


# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
VIEW_FNS = [v_tars_dashboard, v_clock, v_focus, v_neofetch, v_network,
            v_calendar, v_video, v_news_market_hub, v_news_stocks, v_etf_crypto]

def _in_text_input_mode():
    v = ST.view
    if v == 0 and DS.input_mode:                                 return True
    if ST.todo_add:                                              return True
    if v == 5 and (CS.add_mode or CS.ics_mode or CS.del_mode or CS.ics_sel_mode):  return True
    if v == 1 and LS.mode in ("add_url", "add_file"):             return True
    if v == 6 and VS.mode in ("add_url", "add_file"):            return True
    if v == 8 and NSS.stock_input:                               return True
    if v == 9 and ECS.input_mode:                                return True
    return False


def _show_credits_splash(stdscr):
    """Display OpenCode and project credits splash screen"""
    stdscr.erase()
    H, W = stdscr.getmaxyx()
    
    credits = [
        "",
        "╔════════════════════════════════════════════════════════════════╗",
        "║          DENJI SYNTHETIC COMMAND INTERFACE v3.0                ║",
        "║                    NEURAL CORE: AI BRAIN                       ║",
        "╚════════════════════════════════════════════════════════════════╝",
        "",
        "POWERED BY OPENCODE AGENT ARCHITECTURE",
        "",
        "OpenCode Contributors:",
        "  • @thdxr (Founder & Lead Developer)",
        "  • @adamdotdevin (Core Architecture)",
        "  • @rekram1-node (Infrastructure)",
        "  • @iamdavidhill, @kitlangton, @jayair",
        "  • @fwang, @Brendonovich, @Hona",
        "  • +846 community contributors",
        "",
        "Denji AI Integration:",
        "  • OpenCode foundation for agent patterns",
        "  • Extended for terminal-based personality synthesis",
        "  • Multi-modal I/O framework (typing, voice, camera)",
        "",
        "Credits & Acknowledgments:",
        "  • TARS interface inspired by sci-fi HUD design",
        "  • Speech synthesis: pyttsx3, SAPI, PowerShell",
        "  • Computer vision: OpenCV",
        "  • Terminal UI: curses (Python standard library)",
        "",
        "LICENSE: MIT (OpenCode) & Custom (Denji Integration)",
        "",
        "Press any key to continue to Denji Neural Core...",
    ]
    
    y = max(0, (H - len(credits)) // 2)
    for line in credits:
        if y < H:
            x = max(0, (W - len(line)) // 2)
            put(stdscr, y, x, line[:W], cp(P_CYAN, bold=True) if "DENJI" in line else cp(P_HI) if "OpenCode" in line else cp(P_DIM))
            y += 1
    
    stdscr.refresh()
    
    # Wait for key press with timeout
    stdscr.timeout(100)
    for _ in range(100):  # ~10 seconds max
        k = stdscr.getch()
        if k != -1:
            break
        time.sleep(0.05)
    
    stdscr.timeout(50)


def main(stdscr):
    os.environ["ESCDELAY"] = "0"

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)
    stdscr.keypad(True)
    init_colors()
    # Enable mouse: clicks + scroll wheel
    # ALL_MOUSE_EVENTS gives clicks + scroll. REPORT_MOUSE_POSITION is intentionally
    # omitted — it floods getch() with motion events on every pixel move.
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    curses.mouseinterval(0)

    # Warm subsystems once at startup without blocking UI launch.
    threading.Thread(target=denji_startup_boot, daemon=True).start()

    # Show credits splash on first launch
    _show_credits_splash(stdscr)

    if not AUDIO._backend:
        AUDIO.playing = False

    while True:
        stdscr.erase()
        H, W = stdscr.getmaxyx()
        if H < 24 or W < 72:
            put(stdscr, H//2, max(0,(W-44)//2),
                f"  Terminal too small ({W}x{H}) — need 72x24+  ",
                cp(P_RED, bold=True))
            stdscr.refresh()
            if stdscr.getch() == ord('q'): break
            continue

        tick()
        draw_topbar(stdscr, W)

        main_x, main_w, rail_x, rail_w = _responsive_layout(W)
        if rail_x is None:
            if main_x == 0 and main_w == W:
                VIEW_FNS[ST.view](stdscr, W, H)
            else:
                main_win = stdscr.derwin(H, main_w, 0, main_x)
                VIEW_FNS[ST.view](main_win, main_w, H)
        else:
            main_win = stdscr.derwin(H, main_w, 0, main_x)
            VIEW_FNS[ST.view](main_win, main_w, H)
            draw_side_rail(stdscr, rail_x, rail_w, H)

        draw_navbar(stdscr, W, H)
        draw_footer(stdscr, W, H)
        stdscr.refresh()

        in_text = _in_text_input_mode()
        max_keys = 256 if in_text else 32  # enough for mouse events per frame
        for _ in range(max_keys):
            k = stdscr.getch()
            if k == -1:
                break
            if k == ord('q') and not in_text:
                VIDEO.stop()
                AUDIO._kill()
                denji_shutdown()
                save_todos(ST.todos)
                return
            handle_key(k)
            in_text = _in_text_input_mode()


def detect_windows_displays():
    """Return monitor info on Windows. On non-Windows returns single-display default."""
    info = {
        "count": 1,
        "primary": None,
        "secondary": None,
        "all": [],
    }
    if platform.system() != "Windows":
        return info

    try:
        import ctypes

        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
            ]

        monitors = []
        monitor_enum_proc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(RECT),
            ctypes.c_longlong,
        )

        def _enum_monitor(hmon, _hdc, _lprc, _lparam):
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                r = mi.rcMonitor
                monitors.append({
                    "left": int(r.left),
                    "top": int(r.top),
                    "right": int(r.right),
                    "bottom": int(r.bottom),
                    "width": int(r.right - r.left),
                    "height": int(r.bottom - r.top),
                    "primary": bool(mi.dwFlags & 1),
                })
            return 1

        user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(_enum_monitor), 0)

        if monitors:
            info["all"] = monitors
            info["count"] = len(monitors)
            info["primary"] = next((m for m in monitors if m["primary"]), monitors[0])
            info["secondary"] = next((m for m in monitors if not m["primary"]), None)
    except Exception:
        pass

    return info


def move_console_to_secondary_display():
    """Move console window to a secondary monitor when available."""
    displays = detect_windows_displays()
    if platform.system() != "Windows":
        return displays

    if displays.get("count", 1) < 2 or not displays.get("secondary"):
        return displays

    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if not hwnd:
            return displays

        user32 = ctypes.windll.user32
        sec = displays["secondary"]

        target_w = max(1000, min(int(sec["width"] * 0.85), sec["width"]))
        target_h = max(700, min(int(sec["height"] * 0.85), sec["height"]))

        x = int(sec["left"] + max(0, (sec["width"] - target_w) // 2))
        y = int(sec["top"] + max(0, (sec["height"] - target_h) // 2))

        user32.MoveWindow(hwnd, x, y, target_w, target_h, True)
    except Exception:
        pass

    return displays


def run_denji():
    displays = move_console_to_secondary_display()
    threading.Thread(target=denji_startup_boot, daemon=True).start()

    backend = AUDIO._backend or ""
    if not backend:
        print("""
  ╔══════════════════════════════════════════════════╗
  ║  NO AUDIO BACKEND FOUND                          ║
  ║                                                  ║
  ║  Install one of these (pick any):                ║
  ║                                                  ║
  ║  Option 1 — Python audio (recommended):          ║
  ║    pip install sounddevice                       ║
  ║                                                  ║
  ║  Option 2 — ffmpeg (also needed for YouTube):    ║
  ║    winget install ffmpeg       (Windows)         ║
  ║    brew install ffmpeg         (macOS)           ║
  ║    sudo apt install ffmpeg     (Linux)           ║
  ║                                                  ║
  ║  The app will still run without audio.           ║
  ╚══════════════════════════════════════════════════╝
""")
        time.sleep(1)
    else:
        bname = os.path.basename(backend) if os.path.isfile(backend) else backend
        dsp_count = displays.get("count", 1)
        dsp_msg = "primary" if dsp_count < 2 else "secondary"
        print(f"""
  Denji StandBy  |  audio: {bname}  |  {platform.system()}  |  displays: {dsp_count} ({dsp_msg})
  SPACE=play/pause  z/x=prev/next  <-/->=views  q=quit
""")
    time.sleep(0.3)
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        denji_shutdown()
        AUDIO._kill()
        save_todos(ST.todos)
    print("\n  Goodbye! Todos saved.  [*]\n")


if __name__ == "__main__":
    run_denji()
    
