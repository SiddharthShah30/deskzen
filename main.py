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
#  PAC-MAN LOGO ANIMATION
# ══════════════════════════════════════════════════════════════════════════════

# Pac-Man open / closed mouth frames (5 rows tall, 7 cols wide)
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

# The track width matches LOGO_W = 26, minus 2 padding = 24 usable chars
_TRACK_W = 22   # dots track width (chars)
_DOT     = "·"
_PELLET  = "●"

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


def load_calendar_events():
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
    try:
        with open(CAL_ICS, encoding="utf-8", errors="replace") as f:
            evs += _parse_ics(f.read())
    except Exception: pass
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


def fetch_ics_url(url):
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
        self.status_msg = ""
        self._spec_t    = 0.0
        self._backend   = self._detect()
        if self._backend != "sounddevice":
            threading.Thread(target=self._try_install_sd, daemon=True).start()

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
        self._new_gen()
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
        self._proc       = None
        self._lock       = threading.Lock()
        self._renderer   = None
        self._installing = False
        threading.Thread(target=self._setup, daemon=True).start()

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
                os.path.join(os.environ.get("LOCALAPPDATA",""), "Programs","mpv","mpv.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA",""), "mpv","mpv.exe"),
                r"C:\mpv\mpv.exe",
                r"C:\Program Files\mpv\mpv.exe",
                r"C:\Program Files (x86)\mpv\mpv.exe",
            ]:
                if os.path.isfile(candidate):
                    return candidate
        return None

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
                is_mpv = "mpv" in os.path.basename(renderer).lower()
                if is_mpv:
                    if platform.system() == "Windows":
                        cmd = [renderer, "--really-quiet", source]
                    else:
                        cmd = [renderer, "--vo=tct", "--really-quiet", source]
                else:
                    ffplay_path = renderer if os.path.isfile(renderer) else shutil.which(renderer) or renderer
                    cmd = [ffplay_path, "-loglevel", "quiet", "-autoexit", source]

                self.status = f"launching player..."
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

                ydl_opts = {
                    "quiet":       True,
                    "no_warnings": True,
                    "format":      "best[height<=480]/bestvideo[height<=480]+bestaudio/best",
                    "noplaylist":  True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                if not info:
                    self.status = "could not fetch video info"
                    return

                title      = (info.get("title") or "YouTube Video")[:40]
                stream_url = info.get("url") or info.get("manifest_url", "")

                if not stream_url and info.get("formats"):
                    fmts = info["formats"]
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
        with self._lock:
            proc = self._proc
            self._proc   = None
            self.playing = False
        if proc:
            try: proc.terminate()
            except: pass
        self.status = ""

    def has_renderer(self): return self._renderer is not None
    def renderer_name(self):
        if self._installing: return "installing..."
        if not self._renderer: return "none"
        return os.path.basename(self._renderer)


VIDEO = VideoPlayer()
AUDIO = AudioEngine()

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
VIEWS = ["DASHBOARD","CLOCK + MUSIC","FOCUS","NEOFETCH","NETWORK","LIBRARY","CALENDAR","VIDEO","NEWS & STOCKS"]

class State:
    def __init__(self):
        self.view       = 0
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

ST = State()

# ══════════════════════════════════════════════════════════════════════════════
#  TICK
# ══════════════════════════════════════════════════════════════════════════════
def tick():
    now = time.time()
    AUDIO.tick()

    # Advance animation time
    ST._anim_t += 0.05

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

def next_event():
    return get_next_event()

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def v_dashboard(win, W, H):
    now = datetime.datetime.now()
    sd  = SD.snap()

    # ── Row 1: Clock (left) + Status (right) ─────────────────────────────────
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

    # ── Row 2: TODOS (left) + NEWS & STOCKS (right) — split 50/50 ────────────
    mid_start = 11
    # Cap todos at a fixed height to make room; remaining space goes to news
    # Available rows: from row 11 to (H - 12) for the dual panel
    dual_avail  = max(6, H - mid_start - 11)   # leave 11 rows at bottom
    todo_h_max  = max(4, dual_avail // 2 + 1)  # todos gets top ~half
    news_h_max  = max(4, dual_avail - todo_h_max)

    lw = W // 2        # left column width
    rw2 = W - lw - 1  # right column width

    # ── TODOS (left) ─────────────────────────────────────────────────────────
    todo_inner = max(2, todo_h_max - 2)
    todo_h     = todo_inner + 2 + (1 if ST.todo_add else 0)
    box(win, mid_start, 0, todo_h, lw,
        "TODOS  [a]=add  [d]=del  [ENTER]=check")
    visible_n = todo_inner
    start = max(0, ST.todo_cur - visible_n + 1) if len(ST.todos) > visible_n else 0

    for i, (done, text) in enumerate(ST.todos[start:start+visible_n]):
        ri  = start+i
        ry  = mid_start+1+i
        sel = (ri == ST.todo_cur)
        put(win, ry, 1, " "*(lw-2),
            cp(P_DIM)|(curses.A_REVERSE if sel else 0))
        tick_c = "✓" if done else " "
        col    = P_DIM if done else (P_AMBER if sel else P_HI)
        line   = f" {'▶' if sel else ' '} [{tick_c}] {text}"
        put(win, ry, 1, line[:lw-2],
            cp(col)|(curses.A_REVERSE if sel else 0))
    if len(ST.todos) > visible_n:
        put(win, mid_start+1, lw-8, f"{ST.todo_cur+1}/{len(ST.todos)}", cp(P_DIM))
    if ST.todo_add:
        put(win, mid_start+1+visible_n, 2,
            f" + {ST.todo_buf}{'█' if int(time.time()*2)%2 else ' '}", cp(P_AMBER))

    # ── NEWS & STOCKS (right of todos) ───────────────────────────────────────
    code   = get_user_country() or "GLOBAL"
    c_info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    flag   = c_info["flag"]
    items  = get_news_items()
    stocks = get_stock_data()
    wl     = load_stock_watchlist()

    ns_title = f"NEWS & STOCKS  {flag} [→ view 9]"
    box(win, mid_start, lw, todo_h, rw2, ns_title)

    # Stock ticker strip (1 line)
    sx = lw + 2; sy = mid_start + 1
    if stocks and wl:
        max_tickers = max(1, (rw2 - 4) // 19)
        for sym in wl[:max_tickers]:
            info = stocks.get(sym.upper())
            if info:
                arrow   = "▲" if info["change"] > 0 else ("▼" if info["change"] < 0 else "─")
                col     = P_GREEN if info["change"] >= 0 else P_RED
                s       = f"{sym} {arrow}{abs(info['pct']):.1f}%  "
                if sx + len(s) >= lw + rw2 - 1: break
                put(win, sy, sx, s, cp(col, bold=True))
                sx += len(s)
        put(win, sy, lw + rw2 - 2, "", cp(P_DIM))   # cap
    put(win, sy + 1, lw + 1, "─" * (rw2 - 2), cp(P_BOX))

    # News headlines (remaining rows)
    news_start_y = sy + 2
    news_rows    = todo_h - 4
    src_cols     = {"Reuters": P_CYAN, "BBC News": P_RED, "AP News": P_AMBER,
                    "Al Jazeera": P_GREEN, "Times of India": P_AMBER, "NDTV": P_AMBER,
                    "Hindu": P_GREEN, "Guardian": P_CYAN, "DW": P_BLUE,
                    "NHK World": P_PINK, "CBC": P_RED, "ABC AU": P_GREEN}
    for i, item in enumerate(items[:news_rows]):
        ny2 = news_start_y + i
        if ny2 >= mid_start + todo_h - 1: break
        sc   = src_cols.get(item["source"], P_BLUE)
        src  = f"[{item['source'][:6]}]"
        line = f"{src} {item['title']}"
        put(win, ny2, lw+2, line[:rw2-3], cp(P_HI if i == 0 else P_MID))

    # ── Pomodoro (left) + Next Event (right) below todos ─────────────────────
    by = mid_start + todo_h + 1
    hw = W//2 - 1
    box(win, by, 0, 5, hw, "POMODORO  [p]=start  [r]=reset")
    pm=int(ST.pomo_secs)//60; ps=int(ST.pomo_secs)%60
    pct=int((1-ST.pomo_secs/max(1,ST.pomo_total))*100)
    pc=P_RED if ST.pomo_phase=="WORK" else P_GREEN
    sym2="▶" if ST.pomo_run else "||"
    put(win,by+1,2,f" {sym2}  {pm:02d}:{ps:02d}  {ST.pomo_phase}",cp(pc,bold=True))
    hbar(win,by+2,2,hw-4,pct,pc)
    dots=" ".join("◉" if i<ST.pomo_done else "○" for i in range(8))
    put(win,by+3,2,dots[:hw-4],cp(P_DIM))

    box(win,by,hw+1,5,W-hw-2,"NEXT EVENT")
    evtitle,evtime = next_event()
    put(win,by+1,hw+3,evtitle,cp(P_HI))
    put(win,by+2,hw+3,evtime, cp(P_DIM))

    # ── Spectrum visualiser ───────────────────────────────────────────────────
    vy = by + 6
    vis_h = max(2, H - vy - 3)
    if vy + vis_h + 1 < H:
        td   = AUDIO.current
        lbl  = f"VISUALIZER  ~ {td['name'][:30]} — {td['artist']}"
        box(win, vy, 0, vis_h+2, W-1, lbl)
        spec = list(ST._spec_smooth)
        draw_spectrum(win, vy+1, 1, vis_h, W-3, spec)

    put(win, H-1, 0,
        " [ENTER]=check  [p] pomo  [r] reset  [a] add  [d] del todo  [space]=music  [←→] views  [q] quit ",
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

    sw = min(W-8, 52)
    hbar(win, 9, (W-sw)//2, sw, now.second*100//60, P_MID)

    mw = min(W-4, 68); mx=(W-mw)//2; my=11
    td      = AUDIO.current
    dur     = float(td.get("duration") or 0)
    with AUDIO._lock:
        elapsed = float(AUDIO.elapsed)
    if dur > 0:
        elapsed = min(elapsed, dur)
        pct = int(elapsed / dur * 100)
    else:
        pct = int((elapsed % 60) / 60 * 100)
    em,es  = divmod(int(elapsed), 60)
    dm,ds2 = divmod(int(dur), 60) if dur > 0 else (0, 0)

    box(win, my, mx, 12, mw, "NOW PLAYING")
    put(win, my+1, mx+2, td["name"][:mw-4], cp(P_HI, bold=True))
    genre = td.get("genre","")
    genre_lbl = {"brown":"Brown Noise","pink":"Pink Noise","white":"White Noise",
                 "rain":"Rain on Glass","space":"Deep Space"}.get(genre,"")
    sub = f"[{genre_lbl}]  {td['artist']}" if genre_lbl else f"by {td['artist']}"
    put(win, my+2, mx+2, sub[:mw-4], cp(P_DIM))
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

    for i in range(min(4, len(AUDIO.library))):
        ri = (AUDIO.track_idx + i) % len(AUDIO.library)
        t_entry = AUDIO.library[ri]; tn, ta = t_entry["name"], t_entry["artist"]
        sel = (ri == AUDIO.track_idx)
        pre = "▶ " if sel else "  "
        put(win, my+7+i, mx+2,
            f"{pre}{tn[:mw//2-4]}  —  {ta}"[:mw-4],
            cp(P_HI if sel else P_DIM))

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

    put(win,H-1,0," [p] start/pause  [r] reset  [s] skip  [f] mode  [←→] views  [q] quit ",cp(P_DIM))

# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 4 — NEOFETCH
# ══════════════════════════════════════════════════════════════════════════════

def v_neofetch(win, W, H):
    sd       = SD.snap()

    # ── Layout ────────────────────────────────────────────────────────────
    AX     = 2          # logo left edge
    AY     = 1          # logo top
    LOGO_W = 26         # pac-man column width
    IX     = AX + LOGO_W + 1   # info column starts here
    KEY_W  = 11         # width of key label field
    VAL_X  = IX + KEY_W

    # ── Animated logo ─────────────────────────────────────────────────────
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
    max_info_w = max(1, W - VAL_X - 2)

    put(win, AY,   IX, user_host[:W-IX-2], cp(P_HI, bold=True))
    put(win, AY+1, IX, "─" * min(len(user_host), W-IX-2), cp(P_BOX))

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
    bw      = W - 8
    if bar_top + bar_h < H - 2:
        box(win, bar_top, 2, bar_h, W-4, "LIVE RESOURCES")
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
            put(win, ry, 4, lbl, cp(P_DIM))
            hbar(win, ry, 9, bw, pct, col)
            put(win, ry, 9+bw+1, f"{pct:3d}%", cp(col))

    put(win, H-1, 0,
        " neofetch · live stats · auto-refresh  [←→] views  [q] quit ",
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

    put(win,H-1,0," real-time data  [←→] views  [q] quit ",cp(P_DIM))


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 6 — MUSIC LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
class LibState:
    cursor   = 0
    mode     = "browse"
    buf      = ""
    msg      = ""
    msg_time = 0.0

LS = LibState()

def v_library(win, W, H):
    lib = AUDIO.library
    n   = len(lib)

    centre(win, 1, "MUSIC LIBRARY", cp(P_HI, bold=True)|curses.A_BOLD)
    centre(win, 2, f"{n} track{'s' if n!=1 else ''}  ·  {len(lib)-len(BUILTIN_TRACKS)} user-added",
           cp(P_DIM))

    list_h  = H - 16
    list_y  = 4
    box(win, list_y, 1, list_h, W-2, "TRACKS  [j/k]=nav  [ENTER]=play  [D]=delete")

    start = max(0, LS.cursor - list_h + 4)
    for i, trk in enumerate(lib[start:start+list_h-2]):
        ri  = start + i
        ry  = list_y + 1 + i
        sel = (ri == LS.cursor)
        now = (ri == AUDIO.track_idx)

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

    if n > list_h-2:
        put(win, list_y, W-10, f" {LS.cursor+1}/{n} ", cp(P_DIM))

    if LS.msg and time.time() - LS.msg_time > 4.0:
        LS.msg = ""
    msg = AUDIO.status_msg or LS.msg
    if msg:
        col = P_RED if "ERROR" in msg else P_GREEN if "Added" in msg else P_AMBER
        centre(win, list_y+list_h, msg[:W-4], cp(col, bold=True))

    panel_y = list_y + list_h + 1
    blink   = "_" if int(time.time()*2)%2 else " "

    if LS.mode == "add_url":
        box(win, panel_y, 2, 6, W-4, "ADD YOUTUBE URL")
        put(win, panel_y+1, 4,
            "Right-click paste (or type) the URL, then ENTER.  ESC = cancel.",
            cp(P_DIM))
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

    else:
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
    bat=sd.get("bat_pct",100); plug=sd.get("bat_plug",True)
    bc=P_GREEN if bat>40 else (P_AMBER if bat>15 else P_RED)
    put(win,0,0," "*W, cp(P_DIM)|curses.A_REVERSE)
    put(win,0,1,f" {ts}  {ds}", cp(P_HI)|curses.A_REVERSE)
    vn=f"  {VIEWS[ST.view]}  "
    put(win,0,(W-len(vn))//2,vn, cp(P_HI)|curses.A_REVERSE|curses.A_BOLD)
    if AUDIO.playing:
        td=AUDIO.current
        note_s=f" ~ {td['name'][:20]} "
        put(win,0,W//2+len(vn)//2+2,note_s, cp(P_CYAN)|curses.A_REVERSE)
    right=f" {'+'if plug else ' '}{bat}%  {sd.get('cpu',0):.0f}%cpu  {sd.get('mem_pct',0):.0f}%mem "
    put(win,0,W-len(right)-1,right, cp(bc)|curses.A_REVERSE)

def draw_navbar(win, W, H):
    dots="  ".join("◆" if i==ST.view else "◇" for i in range(len(VIEWS)))
    put(win,H-2,1,"[← h]",cp(P_DIM))
    centre(win,H-2,dots,cp(P_DIM))
    put(win,H-2,W-7,"[l →]",cp(P_DIM))

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
    add_date  = None
    add_hour  = 9
    add_min   = 0
    add_title = ""
    del_mode  = False
    del_idx   = -1
    cur_ev    = 0
    ics_mode  = False
    ics_buf   = ""
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
        put(win, oy,     ox + 2, "  ⟳ Connect Calendar", cp(P_CYAN, bold=True))
        put(win, oy + 1, ox + 1, "─" * (ow - 2), cp(P_BOX))
        put(win, oy + 3, ox + 3, "Google: Settings → Secret address in iCal format", cp(P_DIM))
        put(win, oy + 4, ox + 3, "Apple:  File → Export → ~/.terminal_standby.ics", cp(P_DIM))
        put(win, oy + 6, ox + 3, "URL / path:", cp(P_DIM))
        put(win, oy + 7, ox + 3, f"{CS.ics_buf}{blink}", cp(P_HI, bold=True))
        put(win, oy + 9, ox + 1, "─" * (ow - 2), cp(P_BOX))
        put(win, oy + 10, ox + 3, "Enter · Sync     Esc · Cancel", cp(P_DIM))

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
    """Apple-Calendar week view: day columns with time gutter, event pills."""
    week, ev_map = _evs_for_week(CS.date)
    GUTTER  = 6
    n_cols  = 7
    col_w   = max(4, (W - GUTTER - 1) // n_cols)
    FIRST_H, LAST_H = 7, 22
    n_hours = LAST_H - FIRST_H + 1
    body_h  = CH - 4          # rows for time grid
    slot_h  = max(1, body_h // n_hours)

    # ── Column headers ────────────────────────────────────────────────────────
    for i, d in enumerate(week):
        x    = GUTTER + 1 + i * col_w
        is_t = (d == today)
        dow  = d.strftime("%a").upper()
        num  = str(d.day)
        if is_t:
            put(win, CY,     x, dow, cp(P_DIM))
            # circle today's date number
            put(win, CY + 1, x, f"[{num}]", cp(P_AMBER, bold=True))
            put(win, CY + 2, x, "─" * (col_w - 1), cp(P_AMBER))
        elif d == CS.date:
            put(win, CY,     x, dow, cp(P_DIM))
            put(win, CY + 1, x, num, cp(P_CYAN, bold=True))
        else:
            wknd = (d.weekday() >= 5)
            put(win, CY,     x, dow, cp(P_BOX if wknd else P_DIM))
            put(win, CY + 1, x, num, cp(P_BOX if wknd else P_MID))

    # header rule
    put(win, CY + 2, GUTTER + 1, "─" * (n_cols * col_w), cp(P_BOX))

    # ── Time gutter + column dividers ─────────────────────────────────────────
    for hi, hour in enumerate(range(FIRST_H, LAST_H + 1)):
        hy = CY + 3 + hi * slot_h
        if hy >= CY + CH: break
        is_now_h = (CS.date.weekday() < 7) and now.date() in week and now.hour == hour
        hcol = P_AMBER if (now.date() in week and now.hour == hour) else P_DIM
        if slot_h >= 2 or hour % 2 == 0:
            put(win, hy, 0, f"{hour:02d}:00", cp(hcol))
        put(win, hy, GUTTER, "┤", cp(P_BOX))
        # horizontal hour rule across all columns
        put(win, hy, GUTTER + 1, "─" * (n_cols * col_w), cp(P_BOX))

    # vertical column dividers
    for i in range(1, n_cols):
        x = GUTTER + i * col_w
        for r in range(CY + 2, CY + CH):
            try: win.addch(r, x, curses.ACS_VLINE, cp(P_BOX))
            except: pass

    # now-line
    if now.date() in week:
        day_idx = week.index(now.date())
        frac    = (now.hour - FIRST_H + now.minute / 60) / n_hours
        now_y   = CY + 3 + int(frac * body_h)
        now_y   = max(CY + 3, min(now_y, CY + CH - 1))
        nx      = GUTTER + 1 + day_idx * col_w
        put(win, now_y, nx, "▶" + "─" * (col_w - 2), cp(P_RED, bold=True))

    # ── Events ────────────────────────────────────────────────────────────────
    for i, d in enumerate(week):
        x    = GUTTER + 1 + i * col_w
        devs = ev_map.get(d, [])
        is_t = (d == today)
        for ri, (s, t) in enumerate(devs):
            frac   = (s.hour - FIRST_H + s.minute / 60) / n_hours
            ey     = CY + 3 + int(frac * body_h)
            ey     = max(CY + 3, min(ey, CY + CH - 1))
            past   = s < now
            is_t_d = (d == today)
            ecol   = P_DIM if past else (P_CYAN if is_t_d else P_BLUE)
            txt    = f"·{s.strftime('%H:%M')} {t}"[:col_w - 1]
            if not past:
                put(win, ey, x, " " * (col_w - 1), cp(ecol) | curses.A_REVERSE)
                put(win, ey, x, txt, cp(P_HI, bold=True) | curses.A_REVERSE)
            else:
                put(win, ey, x, txt, cp(ecol))


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
    hint = " j/k·nav   a·add   d·del   G·sync   t·today   1·Day  2·Week  3·Month  4·Year "
    if CS.msg:
        hcol = P_RED if "ERROR" in CS.msg else P_GREEN
        put(win, H - 1, 0, (" " + CS.msg)[: W], cp(hcol, bold=True))
    else:
        put(win, H - 1, 0, hint[: W], cp(P_DIM))

    CY = 2    # content start row
    CH = H - 3

    # ── Overlay panels take priority ──────────────────────────────────────────
    if CS.add_mode or CS.ics_mode or CS.del_mode:
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

    put(win, 0, 2, "VIDEO", cp(P_CYAN, bold=True))
    rname = VIDEO.renderer_name()
    put(win, 0, 10, f"renderer: {rname}", cp(P_DIM))
    put(win, 1, 0, "─"*W, cp(P_BOX))

    CY = 2; CH = H - 5

    status_txt = VIDEO.status
    if status_txt:
        scol = P_RED if ("error" in status_txt.lower() or "not found" in status_txt.lower()
                         or "failed" in status_txt.lower()) else P_AMBER
        centre(win, CY+1, status_txt[:W-4], cp(scol, bold=True))

    if VIDEO.playing:
        centre(win, CY+3, "▶  NOW PLAYING", cp(P_GREEN, bold=True))
        centre(win, CY+4, VIDEO.title, cp(P_HI, bold=True))
        centre(win, CY+6, "playing in a separate window  ·  press S to stop", cp(P_DIM))
    elif not VIDEO.status:
        mid = CY + CH//2 - 3
        if not VIDEO.has_renderer():
            centre(win, mid,   "no video player found", cp(P_RED, bold=True))
            centre(win, mid+1, "auto-installing mpv in background...", cp(P_AMBER))
            centre(win, mid+2, "or: winget install mpv  /  brew install mpv", cp(P_DIM))
        else:
            centre(win, mid,   f"player ready: {VIDEO.renderer_name()}", cp(P_GREEN))
            centre(win, mid+2, "Y · YouTube URL    O · open file", cp(P_DIM))

    blink = "▌" if int(time.time()*2)%2 else " "
    if VS.mode in ("add_url", "add_file"):
        ow = min(W-8, 64); ox = (W-ow)//2; oy = H//2 - 4
        for r in range(oy, oy+9):
            try: win.move(r, ox); win.clrtoeol()
            except: pass
        label = "play youtube url" if VS.mode == "add_url" else "open video file"
        put(win, oy,   ox+2, label,           cp(P_CYAN, bold=True))
        put(win, oy+1, ox+2, "─"*(ow-4),      cp(P_BOX))
        if VS.mode == "add_url":
            put(win, oy+2, ox+2, "youtube.com/watch?v=...  or  youtu.be/...", cp(P_DIM))
        else:
            put(win, oy+2, ox+2, "full path to video file  (mp4 mkv avi mov webm)", cp(P_DIM))
        put(win, oy+4, ox+2, f"{VS.buf}{blink}", cp(P_HI, bold=True))
        put(win, oy+6, ox+2, "─"*(ow-4), cp(P_BOX))
        put(win, oy+7, ox+2, "enter · play    esc · cancel", cp(P_DIM))

    if VS.msg:
        mcol = P_RED if "error" in VS.msg.lower() else P_GREEN
        put(win, H-2, 2, VS.msg[:W-4], cp(mcol, bold=True))

    put(win, H-1, 0,
        " O · open file    Y · YouTube    S · stop    ←→ · views ",
        cp(P_DIM))


# ══════════════════════════════════════════════════════════════════════════════
#  INPUT HANDLER
# ══════════════════════════════════════════════════════════════════════════════
def handle_key(k):
    v = ST.view

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

    if v == 6 and (CS.add_mode or CS.ics_mode or CS.del_mode):
        _handle_cal_input(k)
        return

    if v == 5 and LS.mode in ("add_url", "add_file"):
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

    if v == 7 and VS.mode in ("add_url", "add_file"):
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

    if k in (curses.KEY_RIGHT, ord('l'), 9):
        ST.view = (v + 1) % len(VIEWS); return
    if k in (curses.KEY_LEFT, ord('h')):
        ST.view = (v - 1) % len(VIEWS); return

    if k == ord(' ') and v != 0: AUDIO.toggle_play(); return
    if k == ord('z'):             AUDIO.prev_track();  return
    if k == ord('x'):             AUDIO.next_track();  return
    if k == ord('s') and v != 2: AUDIO.shuffle = not AUDIO.shuffle; return
    if k == ord('R'):             AUDIO.repeat = not AUDIO.repeat;   return

    if v == 0:
        if k in (curses.KEY_UP,   ord('k')): ST.todo_cur = max(0, ST.todo_cur - 1)
        elif k in (curses.KEY_DOWN, ord('j')): ST.todo_cur = min(len(ST.todos)-1, ST.todo_cur+1)
        elif k in (10, 13) and ST.todos:
            ST.todos[ST.todo_cur][0] ^= True
            save_todos(ST.todos)
        elif k == ord(' '):  AUDIO.toggle_play()
        elif k == ord('a'): ST.todo_add = True; ST.todo_buf = ""
        elif k == ord('d') and ST.todos:
            ST.todos.pop(ST.todo_cur)
            ST.todo_cur = max(0, min(ST.todo_cur, len(ST.todos)-1))
            save_todos(ST.todos)
        elif k == ord('p'): ST.pomo_run = not ST.pomo_run; ST._pw = time.time()
        elif k == ord('r'): ST.pomo_run = False; ST.pomo_secs = ST.pomo_total; ST._pw = time.time()

    elif v == 2:
        if k == ord('p'):   ST.pomo_run = not ST.pomo_run; ST._pw = time.time()
        elif k == ord('r'): ST.pomo_run = False; ST.pomo_secs = ST.pomo_total; ST._pw = time.time()
        elif k == ord('s'):
            ST.pomo_run   = False
            ST.pomo_phase = "BREAK" if ST.pomo_phase == "WORK" else "WORK"
            ST.pomo_total = 5*60.0 if ST.pomo_phase == "BREAK" else 25*60.0
            ST.pomo_secs  = ST.pomo_total; ST._pw = time.time()
        elif k == ord('f'): ST.focus_idx = (ST.focus_idx+1) % len(ST.focus_modes)

    elif v == 5:
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
                    LS.msg = "Cannot remove built-in tracks"; LS.msg_time = time.time()
        elif LS.mode == "confirm_del":
            if k in (ord('y'), ord('Y')):
                ok, msg = AUDIO.remove_track(LS.cursor)
                LS.msg = msg; LS.msg_time = time.time()
                LS.cursor = max(0, min(LS.cursor, len(AUDIO.library)-1))
                LS.mode   = "browse"
            elif k in (ord('n'), ord('N'), 27):
                LS.mode = "browse"

    elif v == 6:
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
        elif k == ord('d'):
            evs = _evs_for_day(CS.date)
            if evs and 0 <= CS.cur_ev < len(evs):
                s, e, t = evs[CS.cur_ev]
                for li, lev in enumerate(CS.local_evs):
                    if (lev.get("title") == t and
                            lev.get("dt","").startswith(s.strftime("%Y-%m-%d"))):
                        CS.del_idx = li; CS.del_mode = True; break
                else:
                    CS.msg = "ICS events cannot be deleted here"; CS.msg_time = time.time()
        elif k == ord('G'):
            CS.ics_mode = True; CS.ics_buf = ""
        elif k == ord('r'):
            threading.Thread(target=refresh_calendar, daemon=True).start()
            CS.msg = "Refreshing..."; CS.msg_time = time.time()

    elif v == 7:
        if k == ord('Y'):   VS.mode = "add_url";  VS.buf = ""
        elif k == ord('O'): VS.mode = "add_file"; VS.buf = ""
        elif k == ord('S'):
            VIDEO.stop()
            VS.msg = "stopped"; VS.msg_time = time.time()

    elif v == 8:
        _handle_news_stocks_key(k)


# ══════════════════════════════════════════════════════════════════════════════
#  NEWS & STOCKS ENGINE
# ══════════════════════════════════════════════════════════════════════════════
import urllib.request as _ureq
import html as _html

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

NEWS_REFRESH_SECS   = 3600   # 1 hour
STOCKS_REFRESH_SECS = 300    # 5 minutes

# ── Country database ──────────────────────────────────────────────────────────
# Each entry: code, flag, display name, [RSS feeds], [default stock tickers]
COUNTRY_DB = {
    "US": {
        "flag": "🇺🇸", "name": "United States",
        "feeds": [
            ("Reuters",    "https://feeds.reuters.com/reuters/topNews"),
            ("AP News",    "https://rsshub.app/apnews/topics/apf-topnews"),
            ("CNN",        "http://rss.cnn.com/rss/cnn_topstories.rss"),
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
            ("NDTV",           "https://feeds.feedburner.com/ndtvnews-top-stories"),
            ("Hindu",          "https://www.thehindu.com/news/national/feeder/default.rss"),
            ("Hindustan Times","https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"),
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
            ("Korea Herald","http://www.koreaherald.com/rss"),
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
            ("Xinhua",    "http://www.xinhuanet.com/english/rss/worldrss.xml"),
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
            ("AP News",    "https://rsshub.app/apnews/topics/apf-topnews"),
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


def _fetch_rss(url, source, limit=5):
    """Fetch one RSS feed, return list of article dicts."""
    try:
        req = _ureq.Request(url, headers={"User-Agent": "TerminalStandBy/3"})
        with _ureq.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        items = []
        import re
        # Extract <item> blocks
        for block in re.findall(r'<item>(.*?)</item>', raw, re.DOTALL)[:limit]:
            title_m = re.search(r'<title[^>]*>(.*?)</title>', block, re.DOTALL)
            date_m  = re.search(r'<pubDate>(.*?)</pubDate>', block, re.DOTALL)
            title   = _html.unescape(_strip_tags(title_m.group(1))) if title_m else ""
            pub     = date_m.group(1).strip()[:22] if date_m else ""
            # Shorten pubDate to just time or "today"
            try:
                from email.utils import parsedate_to_datetime as _pdt
                dt = _pdt(pub)
                now = datetime.datetime.now(datetime.timezone.utc)
                diff = now - dt
                if diff.total_seconds() < 3600:
                    ts = f"{int(diff.total_seconds()//60)}m ago"
                elif diff.total_seconds() < 86400:
                    ts = f"{int(diff.total_seconds()//3600)}h ago"
                else:
                    ts = dt.strftime("%b %d")
            except Exception:
                ts = pub[:12]
            if title and len(title) > 4:
                items.append({"title": title, "source": source, "time": ts})
        return items
    except Exception as e:
        return []


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
    """Fetch stock price via Yahoo Finance unofficial JSON endpoint."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
        req = _ureq.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        with _ureq.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        meta   = data["chart"]["result"][0]["meta"]
        price  = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
        prev   = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
        change = price - prev
        pct    = (change / prev * 100) if prev else 0.0
        name   = meta.get("longName") or meta.get("shortName") or symbol
        return {"price": price, "change": change, "pct": pct, "name": name[:28]}
    except Exception:
        return None


def fetch_stocks_bg(symbols):
    """Background thread: fetch all watched symbols."""
    global _stock_data, _stocks_status, _stocks_last
    _stocks_status = "Fetching prices…"
    new_data = {}
    for sym in symbols:
        result = _fetch_stock_price(sym.upper())
        if result:
            new_data[sym.upper()] = result
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
        _stocks_status = f"Updated  {datetime.datetime.now().strftime('%H:%M')}"
    else:
        _stocks_status = "No data (check internet)"
    _stocks_last = time.time()


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
    while True:
        fetch_news_bg()
        time.sleep(NEWS_REFRESH_SECS)

def _stocks_refresh_loop():
    wl = load_stock_watchlist()
    while True:
        fetch_stocks_bg(wl)
        # Reload watchlist each cycle so new additions are picked up
        wl = load_stock_watchlist()
        time.sleep(STOCKS_REFRESH_SECS)

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
threading.Thread(target=_news_refresh_loop,   daemon=True).start()
threading.Thread(target=_stocks_refresh_loop, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW 9 — NEWS & STOCKS
# ══════════════════════════════════════════════════════════════════════════════

class NewsStocksState:
    scroll        = 0        # news scroll offset
    tab           = 0        # 0=news, 1=stocks, 2=country
    stock_input   = False    # adding new ticker
    stock_buf     = ""
    stock_cur     = 0        # selected row in stocks list
    country_cur   = 0        # cursor in country picker
    country_mode  = False    # True = country picker overlay open
    msg           = ""
    msg_time      = 0.0

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
    for lbl, idx in tabs:
        active = (NSS.tab == idx)
        attr   = cp(P_CYAN, bold=True) | curses.A_REVERSE if active else cp(P_DIM)
        put(win, 1, tx, lbl, attr)
        tx += len(lbl) + 1

    country_lbl = f"  {flag} {cname} "
    put(win, 1, tx + 2, country_lbl, cp(P_AMBER))
    put(win, 1, tx + 2 + len(country_lbl) + 1, "[C]=change country", cp(P_DIM))
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
    # Status line with country info
    code   = get_user_country() or "GLOBAL"
    c_info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    flag   = c_info["flag"]; cname = c_info["name"]
    put(win, 3, 2, f"[ {flag} {cname}  ·  {_news_status}  ·  refreshes hourly ]", cp(P_DIM))
    put(win, 4, 0, "─" * W, cp(P_BOX))

    if not items:
        centre(win, H // 2, "  No news items. Check internet connection.  ", cp(P_AMBER))
        put(win, H-1, 0, " [1] News  [2] Stocks  [j/k] scroll  [r] refresh  [←→] views ", cp(P_DIM))
        return

    content_h = H - 7   # rows available for news
    visible   = []
    # Each item: title line + source/time line + blank = 3 lines
    for item in items:
        visible.append(item)

    # Clamp scroll
    max_scroll = max(0, len(visible) * 3 - content_h)
    NSS.scroll = max(0, min(NSS.scroll, max_scroll))

    # Draw news list
    y      = 5
    offset = NSS.scroll
    src_colors = {"Reuters": P_CYAN, "BBC News": P_RED, "AP News": P_AMBER, "Al Jazeera": P_GREEN}

    for i, item in enumerate(visible):
        title   = item["title"]
        source  = item["source"]
        ts      = item["time"]
        src_col = src_colors.get(source, P_BLUE)

        # 3 virtual lines per item: bullet+title, source·time, blank spacer
        lines = [
            (f"  ● {title}", P_HI,    True,    src_col),
            (f"    ╰ {source}  ·  {ts}", src_col, False, src_col),
            ("", P_DIM, False, P_DIM),
        ]
        for txt, col, bold, _ in lines:
            if offset > 0:
                offset -= 1
                continue
            if y >= H - 2:
                break
            # Subtle alternating row tint
            if i % 2 == 0:
                put(win, y, 0, " " * (W - 1), cp(P_DIM))
            put(win, y, 0, txt[:W - 2], cp(col, bold=bold))
            y += 1
        if y >= H - 2:
            break

    # Scroll indicator
    if max_scroll > 0:
        pct = int(NSS.scroll / max_scroll * (H - 7))
        for sy in range(5, H - 2):
            put(win, sy, W - 1, "│", cp(P_BOX))
        put(win, 5 + pct, W - 1, "█", cp(P_DIM))

    put(win, H-1, 0, " [j/k] scroll  [r] refresh  [C] change country  [2] stocks  [←→] views  [q] quit ", cp(P_DIM))


def _draw_stocks_tab(win, W, H, stocks, watchlist):
    code   = get_user_country() or "GLOBAL"
    c_info = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
    flag   = c_info["flag"]; cname = c_info["name"]
    put(win, 3, 2, f"[ {flag} {cname}  ·  {_stocks_status}  ·  refreshes every 5 min ]", cp(P_DIM))
    put(win, 4, 0, "─" * W, cp(P_BOX))

    # Fixed column widths that scale with terminal width
    C_SYM  = 2
    W_SYM  = 8    # "▶ AAPL  "
    C_NAME = C_SYM + W_SYM
    W_NAME = max(16, W - C_NAME - 32)  # flex
    C_PX   = C_NAME + W_NAME
    C_CHG  = C_PX  + 13
    C_PCT  = C_CHG + 13

    hdr_line = (f"{'  SYM':<{W_SYM}}{'NAME':<{W_NAME}}{'PRICE':>12}  {'CHANGE':>10}  {'%':>8}")
    put(win, 5, C_SYM, hdr_line[:W - 4], cp(P_DIM))
    put(win, 6, 0, "─" * W, cp(P_BOX))

    y = 7
    NSS.stock_cur = max(0, min(NSS.stock_cur, max(0, len(watchlist) - 1)))

    for i, sym in enumerate(watchlist):
        if y >= H - 5:
            break
        sel  = (i == NSS.stock_cur)
        info = stocks.get(sym.upper())

        if info:
            price  = info["price"]
            change = info["change"]
            pct    = info["pct"]
            name   = info["name"]
            if change > 0:
                chg_col = P_GREEN; arrow = "▲"
            elif change < 0:
                chg_col = P_RED;   arrow = "▼"
            else:
                chg_col = P_MID;   arrow = "─"
            price_s  = f"${price:>10.2f}"
            change_s = f"{arrow}{abs(change):>8.2f}"
            pct_s    = f"{pct:>+7.2f}%"
        else:
            name     = "Loading…"
            price_s  = "          ─"
            change_s = "          ─"
            pct_s    = "       ─"
            chg_col  = P_DIM
            arrow    = ""

        sym_lbl  = f" {'▶' if sel else ' '} {sym:<6}"
        name_lbl = name[:W_NAME]
        row_base = cp(P_AMBER if sel else P_HI, bold=sel)
        rev      = curses.A_REVERSE if sel else 0

        if sel:
            put(win, y, 0, " " * (W - 1), cp(P_AMBER) | rev)

        put(win, y, C_SYM,  sym_lbl,                      cp(P_AMBER if sel else P_CYAN, bold=True) | rev)
        put(win, y, C_NAME, f"{name_lbl:<{W_NAME}}",      cp(P_MID)   | rev)
        put(win, y, C_PX,   price_s,                       cp(P_HI, bold=True) | rev)
        if info:
            put(win, y, C_CHG,  f"  {change_s}",           cp(chg_col, bold=True) | rev)
            put(win, y, C_PCT,  f"  {pct_s}",              cp(chg_col) | rev)
        else:
            put(win, y, C_CHG,  f"  {change_s}",           cp(P_DIM) | rev)
        y += 1

    # Add / remove panel
    panel_y = max(y + 1, H - 7)
    put(win, panel_y, 0, "─" * W, cp(P_BOX))

    blink = "█" if int(time.time() * 2) % 2 else " "
    if NSS.stock_input:
        put(win, panel_y + 1, 2, "Add ticker: ", cp(P_DIM))
        put(win, panel_y + 1, 14, (NSS.stock_buf.upper() + blink)[:W - 17], cp(P_AMBER, bold=True))
        put(win, panel_y + 2, 2, "ENTER=confirm   ESC=cancel   (e.g. NVDA, INFY.NS, BTC-USD)", cp(P_DIM))
    else:
        if NSS.msg and time.time() - NSS.msg_time < 4:
            col = P_GREEN if "Added" in NSS.msg or "Removed" in NSS.msg else P_RED
            put(win, panel_y + 1, 2, NSS.msg[:W - 4], cp(col, bold=True))
        else:
            put(win, panel_y + 1, 2,
                f"Watching {len(watchlist)} ticker(s)  ·  [a]=add  [d]=remove selected  [r]=refresh now",
                cp(P_DIM))

    put(win, H-1, 0, " [j/k] select  [a] add  [d] remove  [D] reset to country defaults  [C] country  [r] refresh  [←→] views ", cp(P_DIM))


# ── Key handling for view 8 (News & Stocks) ──────────────────────────────────
def _handle_news_stocks_key(k):
    """Handle keypresses for the news/stocks view."""
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
                    global _news_items
                    _news_items = []
                threading.Thread(target=fetch_news_bg,   daemon=True).start()
                threading.Thread(target=lambda: fetch_stocks_bg(load_stock_watchlist()), daemon=True).start()
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
            threading.Thread(target=fetch_news_bg, daemon=True).start()
        else:
            threading.Thread(target=lambda: fetch_stocks_bg(load_stock_watchlist()), daemon=True).start()
        return

    if NSS.tab == 0:  # ── news tab ──────────────────────────────────────────
        if k in (ord('j'), curses.KEY_DOWN):
            NSS.scroll += 3
        elif k in (ord('k'), curses.KEY_UP):
            NSS.scroll = max(0, NSS.scroll - 3)

    elif NSS.tab == 1:  # ── stocks tab ────────────────────────────────────────
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
                        NSS.msg      = f"Added {sym} — fetching price…"
                        NSS.msg_time = time.time()
                    else:
                        NSS.msg      = f"{sym} is already in your watchlist"
                        NSS.msg_time = time.time()
            elif 32 <= k <= 126:
                if len(NSS.stock_buf) < 10:
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
            elif k == ord('d') and wl:
                idx = max(0, min(NSS.stock_cur, n - 1))
                removed = wl.pop(idx)
                save_stock_watchlist(wl)
                NSS.stock_cur = max(0, min(idx, len(wl) - 1))
                NSS.msg       = f"Removed {removed}"
                NSS.msg_time  = time.time()
            elif k == ord('D'):
                # Reset to country defaults
                code    = get_user_country() or "GLOBAL"
                info    = COUNTRY_DB.get(code, COUNTRY_DB["GLOBAL"])
                defaults = info["stocks"][:]
                save_stock_watchlist(defaults)
                NSS.stock_cur = 0
                threading.Thread(target=lambda: fetch_stocks_bg(defaults), daemon=True).start()
                NSS.msg      = f"Reset to {info['name']} defaults"
                NSS.msg_time = time.time()


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD — inject news/stocks widget
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
VIEW_FNS = [v_dashboard, v_clock, v_focus, v_neofetch, v_network,
            v_library, v_calendar, v_video, v_news_stocks]

def _in_text_input_mode():
    v = ST.view
    if ST.todo_add:                                              return True
    if v == 6 and (CS.add_mode or CS.ics_mode or CS.del_mode):  return True
    if v == 5 and LS.mode in ("add_url", "add_file"):            return True
    if v == 7 and VS.mode in ("add_url", "add_file"):            return True
    if v == 8 and NSS.stock_input:                               return True
    if v == 8 and NSS.country_mode:                              return True
    if v == 8 and not get_user_country():                        return True  # first-run picker
    return False


def main(stdscr):
    os.environ["ESCDELAY"] = "0"

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)
    stdscr.keypad(True)
    init_colors()

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
        VIEW_FNS[ST.view](stdscr, W, H)
        draw_navbar(stdscr, W, H)
        stdscr.refresh()

        in_text = _in_text_input_mode()
        max_keys = 256 if in_text else 8
        for _ in range(max_keys):
            k = stdscr.getch()
            if k == -1:
                break
            if k == ord('q') and not in_text:
                AUDIO._kill()
                save_todos(ST.todos)
                return
            handle_key(k)
            in_text = _in_text_input_mode()


if __name__ == "__main__":
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