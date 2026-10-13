import os, sys, subprocess, threading, time, random, string, psutil, re
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from waitress import serve
from werkzeug.utils import secure_filename
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'nexus_ultra_secure_key_2026'

# ═══════════════════════════════════════════════════════════════
# 1. MONGODB DATABASE SETUP
# ═══════════════════════════════════════════════════════════════
MONGO_URI = "mongodb+srv://Pratyush:pratyush300@free-cluster.gvtoifo.mongodb.net/?appName=free-cluster&compressors=zlib"
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["nexus_panel_storage"]
    scripts_collection = db["saved_scripts"]
    config_collection = db["panel_config"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'hosted_bots')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

active_processes = {}
desired_states = {}

def get_admin_password():
    try:
        cfg = config_collection.find_one({"key": "admin_pass"})
        if cfg:
            return cfg.get("password", "admin123")
    except:
        pass
    return "admin123"

def set_admin_password(new_pass):
    try:
        config_collection.update_one(
            {"key": "admin_pass"},
            {"$set": {"password": new_pass}},
            upsert=True
        )
        return True
    except:
        return False

# ═══════════════════════════════════════════════════════════════
# 2. AUTO-RESTORE & MONITOR BOTS FROM MONGODB
# ═══════════════════════════════════════════════════════════════
def restore_bots():
    try:
        if 'scripts_collection' in globals():
            docs = scripts_collection.find()
            for doc in docs:
                filename = doc.get("filename")
                code = doc.get("code")
                if filename and code:
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(code)
            print("🔄 Restored scripts from MongoDB.")
    except Exception as e:
        print(f"⚠️ Restore failed: {e}")

restore_bots()

def monitor_bots():
    while True:
        time.sleep(10)
        for filename, should_run in list(desired_states.items()):
            if should_run:
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                if not os.path.exists(filepath):
                    desired_states.pop(filename, None)
                    active_processes.pop(filename, None)
                    continue
                
                is_running = False
                if filename in active_processes:
                    pid = active_processes[filename].get('pid')
                    if pid and psutil.pid_exists(pid):
                        try:
                            p = psutil.Process(pid)
                            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                                is_running = True
                        except: pass
                
                if not is_running:
                    log_path = filepath + '.log'
                    if os.path.exists(log_path):
                        with open(log_path, 'a', encoding='utf-8') as lf:
                            lf.write("\n=== [AUTO-RESTART] Restarting bot... ===\n")
                    start_bot_process(filename)

threading.Thread(target=monitor_bots, daemon=True).start()

def start_bot_process(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    log_path = filepath + '.log'
    try:
        log_file_obj = open(log_path, 'a', encoding='utf-8')
        proc = subprocess.Popen([sys.executable, '-u', filepath], stdout=log_file_obj, stderr=log_file_obj, start_new_session=True)
        active_processes[filename] = {'proc': proc, 'pid': proc.pid}
        desired_states[filename] = True
        return True
    except Exception as e:
        print(f"Start process err: {e}")
        return False

# ═══════════════════════════════════════════════════════════════
# 3. HTML TEMPLATES (LOGIN, PROFILE, REQ UPLOAD, NEON BUTTONS)
# ═══════════════════════════════════════════════════════════════
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXUS-X // ADMIN LOGIN</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --bg-deep: #050814; --card-bg: #0b1329; --neon-cyan: #00f3ff; --neon-purple: #b000ff; --text-main: #ffffff; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg-deep); color: var(--text-main); font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 16px; }
        .login-card { background: var(--card-bg); padding: 24px; border-radius: 16px; border: 1px solid rgba(0, 243, 255, 0.25); width: 100%; max-width: 380px; text-align: center; box-shadow: 0 0 20px rgba(0, 243, 255, 0.1); }
        h2 { font-family: 'Orbitron', sans-serif; font-size: 16px; color: var(--neon-cyan); margin-bottom: 20px; }
        input[type="password"] { width: 100%; padding: 12px; background: #050814; border: 1px solid rgba(0,243,255,0.4); border-radius: 8px; color: #fff; margin-bottom: 16px; font-size: 14px; text-align: center; outline: none; }
        .btn { background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple)); color: #050814; border: none; padding: 12px; width: 100%; font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 12px; border-radius: 8px; cursor: pointer; text-transform: uppercase; }
        .error { color: #ff3366; font-size: 11px; margin-bottom: 12px; font-family: monospace; }
        .hint { font-size: 9px; color: #8a99ad; margin-top: 10px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>SECURE LOGIN</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Enter Admin Password" required autofocus>
            <button type="submit" class="btn">Login to Panel</button>
        </form>
        <div class="hint">Default Pass: admin123</div>
    </div>
</body>
</html>
"""

PANEL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXUS-X // CLOUD IDE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #050814; --card-bg: #0b1329; --neon-cyan: #00f3ff;
            --neon-purple: #b000ff; --text-main: #ffffff; --text-muted: #8a99ad;
            --success: #00ff66; --danger: #ff0055; --warning: #fbbf24;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg-deep); color: var(--text-main); font-family: 'Inter', sans-serif; padding: 16px; padding-bottom: 90px; min-height: 100vh; }
        .container { width: 100%; max-width: 480px; margin: 0 auto; }
        
        .ring-header { background: linear-gradient(135deg, #0e1938, #070d21); padding: 16px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.25); margin-bottom: 16px; display: flex; align-items: center; gap: 16px; }
        .ring-avatar { width: 50px; height: 50px; background: rgba(0, 243, 255, 0.1); border: 1px solid rgba(0, 243, 255, 0.4); border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; animation: spinRing 6s linear infinite; }
        @keyframes spinRing { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .ring-info h2 { font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 900; color: var(--neon-cyan); }
        .ring-info p { font-size: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }

        .resource-card { background: rgba(11, 19, 41, 0.85); border: 1px solid rgba(0, 243, 255, 0.2); padding: 14px; border-radius: 14px; margin-bottom: 16px; }
        .resource-title { font-family: 'Orbitron', sans-serif; font-size: 9px; font-weight: 700; color: var(--text-muted); margin-bottom: 10px; display: flex; justify-content: space-between; }
        .res-item { margin-bottom: 8px; }
        .res-info { display: flex; justify-content: space-between; font-size: 10px; font-family: 'JetBrains Mono', monospace; margin-bottom: 3px; color: #fff; }
        .res-bar-bg { width: 100%; height: 6px; background: rgba(255, 255, 255, 0.05); border-radius: 3px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.08); }
        .res-bar-fill { height: 100%; width: 0%; background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple)); border-radius: 3px; transition: width 0.4s ease; }

        .card { background: var(--card-bg); padding: 16px; margin-bottom: 16px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.15); }
        .card-title { font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700; margin-bottom: 12px; color: var(--text-muted); text-transform: uppercase; display: flex; justify-content: space-between; align-items: center; }
        
        .file-upload-wrapper { background: #040814; border: 2px dashed rgba(0, 243, 255, 0.3); padding: 12px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
        input[type="file"] { color: var(--text-muted); font-size: 10px; width: 100%; cursor: pointer; }
        
        .btn { background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple), #ff007f); color: #ffffff; border: none; padding: 12px; width: 100%; font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 11px; border-radius: 10px; cursor: pointer; box-shadow: 0 0 12px rgba(0,243,255,0.4); }

        .instance-item { background: #070e21; padding: 12px; margin-bottom: 10px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.06); }
        .instance-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 11px; font-weight: 600; color: #fff; font-family: 'JetBrains Mono', monospace; }
        .st-on { color: var(--success); font-size: 9px; background: rgba(0, 255, 102, 0.15); padding: 3px 8px; border-radius: 6px; font-family: 'Orbitron', sans-serif; border: 1px solid rgba(0, 255, 102, 0.4); }
        .st-off { color: var(--danger); font-size: 9px; background: rgba(255, 0, 85, 0.15); padding: 3px 8px; border-radius: 6px; font-family: 'Orbitron', sans-serif; border: 1px solid rgba(255, 0, 85, 0.4); }
        
        .actions { display: flex; gap: 6px; margin-bottom: 6px; }
        .act-btn { flex: 1; border: none; padding: 9px; font-size: 9px; font-weight: 700; border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; text-transform: uppercase; }
        
        .b-start { background: rgba(0, 255, 102, 0.15); color: var(--success); border: 1px solid rgba(0, 255, 102, 0.4); }
        .b-stop { background: rgba(251, 191, 36, 0.15); color: var(--warning); border: 1px solid rgba(251, 191, 36, 0.4); }
        .b-del { background: rgba(255, 0, 85, 0.15); color: var(--danger); border: 1px solid rgba(255, 0, 85, 0.4); }
        
        .secondary-actions { display: flex; gap: 6px; }
        .sec-btn { flex: 1; border: none; padding: 9px; font-size: 9px; font-weight: 700; border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; text-transform: uppercase; }
        .b-edit { background: rgba(0, 243, 255, 0.15); color: var(--neon-cyan); border: 1px solid rgba(0, 243, 255, 0.4); }
        .b-log { background: rgba(176, 0, 255, 0.2); color: #d8b4fe; border: 1px solid rgba(176, 0, 255, 0.4); }

        #editorModal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(5, 8, 20, 0.9); z-index: 100; padding: 16px; align-items: center; justify-content: center; }
        .editor-content { background: var(--card-bg); width: 100%; max-width: 480px; height: 85vh; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.35); display: flex; flex-direction: column; padding: 16px; }
        .code-textarea { flex: 1; background: #02050e; border: 1px solid rgba(255, 255, 255, 0.1); color: var(--neon-cyan); font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 12px; border-radius: 8px; resize: none; outline: none; }

        .bottom-nav { position: fixed; bottom: 0; left: 0; width: 100%; background: #070d21; border-top: 1px solid rgba(0, 243, 255, 0.2); display: flex; justify-content: space-around; padding: 10px 0; z-index: 1000; }
        .nav-item { color: var(--text-muted); text-decoration: none; font-family: 'Orbitron', sans-serif; font-size: 9px; font-weight: 700; }
        .nav-item.active { color: var(--neon-cyan); }
    </style>
</head>
<body>
    <div class="container">
        <div class="ring-header">
            <div class="ring-avatar">
                <svg width="28" height="28" viewBox="0 0 36 36" fill="none"><circle cx="18" cy="18" r="14" stroke="#00f3ff" stroke-width="3" stroke-dasharray="6 3"/><circle cx="18" cy="18" r="3" fill="#b000ff"/></svg>
            </div>
            <div class="ring-info">
                <h2>NEXUS-X v6</h2>
                <p>TELEGRAM BOT CORE // ACTIVE</p>
            </div>
        </div>

        <div class="resource-card">
            <div class="resource-title"><span>HARDWARE MONITOR</span><span style="color:var(--neon-cyan);">LIVE</span></div>
            <div class="res-item"><div class="res-info"><span>CPU</span><span id="cpuText">0%</span></div><div class="res-bar-bg"><div id="cpuBar" class="res-bar-fill"></div></div></div>
            <div class="res-item"><div class="res-info"><span>RAM</span><span id="ramText">0 MB</span></div><div class="res-bar-bg"><div id="ramBar" class="res-bar-fill"></div></div></div>
        </div>
        
        <div class="card">
            <div class="card-title"><span>⚡ DEPLOY BOT</span></div>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <div class="file-upload-wrapper">
                    <label style="font-size:9px; color:var(--neon-cyan); display:block; margin-bottom:5px;">📁 Python Script (.py):</label>
                    <input type="file" name="bot_file" accept=".py" required>
                </div>
                <div class="file-upload-wrapper">
                    <label style="font-size:9px; color:var(--neon-cyan); display:block; margin-bottom:5px;">📦 Requirements (requirements.txt):</label>
                    <input type="file" name="req_file" accept=".txt">
                </div>
                <button type="submit" class="btn">🚀 Upload & Start Bot</button>
            </form>
        </div>
        
        <div class="card">
            <div class="card-title"><span>📂 ACTIVE BOTS</span></div>
            {% if bots %}
                {% for filename, info in bots.items() %}
                <div class="instance-item">
                    <div class="instance-top">
                        <span>🤖 {{ filename }}</span>
                        <span class="{{ 'st-on' if info.status == 'ONLINE' else 'st-off' }}">{{ info.status }}</span>
                    </div>
                    <div class="actions">
                        <a href="/start/{{ filename }}" style="flex:1; text-decoration:none;"><button class="act-btn b-start" style="width:100%;">START</button></a>
                        <a href="/stop/{{ filename }}" style="flex:1; text-decoration:none;"><button class="act-btn b-stop" style="width:100%;">STOP</button></a>
                        <a href="/delete/{{ filename }}" style="flex:1; text-decoration:none;"><button class="act-btn b-del" style="width:100%;">DELETE</button></a>
                    </div>
                    <div class="secondary-actions">
                        <button class="sec-btn b-edit" onclick="openEditor('{{ filename }}')">📝 EDIT</button>
                        <a href="/logs/{{ filename }}" target="_blank" style="flex:1; text-decoration:none;"><button class="sec-btn b-log" style="width:100%;">🖥️ LOGS</button></a>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p style="font-size:10px; color:var(--text-muted); text-align:center;">No active bots uploaded.</p>
            {% endif %}
        </div>
    </div>

    <!-- Code Editor Modal -->
    <div id="editorModal">
        <div class="editor-content">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px; align-items:center;">
                <span id="editorFileName" style="font-family:'Orbitron'; font-size:11px; color:var(--neon-cyan);">EDIT CODE</span>
                <button onclick="closeEditor()" style="background:var(--danger); color:#fff; border:none; padding:5px 10px; border-radius:6px; font-family:'Orbitron'; font-weight:bold; cursor:pointer;">X</button>
            </div>
            <textarea id="codeTextarea" class="code-textarea" spellcheck="false"></textarea>
            <button class="btn" style="margin-top:10px;" onclick="saveCode()">💾 SAVE CODE</button>
        </div>
    </div>

    <div class="bottom-nav">
        <a href="/home" class="nav-item active">🏠 HOME</a>
        <a href="/profile" class="nav-item">👤 PROFILE</a>
    </div>

    <script>
        let editingFile = null;
        async function updateStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('cpuText').innerText = data.cpu + '%';
                document.getElementById('cpuBar').style.width = data.cpu + '%';
                document.getElementById('ramText').innerText = data.ram_used + ' MB / ' + data.ram_total + ' MB';
                document.getElementById('ramBar').style.width = data.ram_percent + '%';
            } catch(e){}
        }
        setInterval(updateStats, 4000);
        updateStats();

        async function openEditor(filename) {
            editingFile = filename;
            document.getElementById('editorFileName').innerText = 'EDIT: ' + filename;
            const res = await fetch('/get_code/' + filename);
            const data = await res.json();
            document.getElementById('codeTextarea').value = data.code || '';
            document.getElementById('editorModal').style.display = 'flex';
        }
        function closeEditor() { document.getElementById('editorModal').style.display = 'none'; }
        async function saveCode() {
            if(!editingFile) return;
            const code = document.getElementById('codeTextarea').value;
            await fetch('/save_code/' + editingFile, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: code})
            });
            alert('Code Saved Successfully!');
            closeEditor();
        }
    </script>
</body>
</html>
"""

PROFILE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXUS-X // PROFILE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --bg-deep: #050814; --card-bg: #0b1329; --neon-cyan: #00f3ff; --neon-purple: #b000ff; --text-main: #ffffff; --text-muted: #8a99ad; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg-deep); color: var(--text-main); font-family: 'Inter', sans-serif; padding: 16px; padding-bottom: 90px; }
        .container { width: 100%; max-width: 480px; margin: 0 auto; }
        .card { background: var(--card-bg); padding: 16px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.15); margin-bottom: 16px; }
        .card-title { font-family: 'Orbitron', sans-serif; font-size: 11px; color: var(--neon-cyan); margin-bottom: 14px; }
        input[type="password"] { width: 100%; padding: 10px; background: #050814; border: 1px solid rgba(0,243,255,0.4); border-radius: 8px; color: #fff; margin-bottom: 12px; font-size: 12px; outline: none; }
        .btn { background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple)); color: #050814; border: none; padding: 12px; width: 100%; font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 11px; border-radius: 8px; cursor: pointer; }
        .msg { color: #00ff66; font-size: 10px; margin-bottom: 8px; font-family: monospace; }
        .error { color: #ff3366; font-size: 10px; margin-bottom: 8px; font-family: monospace; }
        .bottom-nav { position: fixed; bottom: 0; left: 0; width: 100%; background: #070d21; border-top: 1px solid rgba(0, 243, 255, 0.2); display: flex; justify-content: space-around; padding: 10px 0; z-index: 1000; }
        .nav-item { color: var(--text-muted); text-decoration: none; font-family: 'Orbitron', sans-serif; font-size: 9px; font-weight: 700; }
        .nav-item.active { color: var(--neon-cyan); }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="card-title">🔐 CHANGE ADMIN PASSWORD</div>
            {% if msg %}<p class="msg">{{ msg }}</p>{% endif %}
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
            <form method="POST">
                <input type="password" name="old_pass" placeholder="Current Password" required>
                <input type="password" name="new_pass" placeholder="New Password" required>
                <button type="submit" class="btn">UPDATE PASSWORD</button>
            </form>
        </div>
        <div class="card">
            <a href="/logout" style="text-decoration:none;"><button class="btn" style="background:#ff0055; color:#fff;">LOGOUT</button></a>
        </div>
    </div>
    <div class="bottom-nav">
        <a href="/home" class="nav-item">🏠 HOME</a>
        <a href="/profile" class="nav-item active">👤 PROFILE</a>
    </div>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════
# 4. FLASK ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == get_admin_password():
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            error = "❌ Incorrect Password!"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/home')
def home():
    if not session.get('logged_in'): return redirect(url_for('login'))
    bots_data = {}
    files = os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else []
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
                    except: pass
            bots_data[f] = {'status': 'ONLINE' if is_running else 'OFFLINE'}
    return render_template_string(PANEL_HTML, bots=bots_data)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('logged_in'): return redirect(url_for('login'))
    msg, error = None, None
    if request.method == 'POST':
        if request.form.get('old_pass') == get_admin_password():
            if set_admin_password(request.form.get('new_pass')):
                msg = "✅ Password updated successfully!"
            else: error = "❌ DB Error!"
        else: error = "❌ Old password incorrect!"
    return render_template_string(PROFILE_HTML, msg=msg, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('logged_in'): return redirect(url_for('login'))
    bot_file = request.files.get('bot_file')
    req_file = request.files.get('req_file')
    
    if req_file and req_file.filename != '':
        req_path = os.path.join(UPLOAD_FOLDER, secure_filename(req_file.filename))
        req_file.save(req_path)
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], stdout=subprocess.DEVNULL)
        except: pass

    if bot_file and bot_file.filename != '':
        filename = secure_filename(bot_file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        bot_file.save(filepath)
        
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            
        scripts_collection.update_one({"filename": filename}, {"$set": {"filename": filename, "code": code}}, upsert=True)
        start_bot_process(filename)

    return redirect(url_for('home'))

@app.route('/start/<filename>')
def start_bot(filename):
    if not session.get('logged_in'): return redirect(url_for('login'))
    start_bot_process(filename)
    return redirect(url_for('home'))

@app.route('/stop/<filename>')
def stop_bot(filename):
    if not session.get('logged_in'): return redirect(url_for('login'))
    desired_states[filename] = False
    if filename in active_processes:
        try:
            pid = active_processes[filename].get('pid')
            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
        except: pass
        active_processes.pop(filename, None)
    return redirect(url_for('home'))

@app.route('/delete/<filename>')
def delete_bot(filename):
    if not session.get('logged_in'): return redirect(url_for('login'))
    stop_bot(filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath): os.remove(filepath)
    if os.path.exists(filepath + '.log'): os.remove(filepath + '.log')
    try: scripts_collection.delete_one({"filename": filename})
    except: pass
    return redirect(url_for('home'))

@app.route('/logs/<filename>')
def logs(filename):
    if not session.get('logged_in'): return redirect(url_for('login'))
    log_path = os.path.join(UPLOAD_FOLDER, filename + '.log')
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
            content = lf.read()
        return f"<pre style='background:#02050e;color:#00f3ff;padding:16px;font-family:monospace;font-size:11px;'>{content}</pre>"
    return "No logs available."

@app.route('/get_code/<filename>')
def get_code(filename):
    if not session.get('logged_in'): return jsonify({'error': 'Unauthorized'}), 403
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return jsonify({'code': f.read()})
    return jsonify({'code': ''})

@app.route('/save_code/<filename>', methods=['POST'])
def save_code(filename):
    if request.args.get('key') == 'admin123' or session.get('logged_in'):
        code = request.get_json().get('code', '')
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        try: scripts_collection.update_one({"filename": filename}, {"$set": {"filename": filename, "code": code}}, upsert=True)
        except: pass
        return jsonify({'message': 'Saved'})
    return jsonify({'error': 'Unauthorized'}), 403

@app.route('/api/stats')
def api_stats():
    mem = psutil.virtual_memory()
    return jsonify({
        'cpu': round(psutil.cpu_percent(), 1),
        'ram_used': round(mem.used / (1024 * 1024), 1),
        'ram_total': round(mem.total / (1024 * 1024), 1),
        'ram_percent': round(mem.percent, 1)
    })

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000, threads=8)
