document.addEventListener("DOMContentLoaded", () => {
    const btnToggle = document.getElementById("start-btn");
    const transcriptEl = document.getElementById("transcript");
    const unknownEl = document.getElementById("unknown-list");
    const recentEl = document.getElementById("recent10");
    const sourceLangSelect = document.getElementById("source-lang");
    const targetLangSelect = document.getElementById("target-lang");

    let recognition;
    let listening = false;
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        alert("Web Speech API not supported (use Chrome or Edge).");
        btnToggle.disabled = true;
        return;
    }
    recognition = new SpeechRec();
    recognition.continuous = true;
    recognition.interimResults = true;

    function updateRecognitionLang() {
        recognition.lang = sourceLangSelect.value || "en-US";
    }
    updateRecognitionLang();
    sourceLangSelect.addEventListener("change", () => {
        if (listening) {
            recognition.stop();
            updateRecognitionLang();
            recognition.start();
        } else {
            updateRecognitionLang();
        }
        transcriptEl.textContent = "";
        unknownEl.innerHTML = '<li class="list-group-item">No unknown words yet.</li>';
        recentEl.innerHTML = '<li class="list-group-item">No recent words yet.</li>';
    });
    targetLangSelect.addEventListener("change", () => {
        unknownEl.innerHTML = '<li class="list-group-item">No unknown words yet.</li>';
        recentEl.innerHTML = '<li class="list-group-item">No recent words yet.</li>';
    });

    recognition.onresult = async (evt) => {
        let interim = "";
        let finalText = "";

        for (let i = evt.resultIndex; i < evt.results.length; i++) {
            const transcript = evt.results[i][0].transcript;
            if (evt.results[i].isFinal) {
                finalText += transcript + " ";
            } else {
                interim += transcript;
            }
        }

        transcriptEl.textContent += finalText;
        transcriptEl.scrollTop = transcriptEl.scrollHeight;

        if (finalText.trim()) {
            await sendForDetection(finalText);
            fetchRecentWords();
        }
    };

    recognition.onerror = (err) => {
        console.error("Speech recognition error:", err);
        stopListening();
    };

    recognition.onend = () => {
        if (listening) {
            recognition.start();
        }
    };

    async function startListening() {
        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch {
            alert("Microphone access is required.");
            return;
        }
        transcriptEl.textContent = "";
        unknownEl.innerHTML = '<li class="list-group-item">Listening…</li>';
        recognition.start();
        btnToggle.textContent = "Stop Listening";
        listening = true;
    }

    function stopListening() {
        recognition.stop();
        btnToggle.textContent = "Start Reading";
        unknownEl.innerHTML = '<li class="list-group-item">Stopped Listening</li>';
        listening = false;
    }

    btnToggle.addEventListener("click", () => {
        listening ? stopListening() : startListening();
    });

    async function sendForDetection(text) {
        try {
            const res = await fetch("/api/vocab/detect", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text }),
            });
            if (!res.ok) throw new Error(res.statusText);
            const data = await res.json();
            renderUnknowns(data.unknowns);
        } catch (err) {
            console.error("Detection API error:", err);
        }
    }

    function renderUnknowns(list) {
        unknownEl.innerHTML = "";
        if (!list || list.length === 0) {
            unknownEl.innerHTML = '<li class="list-group-item">No unknown words!</li>';
            return;
        }
        list.forEach((item) => {
            const exampleFormatted = (item.example || "").replace(/\n/g, "<br>");
            // Escape quotes to safely pass text to onclick
            const meaningEscaped = item.meaning.replace(/'/g, "\\'");
            const exampleEscaped = (item.example || "").replace(/'/g, "\\'").replace(/\n/g, " ");

            const li = document.createElement("li");
            li.className = "list-group-item d-flex justify-content-between align-items-start";
            li.innerHTML = `
                    <div>
                        <strong class="text-danger">${item.word}</strong><br>
                        <small>
                        Hindi: ${item.meaning} 
                        <button class="btn btn-link btn-sm p-0 text-decoration-none" onclick="playText('${meaningEscaped}')">🔊</button>
                        </small><br>
                        <em>
                        ${exampleFormatted}
                        <!-- <button class="btn btn-link btn-sm p-0" onclick="playText('${exampleEscaped}')">🔊</button> -->
                        </em>
                    </div>
                    <button class="btn btn-sm btn-success mark-known" data-word="${item.word}">
                        ✔ Learned
                    </button>
                    `;
            unknownEl.appendChild(li);
        });
        bindMarkKnown();
    }


    function bindMarkKnown() {
        document.querySelectorAll(".mark-known").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const word = btn.dataset.word;
                try {
                    const res = await fetch("/api/vocab/learn", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            word,
                            source_lang: sourceLangSelect.value.split("-")[0],
                            target_lang: targetLangSelect.value.split("-")[0]
                        }),
                    });
                    if (res.ok) btn.closest("li").remove();
                    fetchRecentWords();
                } catch (err) {
                    console.error("Learn API error:", err);
                }
            });
        });
    }

    async function fetchRecentWords() {
        try {
            const res = await fetch("/api/vocab/recent");
            if (!res.ok) throw new Error(res.statusText);
            const data = await res.json();
            renderRecentWords(data.recent);
        } catch (err) {
            console.error("Failed to fetch recent words:", err);
        }
    }

    function renderRecentWords(list) {
        recentEl.innerHTML = "";
        if (!list || list.length === 0) {
            recentEl.innerHTML = '<li class="list-group-item">No recent words yet.</li>';
            return;
        }
        list.forEach((item) => {
            const exampleFormatted = (item.example || "").replace(/\n/g, "<br>");
            const li = document.createElement("li");
            li.className = "list-group-item";
            li.innerHTML = `
            <strong>${item.word}</strong> — Hindi: ${item.meaning}<br>
            <small>${exampleFormatted}</small>
          `;
            recentEl.appendChild(li);
        });
    }

    fetchRecentWords();
});

async function playText(text) {
    if (!text) return;
    try {
        const res = await fetch("/api/vocab/speak", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });
        if (!res.ok) throw new Error(await res.text());
        const audioBlob = await res.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.play();
    } catch (err) {
        console.error("TTS error:", err);
        alert("Could not play audio.");
    }
}
