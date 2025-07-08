import os
import re
import time
import json
import tempfile
import threading
from pathlib import Path
from collections import defaultdict
import requests
import speech_recognition as sr
from flask import Flask, request, jsonify, render_template, send_file
from gtts import gTTS
import io

app = Flask(__name__)

# Paths for known words and cache
KNOWN_JSON_PATH = Path("known_word.json")
CACHE_JSON_PATH = Path("total_word.json")


# Ensure known words file exists
if not KNOWN_JSON_PATH.exists():
    KNOWN_JSON_PATH.write_text("[]", encoding="utf-8")

# Load known words from JSON
def load_known_words(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: set(v) for k, v in data.items()}
    except Exception:
        return {}
    
def save_known_words(path: Path, known_dict: dict) -> None:
    serializable = {k: sorted(list(v)) for k, v in known_dict.items()}
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")

known_words = load_known_words(KNOWN_JSON_PATH)

# Load or initialize cache
if CACHE_JSON_PATH.exists():
    with open(CACHE_JSON_PATH, "r", encoding="utf-8") as f:
        cached_word_data = json.load(f)
else:
    cached_word_data = {}

# Lock for thread-safe cache file writes
cache_lock = threading.Lock()

def save_cache():
    with cache_lock:
        with open(CACHE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(cached_word_data, f, ensure_ascii=False, indent=2)

# In-memory counters for unknown words
_unknown_counts = defaultdict(int)

recent_unknowns = []

def translate_text(text: str, src: str, tgt: str) -> str:
    if not text:
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": src,
            "tl": tgt,
            "dt": "t",
            "q": text
        }
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data[0][0][0]
    except Exception:
        return "Translation not available"

# def get_example_sentence(word: str, tgt: str, src: str) -> str:
#     """
#     Fetch definition and example for the word in target language dictionary API.
#     Returns a formatted string with labels ("Meaning", "Description", "Example") in source language.
#     If lookup in target language fails, fallback to English dictionary.
#     """
#     if not word:
#         return ""

#     labels = {
#         "en": {"meaning": "Meaning", "description": "Description", "example": "Example"},
#         "hi": {"meaning": "अर्थ", "description": "विवरण", "example": "उदाहरण"},
#         "es": {"meaning": "Significado", "description": "Descripción", "example": "Ejemplo"},
#         "fr": {"meaning": "Sens", "description": "Description", "example": "Exemple"},
#         # Add more labels for UI localization as needed
#     }
#     label = labels.get(src, labels["en"])

#     def fetch_definitions(lang):
#         try:
#             url = f"https://api.dictionaryapi.dev/api/v2/entries/{lang}/{word}"
#             resp = requests.get(url, timeout=5)
#             resp.raise_for_status()
#             data = resp.json()
#             if not data or not isinstance(data, list):
#                 return None
#             entry = data[0]
#             meanings = entry.get("meanings", [])
#             if not meanings:
#                 return None
#             parts = []
#             for meaning in meanings:
#                 part_of_speech = meaning.get('partOfSpeech', '')
#                 definitions = meaning.get("definitions", [])
#                 if not definitions:
#                     continue
#                 part_str = f"{label['meaning']} ({part_of_speech}):\n"
#                 for definition in definitions:
#                     desc = definition.get("definition", "")
#                     example = definition.get("example", "")
#                     if desc:
#                         part_str += f"{label['description']}: {desc}\n"
#                     if example:
#                         part_str += f"{label['example']}: “{example}.”\n"
#                 parts.append(part_str.strip())
#             return "\n\n".join(parts) if parts else None
#         except Exception:
#             return None

#     # Try dictionary lookup in target language first
#     result = fetch_definitions(tgt)
#     if result:
#         return result

#     # Fallback to English dictionary if target lookup fails and tgt != 'en'
#     if tgt != "en":
#         fallback = fetch_definitions("en")
#         if fallback:
#             return fallback

#     return f"{label['meaning']}: No definition/example found for “{word}.”"

def get_example_sentence(word: str, tgt: str, src: str) -> list:
    """
    Fetches the first definition and example for a word using the DictionaryAPI.
    Args:
        word (str): The word to look up.
        tgt (str): The target language code (e.g., 'en', 'hi').
        src (str): The source language code (used only for formatting labels).
    Returns:
        list: A list with definition and example as strings.
    """
    if not word:
        return ["No word provided."]

    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/{tgt}/{word}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        entry = data[0]
        meanings = entry.get("meanings", [])
        if not meanings:
            return ["No definition/example found."]

        definitions = meanings[0].get("definitions", [])
        if not definitions:
            return ["No definition/example found."]

        definition_text = definitions[0].get("definition", "")
        example_text = definitions[0].get("example", "")

        result = []
        if definition_text:
            result.append(f"Definition: {definition_text}")
        else:
            result.append("No definition found.")

        if example_text:
            result.append(f"Example: {example_text}.")
        else:
            result.append("No example found.")

        return result

    except Exception as e:
        return [f"No definition/example found for “{word}.” (Error: {e})"]
    
def get_word_info(word: str, src: str, tgt: str) -> dict:
    word_lower = word.lower()
    cache_key = f"{src}-{tgt}-{word_lower}"
    if cache_key in cached_word_data:
        return cached_word_data[cache_key]

    meaning = translate_text(word, src, tgt)
    example = get_example_sentence(word, tgt, src)

    cached_word_data[cache_key] = {"meaning": meaning, "example": example}
    threading.Thread(target=save_cache).start()
    return cached_word_data[cache_key]

def detect_unknown_words(text: str, src: str, tgt: str) -> list:
    global recent_unknowns
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    seen_this_batch = set()
    results = []

    known_key = f"{src}-{tgt}"
    if known_key not in known_words:
        known_words[known_key] = set()

    for w in words:
        if w in seen_this_batch or w in known_words[known_key]:
            continue
        seen_this_batch.add(w)

        _unknown_counts[w] += 1
        if _unknown_counts[w] >= 5:
            known_words[known_key].add(w)
            save_known_words(KNOWN_JSON_PATH, known_words)
            continue

        info = get_word_info(w, src, tgt)

        entry = {
            "word": w,
            "meaning": info["meaning"],
            "example": info["example"]
        }
        results.append(entry)

        recent_unknowns = [item for item in recent_unknowns if item["word"] != w]
        recent_unknowns.insert(0, {"word": w, "timestamp": time.time()})
        if len(recent_unknowns) > 10:
            recent_unknowns.pop()

    return results

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/vocab/detect", methods=["POST"])
def api_detect():
    data = request.get_json()
    text = data.get("text", "")
    source_lang = data.get("source_lang", "en")
    target_lang = data.get("target_lang", "hi")

    results = detect_unknown_words(text, source_lang, target_lang)
    return jsonify({"unknowns": results})

@app.route("/api/vocab/recent", methods=["GET"])
def api_recent():
    output = []
    for item in recent_unknowns[:10]:
        word = item["word"]
        info = cached_word_data.get(f"en-hi-{word}", {"meaning": "", "example": ""})
        output.append({
            "word": word,
            "meaning": info.get("meaning", ""),
            "example": info.get("example", "")
        })
    return jsonify({"recent": output})

@app.route("/api/vocab/learn", methods=["POST"])
def api_learn():
    data = request.get_json()
    word = data.get("word")
    source_lang = data.get("source_lang", "en")
    target_lang = data.get("target_lang", "hi")

    if word:
        known_key = f"{source_lang}-{target_lang}"
        if known_key not in known_words:
            known_words[known_key] = set()
        if word not in known_words[known_key]:
            known_words[known_key].add(word)
            save_known_words(KNOWN_JSON_PATH, known_words)
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "No word provided"}), 400


@app.route("/api/vocab/speak", methods=["POST"])
def api_speak():
    data = request.get_json()
    text = data.get("text", "")
    lang = data.get("lang", "en")  # Default to English if not provided

    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    try:
        tts = gTTS(text=text, lang=lang)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return send_file(mp3_fp, mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5009, debug=True)
