import subprocess
import pyttsx3
import re
from stt import record_and_transcribe
from oll import ask_ollama
from dispacth import execute

def speak(text: str):
    """
    Speaks using female voice (Microsoft Zira).
    Initializes and cleans up per-invocation to avoid pyttsx3 event-loop freeze on Windows.
    """
    print(f"\nBulma: {text}")
    spoken = False

    # 1. Try pyttsx3 with female voice
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for v in voices:
            name = (v.name or "").lower()
            if "zira" in name or "female" in name:
                engine.setProperty('voice', v.id)
                break
        engine.setProperty('rate', 175)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        del engine
        spoken = True
    except Exception:
        spoken = False

    # 2. Guaranteed Windows native fallback if pyttsx3 has COM driver issues
    if not spoken:
        try:
            clean_text = text.replace('"', ' ').replace("'", " ")
            cmd = f'powershell -NoProfile -Command "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female); $s.Speak(\'{clean_text}\')"'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def clean_transcript(text: str) -> str:
    """
    Strips noise, punctuation, and Whisper artifacts like [Music] or '...'.
    Returns empty string if no meaningful human speech was detected.
    """
    if not text:
        return ""
    # Strip bracketed hallucinations e.g. [Music], [Applause], (laughter)
    cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    # Strip all punctuation and dots
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return cleaned.strip()

def is_wake_command(text: str) -> bool:
    clean = text.lower().strip()
    wake_phrases = ["wake up", "wake up bulma", "hey bulma", "bulma wake up", "wake", "bulma","arise"]
    return any(p in clean for p in wake_phrases)

def is_exit_command(text: str) -> bool:
    clean = text.lower().strip()
    exit_phrases = ["close","i dont want you","exit", "quit", "close bulma", "stop listening", "goodbye bulma", "bye bulma"]
    return any(p in clean for p in exit_phrases)

def main():
    print("=" * 50)
    print("       BULMA VOICE ASSISTANT (FEMALE VOICE)       ")
    print("  Status: ACTIVE                                  ")
    print("  - If you stay silent, Bulma will go to sleep.   ")
    print("  - Say 'Arise' to activate her again.    ")
    print("  - Say 'exit' or press Ctrl+C to stop.           ")
    print("=" * 50 + "\n")

    state = "ACTIVE"
    speak("Hello Abishek! I'm Bulma, ready for your commands.")

    while True:
        try:
            if state == "ACTIVE":
                print("\n[Bulma: Listening for commands...]")
                raw_transcript = record_and_transcribe(duration=4.0)
                clean_text = clean_transcript(raw_transcript)

                # Silence Detection: No actual speech detected
                if not clean_text:
                    speak("I didn't hear anything, going to sleep. Say 'Arise' whenever you need me!")
                    state = "SLEEP"
                    continue

                print(f"You said: {raw_transcript}")

                # Check for exit command
                if is_exit_command(clean_text):
                    speak("Goodbye Abishek! Have a great day!")
                    break

                # Parse intent
                intent_json = ask_ollama(raw_transcript)
                intent = intent_json.get("intent", "general_chat")
                reply = intent_json.get("reply", "Okay, doing that.")

                # Always speak the response FIRST
                speak(reply)

                # If user asked her to sleep
                if intent == "sleep":
                    state = "SLEEP"
                    continue

                if intent == "exit":
                    break

                # Execute the system action AFTER speaking
                execute(intent_json)

            elif state == "SLEEP":
                print("\n[Bulma is sleeping... Say 'wake up bulma' to activate, or 'exit' to quit]")
                raw_transcript = record_and_transcribe(duration=3.0)
                clean_text = clean_transcript(raw_transcript)

                # Ignore pure silence while sleeping
                if not clean_text:
                    continue

                print(f"[Heard while sleeping]: {raw_transcript}")

                if is_exit_command(clean_text):
                    speak("Goodbye Abishek!")
                    break

                if is_wake_command(clean_text):
                    speak("I'm awake, Abishek! What do you need?")
                    state = "ACTIVE"
                else:
                    print("Ignored. Say 'Arise' to wake me.")

        except KeyboardInterrupt:
            print("\nStopping Bulma. Goodbye Abishek!")
            break
        except Exception as e:
            print(f"An error occurred: {e}\n")

if __name__ == "__main__":
    main()
