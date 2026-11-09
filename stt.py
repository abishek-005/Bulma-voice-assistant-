import sounddevice as sd
from scipy.io import wavfile
from faster_whisper import WhisperModel
from dotenv import load_dotenv
import numpy as np

# Authenticate with .env token to silence HF Hub warnings
load_dotenv()

# Use CPU int8 — optimized with AVX2, faster & avoids MX230 2GB VRAM limits/crashes
print("Loading Whisper multilingual model (small)...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Whisper model ready.")

def record_and_transcribe(duration=4.0):
    fs = 16000
    print("Listening...")
    rec = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()

    # Fast silence / noise gate:
    # Room ambient noise on laptop mics is typically 0.02 - 0.05.
    # Normal human speech is typically 0.15 - 0.80.
    max_amp = float(np.max(np.abs(rec)))
    rms = float(np.sqrt(np.mean(rec**2)))
    
    if max_amp < 0.08 and rms < 0.015:
        # User was completely silent; skip Whisper processing
        return ""

    # Save output.wav for reference
    wavfile.write("output.wav", fs, rec)

    # Transcribe directly from audio array
    segments, _ = model.transcribe(rec.flatten(), beam_size=3)
    transcript = " ".join([segment.text for segment in segments]).strip()
    return transcript
