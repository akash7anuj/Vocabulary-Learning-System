const contentArea = document.getElementById("contentArea");
const btnKnown = document.getElementById("btnKnown");
const btnUnknown = document.getElementById("btnUnknown");
const btnTotal = document.getElementById("btnTotal");
const btnCache = document.getElementById("btnCache");

let currentList = "known"; // known, unknown, total, cache

// Modal related
const wordModal = new bootstrap.Modal(document.getElementById("wordModal"));
const modalWordInput = document.getElementById("modalWord");
const modalHindiInput = document.getElementById("modalHindi");
const modalDescriptionInput = document.getElementById("modalDescription");
const modalExamplesInput = document.getElementById("modalExamples");

// Fetch & display Known words list
async function loadKnownWords() {
    currentList = "known";
    contentArea.innerHTML = "<p>Loading known words...</p>";
    const res = await fetch("/dashboard/api/words/known");
    const data = await res.json();
    renderWordList(data.words, true);
}

// Fetch & display Unknown words list
async function loadUnknownWords() {
    currentList = "unknown";
    contentArea.innerHTML = "<p>Loading unknown words...</p>";
    const res = await fetch("/dashboard/api/words/unknown");
    const data = await res.json();
    renderWordList(data.words, false);
}

// Fetch & display total words count
async function loadTotalWords() {
    currentList = "total";
    contentArea.innerHTML = "<p>Loading total words count...</p>";
    const res = await fetch("/dashboard/api/words/total");
    const data = await res.json();
    contentArea.innerHTML = `<h3>Total Unique Words: ${data.total}</h3>`;
}

// Fetch & display cached words list
async function loadCachedWords() {
    currentList = "cache";
    contentArea.innerHTML = "<p>Loading cached words...</p>";
    const res = await fetch("/dashboard/api/cache/words");
    const data = await res.json();
    renderCacheList(data.words);
}

// Render Known or Unknown word list with action buttons
function renderWordList(words, isKnown) {
    if (words.length === 0) {
        contentArea.innerHTML = `<p>No ${isKnown ? "known" : "unknown"} words found.</p>`;
        return;
    }
    const listGroup = document.createElement("div");
    listGroup.className = "list-group";

    words.forEach((word) => {
        const item = document.createElement("div");
        item.className =
            "list-group-item d-flex justify-content-between align-items-center";

        const wordSpan = document.createElement("span");
        wordSpan.textContent = word;
        item.appendChild(wordSpan);

        const btnGroup = document.createElement("div");
        btnGroup.className = "btn-group btn-group-sm";

        // View Meaning button
        const viewBtn = document.createElement("button");
        viewBtn.className = "btn btn-info";
        viewBtn.textContent = "View Meaning";
        viewBtn.addEventListener("click", () => openWordModal(word, false));
        btnGroup.appendChild(viewBtn);

        // Edit button
        const editBtn = document.createElement("button");
        editBtn.className = "btn btn-warning";
        editBtn.textContent = "Edit";
        editBtn.addEventListener("click", () => openWordModal(word, true));
        btnGroup.appendChild(editBtn);

        // Move button (Known ↔ Unknown)
        const moveBtn = document.createElement("button");
        moveBtn.className = isKnown ? "btn btn-danger" : "btn btn-success";
        moveBtn.textContent = isKnown ? "Move to Unknown" : "Move to Known";
        moveBtn.addEventListener("click", () => moveWord(word, !isKnown));
        btnGroup.appendChild(moveBtn);

        item.appendChild(btnGroup);
        listGroup.appendChild(item);
    });

    contentArea.innerHTML = "";
    contentArea.appendChild(listGroup);
}

// Render cached words with View/Edit/Delete buttons
function renderCacheList(words) {
    if (words.length === 0) {
        contentArea.innerHTML = "<p>No cached words found.</p>";
        return;
    }
    const listGroup = document.createElement("div");
    listGroup.className = "list-group";

    words.forEach((word) => {
        const item = document.createElement("div");
        item.className = "list-group-item d-flex justify-content-between align-items-center";

        const wordSpan = document.createElement("span");
        wordSpan.textContent = word;
        item.appendChild(wordSpan);

        const btnGroup = document.createElement("div");
        btnGroup.className = "btn-group btn-group-sm";

        // View button
        const viewBtn = document.createElement("button");
        viewBtn.className = "btn btn-info";
        viewBtn.textContent = "View";
        viewBtn.addEventListener("click", () => openWordModal(word, false));
        btnGroup.appendChild(viewBtn);

        // Edit button
        const editBtn = document.createElement("button");
        editBtn.className = "btn btn-warning";
        editBtn.textContent = "Edit";
        editBtn.addEventListener("click", () => openWordModal(word, true));
        btnGroup.appendChild(editBtn);

        // Delete button
        const delBtn = document.createElement("button");
        delBtn.className = "btn btn-danger";
        delBtn.textContent = "Delete";
        delBtn.addEventListener("click", () => deleteCachedWord(word));
        btnGroup.appendChild(delBtn);

        item.appendChild(btnGroup);
        listGroup.appendChild(item);
    });

    contentArea.innerHTML = "";
    contentArea.appendChild(listGroup);
}

async function openWordModal(word, editable = false) {
    const res = await fetch(`/dashboard/api/word/info?word=${encodeURIComponent(word)}`);
    if (!res.ok) {
        alert("Word info not found in cache.");
        return;
    }
    const data = await res.json();

    modalWordInput.value = data.word;
    modalHindiInput.value = data.info.hindi || "";
    modalDescriptionInput.value = data.info.description || "";
    modalExamplesInput.value = (data.info.examples || []).join("\n");

    modalHindiInput.disabled = !editable;
    modalDescriptionInput.disabled = !editable;
    modalExamplesInput.disabled = !editable;

    wordModal.show();
}

document.getElementById("editForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const word = modalWordInput.value;
    const info = {
        hindi: modalHindiInput.value,
        description: modalDescriptionInput.value,
        examples: modalExamplesInput.value.split("\n").filter((ex) => ex.trim()),
    };

    const res = await fetch("/dashboard/api/word/edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word, info }),
    });
    if (res.ok) {
        alert("Saved successfully!");
        wordModal.hide();
        if (currentList === "known") loadKnownWords();
        else if (currentList === "unknown") loadUnknownWords();
        else if (currentList === "cache") loadCachedWords();
    } else {
        alert("Failed to save changes.");
    }
});

async function moveWord(word, toKnown) {
    const res = await fetch("/dashboard/api/word/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word, to_known: toKnown }),
    });
    if (res.ok) {
        alert(`Moved "${word}" to ${toKnown ? "Known" : "Unknown"} words.`);
        if (currentList === "known") loadKnownWords();
        else if (currentList === "unknown") loadUnknownWords();
    } else {
        alert("Failed to move word.");
    }
}

async function deleteCachedWord(word) {
    if (!confirm(`Delete cached info for "${word}"? This cannot be undone.`)) return;
    try {
        const res = await fetch("/dashboard/api/cache/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ word }),
        });
        if (res.ok) {
            alert(`Deleted cache for "${word}".`);
            loadCachedWords();
        } else {
            alert("Failed to delete cached word.");
        }
    } catch {
        alert("Error deleting cached word.");
    }
}

async function updateButtonCounts() {
    try {
        // Known words count
        const resKnown = await fetch("/dashboard/api/words/known");
        const knownData = await resKnown.json();
        btnKnown.textContent = `Known Words (${knownData.words.length})`;

        // Unknown words count
        const resUnknown = await fetch("/dashboard/api/words/unknown");
        const unknownData = await resUnknown.json();
        btnUnknown.textContent = `Unknown Words (${unknownData.words.length})`;

        // Total words count
        const resTotal = await fetch("/dashboard/api/words/total");
        const totalData = await resTotal.json();
        btnTotal.textContent = `Total Words (${totalData.total})`;

        // Cached words count
        const resCache = await fetch("/dashboard/api/cache/words");
        const cacheData = await resCache.json();
        btnCache.textContent = `Cached Words (${cacheData.words.length})`;
    } catch (error) {
        console.error("Error updating button counts:", error);
    }
}


btnKnown.addEventListener("click", loadKnownWords);
btnUnknown.addEventListener("click", loadUnknownWords);
btnTotal.addEventListener("click", loadTotalWords);
btnCache.addEventListener("click", loadCachedWords);

// Load known words by default on page load
loadKnownWords();
updateButtonCounts();