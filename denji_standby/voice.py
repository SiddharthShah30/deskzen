"""
TARS Voice Module - Enhanced Speech Recognition & Text-to-Speech
Handles voice input/output with proper error handling and threading
"""

import threading
import io
import os
import subprocess
import wave
import time
from typing import Callable, Optional, Any
import importlib

# Initialize flags globally
HAS_TTS = False
HAS_SR = False

# Lazy load dependencies
pyttsx3: Any = None
sr: Any = None
sd: Any = None
np: Any = None

try:
    pyttsx3 = importlib.import_module("pyttsx3")
    HAS_TTS = True
except Exception:
    HAS_TTS = False

try:
    sr = importlib.import_module("speech_recognition")
    HAS_SR = True
except Exception:
    HAS_SR = False

try:
    sd = importlib.import_module("sounddevice")
    np = importlib.import_module("numpy")
    HAS_SD = True
except Exception:
    sd = None
    np = None
    HAS_SD = False

try:
    win32com_client = importlib.import_module("win32com.client")
    HAS_SAPI = True
except Exception:
    win32com_client = None
    HAS_SAPI = False


class VoiceEngine:
    """TARS-inspired voice system with recognition and synthesis"""
    
    def __init__(self):
        self.tts_engine = None
        self.sapi_engine = None
        self.recognizer = None
        self.tts_lock = threading.Lock()
        self.sr_lock = threading.Lock()
        self.is_listening = False
        self.last_recognized_text = ""
        self.tts_status = "Ready" if HAS_TTS else "Offline"
        self.sr_status = "Ready" if HAS_SR else "Offline"
        self._init_engines()
    
    def _init_engines(self):
        """Initialize TTS and SR engines"""
        global HAS_TTS, HAS_SR
        
        if HAS_TTS:
            try:
                with self.tts_lock:
                    self.tts_engine = pyttsx3.init()
                    self.tts_engine.setProperty('rate', 150)  # Slower for clarity
            except Exception as e:
                print(f"TTS init error: {e}")
                self.tts_status = "Error"
                HAS_TTS = False
        
        if HAS_SR:
            try:
                with self.sr_lock:
                    self.recognizer = sr.Recognizer()
                    # Improve recognition sensitivity
                    self.recognizer.energy_threshold = 4000
            except Exception as e:
                print(f"SR init error: {e}")
                self.sr_status = "Error"
                HAS_SR = False

        if not HAS_SR and HAS_SD:
            self.sr_status = "Ready"
    
    def speak(self, text: str, wait: bool = False) -> threading.Thread:
        """
        Speak text using TTS
        
        Args:
            text: Text to speak
            wait: If True, block until speech completes
        
        Returns:
            Thread object (will be completed if wait=True)
        """
        def _sapi_fallback():
            if os.name != "nt":
                return
            try:
                if HAS_SAPI and win32com_client is not None:
                    speaker = self.sapi_engine or win32com_client.Dispatch("SAPI.SpVoice")
                    self.sapi_engine = speaker
                    self.tts_status = "Speaking"
                    speaker.Speak(text)
                    self.tts_status = "Ready"
                    return

                safe_text = text.replace("'", "''")
                ps_cmd = (
                    "Add-Type -AssemblyName System.Speech; "
                    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    f"$s.Speak('{safe_text}')"
                )
                self.tts_status = "Speaking"
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True,
                    timeout=20,
                    check=False,
                )
                self.tts_status = "Ready"
            except Exception as e:
                print(f"SAPI fallback error: {e}")
                self.tts_status = "Error"

        def _speak_worker():
            if HAS_TTS and self.tts_engine:
                try:
                    with self.tts_lock:
                        self.tts_status = "Speaking"
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
                        self.tts_status = "Ready"
                        return
                except Exception as e:
                    print(f"TTS error: {e}")
                    self.tts_status = "Error"
            _sapi_fallback()
        
        thread = threading.Thread(target=_speak_worker, daemon=True)
        thread.start()
        
        if wait:
            thread.join()
        
        return thread
    
    def listen(self, timeout: float = 5.0, 
              on_audio_received: Optional[Callable] = None) -> str:
        """
        Listen for audio input and convert to text
        
        Args:
            timeout: How long to listen for (seconds)
            on_audio_received: Callback when audio is detected
        
        Returns:
            Recognized text, or empty string on failure
        """
        if HAS_SD:
            try:
                self.is_listening = True
                self.sr_status = "Listening"
                if on_audio_received:
                    on_audio_received("Listening...")

                sample_rate = 16000
                channels = 1
                frames = int(sample_rate * max(1.0, timeout))
                audio = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype="float32")
                sd.wait()

                if on_audio_received:
                    on_audio_received("Processing...")

                audio_array = audio[:, 0]
                audio_int16 = (audio_array * 32767).clip(-32768, 32767).astype(np.int16)
                raw_bytes = audio_int16.tobytes()

                if HAS_SR and sr is not None:
                    recognizer = self.recognizer or sr.Recognizer()
                    recognizer.energy_threshold = 4000
                    if self.recognizer is None:
                        self.recognizer = recognizer
                    data = sr.AudioData(raw_bytes, sample_rate, 2)
                    try:
                        text = recognizer.recognize_google(data)
                        self.last_recognized_text = text
                        self.sr_status = "Ready"
                        return text
                    except sr.UnknownValueError:
                        self.sr_status = "Ready"
                        return ""
                    except sr.RequestError as e:
                        print(f"API error: {e}")
                        self.sr_status = "Error"
                        return ""

                self.sr_status = "Offline"
                return ""
            except Exception as e:
                print(f"Listen error: {e}")
                self.sr_status = "Error"
                return ""
            finally:
                self.is_listening = False

        if not HAS_SR or not self.recognizer:
            return ""
        
        try:
            with self.sr_lock:
                self.is_listening = True
                self.sr_status = "Listening"
                
                # Get microphone
                with sr.Microphone() as source:
                    # Adjust to ambient noise
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    
                    # Listen
                    if on_audio_received:
                        on_audio_received("Listening...")
                    
                    audio = self.recognizer.listen(source, timeout=timeout)
                    
                    if on_audio_received:
                        on_audio_received("Processing...")
                    
                    # Recognize
                    try:
                        text = self.recognizer.recognize_google(audio)
                        self.last_recognized_text = text
                        self.sr_status = "Ready"
                        return text
                    except sr.UnknownValueError:
                        self.sr_status = "Ready"
                        return ""
                    except sr.RequestError as e:
                        print(f"API error: {e}")
                        self.sr_status = "Error"
                        return ""
        except sr.RequestError:
            self.sr_status = "Offline"
            return ""
        except Exception as e:
            print(f"Listen error: {e}")
            self.sr_status = "Error"
            return ""
        finally:
            self.is_listening = False
    
    def listen_async(self, timeout: float = 5.0,
                    on_complete: Optional[Callable] = None) -> threading.Thread:
        """
        Listen in background thread
        
        Args:
            timeout: How long to listen for
            on_complete: Callback(text) when listening completes
        
        Returns:
            Thread object
        """
        def _listen_worker():
            text = self.listen(timeout, on_audio_received=None)
            if on_complete:
                on_complete(text)
        
        thread = threading.Thread(target=_listen_worker, daemon=True)
        thread.start()
        return thread
    
    def stop_listening(self):
        """Stop active listening"""
        self.is_listening = False
    
    def set_voice_speed(self, rate: int = 150):
        """Set speech rate (words per minute)"""
        if HAS_TTS and self.tts_engine:
            try:
                with self.tts_lock:
                    self.tts_engine.setProperty('rate', rate)
            except Exception:
                pass
    
    def set_voice_volume(self, volume: float = 1.0):
        """Set speech volume (0.0 to 1.0)"""
        if HAS_TTS and self.tts_engine:
            try:
                with self.tts_lock:
                    self.tts_engine.setProperty('volume', max(0, min(1, volume)))
            except Exception:
                pass
    
    def get_status(self) -> dict:
        """Get voice engine status"""
        return {
            "tts": self.tts_status,
            "sr": self.sr_status,
            "listening": self.is_listening,
            "last_text": self.last_recognized_text
        }


# Global voice engine instance
_voice_engine = None

def get_voice_engine() -> VoiceEngine:
    """Get or create the global voice engine"""
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine()
    return _voice_engine
