import json
import time
import requests
import speech_recognition as sr
import pyttsx3
import re
import os
from dotenv import load_dotenv  # NEW

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")  # API key now read from .env

API_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/'
LLM_MODEL = "gemini-2.5-flash-preview-09-2025"
TTS_MODEL = "gemini-2.5-flash-preview-tts"
TTS_VOICE = "Kore"
MAX_RETRIES = 3

chat_history = []
system_instruction = "You are a friendly, conversational AI Voice Assistant. Keep answers concise and clear."

try:
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 150)
except Exception:
    tts_engine = None

r = sr.Recognizer()
microphone = sr.Microphone()

def speak(text):
    if tts_engine:
        print(f"\nAI: {text}")
        tts_engine.say(text)
        tts_engine.runAndWait()
    else:
        print(f"\nAI Response: {text}")

def fetch_with_retry(api_url, payload):
    headers = {'Content-Type': 'application/json'}

    if not API_KEY:
        raise Exception("API Key missing. Add it to .env file.")

    for attempt in range(MAX_RETRIES):
        try:
            full_url = f"{api_url}?key={API_KEY}"
            response = requests.post(full_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception:
            time.sleep(2 ** attempt)

def get_gemini_response(user_prompt):
    global chat_history

    chat_history.append({"role": "user", "parts": [{"text": user_prompt}]})

    api_url = API_BASE_URL + LLM_MODEL + ":generateContent"
    payload = {
        "contents": chat_history,
        "systemInstruction": {"parts": [{"text": system_instruction}]}
    }

    result = fetch_with_retry(api_url, payload)
    generated_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "Error")

    chat_history.append({"role": "model", "parts": [{"text": generated_text}]})
    return generated_text

def listen_and_process():
    with microphone as source:
        r.adjust_for_ambient_noise(source)
        print("\nListening... ")

        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
        except:
            speak("No speech detected.")
            return True

    try:
        user_prompt = r.recognize_google(audio)
        print("You:", user_prompt)

        if user_prompt.lower() in ["exit", "quit", "goodbye"]:
            speak("Goodbye!")
            return False

        response = get_gemini_response(user_prompt)
        speak(response)

    except:
        speak("Sorry, can you repeat again?")

    return True

def main():
    print("--- Audio Chatbot Started ---")
    speak("Hello! How can I help you?")

    running = True
    while running:
        running = listen_and_process()

if __name__ == "__main__":
    main()
