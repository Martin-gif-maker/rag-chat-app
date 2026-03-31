const API = "https://creative-adaptation-production-03fd.up.railway.app";
let chatHistory = [];

async function loadDocuments() {
    const select = document.getElementById("docSelect");
    const res = await fetch(`${API}/documents`);
    const data = await res.json();
    select.innerHTML = data.documents.length
        ? data.documents.map(d => `<option value="${d}">${d}</option>`).join("")
        : `<option value="">-- Upload a PDF first --</option>`;
}

loadDocuments();

document.getElementById("uploadBtn").addEventListener("click", async () => {
    const file = document.getElementById("fileInput").files[0];
    const status = document.getElementById("uploadStatus");

    if (!file) {
        status.textContent = "⚠️ Please select a PDF file first.";
        return;
    }

    status.innerHTML = `<span class="spinner"></span> Uploading...`;
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API}/upload`, { method: "POST", body: formData });
        if (!res.ok) throw new Error("Server error");
        const data = await res.json();
        status.textContent = data.message;
        await loadDocuments();
        document.getElementById("docSelect").value = data.filename;
        chatHistory = [];
        document.getElementById("chatBox").innerHTML = "";
    } catch (err) {
        status.textContent = "❌ Upload failed. Make sure the server is running.";
    }
});

document.getElementById("clearChat").addEventListener("click", () => {
    chatHistory = [];
    document.getElementById("chatBox").innerHTML = "";
});

document.getElementById("docSelect").addEventListener("change", () => {
    chatHistory = [];
    document.getElementById("chatBox").innerHTML = "";
});

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
        appendMessage("⚠️ Please upload and select a document first.", "ai-message");
        return;
    }

    appendMessage(question, "user-message");
    input.value = "";

    askBtn.disabled = true;
    askBtn.textContent = "...";

    const thinking = appendMessage("", "ai-message loading");
    thinking.innerHTML = `<span class="spinner"></span> Thinking...`;

    try {
        const res = await fetch(`${API}/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, filename, chat_history: chatHistory })
        });

        if (!res.ok) throw new Error("Server error");
        const data = await res.json();

        thinking.className = "message ai-message";
        thinking.textContent = data.answer;

        if (data.sources && data.sources.length > 0) {
            const sourcesDiv = document.createElement("div");
            sourcesDiv.className = "sources";
            sourcesDiv.innerHTML = `<strong>📄 Sources:</strong>` +
                data.sources.map(s => `<div class="source-chunk">${s}</div>`).join("");
            thinking.parentNode.insertBefore(sourcesDiv, thinking.nextSibling);
        }

        chatHistory.push({ role: "user", content: question });
        chatHistory.push({ role: "assistant", content: data.answer });

    } catch (err) {
        thinking.className = "message ai-message";
        thinking.textContent = "❌ Something went wrong. Is the server running?";
    } finally {
        askBtn.disabled = false;
        askBtn.textContent = "Ask";
    }
}

function appendMessage(text, className) {
    const chatBox = document.getElementById("chatBox");
    const msg = document.createElement("div");
    msg.className = `message ${className}`;
    msg.textContent = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msg;
}