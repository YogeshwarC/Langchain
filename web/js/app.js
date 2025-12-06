// app.js
import { initEditor, getCode } from './editor.js';

const API_URL = 'http://localhost:8000/api';
const USER_ID = 'web_user_1';

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize Editor
    await initEditor();

    // 2. Setup Chat
    const chatInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('chat-messages');

    // Send Message
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Add User Message
        appendMessage(text, 'user');
        chatInput.value = '';
        chatInput.style.height = 'auto'; // Reset height

        try {
            // Typing indicator...
            const loadingId = appendMessage('...', 'ai', true);

            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, user_id: USER_ID })
            });

            const data = await response.json();

            // Remove loading, add real message
            removeMessage(loadingId);
            appendMessage(data.response, 'ai');

            // If data contains code, maybe update editor? (Optional enhancement)

        } catch (error) {
            console.error(error);
            appendMessage('Error reaching AI Tutor.', 'ai');
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 3. Setup Run Code
    const runBtn = document.getElementById('run-code-btn');
    const previewFrame = document.getElementById('preview-frame');

    runBtn.addEventListener('click', () => {
        const code = getCode();

        // Update Preview (Direct IFrame injection for speed)
        const frameDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
        frameDoc.open();
        frameDoc.write(code);
        frameDoc.close();

        // Optional: Send to backend for analysis
        /*
        fetch(`${API_URL}/execute`, {
            method: 'POST',
            ...
        });
        */
    });

    // Initial Preview Render
    runBtn.click();
});

// UI Helpers
function appendMessage(text, sender, isLoading = false) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    if (isLoading) msgDiv.id = 'loading-msg';

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');

    if (sender === 'ai' && !isLoading) {
        // Parse basic markdown
        contentDiv.innerHTML = marked.parse(text);
    } else {
        contentDiv.textContent = text;
    }

    msgDiv.appendChild(contentDiv);
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;

    return msgDiv.id;
}

function removeMessage(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.remove();
}
