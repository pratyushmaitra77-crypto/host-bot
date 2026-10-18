import os
import sys
import subprocess
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
UPLOAD_FOLDER = 'bots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot_processes = {}
bot_logs = {} # বটের আউটপুট সেভ করার জন্য

# ==========================================
# Premium Indigo/Dark Theme HTML, CSS, JS
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#050505">
    <title>BotDeploy | Premium</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #050505;
            --card-bg: rgba(20, 20, 25, 0.8);
            --border: rgba(255, 255, 255, 0.06);
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
            
            /* Premium Purple/Indigo Colors */
            --primary: #7C3AED; 
            --primary-hover: #6D28D9;
            --accent: #06B6D4; 
            
            --danger: #EF4444;
            --success: #10B981;
            --offline: #374151;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; -webkit-tap-highlight-color: transparent; }
        
        body {
            background-color: var(--bg);
            background-image: radial-gradient(circle at 50% -10%, rgba(124, 58, 237, 0.15) 0%, #050505 60%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container { width: 100%; max-width: 450px; }

        /* Header */
        .header { text-align: center; margin-bottom: 30px; padding-top: 15px; }
        .header h1 { 
            font-size: 28px; 
            font-weight: 700; 
            background: linear-gradient(to right, #a78bfa, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
        }
        .header p { font-size: 13px; color: var(--text-muted); font-weight: 500; letter-spacing: 0.5px; }

        /* Cards */
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }

        /* File Upload */
        .upload-area {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            padding: 30px 20px;
            border: 1.5px dashed rgba(124, 58, 237, 0.4);
            border-radius: 16px;
            background: rgba(124, 58, 237, 0.02);
            transition: all 0.3s; cursor: pointer; position: relative;
            margin-bottom: 15px;
        }
        .upload-area:hover { background: rgba(124, 58, 237, 0.08); border-color: var(--primary); }
        .upload-area input[type="file"] { position: absolute; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        
        .upload-icon { font-size: 32px; margin-bottom: 12px; color: var(--primary); }
        .upload-text { font-size: 14px; font-weight: 600; color: var(--text-main); }
        .file-name { font-size: 12px; color: var(--text-muted); margin-top: 4px; word-break: break-all; }

        /* Buttons */
        .btn {
            width: 100%; padding: 15px; border: none; border-radius: 14px;
            font-size: 15px; font-weight: 700; cursor: pointer; transition: 0.2s;
            display: flex; align-items: center; justify-content: center; gap: 8px;
        }
        .btn:active { transform: scale(0.97); }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), #4F46E5);
            color: #fff;
            box-shadow: 0 8px 20px rgba(124, 58, 237, 0.3);
        }
        .btn-primary:hover { background: linear-gradient(135deg, var(--primary-hover), #4338CA); }

        /* Bot List */
        .bot-list { display: flex; flex-direction: column; gap: 12px; }
        .bot-card { padding: 18px; display: flex; flex-direction: column; gap: 15px; }
        
        .bot-header { display: flex; align-items: center; gap: 12px; }
        .led { width: 10px; height: 10px; border-radius: 50%; background: var(--offline); transition: 0.3s; }
        .led.active { 
            background: var(--success); 
            box-shadow: 0 0 12px var(--success);
            animation: glow 2s infinite alternate;
        }
        @keyframes glow { from { box-shadow: 0 0 5px var(--success); } to { box-shadow: 0 0 15px var(--success); } }

        .bot-name { font-size: 15px; font-weight: 600; flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        
        .actions { display: flex; gap: 8px; }
        .btn-icon {
            padding: 10px; border-radius: 10px; border: 1px solid transparent;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; transition: 0.2s; background: transparent; font-size: 16px;
        }
        .btn-icon.start { background: rgba(16, 185, 129, 0.1); color: var(--success); border-color: rgba(16, 185, 129, 0.2); }
        .btn-icon.start:hover { background: var(--success); color: #000; }
        .btn-icon.kill { background: rgba(239, 68, 68, 0.1); color: var(--danger); border-color: rgba(239, 68, 68, 0.2); }
        .btn-icon.kill:hover { background: var(--danger); color: #fff; }
        .btn-icon.logs { background: rgba(255, 255, 255, 0.05); color: var(--text-muted); }
        .btn-icon.logs:hover { background: rgba(255, 255, 255, 0.15); color: #fff; }
        .btn-icon.del { background: rgba(255, 255, 255, 0.05); color: var(--text-muted); }
        .btn-icon.del:hover { background: rgba(239, 68, 68, 0.8); color: #fff; }

        /* Log Modal */
        #logModal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8); backdrop-filter: blur(5px); z-index: 1000;
            justify-content: center; align-items: center; padding: 20px;
        }
        .modal-content {
            background: #0f0f13; border: 1px solid var(--border);
            width: 100%; max-width: 500px; border-radius: 16px;
            display: flex; flex-direction: column; max-height: 80vh;
        }
        .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; border-bottom: 1px solid var(--border); }
        .modal-header h3 { font-size: 16px; color: var(--text-main); }
        .close-btn { background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; }
        .log-body { padding: 15px 20px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px; color: #a78bfa; white-space: pre-wrap; }

        /* Loader */
        #loader { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:999; justify-content:center; align-items:center;}
        .spinner { width: 35px; height: 35px; border: 3px solid rgba(255,255,255,0.1); border-top: 3px solid var(--primary); border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div id="loader"><div class="spinner"></div></div>

    <!-- Logs Modal -->
    <div id="logModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="logTitle">Bot Logs</h3>
                <button class="close-btn" onclick="closeModal()">✕</button>
            </div>
            <div class="log-body" id="logContent">Loading logs...</div>
        </div>
    </div>

    <div class="container">
        <div class="header">
            <h1>BotDeploy Pro</h1>
            <p>Premium Server Controller</p>
        </div>

        <div class="card">
            <form id="uploadForm">
                <label class="upload-area">
                    <input type="file" id="fileInput" name="file" accept=".py" required>
                    <span class="upload-icon">📁</span>
                    <span class="upload-text">Tap to choose file</span>
                    <span class="file-name" id="fileName">Only .py files allowed</span>
                </label>
                <button type="submit" class="btn btn-primary">
                    <span>🚀</span> Deploy Script
                </button>
            </form>
        </div>

        <div class="bot-list" id="botList">
            <!-- Bots load here -->
        </div>
    </div>

    <script>
        // File Selection
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const fileName = document.getElementById('fileName');
            if(e.target.files.length > 0) {
                fileName.innerText = e.target.files[0].name;
                fileName.style.color = '#a78bfa';
            } else {
                fileName.innerText = 'Only .py files allowed';
                fileName.style.color = '#9CA3AF';
            }
        });

        // Upload
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            document.getElementById('loader').style.display = 'flex';
            
            const formData = new FormData(this);
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                alert(data.message); 
                this.reset();
                document.getElementById('fileName').innerText = 'Only .py files allowed';
                document.getElementById('fileName').style.color = '#9CA3AF';
                loadBots();
            } catch (error) {
                alert("Upload failed!");
            } finally {
                document.getElementById('loader').style.display = 'none';
            }
        });

        // Render Bot List
        async function loadBots() {
            try {
                const res = await fetch('/status');
                const bots = await res.json();
                const list = document.getElementById('botList');
                
                if (Object.keys(bots).length === 0) {
                    list.innerHTML = '';
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
                            <button class="btn-icon logs" onclick="viewLogs('${name}')" title="Console Logs">📄</button>
                            <button class="btn-icon del" onclick="controlBot('${name}', 'delete')" title="Delete">🗑</button>
                        </div>
                    `;
                    list.appendChild(card);
                }
            } catch (e) {}
        }

        // Control Bot
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
                
                // Show error in alert if bot crashes
                if(action === 'start' && data.error) {
                    alert("Bot crashed! Check Logs for details.");
                    viewLogs(filename); // Auto open logs
                }
                loadBots();
            } catch (error) {} finally {
                document.getElementById('loader').style.display = 'none';
            }
        }

        // View Logs
        async function viewLogs(filename) {
            document.getElementById('logTitle').innerText = `Console: ${filename}`;
            document.getElementById('logContent').innerText = "Loading...";
            document.getElementById('logModal').style.display = 'flex';

            const res = await fetch(`/logs/${filename}`);
            const data = await res.json();
            document.getElementById('logContent').innerText = data.logs || "No output generated yet.";
        }

        function closeModal() {
            document.getElementById('logModal').style.display = 'none';
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
    # Read logs from file
    log_file = os.path.join(UPLOAD_FOLDER, f"{filename}.log")
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = f.read()
        return jsonify({"logs": logs})
    return jsonify({"logs": "Log file not found. Start the bot first."})

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
            # Save stdout and stderr to a log file
            log_file = open(log_filepath, "w")
            proc = subprocess.Popen(
                [sys.executable, "-u", filepath], 
                cwd=UPLOAD_FOLDER,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True
            )
            bot_processes[filename] = proc
            
            # Give it a second to crash if modules are missing
            import time
            time.sleep(1.5) 
            
            if proc.poll() is not None:
                # Process died immediately
                return jsonify({"message": "Bot crashed on startup!", "error": True})
                
            return jsonify({"message": f"{filename} started!"})
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
            return jsonify({"message": f"{filename} killed!"})
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
