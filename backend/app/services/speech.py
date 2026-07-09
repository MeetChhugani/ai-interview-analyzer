import os
import re
from typing import Dict, Any, List

# Standard filler words to track (focused only on core vocalized ticks to prevent false positive penalties on conversational words)
FILLER_WORDS = ["um", "uh"]

# Mock transcripts as final fallback if libraries are missing
MOCK_TRANSCRIPTS = [
    "Um, so I believe I am a strong candidate for this role because, uh, I have extensive experience in Flutter and backend development.",
    "Actually, I've worked with FastAPI for about two years now, and, you know, it is extremely fast and scalable.",
    "Basically, my biggest strength is problem-solving. Uh, I literally love taking on difficult challenges and, like, breaking them down.",
    "I'm highly motivated to join your team. I have great communication skills and I am, um, excited to collaborate."
]
_mock_index = 0

def transcribe_audio(audio_file_path: str, duration_seconds: float) -> Dict[str, Any]:
    """
    Transcribes audio using:
    1. OpenAI Whisper API if OPENAI_API_KEY is present.
    2. Google Speech Recognition (free, keyless) via speech_recognition as a standard fallback.
    3. Fallback to mock data only if transcription tools are unavailable.
    """
    global _mock_index
    text = ""
    api_key = os.getenv("OPENAI_API_KEY")

    # 1. Attempt OpenAI Whisper
    if api_key:
        try:
            import httpx
            with open(audio_file_path, "rb") as f:
                files = {"file": f}
                headers = {"Authorization": f"Bearer {api_key}"}
                response = httpx.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data={"model": "whisper-1"},
                    timeout=30.0
                )
                if response.status_code == 200:
                    text = response.json().get("text", "")
                else:
                    print(f"OpenAI Whisper returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"OpenAI Whisper error: {str(e)}")
    
    # 2. Attempt Google Web Speech API (Free & Keyless) via SpeechRecognition
    if not text or text.startswith("Error") or text.startswith("Transcription error"):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(audio_file_path) as source:
                audio_data = r.record(source)
            # recognize_google is free, keyless, and uses Google's web service
            text = r.recognize_google(audio_data)
            print(f"Google Speech Recognition success: '{text}'")
        except sr.UnknownValueError:
            # Google Speech could not understand the audio (often silence or mumbling)
            print("Google Speech Recognition: Audio was unclear or silent.")
            text = ""
        except sr.RequestError as e:
            # Google Speech service failed or no internet
            print(f"Google Speech Recognition service error: {e}")
            text = ""
        except Exception as e:
            print(f"Google Speech Recognition general error: {str(e)}")
            text = ""

    # 3. Final fallback: If everything failed, or if it was empty, we can check if we should mock it.
    if not text:
        try:
            import speech_recognition as sr
            # If SpeechRecognition is installed and worked, but returned empty, it means silence.
            text = "No speech detected."
        except ImportError:
            text = MOCK_TRANSCRIPTS[_mock_index % len(MOCK_TRANSCRIPTS)]
            _mock_index += 1

    analysis = analyze_text(text, duration_seconds)
    audio_metrics = analyze_audio_file(audio_file_path)
    analysis["audio_metrics"] = audio_metrics
    return analysis

def analyze_text(text: str, duration_seconds: float) -> Dict[str, Any]:
    """
    Analyzes the transcribed text for WPM, filler words, and clarity.
    """
    if not text or text == "No speech detected.":
        return {
            "text": "No speech detected.",
            "word_count": 0,
            "wpm": 0,
            "filler_words_count": 0,
            "filler_words_breakdown": {},
            "filler_ratio": 0.0,
            "suggestions": ["No speech was detected. Please make sure your microphone is working and speak clearly."]
        }

    # Clean and split text into words
    words = re.findall(r'\b\w+\b', text.lower())
    word_count = len(words)
    
    # Calculate WPM
    duration_minutes = duration_seconds / 60.0 if duration_seconds > 0 else 0.1
    wpm = int(word_count / duration_minutes)

    # Count filler words
    filler_counts = {}
    total_fillers = 0
    for filler in FILLER_WORDS:
        # Match word boundaries for fillers (e.g. "so" matches "so", not "some")
        matches = len(re.findall(r'\b' + re.escape(filler) + r'\b', text.lower()))
        if matches > 0:
            filler_counts[filler] = matches
            total_fillers += matches

    # Calculate speech fluency metrics
    filler_ratio = total_fillers / word_count if word_count > 0 else 0
    
    # Generate speech-related suggestions
    suggestions = []
    if text == "No speech detected.":
        suggestions.append("No speech was detected. Please make sure your microphone is working and speak clearly.")
    else:
        if wpm < 100:
            suggestions.append("Your speaking speed is a bit slow. Try to speak more dynamically to keep the interviewer engaged.")
        elif wpm > 160:
            suggestions.append("You are speaking quite fast. Slow down slightly, pause between ideas, and take a breath.")
        else:
            suggestions.append("Excellent pacing! Your speaking speed is in the ideal range of 110-150 WPM.")

        if filler_ratio > 0.05:
            suggestions.append(f"You used {total_fillers} filler words. Try pausing briefly instead of saying '{list(filler_counts.keys())[0]}'.")
        else:
            suggestions.append("Great job keeping filler words to a minimum!")

    return {
        "text": text,
        "word_count": word_count,
        "wpm": wpm,
        "filler_words_count": total_fillers,
        "filler_words_breakdown": filler_counts,
        "filler_ratio": filler_ratio,
        "suggestions": suggestions
    }

def analyze_audio_file(file_path: str) -> Dict[str, float]:
    """
    Analyzes the WAV audio file to compute RMS energy volume, volume standard deviation (tone modulation),
    and zero-crossing rate variance.
    """
    import wave
    import struct
    import numpy as np

    default_metrics = {"rms": 0.05, "rms_std": 0.03, "zcr_var": 0.01}
    if not file_path or not os.path.exists(file_path):
        return default_metrics

    try:
        with wave.open(file_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            
            if n_frames == 0:
                return {"rms": 0.0, "rms_std": 0.0, "zcr_var": 0.0}
            
            data = wf.readframes(n_frames)
            
            if sampwidth == 1:
                fmt = f"{n_frames * n_channels}B"
                samples = np.array(struct.unpack(fmt, data), dtype=np.float32) - 128.0
            elif sampwidth == 2:
                fmt = f"<{n_frames * n_channels}h"
                samples = np.array(struct.unpack(fmt, data), dtype=np.float32)
            elif sampwidth == 4:
                fmt = f"<{n_frames * n_channels}i"
                samples = np.array(struct.unpack(fmt, data), dtype=np.float32)
            else:
                return default_metrics
            
            if n_channels > 1:
                samples = samples.reshape(-1, n_channels)
                samples = samples.mean(axis=1)
                
            if len(samples) == 0:
                return {"rms": 0.0, "rms_std": 0.0, "zcr_var": 0.0}
                
            max_val = np.max(np.abs(samples))
            if max_val > 0:
                samples = samples / max_val
            
            frame_size = int(framerate * 0.05)
            if frame_size == 0:
                frame_size = 1024
            
            rms_values = []
            zcrs = []
            for i in range(0, len(samples), frame_size):
                chunk = samples[i:i+frame_size]
                if len(chunk) > 0:
                    rms = np.sqrt(np.mean(chunk**2))
                    rms_values.append(rms)
                if len(chunk) > 1:
                    zcr = np.mean(np.abs(np.diff(np.sign(chunk))) > 0)
                    zcrs.append(zcr)
            
            rms_values = np.array(rms_values)
            zcrs = np.array(zcrs)
            
            avg_rms = float(np.mean(rms_values)) if len(rms_values) > 0 else 0.0
            std_rms = float(np.std(rms_values)) if len(rms_values) > 0 else 0.0
            var_zcr = float(np.var(zcrs)) if len(zcrs) > 0 else 0.0
            
            return {
                "rms": round(avg_rms, 4),
                "rms_std": round(std_rms, 4),
                "zcr_var": round(var_zcr, 4)
            }
    except Exception as e:
        print(f"Error analyzing WAV file: {e}")
        return default_metrics
