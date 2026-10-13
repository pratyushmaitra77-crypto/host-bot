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
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%) translateY(100px); 
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
                <input type="file" id="botFile" accept=".py">
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

    <div id="editorModal">
        <div class="editor-content">
            <div class="editor-header">
                <span id="editorFileName" class="editor-title">EDIT CODE</span>
                <button class="close-term" onclick="closeEditor()">CLOSE</button>
            </div>
            <textarea id="codeTextarea" class="code-textarea" spellcheck="false"></textarea>
            <div class="editor-footer">
                <button class="btn" style="padding: 10px;" onclick="saveCode()">💾 SAVE & APPLY CODE</button>
            </div>
        </div>
    </div>

    <div id="toast">SYSTEM READY</div>
    <script>
        const KEY = 'admin123';
        let activeLogFile = null, logInterval = null, isMinimized = false, editingFile = null;

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

                document.getElementById('ramText').innerText = `${data.ram_used} MB / ${data.ram_total} MB (${data.ram_percent}%)`;
                document.getElementById('ramBar').style.width = data.ram_percent + '%';

                document.getElementById('diskText').innerText = `${data.disk_used} GB / ${data.disk_total} GB (${data.disk_percent}%)`;
                document.getElementById('diskBar').style.width = data.disk_percent + '%';
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

        async function loadInstances() {
            try {
                const res = await fetch(`/instances?key=${KEY}`);
                const list = await res.json();
                const container = document.getElementById('instanceList');
                if(!list.length) {
                    container.innerHTML = '<div class="empty">No active instances found.</div>';
                    return;
                }
                let html = '';
                list.forEach(item => {
                    html += `
                        <div class="instance-item">
                            <div class="instance-top">
                                <span>${item.filename}</span>
                                <span class="${item.running ? 'st-on' : 'st-off'}">${item.running ? 'RUNNING' : 'STOPPED'}</span>
                            </div>
                            <div class="metrics-row">
                                <span class="metric-badge">PID: ${item.pid || 'N/A'}</span>
                                <span class="metric-badge">CPU: ${item.cpu}%</span>
                                <span class="metric-badge">RAM: ${item.memory}MB</span>
                            </div>
                            <div class="actions">
                                <button class="act-btn b-start" onclick="controlBot('${item.filename}', 'start')">START</button>
                                <button class="act-btn b-stop" onclick="controlBot('${item.filename}', 'stop')">STOP</button>
                                <button class="act-btn b-del" onclick="controlBot('${item.filename}', 'delete')">DELETE</button>
                            </div>
                            <div class="secondary-actions">
                                <button class="sec-btn b-edit" onclick="openEditor('${item.filename}')">EDIT</button>
                                <button class="sec-btn b-log" onclick="openTerminal('${item.filename}')">LOGS</button>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            } catch(e) {}
        }

        async function controlBot(filename, action) {
            try {
                const res = await fetch('/control', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename, action, license_key: KEY})
                });
                const data = await res.json();
                showToast(data.message || data.error);
                loadInstances();
            } catch(e) { showToast('ACTION FAILED'); }
        }

        async function openEditor(filename) {
            editingFile = filename;
            try {
                const res = await fetch(`/get_code?filename=${filename}&key=${KEY}`);
                const data = await res.json();
                if(data.error) { showToast(data.error); return; }
                document.getElementById('editorFileName').innerText = 'EDIT: ' + filename;
                document.getElementById('codeTextarea').value = data.code;
                document.getElementById('editorModal').style.display = 'flex';
            } catch(e) { showToast('FAILED TO LOAD CODE'); }
        }

        function closeEditor() {
            document.getElementById('editorModal').style.display = 'none';
            editingFile = null;
        }

        async function saveCode() {
            if(!editingFile) return;
            const code = document.getElementById('codeTextarea').value;
            try {
                const res = await fetch('/save_code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename: editingFile, code, license_key: KEY})
                });
                const data = await res.json();
                showToast(data.message || data.error);
                closeEditor();
            } catch(e) { showToast('SAVE FAILED'); }
        }

        function openTerminal(filename) {
            activeLogFile = filename;
            document.getElementById('termFileName').innerText = 'LOGS: ' + filename;
            document.getElementById('terminalCard').style.display = 'block';
            fetchLogs();
            if(logInterval) clearInterval(logInterval);
            logInterval = setInterval(fetchLogs, 2000);
        }

        async function fetchLogs() {
            if(!activeLogFile) return;
            try {
                const res = await fetch(`/logs?filename=${activeLogFile}&key=${KEY}`);
                const data = await res.json();
                const term = document.getElementById('terminalOutput');
                term.innerText = data.logs || 'No logs available.';
                term.scrollTop = term.scrollHeight;
            } catch(e) {}
        }

        function closeTerminal() {
            document.getElementById('terminalCard').style.display = 'none';
            activeLogFile = null;
            if(logInterval) clearInterval(logInterval);
        }

        function toggleMinimize() {
            const term = document.getElementById('terminalOutput');
            const btn = document.getElementById('minBtn');
            isMinimized = !isMinimized;
            term.style.display = isMinimized ? 'none' : 'block';
            btn.innerText = isMinimized ? 'MAX' : 'MIN';
        }

        setInterval(updateSystemStats, 3000);
        setInterval(loadInstances, 4000);
        updateSystemStats();
        loadInstances();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(AUTO_PILOT_HTML)

@app.route('/system_stats')
def system_stats():
    if request.args.get('key') != DEFAULT_KEY:
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return jsonify({
            'cpu_percent': current_cpu,
            'ram_used': round(ram.used / (1024 * 1024)),
            'ram_total': round(ram.total / (1024 * 1024)),
            'ram_percent': ram.percent,
            'disk_used': round(disk.used / (1024 ** 3), 1),
            'disk_total': round(disk.total / (1024 ** 3), 1),
            'disk_percent': disk.percent
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload():
    if request.form.get('license_key') != DEFAULT_KEY:
        return jsonify({'error': 'Unauthorized'}), 403
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        
        log_path = path + '.log'
        if filename not in active_processes or not active_processes[filename].get('running'):
            try:
                log_file = open(log_path, 'w')
                proc = subprocess.Popen([sys.executable, path], stdout=log_file, stderr=log_file)
                active_processes[filename] = {
                    'process': proc,
                    'pid': proc.pid,
                    'log_path': log_path,
                    'running': True
                }
            except Exception as e:
                pass
        return jsonify({'message': 'DEPLOY SUCCESSFUL'})
    return jsonify({'error': 'Upload failed'})

@app.route('/instances')
def instances():
    if request.args.get('key') != DEFAULT_KEY:
        return jsonify({'error': 'Unauthorized'}), 403
    res = []
    try:
        for f in os.listdir(UPLOAD_FOLDER):
            if f.endswith('.py'):
                path = os.path.join(UPLOAD_FOLDER, f)
                info = active_processes.get(f, {})
                proc = info.get('process')
                is_running = False
                cpu = 0.0
                mem = 0.0
                pid = info.get('pid')
                
                if proc and proc.poll() is None:
                    is_running = True
                    try:
                        p = psutil.Process(pid)
                        cpu = round(p.cpu_percent(interval=0.1), 1)
                        mem = round(p.memory_info().rss / (1024 * 1024), 1)
                    except:
                        pass
                else:
                    info['running'] = False
                
                res.append({
                    'filename': f,
                    'running': is_running,
                    'pid': pid if is_running else None,
                    'cpu': cpu,
                    'memory': mem
                })
    except:
        pass
    return jsonify(res)

@app.route('/control', methods=['POST'])
def control():
    data = request.json
    if data.get('license_key') != DEFAULT_KEY:
        return jsonify({'error': 'Unauthorized'}), 403
    filename = data.get('filename')
    action = data.get('action')
    path = os.path.join(UPLOAD_FOLDER, filename)
    log_path = path + '.log'
    
    if action == 'start':
        if filename in active_processes and active_processes[filename].get('process') and active_processes[filename]['process'].poll() is None:
            return jsonify({'message': 'ALREADY RUNNING'})
        try:
            log_file = open(log_path, 'w')
            proc = subprocess.Popen([sys.executable, path], stdout=log_file, stderr=log_file)
            active_processes[filename] = {
                'process': proc,
                'pid': proc.pid,
                'log_path': log_path,
                'running': True
            }
            return jsonify({'message': 'STARTED SUCCESSFULLY'})
        except Exception as e:
            return jsonify({'error': str(e)})
            
    elif action == 'stop':
        if filename in active_processes and active_processes[filename].get('process'):
            try:
                active_processes[filename]['process'].terminate()
                active_processes[filename]['running'] = False
                return jsonify({'message': 'STOPPED SUCCESSFULLY'})
            except Exception as e:
                return jsonify({'error': str(e)})
        return jsonify({'message': 'NOT RUNNING'})
        
    elif action == 'delete':
        if filename in active_processes and active_processes[filename].get('process'):
            try:
                active_processes[filename]['process'].terminate()
            except:
                pass
            del active_processes[filename]
        try:
            if os.path.exists(path): os.remove(path)
            if os.path.exists(log_path): os.remove(log_path)
            return jsonify({'message': 'DELETED SUCCESSFULLY'})
        except Exception as e:
            return jsonify({'error': str(e)})
            
    return jsonify({'error': 'Invalid action'})

@app.route('/get_code')
def get_code():
    if request.args.get('key') != DEFAULT_KEY:
        return jsonify({'error': 'Unauthorized'}), 403
    filename = request.args.get('filename')
    path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        return jsonify({'code': code})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/save_code', methods=['POST'])
def save_code():
    data = request.json
    if data.get('license_key') != DEFAULT_KEY:
        return jsonify({'error': 'Unauthorized'}), 403
    filename = data.get('filename')
    code = data.get('code')
    path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        return jsonify({'message': 'SAVED & APPLIED'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/logs')
def logs():
    if request.args.get('key') != DEFAULT_KEY:
        return jsonify({'error': 'Unauthorized'}), 403
    filename = request.args.get('filename')
    log_path = os.path.join(UPLOAD_FOLDER, filename + '.log')
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'logs': content})
        return jsonify({'logs': 'No logs generated yet.'})
    except Exception as e:
        return jsonify({'logs': 'Error reading logs: ' + str(e)})

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=7860)
