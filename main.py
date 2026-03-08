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
    """Brown noise: integrated white noise → deep bass rumble."""
    out  = _array.array('h')
    last = state.get('b', 0.0)
    for _ in range(n):
        white = random.gauss(0, 1.0)
        last  = last * 0.998 + white * 0.002   # leaky integrator
        v = max(-32767, min(32767, int(last * 26000)))
        out.append(v)
    state['b'] = last
    return out.tobytes()

def _gen_pink(n, state):
    """Pink noise (1/f): Voss-McCartney algorithm."""
    b = state.get('b', [0.0]*7)
    out = _array.array('h')
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
        v = max(-32767, min(32767, int(pink * 28000)))
        out.append(v)
    state['b'] = b
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
        self._play_gen  = 0          # generation counter — kill stale threads
        self._proc      = None       # subprocess for file playback
        self.status_msg = ""
        self._backend   = self._detect()
        # spectrum smoothing state (per track type)
        self._spec_t    = 0.0

    def _detect(self):
        for cmd in ("ffplay","afplay","mpv","mplayer"):
            if shutil.which(cmd): return cmd
        if platform.system() == "Windows":
            try: import winsound; return "winsound"
            except ImportError: pass
            if shutil.which("powershell"): return "powershell"
        if shutil.which("aplay"): return "aplay"
        return None

    # ── spectrum (noise-reactive per genre) ──────────────────────────────
    def get_spectrum(self, n=32):
        if not self.playing:
            return [0.0]*n
        trk   = self.current
        genre = trk.get("genre","")
        t     = self.elapsed
        out   = []
        for b in range(n):
            frac = b / max(1, n-1)   # 0=bass, 1=treble
            if genre == "brown":
                # heavy bass, rolls off steeply
                v = math.exp(-frac * 5.0) * (0.7 + 0.3*math.sin(t*1.3+b*0.5))
            elif genre == "pink":
                # 1/f: slopes gently
                v = (1.0-frac*0.7) * (0.5 + 0.4*math.sin(t*0.9+b*0.3))
            elif genre == "white":
                # flat
                v = 0.5 + 0.4*math.sin(t*2.1*frac+b)
            elif genre == "rain":
                # mid-heavy with occasional high spikes (droplets)
                base = math.exp(-((frac-0.35)**2)/0.08)
                drop = 0.6*math.exp(-((frac-0.8)**2)/0.02)*abs(math.sin(t*7.3))
                v = base*0.6 + drop
            elif genre == "space":
                # concentrated in bass/sub with slow movement
                v = math.exp(-frac*8)*(0.8+0.2*math.sin(t*0.3+frac*3))
                v += 0.15*math.exp(-((frac-0.1)**2)/0.01)*abs(math.sin(t*0.7))
            else:
                # user track: generic reactive
                bpm  = trk.get("bpm",90)
                beat = 60.0/bpm
                kick = math.exp(-(t%beat)/beat*8)*0.8
                v = (0.4+0.4*kick)*math.exp(-frac*3)
                v += 0.2*abs(math.sin(t*frac*2+b*0.5))
            noise = random.uniform(-0.05, 0.05)
            out.append(min(1.0, max(0.0, v + noise)))
        return out

    # ── playback ──────────────────────────────────────────────────────────
    def _new_gen(self):
        """Increment generation; old threads check this and exit."""
        with self._lock:
            self._play_gen += 1
            return self._play_gen

    def _spawn(self):
        """Start a new playback thread for current track."""
        with self._lock:
            gen = self._play_gen
            idx = self.track_idx
            start = self.elapsed
        threading.Thread(
            target=self._play_thread,
            args=(gen, idx, start),
            daemon=True
        ).start()

    def _alive(self, gen):
        """Return True if this generation is still current."""
        with self._lock:
            return gen == self._play_gen

    def _play_thread(self, gen, idx, start_sec):
        trk = self.library[idx] if idx < len(self.library) else BUILTIN_TRACKS[0]
        if trk.get("source") == "builtin":
            self._stream_builtin(gen, trk, start_sec)
        else:
            self._play_file(gen, trk["source"], start_sec, trk.get("duration",0))

        # natural end (not killed) → advance
        if self._alive(gen):
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

    def _stream_builtin(self, gen, trk, start_sec):
        """Stream noise into ffplay pipe, or fall back to temp-WAV for Windows."""
        genre = trk.get("genre", "brown")
        genfn = _GENERATORS.get(genre, _gen_brown)
        state = {}

        # Windows: winsound/powershell can't stream raw PCM → write temp WAV
        if self._backend in ("winsound","powershell") or not shutil.which("ffplay"):
            self._stream_builtin_file(gen, genfn, state, start_sec)
            return

        # Skip forward in generator state without playing
        skip_chunks = int(start_sec * SR / self.CHUNK)
        for _ in range(skip_chunks):
            if not self._alive(gen): return
            genfn(self.CHUNK, state)

        proc = self._open_pipe()
        if proc is None:
            # No pipe backend — try file fallback
            self._stream_builtin_file(gen, genfn, state, start_sec)
            return

        with self._lock:
            self._proc = proc

        try:
            while self._alive(gen):
                data = genfn(self.CHUNK, state)
                try:
                    proc.stdin.write(data)
                    proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    break
                time.sleep(self.CHUNK / SR * 0.6)  # pace to ~60% of realtime
        finally:
            try: proc.stdin.close()
            except: pass
            try: proc.wait(timeout=2)
            except: proc.terminate()
            with self._lock:
                if self._proc is proc:
                    self._proc = None

    def _stream_builtin_file(self, gen, genfn, state, start_sec):
        """Fallback: generate 60s WAV, play it, loop while alive."""
        import tempfile, wave as wv
        SEG = 60  # seconds per segment
        while self._alive(gen):
            n = SEG * SR
            raw = genfn(n, state)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                with wv.open(tmp.name,"wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
                    wf.writeframes(raw)
                b = self._backend
                if b == "afplay":
                    cmd = ["afplay", tmp.name]
                elif b == "winsound":
                    import winsound
                    winsound.PlaySound(tmp.name,
                                      winsound.SND_FILENAME|winsound.SND_ASYNC)
                    t0 = time.time()
                    while time.time()-t0 < SEG:
                        if not self._alive(gen):
                            winsound.PlaySound(None, winsound.SND_PURGE)
                            return
                        time.sleep(0.05)
                    continue
                elif b == "powershell":
                    script = (f"$p=(New-Object Media.SoundPlayer '{tmp.name}');"
                              f"$p.PlaySync()")
                    cmd = ["powershell","-NoProfile","-Command",script]
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
            finally:
                try: os.unlink(tmp.name)
                except: pass

    def _open_pipe(self):
        """Open ffplay/aplay subprocess ready to receive raw PCM on stdin."""
        try:
            if self._backend in ("ffplay",):
                cmd = ["ffplay","-f","s16le","-ar",str(SR),"-ac","1",
                       "-nodisp","-loglevel","quiet",
                       "-"]
            elif self._backend == "aplay":
                cmd = ["aplay","-f","S16_LE","-r",str(SR),"-c","1","--quiet"]
            elif self._backend == "afplay":
                # afplay cannot read raw PCM from stdin — use ffplay if available
                if shutil.which("ffplay"):
                    cmd = ["ffplay","-f","s16le","-ar",str(SR),"-ac","1",
                           "-nodisp","-loglevel","quiet","-"]
                else:
                    return None
            else:
                return None

            return subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return None

    def _play_file(self, gen, path, start_sec, duration):
        """Play a local file via the detected backend."""
        try:
            ss = str(int(start_sec))
            b  = self._backend
            if b == "ffplay":
                cmd = ["ffplay","-nodisp","-loglevel","quiet","-ss",ss, path]
            elif b == "afplay":
                cmd = ["afplay", path]
                # afplay has no -ss; if start_sec>5 just play from beginning
            elif b == "mpv":
                cmd = ["mpv","--no-video","--really-quiet",f"--start={ss}", path]
            elif b == "mplayer":
                cmd = ["mplayer","-nogui","-really-quiet","-ss",ss, path]
            elif b == "aplay":
                # aplay = raw only, redirect through ffplay
                cmd = ["ffplay","-nodisp","-loglevel","quiet","-ss",ss, path]
            elif b == "winsound":
                self._play_win_file(gen, path, duration - start_sec); return
            elif b == "powershell":
                self._play_ps_file(gen, path, duration - start_sec); return
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

    def _play_win_file(self, gen, path, remaining):
        import winsound
        # winsound only handles WAV; if mp3, convert to temp wav first via ffmpeg
        import tempfile, wave as wv
        if path.lower().endswith(".wav"):
            wav_path = path
            cleanup  = False
        else:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wav_path = tmp.name; tmp.close(); cleanup = True
            try:
                subprocess.run(["ffmpeg","-y","-i",path,"-ar","44100",
                                "-ac","1","-f","wav", wav_path],
                               capture_output=True, timeout=30)
            except Exception:
                if cleanup:
                    try: os.unlink(wav_path)
                    except: pass
                return
        try:
            winsound.PlaySound(wav_path, winsound.SND_FILENAME|winsound.SND_ASYNC)
            t0 = time.time()
            while time.time()-t0 < remaining:
                if not self._alive(gen):
                    winsound.PlaySound(None, winsound.SND_PURGE); break
                time.sleep(0.05)
        except Exception:
            pass
        finally:
            if cleanup:
                try: os.unlink(wav_path)
                except: pass

    def _play_ps_file(self, gen, path, remaining):
        try:
            script = (f"Add-Type -AssemblyName presentationCore;"
                      f"$m=[System.Windows.Media.MediaPlayer]::new();"
                      f"$m.Open([Uri]::new('{path}'));$m.Play();"
                      f"Start-Sleep {max(1,int(remaining))}")
            proc = subprocess.Popen(
                ["powershell","-NoProfile","-Command",script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with self._lock: self._proc = proc
            while proc.poll() is None:
                if not self._alive(gen): proc.terminate(); break
                time.sleep(0.05)
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
VIEWS = ["DASHBOARD","CLOCK + MUSIC","FOCUS","NEOFETCH","NETWORK","LIBRARY"]

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
        # events
        self.events = [(16,0,"Dev Standup"),(18,30,"Team Retro"),(21,0,"Gym session")]
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
    now = datetime.datetime.now()
    for h,m,name in ST.events:
        ev = now.replace(hour=h,minute=m,second=0,microsecond=0)
        if ev > now:
            diff = int((ev-now).total_seconds())
            hh,rem = divmod(diff,3600); mm=rem//60
            return f"{h:02d}:{m:02d}  {name}", f"in {hh}h {mm:02d}m"
    return "No more events", "tomorrow →"

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
        "TODOS  [a]=add  [d]=del  [j/k]=nav  [SPC]=check")
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
        " [p] pomo  [r] reset  [a] add todo  [d] del  [←→/TAB] views  [q] quit ",
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
    # loading indicator if track not ready
    if AUDIO.track_idx not in AUDIO._pcm_cache:
        put(win, my+1, mx+2, "⠋ Synthesizing track…", cp(P_AMBER))
    else:
        put(win, my+1, mx+2, td["name"][:mw-4],       cp(P_HI, bold=True))
    put(win, my+2, mx+2, f"by {td['artist']}"[:mw-4], cp(P_DIM))

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
    box(win,1,rx,14,rw,"CONNECTED DEVICES")
    devices=[("AirPods Pro","BT",78,True),("Magic Keyboard","BT",42,True),
             ("Magic Mouse","BT",11,True),("iPhone 15 Pro","BT",91,False),
             ("Ext. Display","USB",None,True),("USB-C Hub","USB",None,True)]
    for i,(name,dtype,bat,conn) in enumerate(devices):
        dy=2+i*2
        if 1+dy+1>=15: break
        cs="● CONN" if conn else "○ DISC"
        cc=P_GREEN if conn else P_DIM
        put(win,1+dy,rx+2,name[:rw-12],cp(P_MID))
        put(win,1+dy,rx+rw-6,f"[{dtype}]",cp(P_DIM))
        put(win,2+dy,rx+2,cs,cp(cc))
        if bat is not None:
            bc=P_GREEN if bat>40 else (P_AMBER if bat>15 else P_RED)
            put(win,2+dy,rx+rw-7,f"{bat:3d}%",cp(bc))

    bat=sd["bat_pct"]; plug=sd["bat_plug"]
    bc=P_GREEN if bat>40 else (P_AMBER if bat>15 else P_RED)
    box(win,16,0,7,W-1,"BATTERY & POWER")
    put(win,17,2,f"{'+ CHARGING' if plug else '  ON BATTERY'}  {bat}%",cp(bc,bold=True))
    hbar(win,18,2,W-5,bat,bc)
    put(win,19,2,"charging" if plug else f"~{int(bat*1.5)} min remaining",cp(P_DIM))
    put(win,20,2,f"cpu {sd['cpu']:.0f}%  mem {sd['mem_pct']:.0f}%  disk {sd['disk_pct']:.0f}%",cp(P_DIM))

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

    # ── GLOBAL MUSIC CONTROLS (all views) ────────────────────────────────
    if k == ord(' '):  AUDIO.toggle_play(); return
    if k == ord('z'):  AUDIO.prev_track();  return
    if k == ord('x'):  AUDIO.next_track();  return
    if k == ord('s') and v != 2:  AUDIO.shuffle = not AUDIO.shuffle; return
    if k == ord('R'):  AUDIO.repeat = not AUDIO.repeat; return

    # ── VIEW-SPECIFIC ─────────────────────────────────────────────────────
    if v == 0:  # dashboard
        if k in (curses.KEY_UP,   ord('k')): ST.todo_cur = max(0, ST.todo_cur - 1)
        elif k in (curses.KEY_DOWN, ord('j')): ST.todo_cur = min(len(ST.todos)-1, ST.todo_cur+1)
        elif k == 32 and ST.todos:
            ST.todos[ST.todo_cur][0] ^= True
            save_todos(ST.todos)
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

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
VIEW_FNS=[v_dashboard,v_clock,v_focus,v_neofetch,v_network,v_library]

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
    backend_name = AUDIO._backend or "none (no audio)"
    print(f"""
  Terminal StandBy v3
  ───────────────────────────────────────────────
  Audio backend : {backend_name}
  Platform      : {platform.system()} {platform.release()}
  psutil        : {'yes' if HAS_PSUTIL else 'no — install for real stats'}
  ───────────────────────────────────────────────
  First launch synthesizes tracks in background.
  You'll hear music within a few seconds of start.

  Controls:  ←/→ or h/l  switch views
             SPACE        play / pause
             z / x        prev / next track
             q            quit
  ───────────────────────────────────────────────
  Starting…
""")
    time.sleep(0.5)
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        AUDIO._kill()
        save_todos(ST.todos)
    print("\n  Goodbye! Todos saved.  [*]\n")