import os
import sys
import subprocess
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
UPLOAD_FOLDER = 'bots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot_processes = {}

# ==========================================
# Premium PWA HTML, CSS, JS
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#09090b">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Bot Controller</title>
    <!-- Google Fonts for Premium Look -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #09090b;
            --card-bg: rgba(25, 25, 30, 0.6);
            --border: rgba(255, 255, 255, 0.08);
            --text-main: #f4f4f5;
            --text-muted: #a1a1aa;
            --neon-green: #00ff88;
            --neon-glow: rgba(0, 255, 136, 0.4);
            --danger: #ff4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        
        body {
            background-color: var(--bg);
            background-image: radial-gradient(circle at 50% 0%, #1a1a24 0%, #09090b 70%);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container { width: 100%; max-width: 500px; }

        /* Header */
        .header { text-align: center; margin-bottom: 30px; padding-top: 10px; }
        .header h1 { 
            font-size: 26px; 
            font-weight: 700; 
            letter-spacing: 1px;
            background: linear-gradient(90deg, #00ff88, #00b8ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
        }
        .header p { font-size: 13px; color: var(--text-muted); font-weight: 300; }

        /* Upload Card */
        .upload-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .file-drop-area {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 25px;
            border: 2px dashed rgba(0, 255, 136, 0.3);
            border-radius: 12px;
            background: rgba(0, 255, 136, 0.03);
            transition: 0.3s;
            cursor: pointer;
            margin-bottom: 15px;
        }
        .file-drop-area:hover { background: rgba(0, 255, 136, 0.08); border-color: var(--neon-green); }
        .file-drop-area input[type="file"] { position: absolute; left: 0; top: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        
        .icon { font-size: 30px; margin-bottom: 10px; }
        .file-label { font-size: 14px; font-weight: 600; color: var(--neon-green); }
        .file-name { font-size: 12px; color: var(--text-muted); margin-top: 5px; word-break: break-all; }

        /* Buttons */
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 12px;
            font-family: inherit;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .btn:active { transform: scale(0.97); }
        
        .btn-deploy {
            background: var(--neon-green);
            color: #000;
            box-shadow: 0 4px 15px var(--neon-glow);
        }
        .btn-deploy:hover { background: #00cc6a; }

        /* Bot Cards */
        .bot-list { display: flex; flex-direction: column; gap: 15px; }
        
        .bot-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            transition: 0.3s;
            position: relative;
            overflow: hidden;
        }
        
        .bot-card.running { border-color: rgba(0, 255, 136, 0.3); box-shadow: 0 0 20px rgba(0, 255, 136, 0.05); }

        .bot-header { display: flex; align-items: center; gap: 12px; }
        
        /* Pulsing LED */
        .led { width: 12px; height: 12px; border-radius: 50%; background: #333; border: 1px solid #555; }
        .led.active { 
            background: var(--neon-green); 
            border-color: var(--neon-green);
            box-shadow: 0 0 10px var(--neon-green);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 var(--neon-glow); }
            70% { box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
            100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
        }

        .bot-name { font-size: 16px; font-weight: 600; flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .status-text { font-size: 11px; font-weight: 700; letter-spacing: 1px; color: var(--text-muted); }
        .status-text.active { color: var(--neon-green); }

        .actions { display: flex; gap: 8px; }
        
        .btn-act { flex: 1; padding: 10px; border-radius: 10px; font-size: 13px; font-weight: 600; border: 1px solid transparent; }
        .btn-start { background: rgba(0, 255, 136, 0.1); color: var(--neon-green); border-color: rgba(0, 255, 136, 0.2); }
        .btn-start:hover { background: var(--neon-green); color: #000; }
        .btn-kill { background: rgba(255, 68, 68, 0.1); color: var(--danger); border-color: rgba(255, 68, 68, 0.2); }
        .btn-kill:hover { background: var(--danger); color: #fff; }
        .btn-del { background: rgba(255, 255, 255, 0.05); color: var(--text-muted); }
        .btn-del:hover { background: rgba(255, 68, 68, 0.8); color: #fff; }

        /* Empty State */
        .empty-state { text-align: center; color: var(--text-muted); font-size: 14px; padding: 40px 0; font-style: italic; }
        
        /* Loader */
        #loader { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); backdrop-filter:blur(3px); z-index:999; justify-content:center; align-items:center;}
        .spinner { width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.1); border-top: 4px solid var(--neon-green); border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div id="loader"><div class="spinner"></div></div>

    <div class="container">
        <div class="header">
            <h1>BOT DEPLOYER</h1>
            <p>Premium Cloud Controller</p>
        </div>

        <div class="upload-card">
            <form id="uploadForm">
                <label class="file-drop-area">
                    <input type="file" id="fileInput" name="file" accept=".py" required>
                    <span class="icon">📁</span>
                    <span class="file-label">Tap to Choose .py File</span>
                    <span class="file-name" id="fileName">No file selected</span>
                </label>
                <button type="submit" class="btn btn-deploy">
                    <span>🚀</span> Deploy Bot
                </button>
            </form>
        </div>

        <div class="bot-list" id="botList">
            <!-- Bots will appear here -->
            <div class="empty-state">No bots deployed yet.</div>
        </div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const fileName = document.getElementById('fileName');
        const loader = document.getElementById('loader');

        // File Select Logic
        fileInput.addEventListener('change', function(e) {
            if(e.target.files.length > 0) {
                fileName.innerText = e.target.files[0].name;
                fileName.style.color = '#00ff88';
            } else {
                fileName.innerText = 'No file selected';
                fileName.style.color = '#a1a1aa';
            }
        });

        // Upload Function
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            loader.style.display = 'flex';
            
            const formData = new FormData(this);
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                
                // Custom Toast (Alert replacement)
                alert(data.message); 
                
                this.reset();
                fileName.innerText = 'No file selected';
                fileName.style.color = '#a1a1aa';
                loadBots();
            } catch (error) {
                alert("Upload failed!");
            } finally {
                loader.style.display = 'none';
            }
        });

        // Fetch and Render Bots
        async function loadBots() {
            try {
                const res = await fetch('/status');
                const bots = await res.json();
                const list = document.getElementById('botList');
                
                if (Object.keys(bots).length === 0) {
                    list.innerHTML = '<div class="empty-state">No bots deployed yet.</div>';
                    return;
                }

                list.innerHTML = '';
                for (const [name, isRunning] of Object.entries(bots)) {
                    const card = document.createElement('div');
                    card.className = `bot-card ${isRunning ? 'running' : ''}`;
                    
                    card.innerHTML = `
                        <div class="bot-header">
                            <div class="led ${isRunning ? 'active' : ''}"></div>
                            <div class="bot-name" title="${name}">${name}</div>
                        </div>
                        <div class="status-text ${isRunning ? 'active' : ''}">
                            ${isRunning ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}
                        </div>
                        <div class="actions">
                            <button class="btn btn-act btn-start" onclick="controlBot('${name}', 'start')">▶ Start</button>
                            <button class="btn btn-act btn-kill" onclick="controlBot('${name}', 'kill')">■ Kill</button>
                            <button class="btn btn-act btn-del" onclick="controlBot('${name}', 'delete')">🗑</button>
                        </div>
                    `;
                    list.appendChild(card);
                }
            } catch (e) {
                console.log("Error loading bots:", e);
            }
        }

        // Control Actions (Start, Kill, Delete)
        async function controlBot(filename, action) {
            if (action === 'delete' && !confirm(`Delete ${filename} permanently?`)) return;
            
            loader.style.display = 'flex';
            try {
                const res = await fetch('/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: filename, action: action })
                });
                const data = await res.json();
                if (data.message && action !== 'start' && action !== 'kill') alert(data.message);
                loadBots();
            } catch (error) {
                alert("Action failed!");
            } finally {
                loader.style.display = 'none';
            }
        }

        // Refresh every 3 seconds
        setInterval(loadBots, 3000);
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
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.py')]
    status = {}
    for f in files:
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

    if action == 'start':
        if filename in bot_processes and bot_processes[filename].poll() is None:
            return jsonify({"message": "Bot is already running!"})
        try:
            proc = subprocess.Popen([sys.executable, "-u", filepath], cwd=UPLOAD_FOLDER)
            bot_processes[filename] = proc
            return jsonify({"message": f"{filename} started!"})
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"})

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

    elif action == 'delete':
        if filename in bot_processes and bot_processes[filename].poll() is None:
            bot_processes[filename].kill()
            del bot_processes[filename]
        try:
            os.remove(filepath)
            return jsonify({"message": f"{filename} deleted!"})
        except Exception as e:
            return jsonify({"message": f"Error deleting file!"})

    return jsonify({"message": "Invalid action!"})

# ==========================================
# Main Server
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🚀 PREMIUM PANEL STARTED ON PORT {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
