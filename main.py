#!/usr/bin/env python3
"""
Terminal StandBy v3
Apple-style standby for your terminal.
Real synthesized music · Live spectrum visualizer · Neofetch panel
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

import time, threading, socket, os, datetime, random, json, math, struct, shutil

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ══════════════════════════════════════════════════════════════════════════════
#  COLOURS
# ══════════════════════════════════════════════════════════════════════════════
P_DIM   = 1;  P_MID  = 2;  P_HI   = 3
P_GREEN = 4;  P_AMBER= 5;  P_RED  = 6
P_BLUE  = 7;  P_CYAN = 8;  P_PINK = 9;  P_BOX = 10

def init_colors():
    curses.start_color(); curses.use_default_colors()
    curses.init_pair(P_DIM,   238, -1); curses.init_pair(P_MID,   246, -1)
    curses.init_pair(P_HI,    255, -1); curses.init_pair(P_GREEN,  82, -1)
    curses.init_pair(P_AMBER, 214, -1); curses.init_pair(P_RED,   203, -1)
    curses.init_pair(P_BLUE,   75, -1); curses.init_pair(P_CYAN,   87, -1)
    curses.init_pair(P_PINK,  213, -1); curses.init_pair(P_BOX,   240, -1)

def cp(p, bold=False):
    a = curses.color_pair(p)
    if bold: a |= curses.A_BOLD
    return a

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
#  AUDIO ENGINE  –  procedural synth → ffplay / afplay / Windows WAVE
# ══════════════════════════════════════════════════════════════════════════════
SR    = 44100   # sample rate
CHUNK = 2048    # samples per write

# --- waveform generators ---
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

# --- envelope ---
def env(i, n, a_frac=0.05, r_frac=0.15):
    at = int(n*a_frac); rel = int(n*r_frac)
    if i < at:   return i/max(1,at)
    if i > n-rel:return (n-i)/max(1,rel)
    return 1.0

# --- note frequencies ---
def midi(n):   return 440.0 * 2**((n-69)/12)


# ══════════════════════════════════════════════════════════════════════════════
#  MUSIC LIBRARY  —  built-in focus sounds + user tracks
# ══════════════════════════════════════════════════════════════════════════════
import array as _array

LIBRARY_FILE = os.path.join(os.path.expanduser("~"), ".terminal_standby_music.json")

# ══════════════════════════════════════════════════════════════════════════════
#  CALENDAR ENGINE  — reads ICS (Google/Apple) + local JSON events
# ══════════════════════════════════════════════════════════════════════════════
CAL_FILE  = os.path.join(os.path.expanduser("~"), ".terminal_standby_cal.json")
CAL_ICS   = os.path.join(os.path.expanduser("~"), ".terminal_standby.ics")
_CAL_LOCK = threading.Lock()
_CAL_EVENTS = []          # list of (datetime, datetime, str title)
_CAL_STATUS = ""          # shown in calendar view


def _parse_ics_date(val):
    """Parse DTSTART / DTEND values (may be DATE or DATETIME)."""
    val = val.split(";")[-1].split(":")[-1].strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _parse_ics(text):
    """Parse an ICS file/string → list of (start_dt, end_dt, title)."""
    events = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    # Unfold continuation lines
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


def load_calendar_events():
    """Load events from: ICS file + local JSON. Returns sorted list."""
    evs = []
    # Local JSON events
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
    # ICS file (Google Cal / Apple Cal export)
    try:
        with open(CAL_ICS, encoding="utf-8", errors="replace") as f:
            evs += _parse_ics(f.read())
    except Exception: pass
    return sorted(set(evs), key=lambda e: e[0])


def save_local_events(local_evs):
    """Save manual JSON events (ICS events are not modified)."""
    try:
        with open(CAL_FILE, "w") as f:
            json.dump(local_evs, f, indent=2)
    except Exception: pass


def refresh_calendar():
    """Reload calendar events into _CAL_EVENTS. Call in background."""
    global _CAL_EVENTS, _CAL_STATUS
    evs = load_calendar_events()
    with _CAL_LOCK:
        _CAL_EVENTS = evs
    _CAL_STATUS = f"Loaded {len(evs)} events"


def fetch_ics_url(url):
    """Download an ICS URL and save to CAL_ICS. Returns (ok, msg)."""
    global _CAL_STATUS
    try:
        import urllib.request
        _CAL_STATUS = "Fetching calendar..."
        req = urllib.request.Request(url, headers={"User-Agent": "TerminalStandBy/3"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        if "BEGIN:VCALENDAR" not in data:
            _CAL_STATUS = "ERROR: Not a valid ICS file"
            return False, "Not a valid ICS"
        with open(CAL_ICS, "w", encoding="utf-8") as f:
            f.write(data)
        refresh_calendar()
        _CAL_STATUS = f"Synced {len(_CAL_EVENTS)} events"
        return True, f"Synced {len(_CAL_EVENTS)} events"
    except Exception as e:
        _CAL_STATUS = f"ERROR: {e}"
        return False, str(e)


def get_next_event():
    """Return (title, time_str) for the next upcoming event."""
    now = datetime.datetime.now()
    with _CAL_LOCK:
        evs = list(_CAL_EVENTS)
    for start, end, title in evs:
        if start > now:
            diff = int((start - now).total_seconds())
            hh, rem = divmod(diff, 3600); mm = rem // 60
            ts = f"{start.strftime('%H:%M')}  {title}"
            remaining = f"in {hh}h {mm:02d}m" if hh > 0 else f"in {mm}m"
            return ts[:40], remaining
    # Check today's events that may be ongoing
    for start, end, title in evs:
        if start.date() == now.date() and start <= now:
            return f"{start.strftime('%H:%M')}  {title}"[:40], "ongoing"
    return "No events today", ""


# Load events at startup in background
threading.Thread(target=refresh_calendar, daemon=True).start()


CACHE_DIR    = os.path.join(os.path.expanduser("~"), ".terminal_standby_cache")
SR = 44100

# Built-in focus/ambient tracks (generated as streaming noise — no pre-synthesis wait)
BUILTIN_TRACKS = [
    {
        "name":     "Brown Noise",
        "artist":   "Focus Aid",
        "source":   "builtin",
        "genre":    "brown",
        "duration": 0,           # infinite / loops
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


# ── Noise generators (streaming, return bytes per chunk) ─────────────────────

def _gen_brown(n, state):
    """Brown noise: double-integrated white noise — very deep, smooth rumble."""
    out   = _array.array('h')
    b1    = state.get('b1', 0.0)   # first integrator
    b2    = state.get('b2', 0.0)   # second integrator (extra bass smoothing)
    for _ in range(n):
        white = random.gauss(0, 1.0)
        b1    = b1 * 0.998 + white * 0.002
        b2    = b2 * 0.995 + b1   * 0.005   # smooth again → softer, deeper
        v = max(-32767, min(32767, int(b2 * 18000)))  # lower amplitude
        out.append(v)
    state['b1'] = b1
    state['b2'] = b2
    return out.tobytes()

def _gen_pink(n, state):
    """Pink noise (1/f): Voss-McCartney + gentle low-pass for softness."""
    b    = state.get('b', [0.0]*7)
    prev = state.get('p', 0.0)   # low-pass state
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
        # Single-pole low-pass @ ~8kHz cutoff → removes harshness
        prev = prev * 0.85 + pink * 0.15
        v = max(-32767, min(32767, int(prev * 18000)))  # lower amplitude
        out.append(v)
    state['b'] = b
    state['p'] = prev
    return out.tobytes()

def _gen_white(n, _state):
    """White noise: flat spectrum."""
    out = _array.array('h')
    for _ in range(n):
        v = max(-32767, min(32767, int(random.gauss(0, 1.0) * 10000)))
        out.append(v)
    return out.tobytes()

def _gen_rain(n, state):
    """Rain simulation: filtered brown noise + occasional droplet pops."""
    out  = _array.array('h')
    last = state.get('b', 0.0)
    drop_countdown = state.get('dc', 0)
    drop_amp       = state.get('da', 0.0)
    for i in range(n):
        # base rain texture: faster-changing brown noise
        white = random.gauss(0, 1.0)
        last  = last * 0.95 + white * 0.05
        rain  = last * 0.6
        # droplet pop
        if drop_countdown <= 0:
            drop_amp       = random.uniform(0.2, 0.9)
            drop_countdown = random.randint(SR//20, SR//3)  # 50ms-333ms
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
    """Deep space: slow sine drone + subtle brown texture."""
    out   = _array.array('h')
    t_off = state.get('t', 0)
    last  = state.get('b', 0.0)
    for i in range(n):
        t     = (t_off + i) / SR
        # fundamental drone ~60Hz with slow beating
        drone = (0.5 * math.sin(2*math.pi*60*t)
               + 0.3 * math.sin(2*math.pi*60.3*t)
               + 0.15* math.sin(2*math.pi*90*t)
               + 0.1 * math.sin(2*math.pi*120*t))
        # subtle brown texture
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
        ydl_opts = {
            "format":         "bestaudio/best",
            "outtmpl":        os.path.join(CACHE_DIR, "%(id)s.%(ext)s"),
            "quiet":          True,
            "no_warnings":    True,
            "postprocessors": [{"key":"FFmpegExtractAudio",
                                "preferredcodec":"mp3",
                                "preferredquality":"192"}],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info   = ydl.extract_info(url, download=True)
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
    CHUNK = SR // 8    # 0.125s chunks — smooth streaming, low latency

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
        self.status_msg = ""
        self._spec_t    = 0.0
        self._backend   = self._detect()
        # Try to install sounddevice in background if not found
        if self._backend != "sounddevice":
            threading.Thread(target=self._try_install_sd, daemon=True).start()

    def _try_install_sd(self):
        """Silent one-time install of sounddevice if missing."""
        try:
            import sounddevice  # noqa
            self._backend = "sounddevice"
            return
        except ImportError:
            pass
        try:
            self.status_msg = "Installing audio engine (one-time)..."
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "sounddevice", "-q"],
                timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import sounddevice  # noqa
            self._backend   = "sounddevice"
            self.status_msg = ""
        except Exception:
            self.status_msg = ""

    def _detect(self):
        """
        Priority order:
          1. sounddevice  — pure Python, bundles PortAudio on Windows, gapless
          2. ffplay        — subprocess pipe, works everywhere ffmpeg is installed
          3. afplay        — macOS only, file-based fallback
          4. aplay         — Linux ALSA fallback
          5. winsound      — last resort Windows, WAV only
        """
        # Try sounddevice (auto-installs once if missing)
        try:
            import sounddevice  # noqa
            return "sounddevice"
        except Exception:
            pass
        # Try subprocess players
        for cmd in ("ffplay", "afplay", "mpv", "mplayer", "aplay"):
            if shutil.which(cmd):
                return cmd
        # Windows: search common ffmpeg locations
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
                import winsound  # noqa
                return "winsound"
            except ImportError:
                pass
        return None

    @staticmethod
    def _ensure_sounddevice():
        """Install sounddevice if not present. Returns True on success."""
        try:
            import sounddevice  # noqa
            return True
        except Exception:
            pass
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "sounddevice", "-q"],
                timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import sounddevice  # noqa
            return True
        except Exception:
            return False

    # ── spectrum (beat/noise reactive) ───────────────────────────────────
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

    # ── playback ─────────────────────────────────────────────────────────
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
        # natural end → advance (only for finite tracks)
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

    # ── built-in noise streaming ──────────────────────────────────────────
    def _play_builtin(self, gen, trk, start_sec):
        genre = trk.get("genre", "brown")
        genfn = _GENERATORS.get(genre, _gen_brown)
        state = {}
        # Advance generator state to match start position (no audio output)
        skip = int(start_sec * SR / self.CHUNK)
        for _ in range(skip):
            if not self._alive(gen): return
            genfn(self.CHUNK, state)

        b = self._backend or ""
        # ── sounddevice path (best: direct to OS audio, no subprocess) ────
        if b == "sounddevice":
            self._stream_sounddevice(gen, genfn, state)
        # ── ffplay/aplay pipe path ─────────────────────────────────────────
        elif b in ("ffplay","aplay") or (os.path.isfile(b) and "ffplay" in b.lower()):
            self._stream_pipe(gen, genfn, state)
        # ── WAV segment fallback (afplay / winsound) ───────────────────────
        else:
            self._stream_wav_segments(gen, genfn, state)

    def _stream_sounddevice(self, gen, genfn, state):
        """Play noise directly via sounddevice — gapless, zero subprocess."""
        try:
            import sounddevice as sd
        except ImportError:
            # Not installed yet — fall through to pipe/wav
            self._stream_pipe(gen, genfn, state)
            return

        try:
            with sd.RawOutputStream(samplerate=SR, channels=1,
                                    dtype='int16', blocksize=self.CHUNK) as stream:
                while self._alive(gen):
                    chunk = genfn(self.CHUNK, state)
                    stream.write(chunk)   # blocks until OS buffer is ready
        except Exception as e:
            err = str(e).lower()
            if "invalid device" in err or "no default" in err or "device unavailable" in err:
                # No audio output device — fall back gracefully
                self._stream_pipe(gen, genfn, state)
            elif self._alive(gen):
                # Other error — retry once via pipe
                self._stream_pipe(gen, genfn, state)

    def _stream_pipe(self, gen, genfn, state):
        """Stream raw PCM into ffplay or aplay via stdin pipe."""
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
            with self._lock: self._proc = proc
            while self._alive(gen):
                try:
                    proc.stdin.write(genfn(self.CHUNK, state))
                    proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    break
                time.sleep(self.CHUNK / SR * 0.5)
        except Exception:
            pass
        finally:
            try: proc.stdin.close()
            except: pass
            try: proc.wait(timeout=2)
            except: proc.terminate()
            with self._lock:
                if self._proc is proc: self._proc = None

    def _stream_wav_segments(self, gen, genfn, state):
        """Generate 30s WAV files and play them in a loop (afplay / winsound)."""
        import tempfile, wave as wv
        SEG  = 30
        SR_W = 22050 if self._backend == "winsound" else SR
        dec  = SR // SR_W   # decimation factor

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
                    with self._lock: self._proc = proc
                    while proc.poll() is None:
                        if not self._alive(gen): proc.terminate(); return
                        time.sleep(0.05)
                elif b == "winsound":
                    import winsound
                    done = threading.Event()
                    wav  = tmp.name
                    def _play(p=wav, e=done):
                        try: winsound.PlaySound(p, winsound.SND_FILENAME|winsound.SND_SYNC)
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

    # ── file playback (user tracks) ───────────────────────────────────────
    def _play_file(self, gen, path, start_sec, duration):
        """Play a user audio file via best available backend."""
        b  = self._backend or ""
        ss = str(int(start_sec))

        # sounddevice can't decode MP3/FLAC — use ffplay/subprocess for files
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
            with self._lock: self._proc = proc
            while proc.poll() is None:
                if not self._alive(gen): proc.terminate(); break
                time.sleep(0.05)
            with self._lock:
                if self._proc is proc: self._proc = None
        except Exception:
            pass

    def _play_win_winsound(self, gen, path, remaining):
        import winsound, tempfile, wave as wv
        # Convert to WAV via ffmpeg if available, else try direct
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
                return  # can't play non-WAV without ffmpeg
        try:
            done = threading.Event()
            def _pl(p=wav_path, e=done):
                try: winsound.PlaySound(p, winsound.SND_FILENAME|winsound.SND_SYNC)
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
            with self._lock: self._proc = proc
            while proc.poll() is None:
                if not self._alive(gen): proc.terminate(); break
                time.sleep(0.1)
            with self._lock:
                if self._proc is proc: self._proc = None
        except Exception:
            pass

    def _kill(self):
        """Stop current playback immediately."""
        self._new_gen()          # invalidate running thread
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc:
            try: proc.terminate()
            except: pass
        if platform.system() == "Windows":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except: pass

    # ── public API ────────────────────────────────────────────────────────
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
        """Advance elapsed counter. Call each frame."""
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
                self.elapsed += dt   # infinite loop — just count up

    @property
    def current(self):
        if not self.library:
            return BUILTIN_TRACKS[0]
        return self.library[self.track_idx]


AUDIO = AudioEngine()

# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM DATA
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
        self.kernel    = platform.release()[:26]
        self.cpu_name  = self._cpu()
        self.gpu_name  = self._gpu()
        self.uptime    = 0
        self.ssid      = self._ssid()
        self.local_ip  = self._local_ip()
        self.cpu_cores = os.cpu_count() or 1
        self._pnet     = None
        self._boot     = psutil.boot_time() if HAS_PSUTIL else time.time()
        self.devices       = []   # list of dicts: name,type,connected,battery
        self._dev_last     = 0.0  # last device scan time
        self._dev_scanning = False

    @staticmethod
    def _os():
        s = platform.system()
        if s == "Darwin":
            v = platform.mac_ver()[0]; return f"macOS {v}"
        if s == "Windows": return f"Windows {platform.version()[:22]}"
        # try to get distro name on Linux
        try:
            for f in ["/etc/os-release","/etc/lsb-release"]:
                if os.path.exists(f):
                    for line in open(f):
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=",1)[1].strip().strip('"')[:28]
        except: pass
        return f"Linux {platform.release()[:20]}"

    @staticmethod
    def _cpu():
        try:
            if platform.system() == "Darwin":
                r = subprocess.run(["sysctl","-n","machdep.cpu.brand_string"],
                                   capture_output=True,text=True,timeout=1)
                return r.stdout.strip()[:34]
            if platform.system() == "Linux":
                for line in open("/proc/cpuinfo"):
                    if "model name" in line:
                        return line.split(":",1)[1].strip()[:34]
            if platform.system() == "Windows":
                r = subprocess.run(["wmic","cpu","get","name","/value"],
                                   capture_output=True,text=True,timeout=2)
                for line in r.stdout.splitlines():
                    if "Name=" in line:
                        return line.split("=",1)[1].strip()[:34]
        except: pass
        return platform.processor()[:34] or "Unknown CPU"

    @staticmethod
    def _gpu():
        try:
            if platform.system() == "Darwin":
                r = subprocess.run(["system_profiler","SPDisplaysDataType"],
                                   capture_output=True,text=True,timeout=3)
                for line in r.stdout.splitlines():
                    if "Chipset Model" in line or "Chip" in line:
                        return line.split(":",1)[1].strip()[:30]
            if platform.system() == "Linux":
                r = subprocess.run(["lspci"],capture_output=True,text=True,timeout=2)
                for line in r.stdout.splitlines():
                    if "VGA" in line or "3D" in line:
                        return line.split(":",2)[-1].strip()[:30]
            if platform.system() == "Windows":
                r = subprocess.run(["wmic","path","win32_VideoController",
                                    "get","name","/value"],
                                   capture_output=True,text=True,timeout=2)
                for line in r.stdout.splitlines():
                    if "Name=" in line:
                        return line.split("=",1)[1].strip()[:30]
        except: pass
        return "N/A"

    @staticmethod
    def _ssid():
        try:
            if platform.system() == "Darwin":
                r = subprocess.run(["/System/Library/PrivateFrameworks/"
                                    "Apple80211.framework/Versions/Current/"
                                    "Resources/airport","-I"],
                                   capture_output=True,text=True,timeout=2)
                for line in r.stdout.splitlines():
                    if " SSID:" in line and "BSSID" not in line:
                        return line.split(":",1)[1].strip()
            if platform.system() == "Linux":
                r = subprocess.run(["iwgetid","-r"],capture_output=True,text=True,timeout=2)
                return r.stdout.strip() or "N/A"
            if platform.system() == "Windows":
                r = subprocess.run(["netsh","wlan","show","interfaces"],
                                   capture_output=True,text=True,timeout=2)
                for line in r.stdout.splitlines():
                    if "SSID" in line and "BSSID" not in line:
                        return line.split(":",1)[1].strip()
        except: pass
        return "N/A"

    @staticmethod
    def _local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
            return ip
        except: return "127.0.0.1"

    @staticmethod
    def _scan_devices():
        """Scan real connected devices: Bluetooth, USB, HID. Cross-platform."""
        devs = []
        sys_name = platform.system()

        if sys_name == "Windows":
            # ── Step 1: get CURRENTLY CONNECTED BT devices via IsConnected prop ──
            # DEVPKEY_Device_IsConnected = {83DA6326-97A6-4088-9453-A1923F573B29} 15
            # This is the correct "right now connected" flag — NOT Status OK
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

            bt_names = {}   # key -> entry dict, for battery fill-in
            seen_names = set()

            # BT: query IsConnected property for every BT device
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

            # ── Step 2: battery — three methods, first one wins ────────────
            if bt_names:
                # Method A: DEVPKEY {104EA319} 2  (GATT battery, Win10 1903+)
                try:
                    ps_batA = (
                        "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |"
                        " ForEach-Object {"
                        "  $b=(Get-PnpDeviceProperty -InstanceId $_.InstanceId"
                        "   -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2'"
                        "   -ErrorAction SilentlyContinue).Data;"
                        "  if($b -ne $null -and $b -ge 0 -and $b -le 100){"
                        "    Write-Output ($_.FriendlyName+'|'+[int]$b)"
                        "  }"
                        "}"
                    )
                    r_a = subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_batA],
                        capture_output=True, text=True, timeout=10)
                    for line in r_a.stdout.strip().splitlines():
                        line = line.strip()
                        if "|" not in line: continue
                        bname, bval = line.rsplit("|", 1)
                        bval = bval.strip()
                        if not bval.isdigit(): continue
                        bkey = " ".join(bname.strip().lower().split()[:2])
                        if bkey in bt_names and bt_names[bkey]["battery"] is None:
                            bt_names[bkey]["battery"] = int(bval)
                except Exception: pass

                # Method B: Registry BatteryLevel key
                try:
                    ps_batB = (
                        "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |"
                        " ForEach-Object {"
                        "  $reg='HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\'+$_.InstanceId;"
                        "  $b=(Get-ItemProperty -Path $reg -Name BatteryLevel"
                        "   -ErrorAction SilentlyContinue).BatteryLevel;"
                        "  if($b -ne $null -and $b -ge 0 -and $b -le 100){"
                        "    Write-Output ($_.FriendlyName+'|'+[int]$b)"
                        "  }"
                        "}"
                    )
                    r_b = subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_batB],
                        capture_output=True, text=True, timeout=10)
                    for line in r_b.stdout.strip().splitlines():
                        line = line.strip()
                        if "|" not in line: continue
                        bname, bval = line.rsplit("|", 1)
                        bval = bval.strip()
                        if not bval.isdigit(): continue
                        bkey = " ".join(bname.strip().lower().split()[:2])
                        if bkey in bt_names and bt_names[bkey]["battery"] is None:
                            bt_names[bkey]["battery"] = int(bval)
                except Exception: pass

                # Method C: WMI Win32_Battery (paired devices that expose it)
                try:
                    ps_batC = (
                        "Get-WmiObject Win32_Battery -ErrorAction SilentlyContinue |"
                        " Select-Object Name,EstimatedChargeRemaining |"
                        " ForEach-Object {"
                        "  if($_.EstimatedChargeRemaining -ne $null){"
                        "    Write-Output ($_.Name+'|'+[int]$_.EstimatedChargeRemaining)"
                        "  }"
                        "}"
                    )
                    r_c = subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_batC],
                        capture_output=True, text=True, timeout=8)
                    for line in r_c.stdout.strip().splitlines():
                        line = line.strip()
                        if "|" not in line: continue
                        bname, bval = line.rsplit("|", 1)
                        bval = bval.strip()
                        if not bval.isdigit(): continue
                        bkey = " ".join(bname.strip().lower().split()[:2])
                        if bkey in bt_names and bt_names[bkey]["battery"] is None:
                            bt_names[bkey]["battery"] = int(bval)
                except Exception: pass

            # Strip internal _iid field before storing
            for d in devs:
                d.pop("_iid", None)

            # ── Step 3: USB / WPD / gamepad devices ───────────────────────
            try:
                ps_usb = (
                    "Get-WmiObject Win32_PnPEntity -ErrorAction SilentlyContinue |"
                    " Where-Object {"
                    "  $_.PNPClass -in @('WPD','DiskDrive') -or"
                    "  ($_.PNPClass -eq 'HIDClass' -and $_.Name -match 'Xbox|Controller|Gamepad') -or"
                    "  ($_.PNPClass -eq 'USB' -and $_.Present -eq $true -and"
                    "   $_.Name -notmatch 'Hub|Root|Host|Composite|Unknown|Microsoft|Intel|Realtek')"
                    "} | ForEach-Object { Write-Output ($_.Name+'|'+$_.PNPClass) }"
                )
                r_usb = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_usb],
                    capture_output=True, text=True, timeout=10)
                for line in r_usb.stdout.strip().splitlines():
                    line = line.strip()
                    if not line or "|" not in line: continue
                    name, cls = line.rsplit("|", 1)
                    name = name.strip(); cls = cls.strip()
                    if not name: continue
                    nl = name.lower()
                    if any(x in nl for x in _JUNK): continue
                    if any(x in nl for x in _SKIP): continue
                    key = " ".join(nl.split()[:2])
                    if key in seen_names: continue
                    seen_names.add(key)
                    if any(x in nl for x in ("xbox","controller","gamepad","joystick")):
                        dtype = "CTRL"
                    elif any(x in nl for x in ("phone","android","iphone","mobile","adb")):
                        dtype = "PHONE"
                    elif any(x in nl for x in ("camera","webcam","imaging")):
                        dtype = "CAM"
                    elif any(x in nl for x in ("headset","headphone","earphone","buds","airpod")):
                        dtype = "AUDIO"
                    elif any(x in nl for x in ("storage","disk","drive","flash","ssd","hdd")):
                        dtype = "STOR"
                    elif any(x in nl for x in ("mouse","trackpad","touchpad")):
                        dtype = "MOUSE"
                    elif any(x in nl for x in ("keyboard","kbd")):
                        dtype = "KBD"
                    elif cls == "WPD":
                        dtype = "MTP"
                    else:
                        dtype = "USB"
                    devs.append({"name": name[:30], "type": dtype,
                                 "connected": True, "battery": None})
            except Exception: pass

        elif sys_name == "Darwin":
            # ── macOS: system_profiler for BT + USB ──────────────────────
            try:
                r = subprocess.run(
                    ["system_profiler","SPBluetoothDataType","-json"],
                    capture_output=True, text=True, timeout=5)
                import json as _json
                data = _json.loads(r.stdout)
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
                import json as _json
                data = _json.loads(r.stdout)
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

        else:  # Linux
            # ── Bluetooth via bluetoothctl ────────────────────────────────
            try:
                r = subprocess.run(["bluetoothctl","devices","Connected"],
                                   capture_output=True, text=True, timeout=3)
                for line in r.stdout.splitlines():
                    parts = line.split(None, 2)
                    if len(parts) >= 3 and parts[0]=="Device":
                        devs.append({"name":parts[2][:28],"type":"BT",
                                     "connected":True,"battery":None})
            except Exception: pass
            # ── USB via lsusb ─────────────────────────────────────────────
            try:
                r = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=3)
                for line in r.stdout.splitlines():
                    # "Bus 001 Device 002: ID 1234:5678 Vendor Product Name"
                    if ":" in line:
                        name = line.split(":",1)[1].strip().split("ID")[0]
                        name = name.strip()
                        if name and "Hub" not in name and "root" not in name.lower():
                            devs.append({"name":name[:28],"type":"USB",
                                         "connected":True,"battery":None})
            except Exception: pass

        return devs[:16]   # cap at 16 devices

    def poll(self):
        if not HAS_PSUTIL: return
        with self._lock:
            try:
                b = psutil.sensors_battery()
                if b: self.bat_pct,self.bat_plug = int(b.percent),b.power_plugged
            except: pass
            try: self.cpu = psutil.cpu_percent(interval=None)
            except: pass
            try:
                m = psutil.virtual_memory()
                self.mem_pct,self.mem_used,self.mem_total = m.percent,m.used/1e9,m.total/1e9
            except: pass
            try:
                p = "/" if platform.system()!="Windows" else "C:\\"
                self.disk_pct = psutil.disk_usage(p).percent
            except: pass
            try:
                n = psutil.net_io_counters()
                if self._pnet:
                    self.net_dn=(n.bytes_recv-self._pnet.bytes_recv)/1024/2
                    self.net_up=(n.bytes_sent-self._pnet.bytes_sent)/1024/2
                self._pnet = n
            except: pass
            try: self.uptime = int(time.time()-self._boot)
            except: pass
        # Scan devices every 8 seconds in background thread (slow PS calls)
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
            return {k:v for k,v in self.__dict__.items() if not k.startswith("_")}

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
#  CAVA-STYLE SPECTRUM VISUALIZER WIDGET
# ══════════════════════════════════════════════════════════════════════════════
# Block characters for sub-character resolution (8 levels per cell)
_VCHR = " ▁▂▃▄▅▆▇█"   # 0-8

def draw_spectrum(win, y, x, h, w, spectrum, col_low=P_CYAN, col_mid=P_BLUE, col_hi=P_PINK):
    """
    Draw a CAVA-style spectrum bar chart.
    spectrum: list of floats [0..1], len=number of bars
    h: height in rows; w: width in chars
    Each bar is 2 chars wide + 1 gap.
    """
    n_bars = min(len(spectrum), w // 2)
    if n_bars < 1: return

    for b in range(n_bars):
        amp   = spectrum[b]
        # height in sub-char units (each row = 8 levels)
        total = h * 8
        val   = int(amp * total)

        bx = x + b * (w // n_bars)
        for row in range(h):
            row_y = y + h - 1 - row        # draw bottom-up
            row_units_start = row * 8
            row_units_end   = row_units_start + 8
            if val <= row_units_start:
                ch = " "
            elif val >= row_units_end:
                ch = "█"
            else:
                lvl = val - row_units_start
                ch  = _VCHR[lvl]

            # colour gradient: low=cyan, mid=blue, high=pink
            frac = (h - 1 - row) / max(1, h-1)
            if frac < 0.4:   col = col_low
            elif frac < 0.75:col = col_mid
            else:             col = col_hi

            put(win, row_y, bx,   ch, cp(col, bold=(frac>0.6)))
            put(win, row_y, bx+1, ch, cp(col, bold=(frac>0.6)))

# ══════════════════════════════════════════════════════════════════════════════
#  APP STATE
# ══════════════════════════════════════════════════════════════════════════════
VIEWS = ["DASHBOARD","CLOCK + MUSIC","FOCUS","NEOFETCH","NETWORK","LIBRARY","CALENDAR"]

class State:
    def __init__(self):
        self.view       = 0
        self.todos      = load_todos()
        self.todo_cur   = 0
        self.todo_add   = False
        self.todo_buf   = ""
        # pomodoro
        self.pomo_total = 25*60.0
        self.pomo_secs  = 25*60.0
        self.pomo_run   = False
        self.pomo_done  = 0
        self.pomo_phase = "WORK"
        self._pw        = time.time()
        self.focus_modes= ["DEEP WORK","READING","CODING","REVIEW","WRITING"]
        self.focus_idx  = 0
        # calendar view state
        self.cal_mode  = "week"   # day | week | month
        self.cal_date  = datetime.datetime.now().date()  # currently viewed date
        self.cal_add   = False
        self.cal_buf   = ""   # typing buffer for add-event
        # spectrum smoothing
        self._spec_smooth = [0.0]*32

ST = State()

# ══════════════════════════════════════════════════════════════════════════════
#  TICK
# ══════════════════════════════════════════════════════════════════════════════
def tick():
    now = time.time()
    AUDIO.tick()

    # pomodoro
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

    # smooth spectrum
    raw = AUDIO.get_spectrum(32)
    ST._spec_smooth = [0.6*s + 0.4*r for s,r in zip(ST._spec_smooth, raw)]

# ══════════════════════════════════════════════════════════════════════════════
#  SHARED: next event helper
# ══════════════════════════════════════════════════════════════════════════════
def next_event():
    return get_next_event()

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def v_dashboard(win, W, H):
    now = datetime.datetime.now()
    sd  = SD.snap()

    # ── row 1: clock + status ─────────────────────────────────────────────
    cw = W//2 - 1
    box(win, 1, 0, 9, cw, "CLOCK")
    ts = now.strftime("%H:%M")
    big_time(win, 2, max(1,(cw-btw(ts))//2), ts)
    put(win, 7, 2, now.strftime("%A, %b %d").upper(), cp(P_DIM))

    rx = W//2; rw = W-rx-1
    box(win, 1, rx, 9, rw, "STATUS")
    bat=sd["bat_pct"]; plug=sd["bat_plug"]
    bc = P_GREEN if bat>40 else (P_AMBER if bat>15 else P_RED)
    bw2 = max(4, rw-15)
    put(win, 2, rx+2, f"BAT {'+'if plug else ' '}{bat:3d}%", cp(bc,bold=True))
    hbar(win, 2, rx+12, bw2, bat, bc)
    put(win, 3, rx+2, f"CPU  {sd['cpu']:5.1f}%", cp(P_CYAN))
    hbar(win, 3, rx+12, bw2, int(sd["cpu"]), P_CYAN)
    put(win, 4, rx+2, f"MEM  {sd['mem_pct']:5.1f}%", cp(P_BLUE))
    hbar(win, 4, rx+12, bw2, int(sd["mem_pct"]), P_BLUE)
    uh,rem=divmod(sd["uptime"],3600); um=rem//60
    put(win, 5, rx+2, f"UP   {uh}h {um:02d}m", cp(P_DIM))
    put(win, 6, rx+2, f"NET  {sd['ssid'][:rw-8]}", cp(P_DIM))
    put(win, 7, rx+2, f"I/O  ↓{kbfmt(sd['net_dn'])} ↑{kbfmt(sd['net_up'])}", cp(P_DIM))

    # ── row 2: todos ──────────────────────────────────────────────────────
    # Reserve space: top(9) + gap(1) + todo_box + gap(1) + pomo(5) + vis(6) + navbar(2) + hint(1)
    reserved   = 10 + 1 + 5 + 6 + 2 + 1
    todo_inner = max(2, H - reserved)
    todo_h     = todo_inner + 2 + (1 if ST.todo_add else 0)
    box(win, 11, 0, todo_h, W-1,
        "TODOS  [a]=add  [d]=del  [j/k]=nav  [ENTER]=check")
    visible_n = todo_inner
    start = max(0, ST.todo_cur - visible_n + 1) if len(ST.todos) > visible_n else 0

    for i, (done, text) in enumerate(ST.todos[start:start+visible_n]):
        ri  = start+i
        ry  = 12+i
        sel = (ri == ST.todo_cur)
        put(win, ry, 1, " "*(W-3),
            cp(P_DIM)|(curses.A_REVERSE if sel else 0))
        tick_c = "✓" if done else " "
        col    = P_DIM if done else (P_AMBER if sel else P_HI)
        line   = f" {'▶' if sel else ' '} [{tick_c}] {text}"
        put(win, ry, 1, line[:W-3],
            cp(col)|(curses.A_REVERSE if sel else 0))
    if len(ST.todos) > visible_n:
        put(win, 12, W-7, f"{ST.todo_cur+1}/{len(ST.todos)}", cp(P_DIM))
    if ST.todo_add:
        put(win, 12+visible_n, 2,
            f" + {ST.todo_buf}{'█' if int(time.time()*2)%2 else ' '}", cp(P_AMBER))

    # ── row 3: pomodoro + next event ──────────────────────────────────────
    by = 11 + todo_h + 1
    hw = W//2 - 1
    box(win, by, 0, 5, hw, "POMODORO  [p]=start  [r]=reset")
    pm=int(ST.pomo_secs)//60; ps=int(ST.pomo_secs)%60
    pct=int((1-ST.pomo_secs/max(1,ST.pomo_total))*100)
    pc=P_RED if ST.pomo_phase=="WORK" else P_GREEN
    sym="▶" if ST.pomo_run else "||"
    put(win,by+1,2,f" {sym}  {pm:02d}:{ps:02d}  {ST.pomo_phase}",cp(pc,bold=True))
    hbar(win,by+2,2,hw-4,pct,pc)
    dots=" ".join("◉" if i<ST.pomo_done else "○" for i in range(8))
    put(win,by+3,2,dots[:hw-4],cp(P_DIM))

    box(win,by,hw+1,5,W-hw-2,"NEXT EVENT")
    evtitle,evtime = next_event()
    put(win,by+1,hw+3,evtitle,cp(P_HI))
    put(win,by+2,hw+3,evtime, cp(P_DIM))

    # ── row 4: CAVA spectrum visualizer ───────────────────────────────────
    vy = by + 6
    vis_h = max(3, H - vy - 3)
    if vy + vis_h + 1 < H:
        td   = AUDIO.current
        lbl  = f"VISUALIZER  ~ {td['name'][:30]} — {td['artist']}"
        box(win, vy, 0, vis_h+2, W-1, lbl)
        spec = list(ST._spec_smooth)  # snapshot to avoid mid-render mutation
        draw_spectrum(win, vy+1, 1, vis_h, W-3, spec)

    put(win, H-1, 0,
        " [ENTER]=check  [p] pomo  [r] reset  [a] add  [d] del  [space]=music  [←→] views  [q] quit ",
        cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 2 — CLOCK + MUSIC
# ══════════════════════════════════════════════════════════════════════════════
def v_clock(win, W, H):
    now = datetime.datetime.now()
    ts  = now.strftime("%H:%M")
    tw  = btw(ts)
    big_time(win, 2, max(0,(W-tw)//2), ts)
    centre(win, 8, now.strftime("%A  %B %d, %Y").upper(), cp(P_DIM))

    # seconds bar
    sw = min(W-8, 52)
    hbar(win, 9, (W-sw)//2, sw, now.second*100//60, P_MID)

    # ── music player box ──────────────────────────────────────────────────
    mw = min(W-4, 68); mx=(W-mw)//2; my=11
    td      = AUDIO.current
    dur     = float(td.get("duration") or 0)
    with AUDIO._lock:
        elapsed = float(AUDIO.elapsed)
    if dur > 0:
        elapsed = min(elapsed, dur)
        pct = int(elapsed / dur * 100)
    else:
        pct = int((elapsed % 60) / 60 * 100)   # infinite: cycle bar per minute
    em,es  = divmod(int(elapsed), 60)
    dm,ds2 = divmod(int(dur), 60) if dur > 0 else (0, 0)

    box(win, my, mx, 12, mw, "NOW PLAYING")
    put(win, my+1, mx+2, td["name"][:mw-4], cp(P_HI, bold=True))
    genre = td.get("genre","")
    genre_lbl = {"brown":"Brown Noise","pink":"Pink Noise","white":"White Noise",
                 "rain":"Rain on Glass","space":"Deep Space"}.get(genre,"")
    sub = f"[{genre_lbl}]  {td['artist']}" if genre_lbl else f"by {td['artist']}"
    put(win, my+2, mx+2, sub[:mw-4], cp(P_DIM))
    # Show audio backend or NO AUDIO warning
    if not AUDIO._backend:
        put(win, my+1, mx+mw-22, "! NO AUDIO BACKEND !", cp(P_RED, bold=True))
        put(win, my+2, mx+2, "  pip install sounddevice  OR  install ffmpeg", cp(P_AMBER))
    else:
        bname = os.path.basename(AUDIO._backend) if os.path.isfile(AUDIO._backend) else AUDIO._backend
        put(win, my+1, mx+mw-len(bname)-4, bname, cp(P_DIM))

    hbar(win, my+3, mx+2, mw-4, pct, P_CYAN)
    put(win, my+4, mx+2, f"{em}:{es:02d}", cp(P_DIM))
    rt = f"{dm}:{ds2:02d}" if dur > 0 else "live"
    put(win, my+4, mx+mw-2-len(rt), rt, cp(P_DIM))

    # controls
    play_lbl = "[ || PAUSE ]" if AUDIO.playing else "[ ▶ PLAY  ]"
    play_col = P_AMBER if AUDIO.playing else P_GREEN
    put(win, my+5, mx+2,        "|< prev [z]",  cp(P_DIM))
    put(win, my+5, mx+mw//2-6,  play_lbl,       cp(play_col, bold=True))
    put(win, my+5, mx+mw-12,    "next [x] >|",  cp(P_DIM))

    scol = P_AMBER if AUDIO.shuffle else P_DIM
    rcol = P_AMBER if AUDIO.repeat  else P_DIM
    shuf_s=f"[{'◈' if AUDIO.shuffle else '◇'}] SHUFFLE [s]"
    rep_s =f"[{'◈' if AUDIO.repeat  else '◇'}] REPEAT  [R]"
    put(win, my+6, mx+2,        shuf_s,  cp(scol))
    put(win, my+6, mx+mw//2+2,  rep_s,   cp(rcol))
    put(win, my+6, mx+mw-10,    f"{AUDIO.track_idx+1}/{len(AUDIO.library)}", cp(P_DIM))

    # track list
    for i in range(min(4, len(AUDIO.library))):
        ri = (AUDIO.track_idx + i) % len(AUDIO.library)
        t_entry = AUDIO.library[ri]; tn, ta = t_entry["name"], t_entry["artist"]
        sel = (ri == AUDIO.track_idx)
        pre = "▶ " if sel else "  "
        put(win, my+7+i, mx+2,
            f"{pre}{tn[:mw//2-4]}  —  {ta}"[:mw-4],
            cp(P_HI if sel else P_DIM))

    # ── CAVA spectrum underneath player ───────────────────────────────────
    vy  = my + 12 + 1
    vis_h = max(3, H - vy - 3)
    if vy + vis_h + 1 < H:
        box(win, vy, mx, vis_h+2, mw, "SPECTRUM")
        draw_spectrum(win, vy+1, mx+1, vis_h, mw-2, ST._spec_smooth)

    put(win, H-1, 0,
        " [space] play/pause  [z] prev  [x] next  [s] shuffle  [R] repeat  [←→] views ",
        cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 3 — FOCUS / POMODORO
# ══════════════════════════════════════════════════════════════════════════════
def v_focus(win, W, H):
    fm   = ST.focus_modes[ST.focus_idx]
    pc   = P_RED if ST.pomo_phase=="WORK" else P_GREEN

    centre(win, 1, f"── {fm} ──", cp(P_HI,bold=True)|curses.A_BOLD)

    # arc
    pm=int(ST.pomo_secs)//60; ps=int(ST.pomo_secs)%60
    pct=1.0-ST.pomo_secs/max(1,ST.pomo_total)
    aw=min(W-10,52); filled=int(pct*aw)
    centre(win, 3, "╺"+"━"*filled+"╌"*(aw-filled)+"╸", cp(pc))

    # big timer
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

    # mini spectrum strip at bottom
    vy=gy+3
    vis_h=max(2,H-vy-3)
    if vy+vis_h+1<H:
        box(win,vy,2,vis_h+2,W-4,"MUSIC")
        draw_spectrum(win,vy+1,3,vis_h,W-6,ST._spec_smooth)

    put(win,H-1,0," [p] start/pause  [r] reset  [s] skip  [f] mode  [←→] views  [q] quit ",cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 4 — NEOFETCH  (rich, real data, cross-platform)
# ══════════════════════════════════════════════════════════════════════════════
_LOGO_MAC = [
    "        ###        ",
    "       #####       ",
    "      #######      ",
    "    ###########    ",
    "   #############   ",
    "  ###############  ",
    "  ###############  ",
    "   #############   ",
    "    ###########    ",
    "      #######      ",
]
_LOGO_LIN = [
    "        /\\         ",
    "       /  \\        ",
    "      /\\   \\       ",
    "     /  \\   \\      ",
    "    / /\\ \\   \\     ",
    "   / /  \\ \\   \\    ",
    "  / /    \\ \\   \\   ",
    " /_/______\\_\\   \\  ",
    "              \\  \\ ",
    "               \\__\\",
]
_LOGO_WIN = [
    "  ████████ ████████",
    "  ████████ ████████",
    "  ████████ ████████",
    "  ████████ ████████",
    "           ████████",
    "  ████████ ████████",
    "  ████████ ████████",
    "  ████████ ████████",
    "  ████████ ████████",
    "                   ",
]

def v_neofetch(win, W, H):
    sd  = SD.snap()
    sys_name = platform.system()
    art  = _LOGO_MAC if sys_name=="Darwin" else (_LOGO_WIN if sys_name=="Windows" else _LOGO_LIN)
    acol = P_CYAN if sys_name=="Darwin" else (P_BLUE if sys_name=="Windows" else P_AMBER)

    ax, ay = 3, 2
    for i, line in enumerate(art):
        put(win, ay+i, ax, line, cp(acol, bold=True))

    uh,rem=divmod(sd["uptime"],3600); um=rem//60
    shell=os.environ.get("SHELL","cmd").split("/")[-1].split("\\")[-1]

    # get terminal size
    term_h, term_w = win.getmaxyx()

    # real packages count attempt
    pkg_count = "N/A"
    try:
        if sys_name=="Darwin":
            r=subprocess.run(["brew","list","--formula"],capture_output=True,text=True,timeout=2)
            pkg_count=str(len(r.stdout.strip().splitlines()))+" (brew)"
        elif sys_name=="Linux":
            for cmd,flag in [("dpkg-query","-l"),("rpm","-qa"),("pacman","-Q")]:
                if shutil.which(cmd):
                    r=subprocess.run([cmd,flag],capture_output=True,text=True,timeout=2)
                    pkg_count=str(len(r.stdout.strip().splitlines()))
                    break
    except: pass

    # terminal emulator
    term_emu = os.environ.get("TERM_PROGRAM", os.environ.get("TERM","unknown"))

    info = [
        ("OS",       sd["os_str"]),
        ("HOST",     sd["hostname"]),
        ("KERNEL",   sd["kernel"]),
        ("UPTIME",   f"{uh}h {um:02d}m"),
        ("SHELL",    shell),
        ("TERMINAL", term_emu[:20]),
        ("PACKAGES", pkg_count),
        ("CPU",      sd["cpu_name"]),
        ("GPU",      sd["gpu_name"]),
        ("MEMORY",   f"{sd['mem_used']:.1f} / {sd['mem_total']:.1f} GB  ({sd['mem_pct']:.0f}%)"),
        ("DISK",     f"{sd['disk_pct']:.0f}% used"),
        ("BATTERY",  f"{sd['bat_pct']}% {'+charging' if sd['bat_plug'] else 'on battery'}"),
        ("LOCAL IP", sd["local_ip"]),
        ("WIFI",     sd["ssid"]),
        ("CORES",    str(sd["cpu_cores"])),
        ("RES",      f"{term_w}x{term_h}"),
    ]

    ix = ax + 22
    user_host = f"{os.environ.get('USER', os.environ.get('USERNAME','user'))}@{sd['hostname']}"
    put(win, ay,   ix, user_host[:W-ix-2], cp(P_HI, bold=True))
    sep = "─" * min(len(user_host), W-ix-2)
    put(win, ay+1, ix, sep, cp(P_BOX))
    for i,(k,v) in enumerate(info):
        put(win, ay+2+i, ix,    f"{k:<10}", cp(P_CYAN))
        put(win, ay+2+i, ix+10, v[:W-ix-13], cp(P_HI))

    # colour palette
    pal_y = ay + max(len(art), len(info)+3) + 1
    put(win, pal_y, ax, "colours  ", cp(P_DIM))
    palettes = [P_DIM,P_MID,P_HI,P_RED,P_AMBER,P_GREEN,P_CYAN,P_BLUE,P_PINK]
    for i,c in enumerate(palettes):
        put(win, pal_y, ax+9+i*3, "██", cp(c))
    for i,c in enumerate(palettes):
        put(win, pal_y+1, ax+9+i*3, "██", cp(c,bold=True))

    # resource bars
    br_y = pal_y + 3
    bw2  = W - 14
    if br_y + 8 < H:
        box(win, br_y, 2, 9, W-4, "LIVE RESOURCES")
        res=[("CPU  ",int(sd["cpu"]),P_CYAN),("MEM  ",int(sd["mem_pct"]),P_BLUE),
             ("DISK ",int(sd["disk_pct"]),P_AMBER),("BAT  ",sd["bat_pct"],P_GREEN if sd["bat_pct"]>40 else P_RED),
             ("NET↓ ",min(100,int(sd["net_dn"]/500*100)),P_GREEN),
             ("NET↑ ",min(100,int(sd["net_up"]/200*100)),P_PINK)]
        for i,(lbl,pct,col) in enumerate(res):
            ry=br_y+1+i
            put(win,ry,4,lbl,cp(P_DIM))
            hbar(win,ry,10,bw2,pct,col)
            put(win,ry,10+bw2+1,f"{pct:3d}%",cp(col))

    put(win,H-1,0," live neofetch · auto-refreshes  [←→] views  [q] quit ",cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 5 — NETWORK + DEVICES
# ══════════════════════════════════════════════════════════════════════════════
def v_network(win, W, H):
    sd  = SD.snap()
    hw  = W//2-1

    box(win,1,0,14,hw,"NETWORK")
    rows=[("SSID",sd["ssid"]),("LOCAL IP",sd["local_ip"]),
          ("HOST",sd["hostname"]),("↓ RECV",kbfmt(sd["net_dn"])),
          ("↑ SEND",kbfmt(sd["net_up"])),("CPU",f"{sd['cpu']:.1f}%"),
          ("MEM",f"{sd['mem_pct']:.1f}%"),("DISK",f"{sd['disk_pct']:.0f}%")]
    for i,(k,v) in enumerate(rows):
        put(win,2+i,2,f"{k:<9}",cp(P_DIM)); put(win,2+i,11,v[:hw-14],cp(P_HI))

    put(win,10,2,"DOWN",cp(P_DIM)); hbar(win,10,7,hw-10,min(100,int(sd["net_dn"]/1000*100)),P_GREEN)
    put(win,11,2,"UP  ",cp(P_DIM)); hbar(win,11,7,hw-10,min(100,int(sd["net_up"]/500*100)), P_BLUE)
    put(win,12,2,"CPU ",cp(P_DIM)); hbar(win,12,7,hw-10,int(sd["cpu"]),P_CYAN)

    rx=hw+1; rw=W-rx-1
    devices = SD.devices   # real scanned devices from SysData
    # type colour map
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
            # Right side: battery% if known, else device type tag (non-BT only)
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

    bat=sd["bat_pct"]; plug=sd["bat_plug"]
    bc=P_GREEN if bat>40 else (P_AMBER if bat>15 else P_RED)
    # dynamic Y position based on device list height
    n_devs   = min(len(SD.devices), 14)
    bat_y    = max(16, 3 + n_devs + 2)
    box(win,bat_y,0,7,W-1,"BATTERY & POWER")
    put(win,bat_y+1,2,f"{'+ CHARGING' if plug else '  ON BATTERY'}  {bat}%  system",cp(bc,bold=True))
    hbar(win,bat_y+2,2,W-5,bat,bc)
    put(win,bat_y+3,2,"charging" if plug else f"~{int(bat*1.5)} min remaining",cp(P_DIM))
    # show BT device battery levels inline
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
        put(win,bat_y+4,2,f"cpu {sd['cpu']:.0f}%  mem {sd['mem_pct']:.0f}%  disk {sd['disk_pct']:.0f}%",cp(P_DIM))

    # spectrum strip
    vy=24; vis_h=max(2,H-vy-3)
    if vy+vis_h+1<H:
        box(win,vy,0,vis_h+2,W-1,"SPECTRUM")
        draw_spectrum(win,vy+1,1,vis_h,W-3,ST._spec_smooth)

    put(win,H-1,0," real-time data  [←→] views  [q] quit ",cp(P_DIM))


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 6 — MUSIC LIBRARY  (add YouTube / local files, manage tracks)
# ══════════════════════════════════════════════════════════════════════════════
class LibState:
    cursor   = 0          # selected row in track list
    mode     = "browse"   # browse | add_url | add_file | confirm_del
    buf      = ""         # text input buffer
    msg      = ""         # feedback message (shown 3s)
    msg_time = 0.0

LS = LibState()

def v_library(win, W, H):
    lib = AUDIO.library
    n   = len(lib)

    # ── header ───────────────────────────────────────────────────────────
    centre(win, 1, "MUSIC LIBRARY", cp(P_HI, bold=True)|curses.A_BOLD)
    centre(win, 2, f"{n} track{'s' if n!=1 else ''}  ·  {len(lib)-len(BUILTIN_TRACKS)} user-added",
           cp(P_DIM))

    # ── track list ────────────────────────────────────────────────────────
    list_h  = H - 16
    list_y  = 4
    box(win, list_y, 1, list_h, W-2, "TRACKS  [j/k]=nav  [ENTER]=play  [D]=delete")

    start = max(0, LS.cursor - list_h + 4)
    for i, trk in enumerate(lib[start:start+list_h-2]):
        ri  = start + i
        ry  = list_y + 1 + i
        sel = (ri == LS.cursor)
        now = (ri == AUDIO.track_idx)

        # icons
        src = trk.get("source","")
        src_icon = "[B]" if src=="builtin" else "[Y]" if ("youtube" in src or "youtu.be" in src) else "[F]"
        play_sym = "> " if now else "  "
        dur      = trk.get("duration", 0) or 0
        if dur > 0:
            dm, ds_ = divmod(int(dur), 60)
            dur_s   = f"{dm}:{ds_:02d}"
        else:
            dur_s   = "live"
        desc = trk.get("desc","") or trk.get("artist","")

        col  = P_AMBER if sel else (P_GREEN if now else P_MID)
        attr = cp(col) | (curses.A_REVERSE if sel else 0)
        name_w = max(10, W-40)
        line = f" {play_sym}{src_icon} {trk['name'][:name_w]:<{name_w}}  {dur_s:<6}  {desc[:20]}"
        put(win, ry, 1, " "*(W-3), attr if sel else 0)
        put(win, ry, 1, line[:W-3], attr)

    # scroll indicator
    if n > list_h-2:
        put(win, list_y, W-10, f" {LS.cursor+1}/{n} ", cp(P_DIM))

    # ── status / download message ──────────────────────────────────────────
    # auto-clear LS.msg after 4s
    if LS.msg and time.time() - LS.msg_time > 4.0:
        LS.msg = ""
    # auto-clear AUDIO.status_msg after 4s (set msg_time when assigned)
    msg = AUDIO.status_msg or LS.msg
    if msg:
        col = P_RED if "ERROR" in msg else P_GREEN if "Added" in msg else P_AMBER
        centre(win, list_y+list_h, msg[:W-4], cp(col, bold=True))

    # ── input panels ──────────────────────────────────────────────────────
    panel_y = list_y + list_h + 1
    blink   = "_" if int(time.time()*2)%2 else " "

    if LS.mode == "add_url":
        box(win, panel_y, 2, 6, W-4, "ADD YOUTUBE URL")
        put(win, panel_y+1, 4,
            "Right-click paste (or type) the URL, then ENTER.  ESC = cancel.",
            cp(P_DIM))
        # show last W-12 chars so end of long URLs is always visible
        disp = LS.buf if len(LS.buf) <= W-12 else "..." + LS.buf[-(W-15):]
        put(win, panel_y+2, 4, (disp + blink)[:W-8], cp(P_AMBER, bold=True))
        put(win, panel_y+3, 4, f"chars: {len(LS.buf)}", cp(P_DIM))
        put(win, panel_y+4, 4,
            "youtube.com/watch?v=XXXX   youtu.be/XXXX   music.youtube.com/...",
            cp(P_DIM))

    elif LS.mode == "add_file":
        box(win, panel_y, 2, 6, W-4, "ADD LOCAL FILE")
        put(win, panel_y+1, 4,
            "Right-click paste (or type) the file path, then ENTER.  ESC = cancel.",
            cp(P_DIM))
        disp = LS.buf if len(LS.buf) <= W-12 else "..." + LS.buf[-(W-15):]
        put(win, panel_y+2, 4, (disp + blink)[:W-8], cp(P_AMBER, bold=True))
        put(win, panel_y+3, 4, f"chars: {len(LS.buf)}", cp(P_DIM))
        put(win, panel_y+4, 4,
            "Supports: MP3  FLAC  WAV  OGG  M4A  AAC  OPUS  WEBM",
            cp(P_DIM))

    elif LS.mode == "confirm_del":
        trk = lib[LS.cursor] if LS.cursor < len(lib) else {}
        box(win, panel_y, 2, 4, W-4, "CONFIRM DELETE")
        centre(win, panel_y+1,
               f"Delete '{trk.get('name','?')[:40]}'?  [Y]=yes  [N/ESC]=cancel",
               cp(P_RED, bold=True))

    else:  # browse mode — show action bar
        box(win, panel_y, 2, 4, W-4, "ACTIONS")
        actions = "[Y] Add YouTube URL    [F] Add local file    [D] Delete selected    [ENTER] Play"
        centre(win, panel_y+1, actions[:W-6], cp(P_DIM))
        legend = "[B]=built-in  [Y]=YouTube  [F]=local file   ~ playing now   > selected"
        centre(win, panel_y+2, legend[:W-6], cp(P_DIM))

    put(win, H-1, 0,
        " [Y]=add YouTube  [F]=add file  [D]=del  [ENTER]=play  [j/k]=nav  [←→] views ",
        cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  CHROME
# ══════════════════════════════════════════════════════════════════════════════
def draw_topbar(win, W):
    now=datetime.datetime.now(); sd=SD.snap()
    ts=now.strftime("%H:%M:%S"); ds=now.strftime("%a %b %d").upper()
    bat=sd["bat_pct"]; plug=sd["bat_plug"]
    bc=P_GREEN if bat>40 else (P_AMBER if bat>15 else P_RED)
    put(win,0,0," "*W, cp(P_DIM)|curses.A_REVERSE)
    put(win,0,1,f" {ts}  {ds}", cp(P_HI)|curses.A_REVERSE)
    vn=f"  {VIEWS[ST.view]}  "
    put(win,0,(W-len(vn))//2,vn, cp(P_HI)|curses.A_REVERSE|curses.A_BOLD)
    # music note if playing
    if AUDIO.playing:
        td=AUDIO.current
        note_s=f" ~ {td['name'][:20]} "
        put(win,0,W//2+len(vn)//2+2,note_s, cp(P_CYAN)|curses.A_REVERSE)
    right=f" {'+'if plug else ' '}{bat}%  {sd['cpu']:.0f}%cpu  {sd['mem_pct']:.0f}%mem "
    put(win,0,W-len(right)-1,right, cp(bc)|curses.A_REVERSE)

def draw_navbar(win, W, H):
    dots="  ".join("◆" if i==ST.view else "◇" for i in range(len(VIEWS)))
    put(win,H-2,1,"[← h]",cp(P_DIM))
    centre(win,H-2,dots,cp(P_DIM))
    put(win,H-2,W-7,"[l →]",cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  INPUT
# ══════════════════════════════════════════════════════════════════════════════
def _text_input(buf, k):
    """
    Handle a keypress for a text input field. Returns updated string.
    Accepts the full printable Unicode range so URLs/paths work correctly.
    Ctrl+V (22) is silently ignored — paste via right-click in terminal.
    """
    if k in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
        return buf[:-1]
    if k == 23:   # Ctrl+W — delete last word
        parts = buf.rstrip().rsplit(None, 1)
        return parts[0] + " " if len(parts) > 1 else ""
    if k == 21:   # Ctrl+U — clear line
        return ""
    # ignore control characters (< 32) and special curses keys (large ints)
    if k < 32 or k > 0x10FFFF:
        return buf
    try:
        return buf + chr(k)
    except (ValueError, OverflowError):
        return buf


# Bracketed paste buffer: some terminals wrap pasted text in ESC[200~ ... ESC[201~
# curses sees this as a stream of chars; we just accept them all naturally.
# The user should right-click → Paste in their terminal emulator.


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 7 — CALENDAR  (day / week / month  ·  Google Cal & Apple Cal via ICS)
# ══════════════════════════════════════════════════════════════════════════════
class CalState:
    mode      = "week"    # "day" | "week" | "month"
    date      = datetime.datetime.now().date()
    # ── add-event form (step-by-step) ──
    add_mode  = False
    add_step  = 0         # 0=date  1=time  2=title
    add_date  = None      # datetime.date
    add_hour  = 9
    add_min   = 0
    add_title = ""
    # ── delete mode ──
    del_mode  = False     # confirm-delete overlay open
    del_idx   = -1        # index into local_evs to delete
    cur_ev    = 0         # currently selected event index (in day view)
    # ── ICS sync ──
    ics_mode  = False
    ics_buf   = ""
    # ── status ──
    msg       = ""
    msg_time  = 0.0
    local_evs = []        # list of {"dt": "YYYY-MM-DD HH:MM", "title": "..."}

CS = CalState()
# Load local events
try:
    with open(CAL_FILE) as _f:
        CS.local_evs = json.load(_f)
except Exception:
    CS.local_evs = []


def _evs_for_day(d):
    """Return events for date d as list of (start_dt, end_dt, title)."""
    with _CAL_LOCK:
        evs = list(_CAL_EVENTS)
    return [(s, e, t) for s, e, t in evs if s.date() == d]


def _evs_for_week(d):
    """Return events for the ISO week containing d."""
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
    """Return (grid of weeks, events dict) for the month of d."""
    import calendar as _cal
    first = d.replace(day=1)
    days_in = _cal.monthrange(d.year, d.month)[1]
    all_days = [first + datetime.timedelta(days=i) for i in range(days_in)]
    # Pad to full weeks
    start_pad = first.weekday()   # Mon=0
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


def v_calendar(win, W, H):
    now   = datetime.datetime.now()
    today = now.date()

    if CS.msg and time.time() - CS.msg_time > 4:
        CS.msg = ""

    # ── Minimal header ────────────────────────────────────────────────────
    #   MARCH 2026              day  week  month
    month_s = CS.date.strftime("%B %Y").upper()
    put(win, 0, 2, month_s, cp(P_HI, bold=True))

    # Mode tabs — highlight active
    tabs = [("day","1"), ("week","2"), ("month","3")]
    tx = W - 28
    for name, key in tabs:
        active = (CS.mode == name)
        lbl = f" {name.upper()} "
        col = cp(P_CYAN, bold=True) if active else cp(P_DIM)
        attr = col | (curses.A_UNDERLINE if active else 0)
        put(win, 0, tx, lbl, attr)
        tx += len(lbl) + 1

    # Thin separator
    put(win, 1, 0, "─"*W, cp(P_BOX))

    # Bottom hint — single clean line
    hint = " j/k · nav    a · add    d · delete    G · sync    t · today    1/2/3 · day/week/month "
    if CS.msg:
        hcol = P_RED if "ERROR" in CS.msg else P_GREEN
        put(win, H-1, 0, (" " + CS.msg)[:W], cp(hcol, bold=True))
    else:
        put(win, H-1, 0, hint[:W], cp(P_DIM))

    CY = 2          # content start row
    CH = H - 3      # content height

    # ── Input overlays ───────────────────────────────────────────────────
    if CS.add_mode or CS.ics_mode or CS.del_mode:
        blink = "▌" if int(time.time()*2)%2 else " "
        ow = min(W-8, 58); ox = (W-ow)//2; oy = H//2 - 5

        for r in range(oy, oy+11):
            try: win.move(r, ox); win.clrtoeol()
            except: pass

        # ── ADD EVENT — 3-field form ──────────────────────────────────────
        if CS.add_mode:
            step = CS.add_step
            put(win, oy,   ox+2, "new event", cp(P_CYAN, bold=True))
            put(win, oy+1, ox+2, "─"*(ow-4),  cp(P_BOX))

            # Field 1: DATE
            d_str = CS.add_date.strftime("%Y-%m-%d") if CS.add_date else CS.date.strftime("%Y-%m-%d")
            f1_attr = (cp(P_AMBER, bold=True) | curses.A_UNDERLINE) if step==0 else cp(P_MID)
            put(win, oy+3, ox+4, "date   ", cp(P_DIM))
            put(win, oy+3, ox+11, d_str, f1_attr)
            if step==0: put(win, oy+3, ox+19, "  ← → day  shift+←→ month  enter→next", cp(P_DIM))

            # Field 2: TIME
            t_str = f"{CS.add_hour:02d}:{CS.add_min:02d}"
            f2_attr = (cp(P_AMBER, bold=True) | curses.A_UNDERLINE) if step==1 else cp(P_MID)
            put(win, oy+5, ox+4, "time   ", cp(P_DIM))
            put(win, oy+5, ox+11, t_str, f2_attr)
            if step==1: put(win, oy+5, ox+17, "  ↑↓ hour  ← → minute  enter→next", cp(P_DIM))

            # Field 3: TITLE
            t_buf  = CS.add_title
            f3_attr = (cp(P_HI, bold=True)) if step==2 else cp(P_MID)
            put(win, oy+7, ox+4, "title  ", cp(P_DIM))
            if step==2:
                put(win, oy+7, ox+11, f"{t_buf}{blink}", f3_attr)
            else:
                put(win, oy+7, ox+11, t_buf if t_buf else "─", f3_attr)

            put(win, oy+9, ox+2, "─"*(ow-4), cp(P_BOX))
            if step==2:
                put(win, oy+10, ox+4, "enter · save", cp(P_GREEN))
            else:
                put(win, oy+10, ox+4, "enter · next field", cp(P_DIM))
            put(win, oy+10, ox+22, "esc · cancel", cp(P_DIM))

        # ── ICS SYNC ──────────────────────────────────────────────────────
        elif CS.ics_mode:
            put(win, oy,   ox+2, "connect calendar", cp(P_CYAN, bold=True))
            put(win, oy+1, ox+2, "─"*(ow-4),         cp(P_BOX))
            put(win, oy+3, ox+2, "Google Cal: Settings → Secret address in iCal format", cp(P_DIM))
            put(win, oy+4, ox+2, "Apple Cal:  File → Export → save to ~/.terminal_standby.ics", cp(P_DIM))
            put(win, oy+6, ox+4, f"{CS.ics_buf}{blink}", cp(P_HI, bold=True))
            put(win, oy+8, ox+2, "─"*(ow-4),         cp(P_BOX))
            put(win, oy+9, ox+4, "enter · sync    esc · cancel", cp(P_DIM))

        # ── DELETE CONFIRM ────────────────────────────────────────────────
        elif CS.del_mode:
            ev = CS.local_evs[CS.del_idx] if 0 <= CS.del_idx < len(CS.local_evs) else None
            put(win, oy,   ox+2, "delete event", cp(P_RED, bold=True))
            put(win, oy+1, ox+2, "─"*(ow-4),    cp(P_BOX))
            if ev:
                put(win, oy+3, ox+4, ev.get("title","?")[:ow-6], cp(P_HI))
                put(win, oy+4, ox+4, ev.get("dt","")[:ow-6],     cp(P_DIM))
            put(win, oy+6, ox+2, "─"*(ow-4), cp(P_BOX))
            put(win, oy+7, ox+4, "y · confirm delete    n / esc · cancel", cp(P_DIM))
        return

    # ─────────────────────────────────────────────────────────────────────
    # DAY VIEW  — clean hour timeline
    # ─────────────────────────────────────────────────────────────────────
    if CS.mode == "day":
        evs      = _evs_for_day(CS.date)
        is_today = (CS.date == today)

        # Date label
        if is_today:
            dlbl = f"  today  ·  {CS.date.strftime('%A, %d %B')}"
            put(win, CY, 0, dlbl, cp(P_AMBER, bold=True))
        else:
            dlbl = f"  {CS.date.strftime('%A, %d %B %Y')}"
            put(win, CY, 0, dlbl, cp(P_MID))

        # Hour slot height: try to show 7am-10pm in available rows
        FIRST_H, LAST_H = 7, 22
        n_hours  = LAST_H - FIRST_H + 1
        slot_h   = max(1, (CH - 2) // n_hours)
        time_col = 2
        ev_col   = 9

        for hi, hour in enumerate(range(FIRST_H, LAST_H+1)):
            hy = CY + 2 + hi * slot_h
            if hy >= CY + CH: break

            is_now = is_today and now.hour == hour
            # Hour label
            if slot_h > 1 or (hour % 2 == 0):          # skip odd hours if tight
                hcol = P_AMBER if is_now else P_DIM
                put(win, hy, time_col, f"{hour:02d}", cp(hcol))

            # Current-time indicator
            if is_now:
                put(win, hy, ev_col-1, "▶", cp(P_AMBER, bold=True))

            # Hairline
            put(win, hy, ev_col, "·"*2, cp(P_BOX))

            # Events
            hour_evs = [(s,e,t) for s,e,t in evs if s.hour == hour]
            for ei, (s, e, t) in enumerate(hour_evs):
                ey = hy + ei
                if ey >= CY + CH: break
                # global event index across all hours
                g_idx = evs.index((s,e,t))
                sel   = (g_idx == CS.cur_ev)
                upcoming = s >= now
                ecol  = P_AMBER if sel else (P_CYAN if upcoming else P_DIM)
                mins  = f":{s.minute:02d}" if s.minute else "   "
                # mark local-only events with ● so user knows they can delete them
                is_local = any(
                    lev.get("title") == t and
                    lev.get("dt","").startswith(s.strftime("%Y-%m-%d"))
                    for lev in CS.local_evs
                )
                marker = "●" if is_local else "○"
                row_txt = f" {marker} {mins}  {t}"[:W-ev_col-3]
                put(win, ey, ev_col+2, row_txt, cp(ecol, bold=(sel or upcoming)))
                if sel:
                    put(win, ey, ev_col, "▶", cp(P_AMBER, bold=True))

        if not evs:
            put(win, CY+CH//2,   0, " "*W, 0)
            centre(win, CY+CH//2,   "nothing scheduled", cp(P_DIM))
            centre(win, CY+CH//2+1, "press a to add an event", cp(P_DIM))

    # ─────────────────────────────────────────────────────────────────────
    # WEEK VIEW  — 7 columns, events stacked per day
    # ─────────────────────────────────────────────────────────────────────
    elif CS.mode == "week":
        week, ev_map = _evs_for_week(CS.date)
        col_w = (W - 1) // 7

        # Day headers
        for i, d in enumerate(week):
            x    = 1 + i * col_w
            is_t = (d == today)
            name = d.strftime("%a").upper()
            num  = str(d.day)
            if is_t:
                # Underline today's number
                put(win, CY,   x, name, cp(P_DIM))
                put(win, CY+1, x, num,  cp(P_AMBER, bold=True))
                put(win, CY+2, x, "──", cp(P_AMBER))
            else:
                put(win, CY,   x, name, cp(P_DIM))
                put(win, CY+1, x, num,  cp(P_MID))

        # Vertical column dividers
        for i in range(1, 7):
            x = i * col_w
            for r in range(CY, CY+CH):
                try: win.addch(r, x, curses.ACS_VLINE, cp(P_BOX))
                except: pass

        # Events per column
        ev_start_y = CY + 3
        max_ev_rows = CH - 3
        for i, d in enumerate(week):
            x    = 1 + i * col_w
            devs = ev_map.get(d, [])
            is_t = (d == today)
            for ri, (s, t) in enumerate(devs[:max_ev_rows]):
                ry      = ev_start_y + ri
                if ry >= CY + CH: break
                upcoming = s.date() >= today
                if is_t and upcoming:
                    ecol = P_CYAN
                elif upcoming:
                    ecol = P_MID
                else:
                    ecol = P_DIM
                # time + title clipped to column width
                txt = f"{s.strftime('%H:%M')} {t}"
                put(win, ry, x, txt[:col_w-1], cp(ecol))

    # ─────────────────────────────────────────────────────────────────────
    # MONTH VIEW  — clean grid, event dots + first title
    # ─────────────────────────────────────────────────────────────────────
    elif CS.mode == "month":
        weeks, ev_map = _evs_for_month(CS.date)
        col_w      = (W - 1) // 7
        row_h      = max(2, (CH - 2) // max(1, len(weeks)))
        day_names  = ["MON","TUE","WED","THU","FRI","SAT","SUN"]

        # Weekday header
        for i, dn in enumerate(day_names):
            is_wknd = i >= 5
            put(win, CY, 1+i*col_w, dn, cp(P_DIM if not is_wknd else P_BOX))
        put(win, CY+1, 0, "─"*W, cp(P_BOX))

        for wi, week in enumerate(weeks):
            wy = CY + 2 + wi * row_h
            for di, d in enumerate(week):
                x = 1 + di * col_w
                if d is None:
                    continue
                is_t   = (d == today)
                is_sel = (d == CS.date)
                evs    = ev_map.get(d, [])
                n_ev   = len(evs)

                # Day number styling
                num = str(d.day)
                if is_t:
                    # Today: number + underline accent
                    put(win, wy, x, num, cp(P_AMBER, bold=True))
                    put(win, wy, x+len(num), "▾", cp(P_AMBER))
                elif is_sel:
                    put(win, wy, x, num, cp(P_CYAN, bold=True))
                elif di >= 5:  # weekend
                    put(win, wy, x, num, cp(P_BOX))
                else:
                    put(win, wy, x, num, cp(P_MID))

                # Event indicators
                if n_ev and row_h >= 2:
                    # Coloured dot count then first title clipped
                    dot_c = P_GREEN if d >= today else P_DIM
                    dots  = "·" * min(n_ev, col_w-4)
                    put(win, wy+1, x, dots[:col_w-2], cp(dot_c))
                    if row_h >= 3 and evs:
                        put(win, wy+2, x, evs[0][:col_w-1], cp(P_DIM))

    # ── No calendar notice ────────────────────────────────────────────────
    with _CAL_LOCK:
        n_total = len(_CAL_EVENTS)
    if n_total == 0 and not CS.add_mode and not CS.ics_mode:
        centre(win, H-2,
               "no events · press G to connect Google or Apple Calendar",
               cp(P_DIM))


def _handle_cal_input(k):
    """Handle all calendar overlay key input (add form, delete confirm, ICS)."""
    # ── ADD FORM ──────────────────────────────────────────────────────────
    if CS.add_mode:
        step = CS.add_step

        if step == 0:   # DATE field  — arrow keys change day/month
            if k in (10, 13):
                CS.add_step = 1
            elif k == 27:
                CS.add_mode = False
            elif k == curses.KEY_RIGHT:
                CS.add_date = CS.add_date + datetime.timedelta(days=1)
            elif k == curses.KEY_LEFT:
                CS.add_date = CS.add_date - datetime.timedelta(days=1)
            elif k == curses.KEY_SR or k == 337:   # Shift+Up → +1 month
                import calendar as _c
                y, m = CS.add_date.year, CS.add_date.month
                m += 1
                if m > 12: m, y = 1, y+1
                d = min(CS.add_date.day, _c.monthrange(y,m)[1])
                CS.add_date = CS.add_date.replace(year=y, month=m, day=d)
            elif k == curses.KEY_SF or k == 336:   # Shift+Down → -1 month
                import calendar as _c
                y, m = CS.add_date.year, CS.add_date.month
                m -= 1
                if m < 1: m, y = 12, y-1
                d = min(CS.add_date.day, _c.monthrange(y,m)[1])
                CS.add_date = CS.add_date.replace(year=y, month=m, day=d)

        elif step == 1:  # TIME field  — up/down = hour, left/right = minute
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

        elif step == 2:  # TITLE field  — free text
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

    # ── DELETE CONFIRM ────────────────────────────────────────────────────
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

    # ── ICS SYNC ─────────────────────────────────────────────────────────
    elif CS.ics_mode:
        if k in (10, 13):
            url = CS.ics_buf.strip()
            if url:
                def _sync(u=url):
                    ok, msg = fetch_ics_url(u)
                    CS.msg = msg; CS.msg_time = time.time()
                threading.Thread(target=_sync, daemon=True).start()
            CS.ics_mode = False; CS.ics_buf = ""
        elif k == 27:
            CS.ics_mode = False; CS.ics_buf = ""
        elif k in (curses.KEY_BACKSPACE, 127, 8):
            CS.ics_buf = CS.ics_buf[:-1]
        elif 32 <= k <= 126:
            CS.ics_buf += chr(k)


def handle_key(k):
    v = ST.view

    # ── TEXT INPUT MODES — consume ALL keys, no globals ──────────────────
    # Todo add mode
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
        return  # swallow everything while typing

    # Calendar input modes — consume ALL keys before global nav
    if v == 6 and (CS.add_mode or CS.ics_mode or CS.del_mode):
        _handle_cal_input(k)
        return

    # Library text input mode — must check BEFORE global nav
    if v == 5 and LS.mode in ("add_url", "add_file"):
        if k in (10, 13):
            t = LS.buf.strip()
            if t:
                if LS.mode == "add_url":
                    AUDIO.add_youtube(t)
                else:
                    ok, msg = AUDIO.add_file(t)
                    LS.msg = msg
                    LS.msg_time = time.time()
            LS.mode = "browse"
            LS.buf  = ""
        elif k == 27:
            LS.mode = "browse"
            LS.buf  = ""
        else:
            LS.buf = _text_input(LS.buf, k)
        return  # swallow everything while typing

    # ── GLOBAL NAV (only when NOT in text-input mode) ────────────────────
    if k in (curses.KEY_RIGHT, ord('l'), 9):
        ST.view = (v + 1) % len(VIEWS)
        return
    if k in (curses.KEY_LEFT, ord('h')):
        ST.view = (v - 1) % len(VIEWS)
        return

    # ── GLOBAL MUSIC CONTROLS (all views except dashboard where space=todo) ─
    if k == ord(' ') and v != 0:  AUDIO.toggle_play(); return
    if k == ord('z'):  AUDIO.prev_track();  return
    if k == ord('x'):  AUDIO.next_track();  return
    if k == ord('s') and v != 2:  AUDIO.shuffle = not AUDIO.shuffle; return
    if k == ord('R'):  AUDIO.repeat = not AUDIO.repeat; return

    # ── VIEW-SPECIFIC ─────────────────────────────────────────────────────
    if v == 0:  # dashboard
        if k in (curses.KEY_UP,   ord('k')): ST.todo_cur = max(0, ST.todo_cur - 1)
        elif k in (curses.KEY_DOWN, ord('j')): ST.todo_cur = min(len(ST.todos)-1, ST.todo_cur+1)
        elif k in (10, 13) and ST.todos:     # ENTER = tick/untick todo
            ST.todos[ST.todo_cur][0] ^= True
            save_todos(ST.todos)
        elif k == ord(' '):  AUDIO.toggle_play()  # space still plays music
        elif k == ord('a'): ST.todo_add = True; ST.todo_buf = ""
        elif k == ord('d') and ST.todos:
            ST.todos.pop(ST.todo_cur)
            ST.todo_cur = max(0, min(ST.todo_cur, len(ST.todos)-1))
            save_todos(ST.todos)
        elif k == ord('p'): ST.pomo_run = not ST.pomo_run; ST._pw = time.time()
        elif k == ord('r'): ST.pomo_run = False; ST.pomo_secs = ST.pomo_total; ST._pw = time.time()

    elif v == 2:  # focus
        if k == ord('p'):   ST.pomo_run = not ST.pomo_run; ST._pw = time.time()
        elif k == ord('r'): ST.pomo_run = False; ST.pomo_secs = ST.pomo_total; ST._pw = time.time()
        elif k == ord('s'):
            ST.pomo_run   = False
            ST.pomo_phase = "BREAK" if ST.pomo_phase == "WORK" else "WORK"
            ST.pomo_total = 5*60.0 if ST.pomo_phase == "BREAK" else 25*60.0
            ST.pomo_secs  = ST.pomo_total
            ST._pw        = time.time()
        elif k == ord('f'): ST.focus_idx = (ST.focus_idx+1) % len(ST.focus_modes)

    elif v == 5:  # library browse mode (add_url/add_file handled above)
        if LS.mode == "browse":
            if k in (curses.KEY_UP,   ord('k')): LS.cursor = max(0, LS.cursor-1)
            elif k in (curses.KEY_DOWN, ord('j')): LS.cursor = min(len(AUDIO.library)-1, LS.cursor+1)
            elif k in (10, 13): AUDIO.play_index(LS.cursor)
            elif k == ord('Y'): LS.mode = "add_url";  LS.buf = ""
            elif k == ord('F'): LS.mode = "add_file"; LS.buf = ""
            elif k == ord('D'):
                if LS.cursor >= len(BUILTIN_TRACKS):
                    LS.mode = "confirm_del"
                else:
                    LS.msg = "Cannot remove built-in tracks"
                    LS.msg_time = time.time()
        elif LS.mode == "confirm_del":
            if k in (ord('y'), ord('Y')):
                ok, msg = AUDIO.remove_track(LS.cursor)
                LS.msg      = msg
                LS.msg_time = time.time()
                LS.cursor   = max(0, min(LS.cursor, len(AUDIO.library)-1))
                LS.mode     = "browse"
            elif k in (ord('n'), ord('N'), 27):
                LS.mode = "browse"

    elif v == 6:  # calendar navigation (input modes handled above)
        if k == ord('1'):   CS.mode = "day"
        elif k == ord('2'): CS.mode = "week"
        elif k == ord('3'): CS.mode = "month"
        elif k in (ord('j'), curses.KEY_DOWN):
            if CS.mode == "day":
                # Move event cursor in day view if events exist
                evs = _evs_for_day(CS.date)
                if evs:
                    CS.cur_ev = (CS.cur_ev + 1) % len(evs)
                else:
                    CS.date += datetime.timedelta(days=1)
            else:
                step = 7 if CS.mode=="week" else 28
                CS.date += datetime.timedelta(days=step)
        elif k in (ord('k'), curses.KEY_UP):
            if CS.mode == "day":
                evs = _evs_for_day(CS.date)
                if evs:
                    CS.cur_ev = (CS.cur_ev - 1) % len(evs)
                else:
                    CS.date -= datetime.timedelta(days=1)
            else:
                step = 7 if CS.mode=="week" else 28
                CS.date -= datetime.timedelta(days=step)
        elif k in (curses.KEY_RIGHT, curses.KEY_LEFT) and CS.mode != "day":
            # left/right navigate days in week/month view
            CS.date += datetime.timedelta(days=1 if k==curses.KEY_RIGHT else -1)
        elif k == ord('t'):
            CS.date  = datetime.datetime.now().date()
            CS.cur_ev = 0
        elif k == ord('a'):
            # Open structured add form
            CS.add_mode  = True
            CS.add_step  = 0
            CS.add_date  = CS.date
            CS.add_hour  = 9
            CS.add_min   = 0
            CS.add_title = ""
        elif k == ord('d'):
            # Delete: only local events, cursor must be on one
            evs = _evs_for_day(CS.date)
            if evs and 0 <= CS.cur_ev < len(evs):
                s, e, t = evs[CS.cur_ev]
                # find matching local event
                for li, lev in enumerate(CS.local_evs):
                    if (lev.get("title") == t and
                            lev.get("dt","").startswith(s.strftime("%Y-%m-%d"))):
                        CS.del_idx  = li
                        CS.del_mode = True
                        break
                else:
                    CS.msg      = "ICS events cannot be deleted here"
                    CS.msg_time = time.time()
        elif k == ord('G'):
            CS.ics_mode = True; CS.ics_buf = ""
        elif k == ord('r'):
            threading.Thread(target=refresh_calendar, daemon=True).start()
            CS.msg = "Refreshing..."; CS.msg_time = time.time()

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
VIEW_FNS=[v_dashboard,v_clock,v_focus,v_neofetch,v_network,v_library,v_calendar]

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)   # 20fps, fast enough for paste
    stdscr.keypad(True)  # enable special keys properly
    init_colors()

    # Audio starts paused; user presses SPACE to begin
    if not AUDIO._backend:
        AUDIO.playing = False

    while True:
        stdscr.erase()
        H,W=stdscr.getmaxyx()
        if H<24 or W<72:
            put(stdscr,H//2,max(0,(W-44)//2),
                f"  Terminal too small ({W}x{H}) — need 72x24+  ",
                cp(P_RED,bold=True))
            stdscr.refresh()
            if stdscr.getch()==ord('q'): break
            continue
        tick()
        draw_topbar(stdscr,W)
        VIEW_FNS[ST.view](stdscr,W,H)
        draw_navbar(stdscr,W,H)
        stdscr.refresh()
        k=stdscr.getch()
        if k==ord('q'): break
        if k!=-1: handle_key(k)

if __name__=="__main__":
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
        print(f"""
  Terminal StandBy  |  audio: {bname}  |  {platform.system()}
  SPACE=play/pause  z/x=prev/next  ←/→=views  q=quit
""")
    time.sleep(0.3)
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        AUDIO._kill()
        save_todos(ST.todos)
    print("\n  Goodbye! Todos saved.  [*]\n")