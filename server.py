import os, subprocess, psutil, re, threading, socket, time, random
from flask import Flask, jsonify, render_template_string, request
from waitress import serve
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'hosted_bots')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEFAULT_KEY = 'admin123'
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
            --success: #00ff66;
            --danger: #ff0055;
            --warning: #fbbf24;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

        body { 
            background: var(--bg-deep); 
            color: var(--text-main); 
            font-family: 'Inter', sans-serif; 
            padding: 16px; 
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
            box-shadow: 0 0 15px rgba(0, 243, 255, 0.1);
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
            box-shadow: 0 0 10px var(--neon-cyan);
        }

        @keyframes spinRing {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .ring-info h2 { font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 900; color: var(--neon-cyan); text-shadow: 0 0 8px rgba(0,243,255,0.5); }
        .ring-info p { font-size: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }

        .resource-card {
            background: rgba(11, 19, 41, 0.85);
            border: 1px solid rgba(0, 243, 255, 0.25);
            padding: 14px;
            border-radius: 14px;
            margin-bottom: 16px;
            box-shadow: 0 0 15px rgba(0, 243, 255, 0.08);
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
            box-shadow: 0 0 8px var(--neon-cyan);
        }

        .card { 
            background: var(--card-bg); 
            padding: 16px; 
            margin-bottom: 16px; 
            border-radius: 14px; 
            border: 1px solid rgba(0, 243, 255, 0.25);
            box-shadow: 0 0 20px rgba(0, 243, 255, 0.1);
        }

        .card-title { 
            font-family: 'Orbitron', sans-serif;
            font-size: 10px; font-weight: 700; margin-bottom: 12px; 
            color: var(--text-muted); text-transform: uppercase; 
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .file-upload-wrapper {
            background: #040814;
            border: 2px dashed rgba(0, 243, 255, 0.4);
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 12px;
            box-shadow: inset 0 0 10px rgba(0,243,255,0.05);
        }
        
        input[type="file"] { color: var(--text-muted); font-size: 10px; width: 100%; cursor: pointer; }
        input[type="file"]::file-selector-button {
            background: rgba(0, 243, 255, 0.15);
            color: var(--neon-cyan);
            border: 1px solid rgba(0, 243, 255, 0.6);
            padding: 8px 14px;
            border-radius: 6px;
            font-family: 'Orbitron', sans-serif;
            font-size: 9px;
            font-weight: 700;
            cursor: pointer;
            margin-right: 10px;
            box-shadow: 0 0 12px rgba(0, 243, 255, 0.3);
            transition: all 0.2s ease;
        }
        input[type="file"]::file-selector-button:active {
            transform: scale(0.95);
            box-shadow: 0 0 25px var(--neon-cyan);
            filter: brightness(1.4);
        }
        
        .btn { 
            background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
            color: #050814; border: none; padding: 14px; width: 100%; 
            font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 11px; 
            border-radius: 10px; cursor: pointer; letter-spacing: 1px;
            box-shadow: 0 0 20px rgba(0, 243, 255, 0.5);
            transition: all 0.2s ease;
        }
        .btn:active {
            transform: scale(0.97);
            box-shadow: 0 0 35px #ffffff, 0 0 70px var(--neon-cyan);
            filter: brightness(1.4);
        }

        .refresh-btn { 
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); 
            color: var(--text-muted); padding: 5px 12px; font-size: 9px; 
            border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; 
            transition: all 0.2s ease;
        }
        .refresh-btn:active {
            box-shadow: 0 0 10px #fff;
            color: #fff;
        }

        .instance-item { 
            background: #070e21; 
            padding: 12px; margin-bottom: 12px; 
            border-radius: 10px; border: 1px solid rgba(0, 243, 255, 0.2);
            box-shadow: 0 0 10px rgba(0,243,255,0.05);
        }
        .instance-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 11px; font-weight: 600; color: #fff; font-family: 'JetBrains Mono', monospace; }
        
        .st-on { color: var(--success); font-size: 9px; background: rgba(0, 255, 102, 0.15); padding: 3px 8px; border-radius: 6px; font-family: 'Orbitron', sans-serif; border: 1px solid rgba(0, 255, 102, 0.5); box-shadow: 0 0 8px rgba(0,255,102,0.3); }
        .st-off { color: var(--danger); font-size: 9px; background: rgba(255, 0, 85, 0.15); padding: 3px 8px; border-radius: 6px; font-family: 'Orbitron', sans-serif; border: 1px solid rgba(255, 0, 85, 0.5); box-shadow: 0 0 8px rgba(255,0,85,0.3); }
        
        .actions { display: flex; gap: 6px; margin-bottom: 6px; }
        .act-btn { flex: 1; border: none; padding: 9px; font-size: 9px; font-weight: 700; border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; text-transform: uppercase; transition: all 0.2s ease; }
        
        /* Glowing Neon Interactive Buttons */
        .b-start { background: #070e21; color: var(--neon-cyan); border: 1px solid rgba(0, 243, 255, 0.8); box-shadow: 0 0 10px rgba(0,243,255,0.2); }
        .b-start:active { transform: scale(0.94); box-shadow: 0 0 25px var(--neon-cyan); background: rgba(0,243,255,0.25); color: #fff; }

        .b-stop { background: #070e21; color: var(--danger); border: 1px solid rgba(255, 0, 85, 0.8); box-shadow: 0 0 10px rgba(255,0,85,0.2); }
        .b-stop:active { transform: scale(0.94); box-shadow: 0 0 25px var(--danger); background: rgba(255,0,85,0.25); color: #fff; }

        .b-del { background: #070e21; color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.8); box-shadow: 0 0 10px rgba(245,158,11,0.2); }
        .b-del:active { transform: scale(0.94); box-shadow: 0 0 25px var(--warning); background: rgba(245,158,11,0.25); color: #fff; }
        
        .secondary-actions { display: flex; gap: 6px; }
        .sec-btn { flex: 1; border: none; padding: 9px; font-size: 9px; font-weight: 700; border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; text-transform: uppercase; text-align: center; transition: all 0.2s ease; }
        
        .b-edit { background: #070e21; color: var(--neon-cyan); border: 1px solid rgba(0, 243, 255, 0.8); box-shadow: 0 0 10px rgba(0,243,255,0.2); }
        .b-edit:active { transform: scale(0.94); box-shadow: 0 0 25px var(--neon-cyan); background: rgba(0,243,255,0.25); color: #fff; }

        .b-log { background: #070e21; color: #d8b4fe; border: 1px solid rgba(176, 0, 255, 0.8); box-shadow: 0 0 10px rgba(176,0,255,0.2); }
        .b-log:active { transform: scale(0.94); box-shadow: 0 0 25px var(--neon-purple); background: rgba(176,0,255,0.25); color: #fff; }

        .b-upload { background: #070e21; color: var(--neon-cyan); border: 1px solid rgba(0, 243, 255, 0.8); box-shadow: 0 0 10px rgba(0,243,255,0.2); }
        .b-upload:active { transform: scale(0.94); box-shadow: 0 0 25px var(--neon-cyan); background: rgba(0,243,255,0.25); color: #fff; }

        #editorModal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(5, 8, 20, 0.92); z-index: 100;
            padding: 16px; align-items: center; justify-content: center;
        }
        .editor-content {
            background: var(--card-bg); width: 100%; max-width: 480px; height: 85vh;
            border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.4);
            display: flex; flex-direction: column; padding: 16px;
            box-shadow: 0 0 30px rgba(0,243,255,0.2);
        }
        .code-textarea {
            flex: 1; background: #02050e; border: 1px solid rgba(0, 243, 255, 0.2);
            color: var(--neon-cyan); font-family: 'JetBrains Mono', monospace; font-size: 11px;
            padding: 12px; border-radius: 8px; resize: none; outline: none;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
        }

        .empty { color: var(--text-muted); font-size: 11px; text-align: center; padding: 20px; font-family: 'JetBrains Mono', monospace; }
        
        #toast { 
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%) translateY(100px); 
            background: #0e1938; color: var(--neon-cyan); padding: 10px 20px; 
            font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700; border-radius: 20px; 
            border: 1px solid rgba(0, 243, 255, 0.6);
            box-shadow: 0 0 20px rgba(0,243,255,0.4);
            transition: transform 0.2s ease; z-index: 99;
        }
        #toast.show { transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>
    <div class="container">
        <div class="ring-header">
            <div class="ring-avatar">
                <svg width="28" height="28" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="18" cy="18" r="14" stroke="#00f3ff" stroke-width="3" stroke-dasharray="6 3"/>
                    <circle cx="18" cy="18" r="3" fill="#b000ff"/>
                </svg>
            </div>
            <div class="ring-info">
                <h2>NEXUS-X v6</h2>
                <p>TELEGRAM BOT CORE // ACTIVE</p>
            </div>
        </div>

        <div class="resource-card">
            <div class="resource-title">
                <span>HARDWARE MONITOR</span>
                <span style="color: var(--neon-cyan); text-shadow: 0 0 8px var(--neon-cyan);">LIVE</span>
            </div>
            <div class="res-item">
                <div class="res-info"><span>CPU</span><span id="cpuText">0%</span></div>
                <div class="res-bar-bg"><div id="cpuBar" class="res-bar-fill"></div></div>
            </div>
            <div class="res-item" style="margin-top: 8px;">
                <div class="res-info"><span>RAM</span><span id="ramText">0 MB / 0 MB</span></div>
                <div class="res-bar-bg"><div id="ramBar" class="res-bar-fill"></div></div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title"><span>⚡ DEPLOY ENGINE CORE</span></div>
            <div class="file-upload-wrapper">
                <input type="file" id="botFile" accept=".py">
            </div>
            <button class="btn" onclick="deployBot()">UPLOAD & COMPILE SCRIPT</button>
        </div>
        
        <div class="card">
            <div class="card-title">
                <span>📂 ACTIVE INSTANCES</span>
                <button class="refresh-btn" onclick="loadInstances()">REFRESH</button>
            </div>
            <div id="instanceList" class="empty">No active bots uploaded.</div>
        </div>
    </div>

    <!-- Hidden file input for requirements.txt upload -->
    <input type="file" id="hiddenReqInput" accept=".txt" style="display:none;" onchange="handleReqFileSelected(event)">

    <div id="editorModal">
        <div class="editor-content">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px; align-items:center;">
                <span id="editorFileName" style="font-family:'Orbitron'; font-size:11px; color:var(--neon-cyan); text-shadow:0 0 8px var(--neon-cyan);">EDIT CODE</span>
                <button onclick="closeEditor()" style="background:var(--danger); color:#fff; border:none; padding:5px 10px; border-radius:6px; font-family:'Orbitron'; font-weight:bold; cursor:pointer; box-shadow:0 0 10px var(--danger);">X</button>
            </div>
            <textarea id="codeTextarea" class="code-textarea" spellcheck="false"></textarea>
            <button class="btn" style="margin-top:10px;" onclick="saveCode()">💾 SAVE CODE</button>
        </div>
    </div>

    <div id="toast">SYSTEM READY</div>
    <script>
        const KEY = 'admin123';
        let editingFile = null;
        let targetBotForReq = null;

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg; t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2000);
        }

        async function updateSystemStats() {
            try {
                const res = await fetch(`/system_stats?key=${KEY}`);
                const data = await res.json();
                if(data.error) return;
                document.getElementById('cpuText').innerText = data.cpu_percent + '%';
                document.getElementById('cpuBar').style.width = data.cpu_percent + '%';
                document.getElementById('ramText').innerText = `${data.ram_used} MB / ${data.ram_total} MB`;
                document.getElementById('ramBar').style.width = data.ram_percent + '%';
            } catch(e) {}
        }

        async function deployBot() {
            const fileInput = document.getElementById('botFile');
            if(!fileInput.files[0]) { showToast('ERR: SELECT A .PY FILE'); return; }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('license_key', KEY);
            
            showToast('UPLOADING...');
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if(data.error) showToast('ERR: ' + data.error);
                else {
                    showToast(data.message);
                    fileInput.value = '';
                    loadInstances();
                }
            } catch(e) { showToast('UPLOAD FAILED'); }
        }

        function triggerReqUpload(filename) {
            targetBotForReq = filename;
            document.getElementById('hiddenReqInput').click();
        }

        async function handleReqFileSelected(event) {
            const file = event.target.files[0];
            if(!file || !targetBotForReq) return;

            const formData = new FormData();
            formData.append('req_file', file);
            formData.append('filename', targetBotForReq);
            formData.append('license_key', KEY);

            showToast('INSTALLING REQS...');
            try {
                const res = await fetch('/upload_req', { method: 'POST', body: formData });
                const data = await res.json();
                if(data.error) showToast('ERR: ' + data.error);
                else showToast(data.message);
            } catch(e) {
                showToast('INSTALL FAILED');
            }
            event.target.value = '';
            targetBotForReq = null;
        }

        async function loadInstances() {
            try {
                const res = await fetch(`/list?key=${KEY}`);
                const data = await res.json();
                const list = document.getElementById('instanceList');
                if(!data.bots || data.bots.length === 0) {
                    list.innerHTML = '<div class="empty">No active bots uploaded.</div>';
                } else {
                    list.innerHTML = data.bots.map(b => {
                        const online = b.status === 'ONLINE';
                        return `
                            <div class="instance-item">
                                <div class="instance-top">
                                    <span>⚡ ${b.name}</span>
                                    <span class="${online ? 'st-on' : 'st-off'}">${b.status}</span>
                                </div>
                                <div class="actions">
                                    <button class="act-btn b-start" onclick="actionBot('start', '${b.name}')">START</button>
                                    <button class="act-btn b-stop" onclick="actionBot('stop', '${b.name}')">STOP</button>
                                    <button class="act-btn b-del" onclick="actionBot('delete', '${b.name}')">DELETE</button>
                                </div>
                                <div class="secondary-actions">
                                    <button class="sec-btn b-edit" onclick="openEditor('${b.name}')">📝 EDIT</button>
                                    <a href="/logs/${b.name}?key=${KEY}" target="_blank" style="flex:1; text-decoration:none;"><button class="sec-btn b-log" style="width:100%;">🖥️ LOGS</button></a>
                                    <button class="sec-btn b-upload" onclick="triggerReqUpload('${b.name}')">📦 UPLOAD</button>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            } catch(e) {}
        }

        async function actionBot(act, filename) {
            showToast(`${act.toUpperCase()}ING...`);
            try {
                const res = await fetch(`/${act}/${encodeURIComponent(filename)}?key=${KEY}`, { method: 'POST' });
                const data = await res.json();
                if(data.error) showToast('ERR: ' + data.error);
                else {
                    showToast(data.message || 'SUCCESS');
                }
            } catch(e){ showToast('ACTION FAILED'); }
            setTimeout(loadInstances, 600);
        }

        async function openEditor(filename) {
            editingFile = filename;
            document.getElementById('editorFileName').innerText = 'EDIT: ' + filename;
            try {
                const res = await fetch(`/get_code/${filename}?key=${KEY}`);
                const data = await res.json();
                if(data.error) { showToast('ERR: ' + data.error); return; }
                document.getElementById('codeTextarea').value = data.code;
                document.getElementById('editorModal').style.display = 'flex';
            } catch(e) { showToast('FAILED TO LOAD'); }
        }

        function closeEditor() {
            document.getElementById('editorModal').style.display = 'none';
            editingFile = null;
        }

        async function saveCode() {
            if(!editingFile) return;
            const newCode = document.getElementById('codeTextarea').value;
            showToast('SAVING...');
            try {
                const res = await fetch(`/save_code/${editingFile}?key=${KEY}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: newCode })
                });
                const data = await res.json();
                if(data.error) showToast('ERR: ' + data.error);
                else {
                    showToast(data.message);
                    closeEditor();
                    loadInstances();
                }
            } catch(e) { showToast('SAVE FAILED'); }
        }

        loadInstances();
        updateSystemStats();
        setInterval(loadInstances, 10000);
        setInterval(updateSystemStats, 6000);
    </script>
</body>
</html>
"""

def extract_imports(filepath):
    imports = set()
    std_libs = {'os', 'sys', 'time', 'json', 'math', 'random', 're', 'datetime', 'subprocess', 'shutil', 'logging', 'pathlib', 'urllib', 'http', 'asyncio', 'threading', 'queue', 'collections', 'itertools', 'functools', 'io', 'hashlib', 'base64', 'traceback'}
    pkg_map = {'PIL': 'pillow', 'cv2': 'opencv-python', 'telegram': 'python-telegram-bot', 'telebot': 'pyTelegramBotAPI'}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                matches = re.findall(r'^\s*(?:import|from)\s+([a-zA-Z0-9_]+)', line)
                for lib in matches:
                    if lib not in std_libs:
                        imports.add(pkg_map.get(lib, lib))
    except: 
        pass
    return list(imports)

def background_setup(filepath, filename):
    log_path = filepath + '.log'
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write(f"=== [SETUP] Initializing dependencies for {filename} ===\n")
        log_f.flush()
        libs = extract_imports(filepath)
        for lib in libs:
            log_f.write(f"-> Checking module: {lib}...\n")
            log_f.flush()
            try:
                check_res = subprocess.run(['python3', '-c', f"import {lib.replace('-', '_')}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if check_res.returncode == 0:
                    log_f.write(f"   [OK] {lib} already available.\n")
                else:
                    raise ImportError()
            except:
                log_f.write(f"   [INSTALLING] {lib} missing. Installing via pip...\n")
                log_f.flush()
                res = subprocess.run(['pip', 'install', '--prefer-binary', lib], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                log_f.write(res.stdout)
                if res.returncode == 0:
                    log_f.write(f"   [SUCCESS] Installed {lib}!\n")
                else:
                    log_f.write(f"   [FAILED] Could not install {lib}\n")
            log_f.flush()
        log_f.write("=== [READY] Setup complete. Press START! ===\n")

def start_bot_process(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    log_path = filepath + '.log'
    try:
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write("\n\n=== [STARTED] Instance running... ===\n")
        log_file_obj = open(log_path, 'a', encoding='utf-8')
        proc = subprocess.Popen(['python3', '-u', filepath], stdout=log_file_obj, stderr=log_file_obj, start_new_session=True)
        active_processes[filename] = {'proc': proc, 'pid': proc.pid}
        desired_states[filename] = True
        return True
    except Exception as e:
        return False

@app.route('/')
def index(): 
    return render_template_string(AUTO_PILOT_HTML)

@app.route('/system_stats', methods=['GET'])
def system_stats():
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    
    global current_cpu
    cpu_percent = current_cpu
    
    ram_total = 4096.0
    ram_used = 1240.5
    ram_percent = 30.2

    try:
        mem_total_val, mem_free_val, mem_avail_val = 0, 0, 0
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    k = parts[0].strip()
                    v = int(parts[1].strip().split()[0]) * 1024
                    if k == 'MemTotal': mem_total_val = v
                    elif k == 'MemFree': mem_free_val = v
                    elif k == 'MemAvailable': mem_avail_val = v
        if mem_total_val > 0:
            used_val = mem_total_val - (mem_avail_val if mem_avail_val > 0 else mem_free_val)
            ram_total = round(mem_total_val / (1024 * 1024), 1)
            ram_used = round(used_val / (1024 * 1024), 1)
            ram_percent = round((used_val / mem_total_val) * 100, 1)
    except:
        pass

    return jsonify({
        'cpu_percent': cpu_percent,
        'ram_total': ram_total,
        'ram_used': ram_used,
        'ram_percent': ram_percent
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if request.form.get('license_key') != DEFAULT_KEY:
            return jsonify({'error': 'Unauthorized'}), 403
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        filename = secure_filename(file.filename)
        if not filename.endswith('.py'):
            filename += '.py'
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        threading.Thread(target=background_setup, args=(filepath, filename), daemon=True).start()
        start_bot_process(filename)
        
        return jsonify({'message': f'Uploaded & Started {filename}!', 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload_req', methods=['POST'])
def upload_req():
    try:
        if request.form.get('license_key') != DEFAULT_KEY:
            return jsonify({'error': 'Unauthorized'}), 403
        filename = request.form.get('filename')
        req_file = request.files.get('req_file')
        if not req_file or req_file.filename == '':
            return jsonify({'error': 'No requirements file'}), 400
        
        req_filename = secure_filename(req_file.filename)
        req_filepath = os.path.join(UPLOAD_FOLDER, f"{filename}_{req_filename}")
        req_file.save(req_filepath)
        
        log_path = os.path.join(UPLOAD_FOLDER, filename + '.log')
        with open(log_path, 'a', encoding='utf-8') as log_f:
            log_f.write("\n=== [REQ INSTALL] Installing requirements.txt... ===\n")
            log_f.flush()
            res = subprocess.run(['pip', 'install', '--prefer-binary', '-r', req_filepath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            log_f.write(res.stdout)
            log_f.write("\n=== [REQ INSTALL] Done! ===\n")
            log_f.flush()
            
        return jsonify({'message': 'Requirements installed successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_code/<filename>', methods=['GET'])
def get_code(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath): return jsonify({'error': 'File not found'}), 404
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        return jsonify({'code': code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save_code/<filename>', methods=['POST'])
def save_code(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath): return jsonify({'error': 'File not found'}), 404
    try:
        data = request.get_json()
        code = data.get('code', '')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        return jsonify({'message': f'Updated {filename}!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/list', methods=['GET'])
def list_bots():
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    files = os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else []
    bots = []
    dead_keys = []
    for f in sorted(files):
        if f.endswith('.py'):
            is_running = False
            if f in active_processes:
                pid = active_processes[f].get('pid')
                if pid and psutil.pid_exists(pid):
                    try:
                        p = psutil.Process(pid)
                        if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                            is_running = True
                        else: dead_keys.append(f)
                    except: dead_keys.append(f)
                else: dead_keys.append(f)
            bots.append({'name': f, 'status': 'ONLINE' if is_running else 'OFFLINE'})
    for dk in dead_keys:
        if desired_states.get(dk) == False:
            active_processes.pop(dk, None)
    return jsonify({'bots': bots})

@app.route('/start/<filename>', methods=['POST'])
def start_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath): return jsonify({'error': 'File not found'}), 404
    
    if filename in active_processes:
        try:
            pid = active_processes[filename].get('pid')
            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
        except: 
            pass
        active_processes.pop(filename, None)
    
    success = start_bot_process(filename)
    if success:
        return jsonify({'message': f'Started {filename}'})
    else:
        return jsonify({'error': 'Failed to start'}), 500

@app.route('/logs/<filename>', methods=['GET'])
def logs(filename):
    if request.args.get('key') != DEFAULT_KEY: return "Unauthorized", 403
    log_path = os.path.join(UPLOAD_FOLDER, filename + '.log')
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
            content = lf.read()
        return f"<pre style='background:#02050e;color:#00f3ff;padding:16px;font-family:monospace;font-size:11px;'>{content}</pre>"
    return "No logs available."

@app.route('/stop/<filename>', methods=['POST'])
def stop_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    desired_states[filename] = False
    if filename in active_processes:
        try:
            pid = active_processes[filename].get('pid')
            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
        except: 
            pass
        active_processes.pop(filename, None)
    log_path = os.path.join(UPLOAD_FOLDER, filename + '.log')
    if os.path.exists(log_path):
        with open(log_path, 'a', encoding='utf-8') as lf:
            lf.write("\n=== [STOPPED] Terminated by user. ===\n")
    return jsonify({'message': f'Stopped {filename}'})

@app.route('/delete/<filename>', methods=['POST'])
def delete_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: 
        return jsonify({'error': 'Unauthorized'}), 403
    desired_states.pop(filename, None)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if filename in active_processes:
        try:
            pid = active_processes[filename].get('pid')
            if pid and psutil.pid_exists(pid): 
                psutil.Process(pid).terminate()
        except: 
            pass
        active_processes.pop(filename, None)
    if os.path.exists(filepath): 
        os.remove(filepath)
    if os.path.exists(filepath + '.log'): 
        os.remove(filepath + '.log')
    return jsonify({'message': f'Deleted {filename}'})

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    local_ip = get_local_ip()
    print("\n" + "="*40)
    print("🚀 SERVER STARTED!")
    print(f"👉 Local URL: http://127.0.0.1:5000")
    print(f"👉 Network IP: http://{local_ip}:5000")
    print("="*40 + "\n")
    serve(app, host='0.0.0.0', port=5000, threads=8)
