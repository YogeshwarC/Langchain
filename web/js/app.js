// app.js
import { initEditor, getCode } from './editor.js';

const API_URL = 'http://localhost:8000/api';
const USER_ID = 'web_user_1';

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Setup Chat (Critical Feature - Independent of Editor)
    setupChat();

    // 2. Initialize Editor (Secondary Feature - Can fail gracefully)
    try {
        await initEditor();
    } catch (e) {
        console.error("Editor failed to load:", e);
        // Optional: show error in editor container
        const editorContainer = document.getElementById('editor-container');
        if (editorContainer) editorContainer.textContent = "Editor loading failed (Check Connection). Chat is still active.";
    }

    // 3. Setup Run Code (Depends on Editor logic partially)
    setupExecution();
});

// Setup Chat Logic
function setupChat() {
    const chatInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    // const messagesContainer = document.getElementById('chat-messages'); // Not used directly in setup

    if (!chatInput || !sendBtn) {
        console.error("Chat elements not found!");
        return;
    }

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

            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }

            const data = await response.json();

            // Remove loading, add real message
            removeMessage(loadingId);
            appendMessage(data.response, 'ai');

            // Trigger Syntax Highlighting
            if (typeof Prism !== 'undefined') {
                Prism.highlightAll();
            }

        } catch (error) {
            console.error(error);
            const loadingMsg = document.getElementById('loading-msg');
            if (loadingMsg) removeMessage('loading-msg');
            appendMessage(`Error reaching AI Tutor: ${error.message}`, 'ai');
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// Setup Execution Logic
function setupExecution() {
    const runBtn = document.getElementById('run-code-btn');
    const previewFrame = document.getElementById('preview-frame');

    if (!runBtn || !previewFrame) return;

    runBtn.addEventListener('click', () => {
        const code = getCode();

        // Update Preview (Direct IFrame injection for speed)
        const frameDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
        frameDoc.open();
        frameDoc.write(code);
        frameDoc.close();
    });

    // Initial Preview Render (delayed slightly to ensure editor might be ready, or just run empty)
    setTimeout(() => runBtn.click(), 1000);
}

// UI Helpers
function appendMessage(text, sender, isLoading = false) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    if (isLoading) msgDiv.id = 'loading-msg';

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');

    // Safe Markdown Rendering
    if (sender === 'ai' && !isLoading) {
        try {
            // Check for marked availability
            if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
                contentDiv.innerHTML = marked.parse(text, { breaks: true, gfm: true });
            } else {
                console.warn('marked library missing or invalid. Using fallback parser.');
                contentDiv.classList.add('plain-text-fallback');
                contentDiv.innerHTML = simpleMarkdownParse(text);
            }
        } catch (e) {
            console.error('Markdown rendering error:', e);
            contentDiv.classList.add('plain-text-fallback');
            contentDiv.innerHTML = simpleMarkdownParse(text);
        }
    } else {
        // User messages are plain text but respect newlines
        contentDiv.classList.add('plain-text-fallback'); // Users type raw text
        contentDiv.textContent = text;
    }

    msgDiv.appendChild(contentDiv);
    container.appendChild(msgDiv);

    // Auto-scroll logic
    requestAnimationFrame(() => {
        container.scrollTop = container.scrollHeight;
    });

    return msgDiv.id;
}

/**
 * Simple Fallback Markdown Parser
 * Handles basic headers, bold, code blocks, and newlines
 * Used when 'marked' library fails to load.
 */
function simpleMarkdownParse(text) {
    if (!text) return '';

    // Escape HTML to prevent injection in non-code parts (basic)
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // 1. Code Blocks: ```code```
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang || ''}">${code}</code></pre>`;
    });

    // 2. Inline Code: `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 3. Headers: ### Title
    html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>');

    // 4. Bold: **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 5. Separators: ---
    html = html.replace(/^---$/gm, '<hr>');

    // 6. Lists: - item
    html = html.replace(/^\- (.*$)/gm, '<li>$1</li>');
    // Wrap consecutive lis in ul (simple hack)
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    return html;
}

function removeMessage(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.remove();
}
