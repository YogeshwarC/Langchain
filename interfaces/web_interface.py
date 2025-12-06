
from flask import Flask, render_template_string, request, jsonify
from core.teaching_orchestrator import TeachingOrchestrator
from database.student_database import StudentDatabase
from utils.gemini_client import GeminiClient
import threading
import os
import random

# HTML Template with Nature Theme and Glassmorphism
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Nature Tutor</title>
    <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@300;400;500;600&family=Montserrat:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --glass-bg: rgba(255, 255, 255, 0.25);
            --glass-border: rgba(255, 255, 255, 0.4);
            --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
            --primary-color: #1b5e20; /* Darker Forest Green */
            --accent-color: #4caf50; 
            --text-color: #0a210f; /* Very Dark Green (almost black) for contrast */
            --user-msg-bg: rgba(165, 214, 167, 0.65); /* More opaque green */
            --system-msg-bg: rgba(255, 255, 255, 0.65); /* More opaque white */
        }

        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: 'Quicksand', sans-serif;
            overflow: hidden;
            color: var(--text-color);
            font-weight: 600; /* Bolder globally */
        }

        /* Dynamic Nature Backgrounds */
        .bg-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background-size: cover;
            background-position: center;
            transition: opacity 1.5s ease-in-out;
            filter: brightness(0.9); /* Slightly dim bg for better text pop */
        }

        /* Glassmorphism Container */
        .main-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }

        .chat-interface {
            width: 90%;
            max-width: 900px;
            height: 85vh;
            background: rgba(255, 255, 255, 0.3); /* Lighter, more opaque background */
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 20px;
            border: 1px solid var(--glass-border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: fadeIn 1s ease-out;
        }

        .header {
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid var(--glass-border);
            background: rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            margin: 0;
            font-family: 'Montserrat', sans-serif;
            font-weight: 500;
            font-size: 1.8rem;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            margin: 5px 0 0;
            font-size: 0.9rem;
            opacity: 0.9;
        }

        #chat-container {
            flex-grow: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
            scroll-behavior: smooth;
        }

        /* Scrollbar Styling */
        #chat-container::-webkit-scrollbar {
            width: 8px;
        }
        #chat-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1); 
        }
        #chat-container::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3); 
            border-radius: 4px;
        }

        .message {
            max-width: 80%;
            padding: 12px 18px;
            border-radius: 15px;
            line-height: 1.5;
            position: relative;
            animation: slideUp 0.3s ease-out;
            font-size: 1rem;
            text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }

        .system {
            align-self: flex-start;
            background: var(--system-msg-bg);
            border-bottom-left-radius: 2px;
        }

        .user {
            align-self: flex-end;
            background: var(--user-msg-bg);
            border-bottom-right-radius: 2px;
            text-align: right;
        }

        /* Controls Area */
        .controls {
            padding: 20px;
            background: rgba(0, 0, 0, 0.1);
            display: flex;
            gap: 15px;
            border-top: 1px solid var(--glass-border);
        }

        input {
            flex-grow: 1;
            padding: 15px 20px;
            border-radius: 30px;
            border: 1px solid var(--glass-border);
            background: rgba(255, 255, 255, 0.4); /* Brighter input background */
            color: #000; /* Explicitly dark text for input */
            font-family: 'Quicksand', sans-serif;
            font-size: 1rem;
            font-weight: 600;
            outline: none;
            transition: all 0.3s;
        }

        input::placeholder {
            color: rgba(0, 0, 0, 0.5); /* Darker placeholder */
        }

        input:focus {
            background: rgba(255, 255, 255, 0.6);
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }

        button {
            padding: 12px 30px;
            border-radius: 30px;
            border: none;
            background: var(--primary-color);
            color: white;
            font-family: 'Montserrat', sans-serif;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, background 0.2s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }

        button:hover {
            transform: translateY(-2px);
            background: #388e3c;
        }

        button:active {
            transform: translateY(0);
        }

        /* Formatted Content Styles */
        .message strong {
            color: #a5d6a7;
        }
        
        .message ul {
            margin: 5px 0 5px 20px;
            padding: 0;
        }
        
        .message li {
            margin-bottom: 5px;
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Background Control */
        .bg-controls {
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 100;
        }
        
        .bg-btn {
            background: rgba(255,255,255,0.2);
            padding: 8px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: inline-flex;
            justify-content: center;
            align-items: center;
            font-size: 1.2rem;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    
    <!-- Background Layers -->
    <div id="bg-1" class="bg-container" style="opacity: 1; background-image: url('https://images.unsplash.com/photo-1542273917363-3b1817f69a2d?q=80&w=2074&auto=format&fit=crop');"></div>
    <div id="bg-2" class="bg-container" style="opacity: 0; background-image: url('https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=2560&auto=format&fit=crop');"></div>
    <div id="bg-3" class="bg-container" style="opacity: 0; background-image: url('https://images.unsplash.com/photo-1518173946687-a4c8892bbd9f?q=80&w=2560&auto=format&fit=crop');"></div>
    <div id="bg-4" class="bg-container" style="opacity: 0; background-image: url('https://images.unsplash.com/photo-1472214103451-9374bd1c798e?q=80&w=2560&auto=format&fit=crop');"></div>

    <div class="bg-controls">
        <button class="bg-btn" onclick="changeBg()" title="Change Environment">🌿</button>
    </div>

    <div class="main-container">
        <div class="chat-interface">
            <div class="header">
                <h1>AI Nature Tutor</h1>
                <p>Learn Web Development in Serenity</p>
            </div>
            
            <div id="chat-container">
                <!-- Messages will appear here -->
                <div class="message system">
                    Hello! I'm your AI Tutor. Let's learn about Web Development in this peaceful environment. <br>
                    We'll start with <strong>Priming</strong>. Ready?
                </div>
            </div>
            
            <div class="controls">
                <input id="user-input" type="text" placeholder="Type your answer or question..." autocomplete="off" onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>

    <script>
        const userId = 'user_' + Math.floor(Math.random() * 1000);
        let currentBg = 1;
        const totalBgs = 4;

        // Background Rotation Logic
        function changeBg() {
            // Fade out current
            document.getElementById(`bg-${currentBg}`).style.opacity = '0';
            
            // Increment
            currentBg = currentBg % totalBgs + 1;
            
            // Fade in next
            document.getElementById(`bg-${currentBg}`).style.opacity = '1';
        }

        // Auto-change background every 60 seconds for "living" feel
        setInterval(changeBg, 60000);

        function handleKeyPress(event) {
            if (event.key === 'Enter') sendMessage();
        }

        function appendMessage(text, sender) {
            const div = document.createElement('div');
            div.className = `message ${sender}`;
            // Simple markdown-like bold parsing
            const formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                      .replace(/\n/g, '<br>');
            div.innerHTML = formattedText;
            
            const container = document.getElementById('chat-container');
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }

        async function startSession() {
            try {
                const response = await fetch('/start_priming', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: userId})
                });
                const data = await response.json();
                
                if (data.status === 'priming_complete') {
                     // Wait a moment for effect
                     setTimeout(() => {
                        appendMessage(`**Phase 1 Complete!**`, 'system');
                        appendMessage(`I found ${data.terminology.length} terms and ${data.syntax_etymology.length} syntax elements.`, 'system');
                        appendMessage("Let's check your understanding. (See console for details as this is a demo UI)", 'system');
                     }, 1000);
                } else if (data.message) {
                    appendMessage(data.message, 'system');
                }
            } catch (e) {
                console.error("Connection error:", e);
                appendMessage("Error connecting to the AI Tutor backend.", 'system');
            }
        }

        async function sendMessage() {
            const input = document.getElementById('user-input');
            const text = input.value.trim();
            if (!text) return;
            
            appendMessage(text, 'user');
            input.value = '';

            try {
                const response = await fetch('/submit_answer', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: userId, answer: text})
                });
                const data = await response.json();
                if (data.feedback) {
                    appendMessage(data.feedback, 'system');
                } else {
                    // Fallback for demo
                    setTimeout(() => appendMessage("I received your input. (Backend logic pending)", 'system'), 500);
                }
            } catch (e) {
                appendMessage("Error sending message.", 'system');
            }
        }
        
        // Start the session automatically
        window.onload = startSession;
    </script>
</body>
</html>
"""

app = Flask(__name__)

# Global storage for demo purposes (simple in-memory)
# In production, use redis or database
orchestrators = {}

# Global DB
student_db = StudentDatabase()

def get_orchestrator(user_id, client):
    if user_id not in orchestrators:
        orchestrators[user_id] = TeachingOrchestrator(
            gemini_client=client, 
            student_db=student_db,
            user_id=user_id
        )
    return orchestrators[user_id]

def start_web_server(gemini_client):
    app.config['GEMINI_CLIENT'] = gemini_client
    # Disable flask banner
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(debug=True, use_reloader=False, port=5000)

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_priming', methods=['POST'])
def start_priming():
    user_id = request.json.get('user_id')
    client = app.config['GEMINI_CLIENT']
    
    orch = get_orchestrator(user_id, client)
    result = orch.start_session()
    
    # We serialize the complex objects for JSON response
    # Simplified for demo
    response_data = {
        "status": result.get("status"),
        "terminology": [t.term for t in result.get("terminology", [])],
        "syntax_etymology": [s.syntax_element for s in result.get("syntax_etymology", [])]
    }
    return jsonify(response_data)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    user_id = request.json.get('user_id')
    answer = request.json.get('answer')
    client = app.config['GEMINI_CLIENT']
    
    orch = get_orchestrator(user_id, client)
    # Pass input to current phase
    result = orch.execute_relational_thinking(answer)
    
    return jsonify(result)
