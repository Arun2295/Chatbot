# -*- coding: utf-8 -*-
import json
import random
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# --- Configuration ---
DEFAULT_TARGET_LANGUAGE = "es"  # Spanish
AVAILABLE_LANGUAGES = ["es", "fr", "de", "it"]  # Add more as needed
TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY")  # Get API key from .env file
TRANSLATION_API_BASE_URL = "https://api.mymemory.translated.net/get"  # Example API

# --- Language Learning Content (Simple Dictionary) ---
LANGUAGE_DATA = {
    "es": {
        "hello": "hola",
        "goodbye": "adiós",
        "thank you": "gracias",
        "water": "agua",
        "food": "comida",
        "yes": "sí",
        "no": "no",
    },
    "fr": {
        "hello": "bonjour",
        "goodbye": "au revoir",
        "thank you": "merci",
        "water": "eau",
        "food": "nourriture",
        "yes": "oui",
        "no": "non",
    },
    "de": {
        "hello": "hallo",
        "goodbye": "auf wiedersehen",
        "thank you": "danke",
        "water": "wasser",
        "food": "essen",
        "yes": "ja",
        "no": "nein",
    },
    "it": {
        "hello": "ciao",
        "goodbye": "arrivederci",
        "thank you": "grazie",
        "water": "acqua",
        "food": "cibo",
        "yes": "sì",
        "no": "no",
    },
    "en": {
        "hello": "hello",
        "goodbye": "goodbye",
        "thank you": "thank you",
        "water": "water",
        "food": "food",
        "yes": "yes",
        "no": "no",
    },
}

# --- User Progress (In-memory - Replace with a database for persistence) ---
user_progress = {}  # {user_id: {"target_language": "es", "learned_words": {"hello": True, ...}}}

# --- Helper Functions ---
def get_translation(text, target_language):
    if not TRANSLATION_API_KEY:
        return f"Error: Translation API key not configured. Returning default translation for '{text}' in '{target_language}' (if available)."
    try:
        params = {
            "q": text,
            "langpair": f"en|{target_language}",
            "key": TRANSLATION_API_KEY,
            "de": "your_email@example.com",  # Optional: For API usage statistics
        }
        response = requests.get(TRANSLATION_API_BASE_URL, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        if data and data.get("responseData") and data.get("responseData").get("translatedText"):
            return data["responseData"]["translatedText"]
        else:
            return f"Error: Could not translate '{text}' to '{target_language}' using the API."
    except requests.exceptions.RequestException as e:
        return f"Error: Translation API request failed: {e}"
    except json.JSONDecodeError:
        return "Error: Could not decode JSON response from translation API."

def get_random_word(target_language, learned_words=None):
    if target_language in LANGUAGE_DATA:
        available_words = [
            word
            for word in LANGUAGE_DATA["en"].keys()
            if word in LANGUAGE_DATA["en"]
            and (learned_words is None or word not in learned_words)
        ]
        if available_words:
            return random.choice(available_words)
        else:
            return "Congratulations! You've learned all the words in this category."
    else:
        return f"Language '{target_language}' not supported yet."

def check_translation(word, user_translation, target_language):
    if target_language in LANGUAGE_DATA and word in LANGUAGE_DATA["en"]:
        correct_translation = LANGUAGE_DATA[target_language].get(
            word, "Translation not found"
        )
        if user_translation.lower().strip() == correct_translation.lower().strip():
            return True, correct_translation
        else:
            return False, correct_translation
    else:
        return False, "Language or word data not found."

def update_user_progress(user_id, word, learned=True):
    if user_id not in user_progress:
        user_progress[user_id] = {
            "target_language": DEFAULT_TARGET_LANGUAGE,
            "learned_words": {},
        }
    if learned:
        user_progress[user_id]["learned_words"][word] = True
    elif word in user_progress[user_id]["learned_words"]:
        del user_progress[user_id]["learned_words"][word]

def get_user_language(user_id):
    return user_progress.get(user_id, {}).get("target_language", DEFAULT_TARGET_LANGUAGE)

def set_user_language(user_id, language):
    if language in AVAILABLE_LANGUAGES:
        if user_id not in user_progress:
            user_progress[user_id] = {"target_language": language, "learned_words": {}}
        else:
            user_progress[user_id]["target_language"] = language
        return f"Target language set to {language}."
    else:
        return f"Language '{language}' not supported. Available languages: {', '.join(AVAILABLE_LANGUAGES)}."

# --- API Endpoints ---
@app.route("/start_learning", methods=["POST"])
def start_learning():
    data = request.get_json()
    user_id = data.get("user_id")
    language = data.get("language")

    if not user_id:
        return jsonify({"error": "Missing 'user_id'."}), 400

    if language:
        response = set_user_language(user_id, language)
        return jsonify({"response": response})
    else:
        return jsonify(
            {
                "response": f"Welcome! Your default learning language is {get_user_language(user_id)}. You can specify a language in the request."
            }
        )

@app.route("/get_word", methods=["GET"])
def get_learning_word():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing 'user_id' in query parameters."}), 400

    target_language = get_user_language(user_id)
    learned_words = user_progress.get(user_id, {}).get("learned_words", {})
    word_to_learn = get_random_word(target_language, learned_words)
    return jsonify(
        {"word": word_to_learn, "translation_hint": get_translation(word_to_learn, target_language)}
    )

@app.route("/check_answer", methods=["POST"])
def check_answer():
    data = request.get_json()
    user_id = data.get("user_id")
    word = data.get("word")
    user_translation = data.get("translation")

    if not user_id or not word or not user_translation:
        return jsonify(
            {"error": "Missing 'user_id', 'word', or 'translation' in request body."}
        ), 400

    target_language = get_user_language(user_id)
    is_correct, correct_translation = check_translation(
        word, user_translation, target_language
    )

    if is_correct:
        update_user_progress(user_id, word)
        return jsonify({"result": "Correct!", "correct_translation": correct_translation})
    else:
        return jsonify(
            {
                "result": "Incorrect.",
                "correct_translation": correct_translation,
                "your_answer": user_translation,
            }
        )

@app.route("/translate", methods=["POST"])
def translate_text():
    data = request.get_json()
    text = data.get("text")
    target_language = data.get("target_language")

    if not text or not target_language:
        return jsonify({"error": "Missing 'text' or 'target_language' in request body."}), 400

    translation = get_translation(text, target_language)
    return jsonify({"translation": translation})

@app.route("/set_language", methods=["POST"])
def set_language_preference():
    data = request.get_json()
    user_id = data.get("user_id")
    language = data.get("language")

    if not user_id or not language:
        return jsonify({"error": "Missing 'user_id' or 'language' in request body."}), 400

    response = set_user_language(user_id, language)
    return jsonify({"response": response})

@app.route("/progress", methods=["GET"])
def get_progress():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing 'user_id' in query parameters."}), 400

    progress = user_progress.get(
        user_id, {"target_language": DEFAULT_TARGET_LANGUAGE, "learned_words": {}}
    )
    return jsonify(
        {
            "user_id": user_id,
            "target_language": progress.get("target_language"),
            "learned_word_count": len(progress.get("learned_words")),
        }
    )

if __name__ == "__main__":
    app.run(debug=True)