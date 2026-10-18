import os
import sys
import subprocess
import threading
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
UPLOAD_FOLDER = 'bots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# চলমান বটগুলোর প্রসেস ট্র্যাক করার ডিকশনারি
bot_processes = {}

# ==========================================
# HTML, CSS, JS (Web Panel UI)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Bot Deploy Panel</title>
    <style>
        body { background-color: #0a0a0a; color: #e0e0e0; font-family: 'Consolas', monospace; margin: 0; padding: 20px; }
        .header { text-align: center; margin-bottom: 20px; }
        .header h1 { color: #00ff88; margin: 0; }
        .header p { color: #666; font-size: 14px; }
        
        .upload-box { background: #151515; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; border: 1px solid #222; }
        input[type="file"] { display: none; }
        .btn { padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-family: inherit; font-weight: bold; transition: 0.2s; }
        .btn-upload { background: #333; color: #fff; }
        .btn-upload:hover { background: #555; }
        .btn-deploy { background: #00ff88; color: #000; margin-left: 10px; }
        .btn-deploy:hover { background: #00cc66; }
        
        .bot-list { display: flex; flex-direction: column; gap: 10px; }
        .bot-card { background: #151515; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #222; }
        
        .bot-info { display: flex; align-items: center; gap: 15px; }
        /* LED (Click to toggle on/off visually) */
        .led { width: 20px; height: 20px; border-radius: 50%; background: #1a3a1a; border: 1px solid #333; cursor: pointer; transition: 0.3s; }
        .led.running { background: #00ff88; box-shadow: 0 0 10px #00ff88; border-color: #00ff88; }
        
        .bot-name { font-weight: bold; font-size: 16px; }
        .bot-status { font-size: 12px; color: #555; margin-top: 3px; }
        
        .actions { display: flex; gap: 10px; }
        .btn-start { background: #0d3d0d; color: #00ff88; }
        .btn-start:hover { background: #00ff88; color: #000; }
        .btn-kill { background: #3d0d0d; color: #ff5555; }
        .btn-kill:hover { background: #ff5555; color: #000; }
        .btn-del { background: #2a2a2a; color: #ccc; }
        .btn-del:hover { background: #ff3333; color: #fff; }
        
        @media (max-width: 600px) {
            .bot-card { flex-direction: column; align-items: flex-start; gap: 15px; }
            .actions { width: 100%; justify-content: space-between; }
            .btn { flex: 1; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ BOT DEPLOY PANEL</h1>
        <p>Web Based Controller (Termux & Render Supported)</p>
    </div>

    <div class="upload-box">
        <form id="uploadForm">
            <label for="fileInput" class="btn btn-upload">📁 Choose .py File</label>
            <input type="file" id="fileInput" name="file" accept=".py" required>
            <span id="fileName" style="margin-left: 10px; font-size: 14px; color: #888;">No file chosen</span>
            <button type="submit" class="btn btn-deploy">🚀 DEPLOY</button>
        </form>
    </div>

    <div class="bot-list" id="botList">
        <!-- Bots will be loaded here -->
    </div>

    <script>
        // ফাইল সিলেক্ট করলে নাম দেখাবে
        document.getElementById('fileInput').addEventListener('change', function(e) {
            document.getElementById('fileName').innerText = e.target.files[0] ? e.target.files[0].name : 'No file chosen';
        });

        // ফাইল আপলোড (Deploy)
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const res = await fetch('/upload', { method: 'POST', body: formData });
            const data = await res.json();
            alert(data.message);
            loadBots();
            this.reset();
            document.getElementById('fileName').innerText = 'No file chosen';
        });

        // বট লিস্ট লোড করা এবং স্ট্যাটাস আপডেট করা
        async function loadBots() {
            const res = await fetch('/status');
            const bots = await res.json();
            const list = document.getElementById('botList');
            list.innerHTML = '';

            for (const [name, isRunning] of Object.entries(bots)) {
                const card = document.createElement('div');
                card.className = 'bot-card';
                card.innerHTML = `
                    <div class="bot-info">
                        <div class="led ${isRunning ? 'running' : ''}"></div>
                        <div>
                            <div class="bot-name">${name}</div>
                            <div class="bot-status">${isRunning ? '● RUNNING' : '● STOPPED'}</div>
                        </div>
                    </div>
                    <div class="actions">
                        <button class="btn btn-start" onclick="controlBot('${name}', 'start')">▶ START</button>
                        <button class="btn btn-kill" onclick="controlBot('${name}', 'kill')">■ KILL</button>
                        <button class="btn btn-del" onclick="controlBot('${name}', 'delete')">🗑 DELETE</button>
                    </div>
                `;
                list.appendChild(card);
            }
        }

        // বট কন্ট্রোল (Start, Kill, Delete)
        async function controlBot(filename, action) {
            if (action === 'delete' && !confirm(`Are you sure you want to delete ${filename}?`)) return;
            
            const res = await fetch('/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: filename, action: action })
            });
            const data = await res.json();
            if (data.message) alert(data.message);
            loadBots();
        }

        // প্রতি ২ সেকেন্ডে স্ট্যাটাস চেক করবে
        setInterval(loadBots, 2000);
        loadBots();
    </script>
</body>
</html>
"""

# ==========================================
# Backend Routes
# ==========================================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"})
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.py'):
        return jsonify({"message": "Only .py files are allowed!"})
    
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    return jsonify({"message": f"Successfully deployed {file.filename}!"})

@app.route('/status', methods=['GET'])
def get_status():
    # bots ফোল্ডারের সব ফাইল বের করা
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.py')]
    status = {}
    for f in files:
        # প্রসেস চলছে কিনা চেক করা
        is_running = f in bot_processes and bot_processes[f].poll() is None
        status[f] = is_running
    return jsonify(status)

@app.route('/control', methods=['POST'])
def control_bot():
    data = request.json
    filename = data.get('filename')
    action = data.get('action')
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return jsonify({"message": "File not found!"})

    # START ACTION
    if action == 'start':
        if filename in bot_processes and bot_processes[filename].poll() is None:
            return jsonify({"message": "Bot is already running!"})
        try:
            # পাইথন ফাইলটি রান করা
            proc = subprocess.Popen([sys.executable, "-u", filepath], cwd=UPLOAD_FOLDER)
            bot_processes[filename] = proc
            return jsonify({"message": f"{filename} started successfully!"})
        except Exception as e:
            return jsonify({"message": f"Error starting bot: {str(e)}"})

    # KILL ACTION
    elif action == 'kill':
        if filename in bot_processes and bot_processes[filename].poll() is None:
            bot_processes[filename].terminate()
            try:
                bot_processes[filename].wait(timeout=3)
            except:
                bot_processes[filename].kill()
            del bot_processes[filename]
            return jsonify({"message": f"{filename} killed!"})
        return jsonify({"message": "Bot is not running!"})

    # DELETE ACTION
    elif action == 'delete':
        if filename in bot_processes and bot_processes[filename].poll() is None:
            bot_processes[filename].kill()
            del bot_processes[filename]
        try:
            os.remove(filepath)
            return jsonify({"message": f"{filename} deleted!"})
        except Exception as e:
            return jsonify({"message": f"Error deleting file: {str(e)}"})

    return jsonify({"message": "Invalid action!"})

# ==========================================
# Main Server
# ==========================================
if __name__ == '__main__':
    # Render-এর জন্য PORT ভেরিয়েবল, Termux-এর জন্য 5000
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🚀 WEB PANEL STARTED!")
    print(f"👉 Open browser and go to: http://127.0.0.1:{port} or http://<your-ip>:{port}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
