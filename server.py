import os
import sys
import subprocess
import threading
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
UPLOAD_FOLDER = 'bots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot_processes = {}
bot_logs = {} # বটের লাইভ লগ সেভ করার জন্য

# ==========================================
# Premium UI (HTML + CSS + JS)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Nexus Bot Controller</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #09090b;
            --surface: #18181b;
            --surface-hover: #27272a;
            --border: #3f3f46;
            --text-main: #f4f4f5;
            --text-muted: #a1a1aa;
            
            /* Premium Colors */
            --primary: #6366f1; /* Indigo */
            --primary-glow: rgba(99, 102, 241, 0.3);
            --success: #10b981;
            --danger: #ef4444;
            --cyan: #06b6d4;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; -webkit-tap-highlight-color: transparent; }
        
        body {
            background-color: var(--bg);
            background-image: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #09090b 60%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container { width: 100%; max-width: 480px; }

        /* Header */
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px; }
        .logo { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 20px; }
        .logo-icon { 
            width: 32px; height: 32px; border-radius: 8px; 
            background: linear-gradient(135deg, var(--primary), var(--cyan));
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 0 15px var(--primary-glow);
        }
        .status-badge { font-size: 11px; background: rgba(16, 185, 129, 0.1); color: var(--success); padding: 4px 8px; border-radius: 20px; border: 1px solid rgba(16, 185, 129, 0.2); font-weight: 600; }

        /* Upload Card */
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        
        .upload-area {
            border: 1.5px dashed var(--border); border-radius: 12px; padding: 30px 20px;
            text-align: center; cursor: pointer; transition: all 0.2s; position: relative; margin-bottom: 15px;
        }
        .upload-area:hover { border-color: var(--primary); background: rgba(99, 102, 241, 0.05); }
        .upload-area input[type="file"] { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
        .upload-icon { font-size: 28px; margin-bottom: 10px; }
        .upload-title { font-weight: 600; font-size: 15px; margin-bottom: 4px; }
        .upload-desc { font-size: 12px; color: var(--text-muted); }

        /* Buttons */
        .btn {
            width: 100%; padding: 14px; border: none; border-radius: 10px;
            font-size: 14px; font-weight: 700; cursor: pointer; transition: 0.2s;
            display: flex; align-items: center; justify-content: center; gap: 8px; font-family: inherit;
        }
        .btn:active { transform: scale(0.96); }
        .btn-primary { background: var(--primary); color: #fff; box-shadow: 0 4px 15px var(--primary-glow); }
        .btn-primary:hover { background: #4f46e5; }
        
        /* Bot List */
        .section-title { font-size: 13px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; margin-left: 5px; }
        .bot-list { display: flex; flex-direction: column; gap: 12px; }
        
        .bot-card { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
        .bot-header { display: flex; align-items: center; gap: 10px; }
        
        .led { width: 8px; height: 8px; border-radius: 50%; background: #52525b; }
        .led.active { background: var(--success); box-shadow: 0 0 10px var(--success); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        
        .bot-name { font-weight: 600; font-size: 14px; flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        
        .actions { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; }
        .btn-icon {
            padding: 10px; border-radius: 8px; background: var(--surface-hover); border: 1px solid transparent;
            color: var(--text-main); cursor: pointer; transition: 0.2s; font-size: 14px;
            display: flex; justify-content: center; align-items: center;
        }
        .btn-icon:hover { background: var(--border); }
        .btn-icon.start { color: var(--success); background: rgba(16, 185, 129, 0.1); }
        .btn-icon.start:hover { background: var(--success); color: #000; }
        .btn-icon.kill { color: var(--danger); background: rgba(239, 68, 68, 0.1); }
        .btn-icon.kill:hover { background: var(--danger); color: #fff; }
        .btn-icon.log { color: var(--cyan); background: rgba(6, 182, 212, 0.1); }
        .btn-icon.log:hover { background: var(--cyan); color: #000; }

        /* Console Modal */
        #consoleModal {
            display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8);
            backdrop-filter: blur(5px); z-index: 1000; justify-content: center; align-items: center; padding: 15px;
        }
        .console-box {
            background: #000; border: 1px solid var(--border); border-radius: 12px;
            width: 100%; max-width: 600px; height: 70vh; display: flex; flex-direction: column; overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.8);
        }
        .console-header { padding: 12px 15px; background: var(--surface); border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .console-title { font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
        .console-close { background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; }
        .console-body { 
            padding: 15px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; 
            font-size: 12px; color: #e4e4e7; line-height: 1.5; white-space: pre-wrap; flex-grow: 1;
        }

        /* Toast Notifications */
        #toastContainer { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 2000; display: flex; flex-direction: column; gap: 10px; }
        .toast { 
            background: var(--surface); border: 1px solid var(--border); padding: 12px 20px; 
            border-radius: 8px; font-size: 13px; font-weight: 500; color: #fff;
            box-shadow: 0 10px 20px rgba(0,0,0,0.5); animation: slideDown 0.3s ease;
            display: flex; align-items: center; gap: 8px;
        }
        @keyframes slideDown { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .toast.success { border-left: 3px solid var(--success); }
        .toast.error { border-left: 3px solid var(--danger); }

        /* Loader */
        #loader { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 999; justify-content: center; align-items: center; }
        .spinner { width: 30px; height: 30px; border: 3px solid rgba(255,255,255,0.1); border-top: 3px solid var(--primary); border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div id="toastContainer"></div>
    <div id="loader"><div class="spinner"></div></div>

    <!-- Console Modal -->
    <div id="consoleModal" onclick="if(event.target === this) closeConsole()">
        <div class="console-box">
            <div class="console-header">
                <span class="console-title" id="consoleTitle">Terminal</span>
                <button class="console-close" onclick="closeConsole()">✕</button>
            </div>
            <div class="console-body" id="consoleBody">Connecting to server...</div>
        </div>
    </div>

    <div class="container">
        <div class="header">
            <div class="logo">
                <div class="logo-icon">⚡</div>
                NEXUS HOST
            </div>
            <div class="status-badge">● ONLINE</div>
        </div>

        <div class="card">
            <form id="uploadForm">
                <label class="upload-area" id="dropZone">
                    <input type="file" id="fileInput" name="file" accept=".py" required>
                    <div class="upload-icon">📦</div>
                    <div class="upload-title" id="fileLabel">Upload Bot Script</div>
                    <div class="upload-desc" id="fileDesc">Select a .py file to deploy</div>
                </label>
                <button type="submit" class="btn btn-primary">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/><path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/></svg>
                    Deploy to Server
                </button>
            </form>
        </div>

        <div class="section-title">Active Instances</div>
        <div class="bot-list" id="botList">
            <!-- Bots load here -->
        </div>
    </div>

    <script>
        // File Upload UI
        document.getElementById('fileInput').addEventListener('change', function(e) {
            if(e.target.files.length > 0) {
                document.getElementById('fileLabel').innerText = e.target.files[0].name;
                document.getElementById('fileLabel').style.color = '#6366f1';
                document.getElementById('fileDesc').innerText = 'Ready to deploy';
            }
        });

        // Custom Toast Notification
        function showToast(message, type = 'success') {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `<span>${type === 'success' ? '✅' : '⚠️'}</span> ${message}`;
            container.appendChild(toast);
            setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
        }

        // Upload
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            document.getElementById('loader').style.display = 'flex';
            const formData = new FormData(this);
            
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                showToast(data.message, data.message.includes('Success') ? 'success' : 'error');
                this.reset();
                document.getElementById('fileLabel').innerText = 'Upload Bot Script';
                document.getElementById('fileLabel').style.color = '#f4f4f5';
                document.getElementById('fileDesc').innerText = 'Select a .py file to deploy';
                loadBots();
            } catch (error) {
                showToast("Network Error!", "error");
            } finally {
                document.getElementById('loader').style.display = 'none';
            }
        });

        // Load Bots
        async function loadBots() {
            try {
                const res = await fetch('/status');
                const bots = await res.json();
                const list = document.getElementById('botList');
                
                if (Object.keys(bots).length === 0) {
                    list.innerHTML = '<div style="text-align:center; color:#52525b; font-size:13px; padding:20px;">No bots deployed yet.</div>';
                    return;
                }

                list.innerHTML = '';
                for (const [name, isRunning] of Object.entries(bots)) {
                    const card = document.createElement('div');
                    card.className = `card bot-card`;
                    card.innerHTML = `
                        <div class="bot-header">
                            <div class="led ${isRunning ? 'active' : ''}"></div>
                            <div class="bot-name" title="${name}">${name}</div>
                        </div>
                        <div class="actions">
                            <button class="btn-icon start" onclick="controlBot('${name}', 'start')" title="Start">▶</button>
                            <button class="btn-icon kill" onclick="controlBot('${name}', 'kill')" title="Kill">■</button>
                            <button class="btn-icon log" onclick="viewLog('${name}')" title="Terminal">📟</button>
                            <button class="btn-icon del" onclick="controlBot('${name}', 'delete')" title="Delete">🗑</button>
                        </div>
                    `;
                    list.appendChild(card);
                }
            } catch (e) {}
        }

        // Control Bot (Start, Kill, Delete)
        async function controlBot(filename, action) {
            if (action === 'delete' && !confirm(`Delete ${filename}?`)) return;
            document.getElementById('loader').style.display = 'flex';
            
            try {
                const res = await fetch('/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: filename, action: action })
                });
                const data = await res.json();
                
                if (data.error) {
                    showToast(data.message, 'error');
                    viewLog(filename); // Auto open terminal on crash
                } else {
                    showToast(data.message, 'success');
                }
                loadBots();
            } catch (error) {
                showToast("Action failed!", 'error');
            } finally {
                document.getElementById('loader').style.display = 'none';
            }
        }

        // View Live Terminal
        let logInterval;
        async function viewLog(filename) {
            document.getElementById('consoleTitle').innerText = `Terminal - ${filename}`;
            document.getElementById('consoleModal').style.display = 'flex';
            document.getElementById('consoleBody').innerText = "Fetching logs...\n";
            
            const fetchLog = async () => {
                const res = await fetch(`/logs/${filename}`);
                const data = await res.json();
                const box = document.getElementById('consoleBody');
                box.innerText = data.logs || "Waiting for output...";
                box.scrollTop = box.scrollHeight; // Auto scroll to bottom
            };
            
            await fetchLog();
            clearInterval(logInterval);
            logInterval = setInterval(fetchLog, 1500); // Update logs every 1.5s
        }

        function closeConsole() {
            document.getElementById('consoleModal').style.display = 'none';
            clearInterval(logInterval);
        }

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

@app.route('/logs/<filename>', methods=['GET'])
def get_logs(filename):
    log_file = os.path.join(UPLOAD_FOLDER, f"{filename}.log")
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = f.read()
        return jsonify({"logs": logs})
    return jsonify({"logs": ""})

@app.route('/control', methods=['POST'])
def control_bot():
    data = request.json
    filename = data.get('filename')
    action = data.get('action')
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    log_filepath = os.path.join(UPLOAD_FOLDER, f"{filename}.log")

    if not os.path.exists(filepath):
        return jsonify({"message": "File not found!"})

    if action == 'start':
        if filename in bot_processes and bot_processes[filename].poll() is None:
            return jsonify({"message": "Bot is already running!"})
        
        try:
            # টোকেন বা এনভায়রনমেন্ট ভেরিয়েবল পাস করা
            env = os.environ.copy()
            
            log_file = open(log_filepath, "w")
            proc = subprocess.Popen(
                [sys.executable, "-u", filepath], 
                cwd=UPLOAD_FOLDER,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                env=env
            )
            bot_processes[filename] = proc
            
            # বট ক্র্যাশ করলে ডিটেক্ট করা
            import time
            time.sleep(2) 
            if proc.poll() is not None:
                return jsonify({"message": "Bot crashed! Check Terminal.", "error": True})
                
            return jsonify({"message": f"{filename} started successfully!"})
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}", "error": True})

    elif action == 'kill':
        if filename in bot_processes and bot_processes[filename].poll() is None:
            bot_processes[filename].terminate()
            try:
                bot_processes[filename].wait(timeout=3)
            except:
                bot_processes[filename].kill()
            del bot_processes[filename]
            return jsonify({"message": f"{filename} stopped!"})
        return jsonify({"message": "Bot is not running!"})

    elif action == 'delete':
        if filename in bot_processes and bot_processes[filename].poll() is None:
            bot_processes[filename].kill()
            del bot_processes[filename]
        try:
            os.remove(filepath)
            if os.path.exists(log_filepath):
                os.remove(log_filepath)
            return jsonify({"message": f"{filename} deleted!"})
        except Exception as e:
            return jsonify({"message": f"Error deleting file!"})

    return jsonify({"message": "Invalid action!"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
