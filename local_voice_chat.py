import json
import time
import requests
import speech_recognition as sr
import pyttsx3
import re

# --- Configuration ---
# 1. IMPORTANT: Replace "AIzaSyDSuvU5Pl4M_D6lCiVIjJLCNT3oN0I5dgg" with your actual Google AI API key
API_KEY = "AIzaSyDSuvU5Pl4M_D6lCiVIjJLCNT3oN0I5dgg" 
API_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/'
LLM_MODEL = "gemini-2.5-flash-preview-09-2025"
TTS_MODEL = "gemini-2.5-flash-preview-tts"
TTS_VOICE = "Kore" # This is used for the LLM's system instruction, but pyttsx3 handles the actual voice
MAX_RETRIES = 3

# Global variable to maintain chat history for context
chat_history = []
system_instruction = "You are a friendly, conversational AI Voice Assistant. Keep your answers concise and clear, suitable for a spoken conversation. Use Google Search grounding for factual queries."

# --- Initialization ---
try:
    # Initialize pyttsx3 Text-to-Speech Engine
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 150)  # Speed of speech
except Exception as e:
    print(f"Error initializing pyttsx3: {e}. TTS functionality will be disabled.")
    tts_engine = None

# Initialize Speech Recognizer
r = sr.Recognizer()
# Use the default microphone
microphone = sr.Microphone()

def speak(text):
    """Uses pyttsx3 to speak the given text."""
    if tts_engine:
        print(f"\nAI Speaking: {text}")
        tts_engine.say(text)
        tts_engine.runAndWait()
    else:
        print(f"\n[TTS Disabled] AI Response: {text}")


def fetch_with_retry(api_url, payload):
    """Handles Gemini API calls with exponential backoff."""
    headers = {'Content-Type': 'application/json'}
    
    for attempt in range(MAX_RETRIES):
        try:
            # CORRECTED: Uses f"{api_url}?key={API_KEY}" for API key injection
            full_url = f"{api_url}?key={API_KEY}"
            response = requests.post(full_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                print(f"[API Warning] Rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                print(f"[API Warning] Request Error. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("API request failed after multiple retries.")


def get_gemini_response(user_prompt):
    """Generates text response using Gemini with history and grounding."""
    global chat_history

    if not API_KEY or API_KEY == "YOUR_API_KEY":
        raise Exception("API Key not set. Please update the API_KEY variable in the script.")
        
    # Append user message to history
    chat_history.append({"role": "user", "parts": [{"text": user_prompt}]})

    llm_payload = {
        "contents": chat_history,
        "tools": [{"google_search": {}}],  # Enable search grounding
        "systemInstruction": {"parts": [{"text": system_instruction}]},
    }
    
    api_url = API_BASE_URL + LLM_MODEL + ":generateContent"
    
    try:
        result = fetch_with_retry(api_url, llm_payload)
        candidate = result.get('candidates', [{}])[0]
        generated_text = candidate.get('content', {}).get('parts', [{}])[0].get('text', 'Sorry, I could not generate a response.')
        
        # Append model response to history for context
        chat_history.append({"role": "model", "parts": [{"text": generated_text}]})
        
        return generated_text

    except Exception as e:
        error_message = f"Gemini API Error: {e}"
        print(error_message)
        chat_history.append({"role": "model", "parts": [{"text": "I apologize, but I encountered a technical issue."}]})
        return "I apologize, but I encountered a technical issue while connecting to my brain."


def listen_and_process():
    """Listens for user speech, processes it, and speaks the response."""
    with microphone as source:
        r.adjust_for_ambient_noise(source)
        print("\n\n---------------------------------")
        print("Listening... Speak into the microphone.")
        
        try:
            # Listen for up to 5 seconds
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            print("No speech detected.")
            return

    try:
        print("Recognizing speech...")
        # Use Google's Speech Recognition for transcription
        user_prompt = r.recognize_google(audio)
        print(f"You said: {user_prompt}")
        
        if user_prompt.lower() in ["exit", "quit", "goodbye"]:
            speak("Goodbye! Have a great day.")
            return False

        # 1. Get Gemini text response
        response_text = get_gemini_response(user_prompt)
        
        # 2. Speak the response
        speak(response_text)

    except sr.UnknownValueError:
        print("Could not understand audio.")
        speak("Sorry, I didn't catch that. Could you please repeat yourself?")
    except sr.RequestError as e:
        print(f"Speech recognition service error; {e}")
        speak("I'm having trouble connecting to the speech service. Please check your internet connection.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        speak("I've run into an unexpected problem. Let's try that again.")
        
    return True

# --- Main Chat Loop ---
def main():
    """Main function to start the conversational loop."""
    print("--- Gemini Local Voice Chat Initialized ---")
    speak("Hello! I am your AI voice assistant. How can I help you today?")

    running = True
    while running:
        if not listen_and_process():
            running = False

if __name__ == "__main__":
    main()