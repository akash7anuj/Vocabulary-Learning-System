
# 🌍 Multi-Language Vocabulary Learning System

A web-based speech-to-text vocabulary learning platform that detects spoken words, identifies unknown ones, and provides real-time translations, definitions, and examples in multiple languages.

## 🚀 Features

- 🎙️ **Speech to Text** using Web Speech API (supports multiple spoken languages)
- 🌐 **Multi-language Translation** (via Google Translate API)
- 📚 **Definition & Example** lookup from [dictionaryapi.dev](https://dictionaryapi.dev)
- 📈 **Smart Learning System** — marks words as "known" after repeated exposure
- 🧠 **Recent Unknown Words** — shows a list of recently detected unknown words
- 📁 **Caching & Persistence** — words and their definitions/examples are cached for faster reuse
- ✅ **Mark as Learned** feature per word
- 🎧 Optional: **Text-to-Speech (TTS)** endpoint for pronunciation

## 🧱 Tech Stack

- **Backend:** Python + Flask
- **Frontend:** HTML + JavaScript (Vanilla) + Bootstrap 5
- **APIs Used:**
  - Google Translate (unofficial endpoint)
  - [dictionaryapi.dev](https://dictionaryapi.dev)
- **Speech Recognition:** Web Speech API (Browser built-in)

## 🗂 Project Structure

```
project/
├── server.py                # Flask backend
├── templates/
│   └── index.html           # Main frontend page
├── static/
│   ├── js/
│   │   └── script.js        # Client-side logic
│   └── css/
│       └── styles.css       # (optional) custom styles
├── known_word.json          # JSON storing user-learned words
├── total_word.json          # Cache of word data
├── README.md
```

## ⚙️ Installation

1. **Clone the repo:**
   ```bash
   git clone https://github.com/yourname/vocab-multilang.git
   cd vocab-multilang
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install flask gtts requests
   ```

4. **Run the server:**
   ```bash
   python server.py
   ```

5. **Visit the app in browser:**
   ```
   http://localhost:5009
   ```

## 🧠 How It Works
The app functions as a voice-based vocabulary builder using real-time speech recognition, translation, and dictionary APIs. Here's a step-by-step breakdown:

1. User selects spoken and translation languages
  - For example, Spoken Language: English (US), Translation Language: Hindi.
  - These are selected from dropdowns on the home page.

2. Clicking "Start Reading" activates the microphone
  - The app uses the Web Speech API to continuously listen to your speech and convert it into text.

3. Captured speech is transcribed in real time
  - Text appears live under the "Live Transcript" section.
  - Transcription is split into words using regex (`\b[a-zA-Z]+\b`).

4. Each word is analyzed
  - The app checks if the word is already in your `known_word.json`.
  - If not, it is treated as unknown.

5. Unknown word processing includes:
  - **Translation**: Uses Google Translate API (unofficial) to get the meaning in the target language (e.g., Hindi).
  - **Definition & Example**: Uses `dictionaryapi.dev` to fetch the part of speech, definition, and example usage.
  - **Caching**: Results are stored in `total_word.json` to avoid redundant API calls.

6. Displaying Results on Screen
  - Unknown words appear in the "Unknown Words" list.
  - Each includes:
    - The word in bold
    - Hindi translation
    - Example sentence
    - 🔊 Speaker button for pronunciation (uses gTTS)
    - ✔️ “Mark as Learned” button

7. Automatic Promotion
  - If a word appears 5 times in unknown usage, it is automatically moved to the known list to reflect familiarity.

8. User can mark words as learned
  - When clicked:
    - The word is moved to `unknown_word.json`.
    - Removed from the known list.
    - Also reflected in the dashboard.

9. Dashboard Insights
  - Accessible via `/dashboard`
  - Features include:
    - Track known words, unknown words and cached words
    - View & edit and move from known to unknown words or vice versa
    - Edit meaning, description, and examples
    - Delete words from cached
    - Track total word count and progress

10. Asynchronous Caching & Thread Safety
  - Background threads handle caching to ensure responsiveness.
  - Thread locks (`threading.Lock`) ensure safe file operations.


## 📡 API Routes

| Route                      | Method | Description                             |
|---------------------------|--------|-----------------------------------------|
| `/`                       | GET    | Main UI page                            |
| `/api/vocab/detect`       | POST   | Detects unknown words from text         |
| `/api/vocab/recent`       | GET    | Returns recent 10 unknown words         |
| `/api/vocab/learn`        | POST   | Marks a word as learned                 |
| `/api/vocab/speak`        | POST   | (Optional) Returns TTS audio (MP3)      |

## 📤 Sample Payloads

### `/api/vocab/detect`
```json
{
  "text": "Innovation is the key to progress",
  "source_lang": "en",
  "target_lang": "hi"
}
```

### `/api/vocab/learn`
```json
{
  "word": "innovation",
  "source_lang": "en",
  "target_lang": "hi"
}
```

## 🌐 Supported Languages

| Language     | Speech (Source) | Translate & Dictionary (Target) |
|--------------|------------------|---------------------------------|
| English      | ✅               | ✅                              |
| Hindi        | ✅               | ✅                              |
| Spanish      | ✅               | ✅                              |
| French       | ✅               | ✅                              |
| Chinese      | ✅               | ⚠️ (limited dictionary support) |

> Speech support may vary by browser. Chrome is recommended.

## 📝 To-Do / Future Ideas

- [ ] User authentication & profile-based learning
- [ ] Visual charts for learning progress
- [ ] Offline/desktop version (Electron)
- [ ] Better caching with persistent DB (e.g., SQLite)

## 🧑‍💻 Author

Made with ❤️ by [Your Name]  
GitHub: [https://github.com/yourname](https://github.com/yourname)

## 📜 License

MIT License — Free for personal or educational use.
