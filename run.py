import json
import threading
import time
import re
from pathlib import Path
from collections import defaultdict
import requests
from flask import Flask, request, jsonify, render_template, send_file
import io
from gtts import gTTS


app = Flask(__name__)

KNOWN_JSON_PATH = Path("known_word.json")
UNKNOWN_JSON_PATH = Path("unknown_word.json")
CACHE_JSON_PATH = Path("total_word.json")

# Ensure known words file exists
if not KNOWN_JSON_PATH.exists():
    KNOWN_JSON_PATH.write_text("[]", encoding="utf-8")

# Load known words from JSON
def load_known_words(path: Path) -> set:
    return set(json.loads(path.read_text(encoding="utf-8")))

def save_known_words(path: Path, known_set: set) -> None:
    path.write_text(json.dumps(sorted(known_set), ensure_ascii=False, indent=2), encoding="utf-8")

known_words = load_known_words(KNOWN_JSON_PATH)

# Load or initialize cache
if CACHE_JSON_PATH.exists():
    with open(CACHE_JSON_PATH, "r", encoding="utf-8") as f:
        cached_word_data = json.load(f)
else:
    cached_word_data = {}

# Lock for thread-safe cache file writes
cache_lock = threading.Lock()

def save_caches():
    with cache_lock:
        with open(CACHE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(cached_word_data, f, ensure_ascii=False, indent=2)

# In-memory counters for unknown words
_unknown_counts = defaultdict(int)

# Recent unknown words LIFO list (max 10)
recent_unknowns = []

def translate_to_hindi(text: str, src: str, tgt: str) -> str:
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
        return "Translation not available"  # Translation not available

def get_example_sentence(word: str, src: str, tgt: str) -> str:
    if not word:
        return ["No word provided."]
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/{tgt}/{word}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        entry = data[0]
        meaning = entry.get("meanings", [])[0]
        part_of_speech = meaning.get("partOfSpeech", "")
        definition_data = meaning.get("definitions", [])[0]
        
        definition = definition_data.get("definition", "")
        example = definition_data.get("example", "")
        
        parts = []
        if part_of_speech:
            parts.append(f"Part of Speech: {part_of_speech}")
        if definition:
            parts.append(f"Definition: {definition}")
        if example:
            parts.append(f"Example: “{example}.”")
        
        return "\n".join(parts) or f"No definition/example available for “{word}.”"
    
    except Exception as e:
        return f"No definition/example found for “{word}.”"

def get_word_info(word: str) -> dict:
    """
    Return dict with 'meaning' and 'example' for word.
    Check local JSON cache first, then fallback to APIs.
    """
    word_lower = word.lower()
    if word_lower in cached_word_data:
        return cached_word_data[word_lower]

    meaning = translate_to_hindi(word)
    example = get_example_sentence(word)

    cached_word_data[word_lower] = {"meaning": meaning, "example": example}
    # Save cache asynchronously
    threading.Thread(target=save_caches).start()

    return cached_word_data[word_lower]

def detect_unknown_words(text: str) -> list:
    global recent_unknowns
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    seen_this_batch = set()
    results = []

    for w in words:
        if w in seen_this_batch or w in known_words:
            continue
        seen_this_batch.add(w)

        _unknown_counts[w] += 1
        if _unknown_counts[w] >= 5:
            known_words.add(w)
            save_known_words(KNOWN_JSON_PATH, known_words)
            continue

        info = get_word_info(w)

        entry = {
            "word": w,
            "meaning": info["meaning"],
            "example": info["example"]
        }
        results.append(entry)

        # Update recent_unknowns: unique LIFO max 10
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
    results = detect_unknown_words(text)
    return jsonify({"unknowns": results})

@app.route("/api/vocab/recent", methods=["GET"])
def api_recent():
    output = []
    for item in recent_unknowns[:10]:
        word = item["word"]
        info = get_word_info(word)
        output.append({
            "word": word,
            "meaning": info["meaning"],
            "example": info["example"]
        })
    return jsonify({"recent": output})

@app.route("/api/vocab/learn", methods=["POST"])
def api_learn():
    data = request.get_json()
    word = data.get("word")
    if word:
        if word not in known_words:
            known_words.add(word)
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


# ====== Dashboard related code =====

# Ensure files exist
for path, default_content in [
    (KNOWN_JSON_PATH, "[]"),
    (UNKNOWN_JSON_PATH, "[]"),
    (CACHE_JSON_PATH, "{}"),
]:
    if not path.exists():
        path.write_text(default_content, encoding="utf-8")

file_lock = threading.Lock()

def load_json(path: Path):
    with file_lock:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

def save_json(path: Path, data):
    with file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def load_word_sets():
    known = set(load_json(KNOWN_JSON_PATH))
    unknown = set(load_json(UNKNOWN_JSON_PATH))
    return known, unknown

def save_word_sets(known_set, unknown_set):
    save_json(KNOWN_JSON_PATH, sorted(known_set))
    save_json(UNKNOWN_JSON_PATH, sorted(unknown_set))

def load_cache():
    return load_json(CACHE_JSON_PATH)

def save_cache(cache):
    save_json(CACHE_JSON_PATH, cache)

_unknown_counts = defaultdict(int)
recent_unknowns = []
cache_lock = threading.Lock()


def get_example_and_description(word: str):
    if not word:
        return "", []
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        entry = data[0]
        meaning = entry.get("meanings", [])[0]
        definition = meaning.get("definitions", [])[0].get("definition", "")
        examples = []
        for d in meaning.get("definitions", []):
            ex = d.get("example")
            if ex:
                examples.append(ex)
        return definition, examples
    except Exception:
        return "", []

def get_word_info_dash(word: str) -> dict:
    word_lower = word.lower()
    
    cache = load_json(CACHE_JSON_PATH)
    if word_lower in cache:
        info = cache[word_lower]
        example_text = info.get("example", "")
        examples = [line.strip() for line in example_text.split("\n") if line.strip()]
        return {
            "hindi": info.get("meaning", ""),
            "description": "",  # Optional: Could parse from meaning or elsewhere
            "examples": examples,
        }

    hindi = translate_to_hindi(word)
    description, examples = get_example_and_description(word)

    with cache_lock:
        cache = load_cache()
        cache[word_lower] = {
            "meaning": hindi,
            "example": "\n".join(examples)
        }
        threading.Thread(target=save_cache, args=(cache,)).start()

    return {
        "hindi": hindi,
        "description": description,
        "examples": examples,
    }

def detect_unknown_word(text: str):
    global recent_unknowns
    known_words, unknown_words = load_word_sets()
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    seen_this_batch = set()
    results = []

    for w in words:
        if w in seen_this_batch or w in known_words:
            continue
        seen_this_batch.add(w)

        _unknown_counts[w] += 1
        if _unknown_counts[w] >= 5:
            known_words.add(w)
            if w in unknown_words:
                unknown_words.discard(w)
            save_word_sets(known_words, unknown_words)
            continue

        if w not in unknown_words:
            unknown_words.add(w)
            save_word_sets(known_words, unknown_words)

        info = get_word_info_dash(w)

        results.append({
            "word": w,
            "hindi": info["hindi"],
            "description": info["description"],
            "examples": info["examples"],
        })

        recent_unknowns = [item for item in recent_unknowns if item["word"] != w]
        recent_unknowns.insert(0, {"word": w, "timestamp": time.time()})
        if len(recent_unknowns) > 10:
            recent_unknowns.pop()

    return results




@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/dashboard/api/words/known")
def get_known_words():
    known = load_json(KNOWN_JSON_PATH)
    return jsonify({"words": known})

@app.route("/dashboard/api/words/unknown")
def get_unknown_words():
    unknown = load_json(UNKNOWN_JSON_PATH)
    return jsonify({"words": unknown})

@app.route("/dashboard/api/words/total")
def get_total_words():
    known = set(load_json(KNOWN_JSON_PATH))
    unknown = set(load_json(UNKNOWN_JSON_PATH))
    total = len(known.union(unknown))
    return jsonify({"total": total})

@app.route("/dashboard/api/word/info")
def get_word_info_api():
    word = request.args.get("word", "").lower()
    if not word:
        return jsonify({"error": "No word specified"}), 400
    info = get_word_info_dash(word)
    return jsonify({"word": word, "info": info})

@app.route("/dashboard/api/word/edit", methods=["POST"])
def edit_word():
    data = request.json
    word = data.get("word", "").lower()
    info = data.get("info", {})
    if not word or not isinstance(info, dict):
        return jsonify({"error": "Invalid data"}), 400
    with cache_lock:
        cache = load_cache()
        # Store in your format
        cache[word] = {
            "meaning": info.get("hindi", ""),
            "example": "\n".join(info.get("examples", []))
        }
        save_cache(cache)
    return jsonify({"status": "success"})

@app.route("/dashboard/api/word/move", methods=["POST"])
def move_word():
    data = request.json
    word = data.get("word", "").lower()
    to_known = data.get("to_known", True)
    if not word:
        return jsonify({"error": "No word provided"}), 400

    known_words, unknown_words = load_word_sets()
    if to_known:
        if word in unknown_words:
            unknown_words.discard(word)
        if word not in known_words:
            known_words.add(word)
    else:
        if word in known_words:
            known_words.discard(word)
        if word not in unknown_words:
            unknown_words.add(word)
    save_word_sets(known_words, unknown_words)
    return jsonify({"status": "success"})

@app.route("/dashboard/api/cache/words")
def get_cached_words():
    cache = load_cache()
    words = list(cache.keys())
    return jsonify({"words": words})

@app.route("/dashboard/api/cache/delete", methods=["POST"])
def delete_cached_word():
    data = request.json
    word = data.get("word", "").lower()
    if not word:
        return jsonify({"error": "No word provided"}), 400

    with cache_lock:
        cache = load_cache()
        if word in cache:
            cache.pop(word)
            save_cache(cache)
            return jsonify({"status": "deleted"})
        else:
            return jsonify({"error": "Word not found in cache"}), 404

@app.route("/dashboard/api/vocab/detect", methods=["POST"])
def dashboard_api_detect():
    data = request.get_json()
    text = data.get("text", "")
    results = detect_unknown_word(text)
    return jsonify({"unknowns": results})

@app.route("/dashboard/api/vocab/recent", methods=["GET"])
def dashboard_api_recent():
    output = []
    for item in recent_unknowns[:10]:
        word = item["word"]
        info = get_word_info_dash(word)
        output.append({
            "word": word,
            "hindi": info["hindi"],
            "description": info["description"],
            "examples": info["examples"]
        })
    return jsonify({"recent": output})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
