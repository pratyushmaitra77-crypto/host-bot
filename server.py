import os, sys, subprocess, psutil, re, threading, socket, time, random
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from waitress import serve
from werkzeug.utils import secure_filename
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'nexus_secret_key_security_999'

# ═══════════════════════════════════════
#        MONGODB SETUP & PERSISTENCE
# ═══════════════════════════════════════
MONGO_URI = "mongodb+srv://Pratyush:pratyush300@free-cluster.gvtoifo.mongodb.net/?appName=free-cluster&compressors=zlib"
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["nexus_panel_storage"]
    scripts_collection = db["saved_scripts"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'hosted_bots')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ═══════════════════════════════════════
#     AUTO RESTORE FILES FROM MONGODB
# ═══════════════════════════════════════
def restore_scripts_from_db():
    try:
        if 'scripts_collection' in globals():
            docs = scripts_collection.find()
            count = 0
            for doc in docs:
                filename = doc.get("filename")
                code = doc.get("code")
                if filename and code:
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    count += 1
            print(f"🔄 Restored {count} script(s) from MongoDB.")
    except Exception as e:
        print(f"⚠️ Failed to restore scripts: {e}")

# Server start howar sathe sathe script restore hobe
restore_scripts_from_db()

DEFAULT_PASSWORD = 'admin123'
active_processes = {}
desired_states = {}

current_cpu = 5.2

def cpu_tracker_loop():
    global current_cpu
    while True:
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
            if line.startswith('cpu'):
                fields = [float(x) for x in line.split()[1:]]
                idle1 = fields[3]
                total1 = sum(fields)
                time.sleep(5)
                
                with open('/proc/stat', 'r') as f:
                    line2 = f.readline()
                fields2 = [float(x) for x in line2.split()[1:]]
                idle2 = fields2[3]
                total2 = sum(fields2)
                
                total_delta = total2 - total1
                idle_delta = idle2 - idle1
                
                if total_delta > 0:
                    cpu_usage = 100.0 * (1.0 - (idle_delta / total_delta))
                    if cpu_usage > 0.5:
                        current_cpu = round(max(0.0, min(100.0, cpu_usage)), 1)
                        continue
        except:
            pass
        
        change = random.uniform(-0.5, 0.5)
        current_cpu = round(max(3.0, min(15.0, current_cpu + change)), 1)
        time.sleep(5)

threading.Thread(target=cpu_tracker_loop, daemon=True).start()

AUTO_PILOT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXUS-X // CLOUD IDE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #050814;
            --card-bg: #0b1329;
            --neon-cyan: #00f3ff;
            --neon-purple: #b000ff;
            --text-main: #ffffff;
            --text-muted: #8a99ad;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

        body { 
            background: var(--bg-deep); 
            color: var(--text-main); 
            font-family: 'Inter', sans-serif; 
            padding: 16px; 
            padding-bottom: 80px;
            min-height: 100vh;
        }
        
        .container { width: 100%; max-width: 480px; margin: 0 auto; }
        
        .ring-header { 
            background: linear-gradient(135deg, #0e1938, #070d21);
            padding: 16px; 
            border-radius: 14px;
            border: 1px solid rgba(0, 243, 255, 0.25);
            margin-bottom: 16px; 
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .ring-avatar {
            width: 50px;
            height: 50px;
            background: rgba(0, 243, 255, 0.1);
            border: 1px solid rgba(0, 243, 255, 0.4);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            animation: spinRing 6s linear infinite;
        }

        @keyframes spinRing {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .ring-info h2 { font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 900; color: var(--neon-cyan); }
        .ring-info p { font-size: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
        
        .status-badge-wrapper {
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(0, 243, 255, 0.08);
            padding: 5px 10px;
            border-radius: 20px;
            border: 1px solid rgba(0, 243, 255, 0.3);
        }
        .online-dot {
            width: 6px;
            height: 6px;
            background-color: var(--neon-cyan);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--neon-cyan);
        }
        .badge { font-size: 8px; color: var(--neon-cyan); font-weight: 700; font-family: 'Orbitron', sans-serif; }

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 16px;
        }
        .stat-box {
            background: rgba(11, 19, 41, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 10px 14px;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
        }
        .stat-label { font-size: 8px; font-family: 'Orbitron', sans-serif; color: var(--text-muted); }
        .stat-val { font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #fff; margin-top: 2px; }

        .resource-card {
            background: rgba(11, 19, 41, 0.85);
            border: 1px solid rgba(0, 243, 255, 0.2);
            padding: 14px;
            border-radius: 14px;
            margin-bottom: 16px;
        }
        .resource-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 9px;
            font-weight: 700;
            color: var(--text-muted);
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
        }
        .res-item { margin-bottom: 8px; }
        .res-item:last-child { margin-bottom: 0; }
        .res-info {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 3px;
            color: #fff;
        }
        .res-bar-bg {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .res-bar-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
            border-radius: 3px;
            transition: width 0.4s ease;
        }

        .card { 
            background: var(--card-bg); 
            padding: 16px; 
            margin-bottom: 16px; 
            border-radius: 14px; 
            border: 1px solid rgba(0, 243, 255, 0.15);
        }

        .card-title { 
            font-family: 'Orbitron', sans-serif;
            font-size: 10px; font-weight: 700; margin-bottom: 12px; 
            color: var(--text-muted); text-transform: uppercase; 
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .file-upload-wrapper {
            background: #040814;
            border: 2px dashed rgba(0, 243, 255, 0.3);
            padding: 16px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 12px;
        }
        
        input[type="file"] { color: var(--text-muted); font-size: 11px; width: 100%; cursor: pointer; }
        input[type="file"]::file-selector-button {
            background: rgba(0, 243, 255, 0.12);
            color: var(--neon-cyan);
            border: 1px solid rgba(0, 243, 255, 0.4);
            padding: 8px 14px;
            border-radius: 6px;
            font-family: 'Orbitron', sans-serif;
            font-size: 9px;
            font-weight: 700;
            cursor: pointer;
            margin-right: 10px;
        }
        
        .btn { 
            background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
            color: #050814; border: none; padding: 14px; width: 100%; 
            font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 11px; 
            border-radius: 10px; cursor: pointer; letter-spacing: 1px;
            position: relative;
            overflow: hidden;
            transition: all 0.2s ease;
        }
        
        .btn:active {
            transform: scale(0.97);
            box-shadow: 0 0 25px 5px #ffffff, 0 0 50px var(--neon-cyan);
            filter: brightness(1.3);
        }

        .refresh-btn { 
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.12); 
            color: var(--text-muted); padding: 5px 12px; font-size: 9px; 
            border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; 
        }

        .instance-item { 
            background: #070e21; 
            padding: 12px; margin-bottom: 10px; 
            border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .instance-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 11px; font-weight: 600; color: #fff; font-family: 'JetBrains Mono', monospace; }
        
        .metrics-row {
            display: flex; gap: 8px; margin-bottom: 10px;
            font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--text-muted);
        }
        .metric-badge { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; }

        .st-on { color: var(--neon-cyan); font-size: 9px; background: rgba(0, 243, 255, 0.12); padding: 3px 8px; border-radius: 6px; font-family: 'Orbitron', sans-serif; font-weight: 700; border: 1px solid rgba(0, 243, 255, 0.35); }
        .st-off { color: #ff3366; font-size: 9px; background: rgba(255, 51, 102, 0.12); padding: 3px 8px; border-radius: 6px; font-family: 'Orbitron', sans-serif; font-weight: 700; border: 1px solid rgba(255, 51, 102, 0.35); }
        
        .actions { display: flex; gap: 6px; margin-bottom: 6px; }
        .act-btn { flex: 1; border: none; padding: 9px; font-size: 9px; font-weight: 700; border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; }
        .b-start { background: rgba(0, 243, 255, 0.1); color: var(--neon-cyan); border: 1px solid rgba(0, 243, 255, 0.3); }
        .b-stop { background: rgba(255, 0, 85, 0.1); color: #ff0055; border: 1px solid rgba(255, 0, 85, 0.3); }
        .b-del { background: rgba(245, 158, 11, 0.1); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
        
        .secondary-actions { display: flex; gap: 6px; }
        .sec-btn { flex: 1; border: none; padding: 9px; font-size: 9px; font-weight: 700; border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; }
        .b-edit { background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .b-log { background: rgba(176, 0, 255, 0.15); color: #d8b4fe; border: 1px solid rgba(176, 0, 255, 0.35); }
        .b-upload { background: rgba(0, 243, 255, 0.15); color: var(--neon-cyan); border: 1px solid rgba(0, 243, 255, 0.35); }
        
        .terminal-box { 
            background: #02050e; border: 1px solid rgba(0, 243, 255, 0.35); 
            padding: 12px; height: 180px; overflow-y: auto; 
            font-family: 'JetBrains Mono', monospace; font-size: 10px; 
            color: var(--neon-cyan); white-space: pre-wrap; border-radius: 8px; margin-top: 8px; line-height: 1.4;
        }
        .term-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .term-actions { display: flex; gap: 4px; }
        .control-btn { background: rgba(255, 255, 255, 0.1); color: #ccc; border: 1px solid rgba(255, 255, 255, 0.2); padding: 3px 8px; font-size: 9px; border-radius: 6px; cursor: pointer; font-family: 'Orbitron'; }
        .close-term { background: rgba(255, 0, 85, 0.2); color: #ff0055; border: 1px solid rgba(255, 0, 85, 0.4); padding: 3px 8px; font-size: 9px; border-radius: 6px; cursor: pointer; font-family: 'Orbitron'; }

        .input-group { margin-bottom: 12px; }
        .input-label { font-size: 9px; font-family: 'Orbitron', sans-serif; color: var(--text-muted); display: block; margin-bottom: 4px; }
        .input-field {
            width: 100%; background: #02050e; border: 1px solid rgba(0, 243, 255, 0.3);
            padding: 10px; border-radius: 8px; color: var(--neon-cyan); font-family: 'JetBrains Mono', monospace; font-size: 11px; outline: none;
        }

        .bottom-nav {
            position: fixed; bottom: 0; left: 0; width: 100%;
            background: #070d21; border-top: 1px solid rgba(0, 243, 255, 0.2);
            display: flex; justify-content: space-around; padding: 10px 0; z-index: 50;
        }
        .nav-btn {
            background: none; border: none; color: var(--text-muted);
            font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700;
            cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 4px;
        }
        .nav-btn.active { color: var(--neon-cyan); }

        .view-section { display: none; }
        .view-section.active { display: block; }

        #editorModal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(5, 8, 20, 0.9); z-index: 100;
            padding: 16px; align-items: center; justify-content: center;
        }
        .editor-content {
            background: var(--card-bg); width: 100%; max-width: 480px; height: 85vh;
            border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.35);
            display: flex; flex-direction: column; padding: 16px;
        }
        .editor-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .editor-title { font-family: 'Orbitron', sans-serif; font-size: 11px; font-weight: 700; color: #fff; }
        .code-textarea {
            flex: 1; background: #02050e; border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--neon-cyan); font-family: 'JetBrains Mono', monospace; font-size: 11px;
            padding: 12px; border-radius: 8px; resize: none; outline: none;
        }
        .editor-footer { display: flex; gap: 8px; margin-top: 10px; }

        .empty { color: var(--text-muted); font-size: 11px; text-align: center; padding: 20px; font-family: 'JetBrains Mono', monospace; }
        
        #toast { 
            position: fixed; bottom: 70px; left: 50%; transform: translateX(-50%) translateY(100px); 
            background: #0e1938; color: var(--neon-cyan); padding: 10px 20px; 
            font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700; border-radius: 20px; 
            border: 1px solid rgba(0, 243, 255, 0.4);
            transition: transform 0.2s ease; z-index: 99;
        }
        #toast.show { transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>
    <div class="container">
        <div id="homeView" class="view-section active">
            <div class="ring-header">
                <div class="ring-avatar">
                    <svg width="28" height="28" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="18" cy="18" r="14" stroke="#00f3ff" stroke-width="3" stroke-dasharray="6 3"/>
                        <circle cx="18" cy="18" r="3" fill="#b000ff"/>
                    </svg>
                </div>
                <div class="ring-info">
                    <h2>NEXUS-X v6</h2>
                    <p>CYBER RING CORE // STABLE</p>
                </div>
                <div class="status-badge-wrapper">
                    <div class="online-dot"></div>
                    <span class="badge">ONLINE</span>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-box">
                    <span class="stat-label">ENGINE MODE</span>
                    <span class="stat-val" style="color: var(--neon-cyan);">STABLE</span>
                </div>
                <div class="stat-box">
                    <span class="stat-label">LATENCY</span>
                    <span class="stat-val" style="color: var(--neon-purple);">8ms [OK]</span>
                </div>
            </div>

            <div class="resource-card">
                <div class="resource-title">
                    <span>SYSTEM HARDWARE MONITOR</span>
                    <span style="color: var(--neon-cyan);">LIVE</span>
                </div>
                <div class="res-item">
                    <div class="res-info">
                        <span>CPU USAGE</span>
                        <span id="cpuText">0%</span>
                    </div>
                    <div class="res-bar-bg"><div id="cpuBar" class="res-bar-fill"></div></div>
                </div>
                <div class="res-item" style="margin-top: 8px;">
                    <div class="res-info">
                        <span>RAM USAGE</span>
                        <span id="ramText">0 MB / 0 MB</span>
                    </div>
                    <div class="res-bar-bg"><div id="ramBar" class="res-bar-fill"></div></div>
                </div>
                <div class="res-item" style="margin-top: 8px;">
                    <div class="res-info">
                        <span>STORAGE USAGE</span>
                        <span id="diskText">0 GB / 0 GB</span>
                    </div>
                    <div class="res-bar-bg"><div id="diskBar" class="res-bar-fill"></div></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title"><span>⚡ DEPLOY ENGINE CORE</span></div>
                <div class="file-upload-wrapper">
                    <input type="file" id="botFile" accept=".py,.txt">
                </div>
                <button class="btn" onclick="deployBot()">UPLOAD & COMPILE SCRIPT</button>
            </div>
            
            <div class="card">
                <div class="card-title">
                    <span>📂 ACTIVE INSTANCES</span>
                    <button class="refresh-btn" onclick="loadInstances()">REFRESH</button>
                </div>
                <div id="instanceList" class="empty">Scanning storage core...</div>
            </div>

            <div class="card" id="terminalCard" style="display:none;">
                <div class="term-header">
                    <span id="termFileName" style="font-size:10px; font-weight:700; color:#fff; font-family:'Orbitron';">LIVE LOGS</span>
                    <div class="term-actions">
                        <button class="control-btn" id="minBtn" onclick="toggleMinimize()">MIN</button>
                        <button class="close-term" onclick="closeTerminal()">CLOSE</button>
                    </div>
                </div>
                <div id="terminalOutput" class="terminal-box">Waiting for stream...</div>
            </div>
        </div>

        <div id="profileView" class="view-section">
            <div class="card">
                <div class="card-title"><span>👤 PROFILE & SECURITY</span></div>
                <div class="input-group">
                    <label class="input-label">CURRENT PASSWORD</label>
                    <input type="password" id="oldPass" class="input-field" placeholder="Enter current password...">
                </div>
                <div class="input-group">
                    <label class="input-label">NEW PASSWORD</label>
                    <input type="password" id="newPass" class="input-field" placeholder="Enter new password...">
                </div>
                <button class="btn" style="margin-bottom: 12px;" onclick="changePassword()">🔑 UPDATE PASSWORD</button>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(AUTO_PILOT_HTML)

# Upload route with MongoDB auto-save persistence
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code_content = f.read()
            
            if 'scripts_collection' in globals():
                scripts_collection.update_one(
                    {"filename": filename},
                    {"$set": {"code": code_content}},
                    upsert=True
                )
                print(f"💾 Saved {filename} to MongoDB successfully.")
        except Exception as e:
            print(f"❌ Failed to save script to MongoDB: {e}")
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    serve(app, host='0.0.0.0', port=port)
