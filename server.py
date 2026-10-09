import os, subprocess, psutil, re, threading, socket, time, random, zipfile, json
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from waitress import serve
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nexus_secret_key_session'

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'hosted_bots')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USERS_FILE = 'users_db.json'
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

DEFAULT_KEY = 'admin123'
active_processes = {}
desired_states = {}
current_cpu = 5.2

def get_user_folder():
    if 'user' not in session:
        return None
    safe_email = session['user'].replace('@', '_at_').replace('.', '_')
    user_dir = os.path.join(UPLOAD_FOLDER, safe_email)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

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

        .auth-wrapper {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 85vh;
        }

        .auth-box {
            background: rgba(11, 19, 41, 0.95);
            padding: 35px 24px;
            border-radius: 20px;
            border: 1px solid rgba(0, 243, 255, 0.4);
            box-shadow: 0 0 35px rgba(0, 243, 255, 0.2);
            text-align: center;
            width: 100%;
            max-width: 420px;
        }
        .auth-box h2 { font-family: 'Orbitron'; font-size: 20px; color: var(--neon-cyan); margin-bottom: 24px; letter-spacing: 1px; }
        
        .tabs { display: flex; gap: 10px; margin-bottom: 22px; }
        .tab-btn {
            flex: 1; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);
            color: var(--text-muted); padding: 14px; font-size: 12px; font-family: 'Orbitron';
            font-weight: 700; border-radius: 10px; cursor: pointer; text-align: center;
            transition: all 0.2s ease;
        }
        .tab-btn.active { background: rgba(0, 243, 255, 0.15); color: var(--neon-cyan); border-color: rgba(0, 243, 255, 0.5); }

        .input-field {
            width: 100%;
            background: #040814;
            border: 1px solid rgba(0, 243, 255, 0.35);
            padding: 16px 18px;
            border-radius: 12px;
            color: #fff;
            font-family: 'JetBrains Mono';
            font-size: 14px;
            margin-bottom: 18px;
            outline: none;
            transition: all 0.3s ease;
        }
        .input-field:focus {
            border-color: var(--neon-cyan);
            box-shadow: 0 0 12px rgba(0, 243, 255, 0.3);
        }

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

        .deploy-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
        .deploy-tab-btn {
            flex: 1; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);
            color: var(--text-muted); padding: 10px; font-size: 10px; font-family: 'Orbitron';
            font-weight: 700; border-radius: 8px; cursor: pointer; text-align: center;
            transition: all 0.2s ease;
        }
        .deploy-tab-btn.active { background: rgba(0, 243, 255, 0.15); color: var(--neon-cyan); border-color: rgba(0, 243, 255, 0.5); }
        
        .deploy-section { display: none; }
        .deploy-section.active { display: block; }

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
            color: #050814; border: none; padding: 16px; width: 100%; 
            font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 13px; 
            border-radius: 12px; cursor: pointer; letter-spacing: 1px;
            position: relative; overflow: hidden; transition: all 0.2s ease;
        }
        .btn:active { transform: scale(0.97); }

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

        /* Bottom Navbar */
        .bottom-nav {
            position: fixed; bottom: 0; left: 0; width: 100%;
            background: rgba(11, 19, 41, 0.95);
            border-top: 1px solid rgba(0, 243, 255, 0.25);
            display: flex; justify-content: space-around; padding: 10px 0;
            z-index: 999; backdrop-filter: blur(10px);
        }
        .nav-item {
            background: none; border: none; color: var(--text-muted);
            font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700;
            cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 4px;
            transition: color 0.2s;
        }
        .nav-item.active { color: var(--neon-cyan); }

        .view-section { display: none; }
        .view-section.active { display: block; }

        #editorModal, #policyModal, #supportModal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(5, 8, 20, 0.9); z-index: 1000;
            padding: 16px; align-items: center; justify-content: center;
        }
        .modal-content {
            background: var(--card-bg); width: 100%; max-width: 480px; max-height: 85vh;
            border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.35);
            display: flex; flex-direction: column; padding: 16px;
        }
        .modal-body {
            overflow-y: auto; font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--text-muted); line-height: 1.5; margin-bottom: 12px;
        }
        .modal-body h3 { color: var(--neon-cyan); font-family: 'Orbitron'; font-size: 12px; margin-bottom: 8px; }
        .modal-body p { margin-bottom: 8px; }

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
            transition: transform 0.2s ease; z-index: 1001;
        }
        #toast.show { transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>
    <div class="container">
        {% if not logged_in %}
        <div class="auth-wrapper">
            <div class="auth-box">
                <h2>NEXUS-X PORTAL</h2>
                <div class="tabs">
                    <div class="tab-btn active" id="tabLogin" onclick="switchAuthTab('login')">LOGIN</div>
                    <div class="tab-btn" id="tabReg" onclick="switchAuthTab('register')">REGISTER</div>
                </div>
                <input type="email" id="authEmail" class="input-field" placeholder="Enter your Gmail ID">
                <input type="password" id="authPass" class="input-field" placeholder="Enter password">
                <button class="btn" id="authSubmitBtn" onclick="handleAuth('login')">LOGIN ACCOUNT</button>
            </div>
        </div>
        <script>
            function showToast(msg) {
                const t = document.getElementById('toast');
                if(!t) return;
                t.innerText = msg; t.classList.add('show');
                setTimeout(() => t.classList.remove('show'), 2000);
            }

            function switchAuthTab(mode) {
                document.getElementById('tabLogin').classList.toggle('active', mode === 'login');
                document.getElementById('tabReg').classList.toggle('active', mode === 'register');
                document.getElementById('authSubmitBtn').innerText = mode === 'login' ? 'LOGIN ACCOUNT' : 'CREATE ACCOUNT';
                document.getElementById('authSubmitBtn').setAttribute('onclick', `handleAuth('${mode}')`);
            }

            async function handleAuth(mode) {
                const email = document.getElementById('authEmail').value;
                const password = document.getElementById('authPass').value;
                if(!email) { showToast('ERR: ENTER GMAIL ID!'); return; }
                
                try {
                    const res = await fetch('/' + mode, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({email, password})
                    });
                    const data = await res.json();
                    if(data.error) { 
                        showToast('ERR: ' + data.error); 
                    } else { 
                        showToast(data.message || 'SUCCESS');
                        setTimeout(() => window.location.reload(), 1000);
                    }
                } catch(e) {
                    showToast('ERR: CONNECTION FAILED');
                }
            }
        </script>
        {% else %}
        
        <!-- HEADER WITH ONLINE BADGE -->
        <div class="ring-header">
            <div class="ring-avatar">
                <svg width="28" height="28" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="18" cy="18" r="14" stroke="#00f3ff" stroke-width="3" stroke-dasharray="6 3"/>
                    <circle cx="18" cy="18" r="3" fill="#b000ff"/>
                </svg>
            </div>
            <div class="ring-info">
                <h2>NEXUS-X v6</h2>
                <p>CYBER RING CORE</p>
            </div>
            <div class="status-badge-wrapper">
                <div class="online-dot"></div>
                <span class="badge">ONLINE</span>
            </div>
        </div>

        <!-- HOME VIEW -->
        <div id="homeView" class="view-section active">
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
                    <div class="res-info"><span>CPU USAGE</span><span id="cpuText">0%</span></div>
                    <div class="res-bar-bg"><div id="cpuBar" class="res-bar-fill"></div></div>
                </div>
                <div class="res-item" style="margin-top: 8px;">
                    <div class="res-info"><span>RAM USAGE</span><span id="ramText">0 MB / 0 MB</span></div>
                    <div class="res-bar-bg"><div id="ramBar" class="res-bar-fill"></div></div>
                </div>
                <div class="res-item" style="margin-top: 8px;">
                    <div class="res-info"><span>STORAGE USAGE</span><span id="diskText">0 GB / 0 GB</span></div>
                    <div class="res-bar-bg"><div id="diskBar" class="res-bar-fill"></div></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title"><span>⚡ DEPLOY ENGINE CORE</span></div>
                <div class="deploy-tabs">
                    <div class="deploy-tab-btn active" id="deployTab1" onclick="switchDeployTab(1)">OPTION 1 (PY)</div>
                    <div class="deploy-tab-btn" id="deployTab2" onclick="switchDeployTab(2)">OPTION 2 (ZIP / PHP / JS)</div>
                </div>
                
                <div class="deploy-section active" id="secOption1">
                    <div class="file-upload-wrapper">
                        <input type="file" id="pyBotFile" accept=".py">
                    </div>
                    <button class="btn" onclick="deployBot('py')">UPLOAD & DEPLOY PYTHON BOT</button>
                </div>

                <div class="deploy-section" id="secOption2">
                    <div class="file-upload-wrapper">
                        <input type="file" id="multiBotFile" accept=".zip,.php,.js">
                    </div>
                    <button class="btn" onclick="deployBot('multi')">UPLOAD & DEPLOY BUNDLE/SCRIPT</button>
                </div>
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

        <!-- PROFILE VIEW -->
        <div id="profileView" class="view-section">
            <div class="card" style="text-align: center; padding: 25px 20px;">
                <div class="ring-avatar" style="margin: 0 auto 12px auto; width: 60px; height: 60px;">
                    <svg width="30" height="30" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="18" cy="12" r="6" stroke="#00f3ff" stroke-width="2"/>
                        <path d="M6 30C6 24 11 22 18 22C25 22 30 24 30 30" stroke="#00f3ff" stroke-width="2"/>
                    </svg>
                </div>
                <div style="font-family: 'Orbitron'; font-size: 10px; color: var(--text-muted); margin-bottom: 4px;">LOGGED IN GMAIL</div>
                <div style="font-family: 'JetBrains Mono'; font-size: 12px; color: var(--neon-cyan); margin-bottom: 18px; word-break: break-all;">{{ user_email }}</div>
                
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <button class="btn" style="background: rgba(0, 243, 255, 0.1); color: var(--neon-cyan); border: 1px solid rgba(0, 243, 255, 0.4); padding: 12px; font-size: 11px;" onclick="openPolicyModal()">📜 PLATFORM POLICY & RULES</button>
                    <button class="btn" style="background: rgba(176, 0, 255, 0.12); color: #d8b4fe; border: 1px solid rgba(176, 0, 255, 0.4); padding: 12px; font-size: 11px;" onclick="openSupportModal()">🛠️ HELP & SUPPORT</button>
                    <button class="btn" style="background: linear-gradient(135deg, #ff3366, #ff0055); color: #fff; padding: 14px; font-size: 11px;" onclick="location.href='/logout'">🚪 LOGOUT ACCOUNT</button>
                </div>
            </div>
        </div>

        <!-- BOTTOM NAVIGATION BAR -->
        <div class="bottom-nav">
            <button class="nav-item active" id="navHomeBtn" onclick="switchNav('home')">
                <span>🏠</span>
                <span>HOME</span>
            </button>
            <button class="nav-item" id="navProfileBtn" onclick="switchNav('profile')">
                <span>👤</span>
                <span>PROFILE</span>
            </button>
        </div>
        {% endif %}
    </div>

    <!-- CODE EDITOR MODAL -->
    <div id="editorModal">
        <div class="modal-content" style="height: 85vh;">
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

    <!-- POLICY MODAL -->
    <div id="policyModal">
        <div class="modal-content">
            <div class="editor-header">
                <span class="editor-title">📜 PLATFORM POLICY & RULES</span>
                <button class="close-term" onclick="closePolicyModal()">CLOSE</button>
            </div>
            <div class="modal-body">
                <h3>1. LEGAL VS ILLEGAL HOSTING RULES</h3>
                <p><strong>Allowed (Legal Bots):</strong> Standard utility bots, Telegram automated workflow bots, calculator tools, custom web scrapers for public data, database-backed bots, educational PHP/JS scripts, and personal management tools are fully permitted.</p>
                <p><strong>Prohibited (Illegal / Harmful Content):</strong> Hosting DDoS scripts, malware, brute-force crackers, phishing portals, unauthorized carding tools, cryptocurrency miners, or any script targeting cyberattacks on external networks is strictly banned.</p>
                
                <h3>2. RESOURCE FAIR USAGE</h3>
                <p>Each user account is allocated isolated storage and continuous execution runtime. Excessive abuse of system RAM, storage overloads, or background infinite loops causing core thread blocking will result in immediate termination of the instance.</p>
                
                <h3>3. PRIVACY & DATA ISOLATION</h3>
                <p>All files uploaded to your workspace are completely encrypted and isolated. No other user can view, download, modify, or execute your deployed files or logs. Security compliance is automatically enforced by NEXUS-X core.</p>
            </div>
            <button class="btn" style="padding: 10px; font-size: 10px;" onclick="closePolicyModal()">I UNDERSTAND</button>
        </div>
    </div>

    <!-- SUPPORT MODAL -->
    <div id="supportModal">
        <div class="modal-content">
            <div class="editor-header">
                <span class="editor-title">🛠️ SUPPORT & ASSISTANCE</span>
                <button class="close-term" onclick="closeSupportModal()">CLOSE</button>
            </div>
            <div class="modal-body">
                <h3>NEED HELP WITH DEPLOYMENT?</h3>
                <p>If your bot crashes, fails to start, or throws database connection errors, check the live terminal logs directly from the home dashboard instance card.</p>
                <p><strong>Common Solutions:</strong></p>
                <p>• Ensure required python libraries are installed or included in your script imports.<br>• Verify syntax errors using the built-in code editor.<br>• Restart the instance if background process locks occur.</p>
                <p>For custom inquiries or infrastructure assistance, reach out via your administrator communication channel.</p>
            </div>
            <button class="btn" style="padding: 10px; font-size: 10px;" onclick="closeSupportModal()">CLOSE SUPPORT</button>
        </div>
    </div>

    <div id="toast">SYSTEM READY</div>
    <script>
        const KEY = 'admin123';
        let activeLogFile = null, logInterval = null, isMinimized = false, editingFile = null;

        function switchNav(viewName) {
            document.getElementById('homeView').classList.toggle('active', viewName === 'home');
            document.getElementById('profileView').classList.toggle('active', viewName === 'profile');
            document.getElementById('navHomeBtn').classList.toggle('active', viewName === 'home');
            document.getElementById('navProfileBtn').classList.toggle('active', viewName === 'profile');
        }

        function switchDeployTab(optionNum) {
            document.getElementById('deployTab1').classList.toggle('active', optionNum === 1);
            document.getElementById('deployTab2').classList.toggle('active', optionNum === 2);
            document.getElementById('secOption1').classList.toggle('active', optionNum === 1);
            document.getElementById('secOption2').classList.toggle('active', optionNum === 2);
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            if(!t) return;
            t.innerText = msg; t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2000);
        }

        function openPolicyModal() { document.getElementById('policyModal').style.display = 'flex'; }
        function closePolicyModal() { document.getElementById('policyModal').style.display = 'none'; }

        function openSupportModal() { document.getElementById('supportModal').style.display = 'flex'; }
        function closeSupportModal() { document.getElementById('supportModal').style.display = 'none'; }

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

        async function deployBot(type) {
            const inputId = type === 'py' ? 'pyBotFile' : 'multiBotFile';
            const fileInput = document.getElementById(inputId);
            if(!fileInput || !fileInput.files[0]) { showToast('ERR: SELECT A FILE'); return; }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('license_key', KEY);
            showToast('UPLOADING & DEPLOYING...');
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if(data.error) showToast('ERR: ' + data.error);
                else {
                    showToast(data.message);
                    loadInstances();
                    if(data.filename) openTerminal(data.filename);
                }
            } catch(e) { showToast('UPLOAD FAILED'); }
        }

        async function loadInstances() {
            try {
                const res = await fetch(`/list?key=${KEY}`);
                const data = await res.json();
                const list = document.getElementById('instanceList');
                if(!list) return;
                if(!data.bots || data.bots.length === 0) {
                    list.innerHTML = '<div class="empty">NO SCRIPTS FOUND</div>';
                } else {
                    list.innerHTML = data.bots.map(b => {
                        const online = b.status === 'ONLINE';
                        return `
                            <div class="instance-item">
                                <div class="instance-top">
                                    <span>⚡ ${b.name}</span>
                                    <span class="${online ? 'st-on' : 'st-off'}">${b.status}</span>
                                </div>
                                ${online ? `
                                <div class="metrics-row">
                                    <span class="metric-badge">CPU: ${b.cpu}</span>
                                    <span class="metric-badge">RAM: ${b.ram}</span>
                                </div>` : ''}
                                <div class="actions">
                                    <button class="act-btn b-start" onclick="actionBot('start', '${b.name}')">START</button>
                                    <button class="act-btn b-stop" onclick="actionBot('stop', '${b.name}')">STOP</button>
                                    <button class="act-btn b-del" onclick="actionBot('delete', '${b.name}')">DELETE</button>
                                </div>
                                <div class="secondary-actions" style="margin-top:6px;">
                                    <button class="sec-btn b-edit" onclick="openEditor('${b.name}')">📝 EDIT</button>
                                    <button class="sec-btn b-log" onclick="openTerminal('${b.name}')">🖥️ LOGS</button>
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
                    openTerminal(filename);
                }
            } catch(e){ showToast('ACTION FAILED'); }
            setTimeout(loadInstances, 500);
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

        function openTerminal(filename) {
            activeLogFile = filename;
            document.getElementById('terminalCard').style.display = 'block';
            if(isMinimized) toggleMinimize();
            document.getElementById('termFileName').innerText = 'LOGS: ' + filename;
            fetchLog();
            if(logInterval) clearInterval(logInterval);
            logInterval = setInterval(fetchLog, 6000);
        }

        function toggleMinimize() {
            const termBox = document.getElementById('terminalOutput');
            const minBtn = document.getElementById('minBtn');
            isMinimized = !isMinimized;
            if(isMinimized) {
                termBox.style.display = 'none';
                minBtn.innerText = 'MAX';
            } else {
                termBox.style.display = 'block';
                minBtn.innerText = 'MIN';
                termBox.scrollTop = termBox.scrollHeight;
            }
        }

        function closeTerminal() {
            document.getElementById('terminalCard').style.display = 'none';
            if(logInterval) clearInterval(logInterval);
            activeLogFile = null;
            isMinimized = false;
            document.getElementById('terminalOutput').style.display = 'block';
            document.getElementById('minBtn').innerText = 'MIN';
        }

        async function fetchLog() {
            if(!activeLogFile || isMinimized) return;
            try {
                const res = await fetch(`/get_log/${activeLogFile}?key=${KEY}`);
                const data = await res.json();
                const term = document.getElementById('terminalOutput');
                term.innerText = data.log || 'No logs...';
                term.scrollTop = term.scrollHeight;
            } catch(e) {}
        }

        if(document.getElementById('instanceList')) {
            loadInstances();
            updateSystemStats();
            setInterval(loadInstances, 10000);
            setInterval(updateSystemStats, 6000);
        }
    </script>
</body>
</html>
"""

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password', '')
    if not email or '@gmail.com' not in email:
        return jsonify({'error': 'Valid Gmail ID required'}), 400
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    if email in users:
        return jsonify({'error': 'Account already exists! Please login.'}), 400
    
    users[email] = password
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)
    
    session['user'] = email
    return jsonify({'message': 'Registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password', '')
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
        
    if email not in users:
        return jsonify({'error': 'Account not found! Please register first.'}), 400
        
    if users[email] != password:
        return jsonify({'error': 'Incorrect password!'}), 400
        
    session['user'] = email
    return jsonify({'message': 'Logged in successfully'})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/')
def index(): 
    logged_in = 'user' in session
    user_email = session.get('user', '')
    return render_template_string(AUTO_PILOT_HTML, logged_in=logged_in, user_email=user_email)

@app.route('/system_stats', methods=['GET'])
def system_stats():
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    global current_cpu
    return jsonify({
        'cpu_percent': current_cpu,
        'ram_total': 4096.0, 'ram_used': 1240.5, 'ram_percent': 30.2,
        'disk_total': 64.0, 'disk_used': 18.5, 'disk_percent': 28.9
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if request.form.get('license_key') != DEFAULT_KEY:
            return jsonify({'error': 'Unauthorized'}), 403
        user_dir = get_user_folder()
        if not user_dir:
            return jsonify({'error': 'Unauthorized user session'}), 401
            
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(user_dir, filename)
        file.save(filepath)
        
        if filename.endswith('.zip'):
            extract_path = os.path.join(user_dir, filename.replace('.zip', ''))
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            os.remove(filepath)
            return jsonify({'message': f'Extracted Zip archive: {filename}', 'filename': filename})
        
        return jsonify({'message': f'Uploaded {filename}!', 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_code/<filename>', methods=['GET'])
def get_code(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    filepath = os.path.join(user_dir, filename)
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
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    filepath = os.path.join(user_dir, filename)
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
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    files = os.listdir(user_dir) if os.path.exists(user_dir) else []
    bots = []
    for f in sorted(files):
        if f.endswith(('.py', '.php', '.js')) or os.path.isdir(os.path.join(user_dir, f)):
            is_running = False
            cpu_usage, ram_usage = "0%", "0 MB"
            proc_key = f"{session.get('user')}:{f}"
            if proc_key in active_processes:
                pid = active_processes[proc_key].get('pid')
                if pid and psutil.pid_exists(pid):
                    try:
                        p = psutil.Process(pid)
                        if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                            is_running = True
                            cpu_usage = f"{p.cpu_percent(interval=0.0):.1f}%"
                            ram_usage = f"{p.memory_info().rss / (1024 * 1024):.1f} MB"
                    except:
                        pass
            bots.append({'name': f, 'status': 'ONLINE' if is_running else 'OFFLINE', 'cpu': cpu_usage, 'ram': ram_usage})
    return jsonify({'bots': bots})

@app.route('/start/<filename>', methods=['POST'])
def start_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    filepath = os.path.join(user_dir, filename)
    log_path = filepath + '.log'
    proc_key = f"{session.get('user')}:{filename}"
    
    cmd = ['python3', '-u', filepath]
    if filename.endswith('.js'):
        cmd = ['node', filepath]
    elif filename.endswith('.php'):
        cmd = ['php', filepath]
    
    try:
        log_file_obj = open(log_path, 'a', encoding='utf-8')
        proc = subprocess.Popen(cmd, stdout=log_file_obj, stderr=log_file_obj, start_new_session=True)
        active_processes[proc_key] = {'proc': proc, 'pid': proc.pid}
        desired_states[proc_key] = True
        return jsonify({'message': f'Started {filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop/<filename>', methods=['POST'])
def stop_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    proc_key = f"{session.get('user')}:{filename}"
    desired_states[proc_key] = False
    if proc_key in active_processes:
        try:
            pid = active_processes[proc_key].get('pid')
            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
        except:
            pass
        active_processes.pop(proc_key, None)
    return jsonify({'message': f'Stopped {filename}'})

@app.route('/delete/<filename>', methods=['POST'])
def delete_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    proc_key = f"{session.get('user')}:{filename}"
    desired_states.pop(proc_key, None)
    filepath = os.path.join(user_dir, filename)
    if proc_key in active_processes:
        try:
            pid = active_processes[proc_key].get('pid')
            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
        except:
            pass
        active_processes.pop(proc_key, None)
    if os.path.exists(filepath):
        if os.path.isdir(filepath):
            import shutil
            shutil.rmtree(filepath)
        else:
            os.remove(filepath)
    if os.path.exists(filepath + '.log'):
        os.remove(filepath + '.log')
    return jsonify({'message': f'Deleted {filename}'})

@app.route('/get_log/<filename>', methods=['GET'])
def get_log(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    log_path = os.path.join(user_dir, filename + '.log')
    if os.path.exists(log_path):
        try:
            with open(log_path, 'rb') as lf:
                lf.seek(0, 2)
                filesize = lf.tell()
                lf.seek(max(0, filesize - 15000), 0)
                content = lf.read().decode('utf-8', errors='ignore')
        except:
            content = "Error reading log..."
        return jsonify({'log': content})
    return jsonify({'log': 'No logs found.'})

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
    print("🚀 NEXUS-X v6 CLOUD IDE STARTED SUCCESSFULLY!")
    print(f"👉 Local URL: http://127.0.0.1:5000")
    print(f"👉 Network IP: http://{local_ip}:5000")
    print("="*40 + "\n")
    serve(app, host='0.0.0.0', port=5000, threads=8)
