const API = "https://creative-adaptation-production-03fd.up.railway.app";
let chatHistory = [];

async function loadDocuments() {
    const select = document.getElementById("docSelect");
    try {
        const res = await fetch(`${API}/documents`);
        const data = await res.json();
        if (data.documents.length) {
            select.innerHTML = data.documents
                .map(d => `<option value="${d}">${d}</option>`)
                .join("");
        } else {
            select.innerHTML = `<option value="" disabled>No documents yet</option>`;
        }
    } catch {
        select.innerHTML = `<option value="" disabled>Could not load documents</option>`;
    }
}

loadDocuments();

// drag and drop support
const dropZone = document.getElementById("dropZone");

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/pdf") {
        uploadFile(file);
    } else {
        setStatus("Only PDF files are supported.");
    }
});

document.getElementById("fileInput").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) uploadFile(file);
});

async function uploadFile(file) {
    setStatus(`<span class="spinner"></span> Uploading...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API}/upload`, { method: "POST", body: formData });
        if (!res.ok) throw new Error();
        const data = await res.json();
        setStatus(`✅ ${data.filename} uploaded`);
        await loadDocuments();
        document.getElementById("docSelect").value = data.filename;
        updateActiveDoc(data.filename);
        clearChat();
    } catch {
        setStatus("Upload failed. Try again.");
    }
}

function setStatus(html) {
    document.getElementById("uploadStatus").innerHTML = html;
}

document.getElementById("docSelect").addEventListener("change", (e) => {
    clearChat();
    updateActiveDoc(e.target.value);
});

function updateActiveDoc(name) {
    document.getElementById("activeDoc").textContent = name
        ? `📄 ${name}`
        : "Select a document to start chatting";
}

document.getElementById("clearChat").addEventListener("click", clearChat);

function clearChat() {
    chatHistory = [];
    document.getElementById("chatBox").innerHTML = `
        <div class="welcome-msg">
            <div class="welcome-icon">💬</div>
            <h2>No document selected</h2>
            <p>Upload a PDF on the left and select it to start asking questions.</p>
        </div>`;
}

document.getElementById("askBtn").addEventListener("click", askQuestion);
document.getElementById("questionInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") askQuestion();
});

async function askQuestion() {
    const input = document.getElementById("questionInput");
    const askBtn = document.getElementById("askBtn");
    const filename = document.getElementById("docSelect").value;
    const question = input.value.trim();

    if (!question) return;

    if (!filename) {
        appendMessage("Select a document first.", "ai-message");
        return;
    }

    appendMessage(question, "user-message");
    input.value = "";

    askBtn.disabled = true;
    askBtn.innerHTML = `<span class="spinner"></span>`;

    const thinking = appendMessage("", "ai-message loading");
    thinking.innerHTML = `<span class="spinner"></span> Thinking...`;

    try {
        const res = await fetch(`${API}/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, filename, chat_history: chatHistory })
        });

        if (!res.ok) throw new Error();
        const data = await res.json();

        thinking.className = "message ai-message";
        thinking.innerHTML = `
            ${escapeHtml(data.answer)}
            <button class="copy-btn" onclick="copyText(this)" title="Copy">Copy</button>
        `;

        if (data.sources && data.sources.length > 0) {
            const sourcesDiv = document.createElement("div");
            sourcesDiv.className = "sources";
            sourcesDiv.innerHTML = `<strong>📄 Sources</strong>` +
                data.sources.map(s => `<div class="source-chunk">${escapeHtml(s)}</div>`).join("");
            thinking.parentNode.insertBefore(sourcesDiv, thinking.nextSibling);
        }

        chatHistory.push({ role: "user", content: question });
        chatHistory.push({ role: "assistant", content: data.answer });

    } catch {
        thinking.className = "message ai-message";
        thinking.textContent = "Something went wrong. Is the server running?";
    } finally {
        askBtn.disabled = false;
        askBtn.innerHTML = `Send ➤`;
    }
}

function appendMessage(text, className) {
    const chatBox = document.getElementById("chatBox");

    const welcome = chatBox.querySelector(".welcome-msg");
    if (welcome) welcome.remove();

    const msg = document.createElement("div");
    msg.className = `message ${className}`;
    msg.textContent = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msg;
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br>");
}

function copyText(btn) {
    const msg = btn.parentElement;
    const text = msg.innerText.replace("Copy", "").trim();
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = "Copy"; }, 2000);
    });
}
