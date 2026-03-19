"""
龙虾漏洞 Web 服务 — 5种真实漏洞
每只龙虾运行一个相同的 Flask 服务，AI 负责攻击别人/修补自己
"""
import os
import re
import json
import sqlite3
import hashlib
import subprocess
import time
import base64
import threading
from flask import Flask, request, jsonify, render_template_string, make_response
from urllib.request import urlopen
from urllib.parse import urlparse

app = Flask(__name__)
DB_PATH = "/app/data/lobster.db"
FLAG_PATH = "/app/flag.txt"
PATCH_LOG = "/app/data/patches.json"  # 记录哪些漏洞已修补

def get_flag():
    try:
        return open(FLAG_PATH).read().strip()
    except:
        return "FLAG{placeholder}"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库（含隐藏 flag）"""
    os.makedirs("/app/data", exist_ok=True)
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS secrets (id INTEGER PRIMARY KEY, flag TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    
    # 插入示例数据
    c.execute("DELETE FROM posts")
    c.execute("INSERT INTO posts VALUES (1, '龙虾日记', '今天天气不错，适合打架')")
    c.execute("INSERT INTO posts VALUES (2, '战术研究', '孙子兵法第三篇：谋攻')")
    c.execute("INSERT INTO posts VALUES (3, '美食推荐', '隔壁龙虾看起来不错')")
    
    c.execute("DELETE FROM secrets")
    c.execute(f"INSERT INTO secrets VALUES (1, '{get_flag()}')")
    
    c.execute("DELETE FROM users")
    c.execute("INSERT INTO users VALUES (1, 'admin', 'super_secret_password_123', 'admin')")
    c.execute("INSERT INTO users VALUES (2, 'guest', 'guest', 'user')")
    
    conn.commit()
    conn.close()

def load_patches():
    """加载已修补的漏洞列表"""
    try:
        return json.load(open(PATCH_LOG))
    except:
        return {"patched": []}

def save_patches(patches):
    os.makedirs("/app/data", exist_ok=True)
    json.dump(patches, open(PATCH_LOG, "w"))

def is_patched(vuln_name):
    return vuln_name in load_patches().get("patched", [])


# =============================================
# 漏洞 1: 路径遍历 (Path Traversal) — 10 伤害
# =============================================
@app.route('/files')
def files():
    """
    读取 public 目录下的文件。
    漏洞：没有过滤 ../ ，可以读取 /app/flag.txt
    攻击：GET /files?name=../../flag.txt
    """
    filename = request.args.get('name', 'readme.txt')
    
    if is_patched("path_traversal"):
        # 已修补：限制在 public 目录内
        safe_path = os.path.realpath(os.path.join('/app/public', filename))
        if not safe_path.startswith('/app/public/'):
            return jsonify({"error": "Access denied"}), 403
        try:
            return open(safe_path).read()
        except FileNotFoundError:
            return jsonify({"error": "File not found"}), 404
    else:
        # 漏洞版本
        try:
            filepath = f'/app/public/{filename}'
            return open(filepath).read()
        except FileNotFoundError:
            return jsonify({"error": "File not found"}), 404


# =============================================
# 漏洞 2: SQL 注入 (SQL Injection) — 20 伤害
# =============================================
@app.route('/search')
def search():
    """
    搜索文章。
    漏洞：字符串拼接 SQL
    攻击：GET /search?q=' UNION SELECT 1,flag,1 FROM secrets--
    """
    q = request.args.get('q', '')
    
    if is_patched("sql_injection"):
        # 已修补：参数化查询
        conn = get_db()
        results = conn.execute("SELECT * FROM posts WHERE title LIKE ?", (f'%{q}%',)).fetchall()
        conn.close()
        return jsonify([dict(r) for r in results])
    else:
        # 漏洞版本
        conn = get_db()
        try:
            results = conn.execute(f"SELECT * FROM posts WHERE title LIKE '%{q}%'").fetchall()
            conn.close()
            return jsonify([dict(r) for r in results])
        except Exception as e:
            conn.close()
            return jsonify({"error": str(e)}), 500


# =============================================
# 漏洞 3: 命令注入 (Command Injection) — 35 伤害
# =============================================
@app.route('/ping')
def ping():
    """
    Ping 一个主机。
    漏洞：直接拼接 shell 命令
    攻击：GET /ping?host=;cat /app/flag.txt
    """
    host = request.args.get('host', 'localhost')
    
    if is_patched("command_injection"):
        # 已修补：白名单 + subprocess
        if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
            return jsonify({"error": "Invalid hostname"}), 400
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '2', host], 
                                  capture_output=True, text=True, timeout=5)
            return jsonify({"output": result.stdout})
        except:
            return jsonify({"error": "Ping failed"}), 500
    else:
        # 漏洞版本
        try:
            result = os.popen(f'ping -c 1 {host} 2>&1').read()
            return jsonify({"output": result})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# =============================================
# 漏洞 4: 认证绕过 (Auth Bypass) — 25 伤害
# =============================================
@app.route('/admin')
def admin():
    """
    管理员页面，显示 flag。
    漏洞：JWT 使用弱密钥 "lobster"，且接受 none 算法
    攻击：伪造 JWT token
    """
    token = request.cookies.get('auth_token', '')
    
    if is_patched("auth_bypass"):
        # 已修补：强密钥 + 只接受 HS256
        if not token:
            return jsonify({"error": "Login required", "hint": "POST /login with username & password"}), 401
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return jsonify({"error": "Invalid token"}), 401
            header = json.loads(base64.b64decode(parts[0] + '=='))
            if header.get('alg') != 'HS256':
                return jsonify({"error": "Invalid algorithm"}), 401
            # 使用强密钥验证
            strong_secret = os.environ.get('JWT_SECRET', os.urandom(32).hex())
            expected_sig = hashlib.sha256(f"{parts[0]}.{parts[1]}{strong_secret}".encode()).hexdigest()[:16]
            if parts[2] != expected_sig:
                return jsonify({"error": "Invalid signature"}), 401
            payload = json.loads(base64.b64decode(parts[1] + '=='))
            if payload.get('role') != 'admin':
                return jsonify({"error": "Admin access only"}), 403
            return jsonify({"flag": get_flag(), "message": "Welcome, admin!"})
        except:
            return jsonify({"error": "Auth failed"}), 401
    else:
        # 漏洞版本：弱密钥 "lobster"，接受 none 算法
        if not token:
            return jsonify({"error": "Login required", "hint": "POST /login with username & password"}), 401
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return jsonify({"error": "Invalid token"}), 401
            
            header = json.loads(base64.b64decode(parts[0] + '=='))
            payload = json.loads(base64.b64decode(parts[1] + '=='))
            
            # 漏洞：接受 "none" 算法（不验证签名）
            if header.get('alg') == 'none':
                if payload.get('role') == 'admin':
                    return jsonify({"flag": get_flag(), "message": "Welcome, admin!"})
                return jsonify({"error": "Not admin"}), 403
            
            # 漏洞：弱密钥 "lobster"
            secret = "lobster"
            expected_sig = hashlib.sha256(f"{parts[0]}.{parts[1]}{secret}".encode()).hexdigest()[:16]
            if parts[2] == expected_sig:
                if payload.get('role') == 'admin':
                    return jsonify({"flag": get_flag(), "message": "Welcome, admin!"})
            
            return jsonify({"error": "Invalid token"}), 401
        except:
            return jsonify({"error": "Auth failed"}), 401

@app.route('/login', methods=['POST'])
def login():
    """登录获取 token"""
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", 
                        (username, password)).fetchone()
    conn.close()
    
    if user:
        header = base64.b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload = base64.b64encode(json.dumps({"user": username, "role": user["role"]}).encode()).decode().rstrip('=')
        secret = "lobster"  # 弱密钥
        sig = hashlib.sha256(f"{header}.{payload}{secret}".encode()).hexdigest()[:16]
        token = f"{header}.{payload}.{sig}"
        resp = make_response(jsonify({"message": "Login success", "token": token}))
        resp.set_cookie('auth_token', token)
        return resp
    
    return jsonify({"error": "Invalid credentials"}), 401


# =============================================
# 漏洞 5: SSRF (Server-Side Request Forgery) — 30 伤害
# =============================================
@app.route('/fetch')
def fetch_url():
    """
    获取远程 URL 内容。
    漏洞：没有限制 file:// 协议
    攻击：GET /fetch?url=file:///app/flag.txt
    """
    url = request.args.get('url', '')
    
    if is_patched("ssrf"):
        # 已修补：只允许 http/https，禁止内网
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return jsonify({"error": "Only http/https allowed"}), 400
        if parsed.hostname in ('localhost', '127.0.0.1', '0.0.0.0') or \
           (parsed.hostname and parsed.hostname.startswith('192.168.')):
            return jsonify({"error": "Internal URLs blocked"}), 400
        try:
            data = urlopen(url, timeout=5).read().decode('utf-8', errors='replace')[:5000]
            return jsonify({"content": data})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # 漏洞版本
        if not url:
            return jsonify({"error": "Missing url parameter"}), 400
        try:
            data = urlopen(url, timeout=5).read().decode('utf-8', errors='replace')[:5000]
            return jsonify({"content": data})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# =============================================
# 系统端点
# =============================================
@app.route('/health')
def health():
    """健康检查 — 裁判用来判断服务是否存活"""
    lobster_id = os.environ.get('LOBSTER_ID', '0')
    return jsonify({
        "status": "ok",
        "lobster_id": int(lobster_id),
        "timestamp": time.time(),
        "patched": load_patches().get("patched", [])
    })

@app.route('/patch', methods=['POST'])
def apply_patch():
    """AI 防御接口 — 修补指定漏洞"""
    # 只允许本地调用
    data = request.get_json() or {}
    vuln = data.get('vulnerability', '')
    valid_vulns = ["path_traversal", "sql_injection", "command_injection", "auth_bypass", "ssrf"]
    
    if vuln not in valid_vulns:
        return jsonify({"error": f"Unknown vulnerability: {vuln}", "valid": valid_vulns}), 400
    
    patches = load_patches()
    if vuln in patches["patched"]:
        return jsonify({"ok": True, "message": f"{vuln} already patched"})
    
    patches["patched"].append(vuln)
    save_patches(patches)
    
    # 如果修补了 SQL 注入，需要重新初始化 DB（更新 flag）
    if vuln == "sql_injection":
        init_db()
    
    return jsonify({"ok": True, "message": f"Patched {vuln}!", "patched": patches["patched"]})

@app.route('/unpatch', methods=['POST'])
def remove_patch():
    """移除补丁（用于随机事件）"""
    data = request.get_json() or {}
    vuln = data.get('vulnerability', '')
    patches = load_patches()
    if vuln in patches["patched"]:
        patches["patched"].remove(vuln)
        save_patches(patches)
    return jsonify({"ok": True, "patched": patches["patched"]})

@app.route('/update-flag', methods=['POST'])
def update_flag():
    """裁判更新 flag"""
    data = request.get_json() or {}
    new_flag = data.get('flag', '')
    referee_key = data.get('key', '')
    
    if referee_key != os.environ.get('REFEREE_SECRET', 'lobster-referee-key'):
        return jsonify({"error": "Unauthorized"}), 403
    
    with open(FLAG_PATH, 'w') as f:
        f.write(new_flag)
    
    # 更新数据库里的 flag
    try:
        conn = get_db()
        conn.execute("UPDATE secrets SET flag=? WHERE id=1", (new_flag,))
        conn.commit()
        conn.close()
    except:
        pass
    
    return jsonify({"ok": True})

@app.route('/')
def index():
    lobster_name = os.environ.get('LOBSTER_NAME', 'Unknown')
    lobster_emoji = os.environ.get('LOBSTER_EMOJI', '🦞')
    return render_template_string("""
    <html>
    <head><title>{{ emoji }} {{ name }} 的领地</title></head>
    <body style="background:#1a1a2e;color:#eee;font-family:monospace;padding:20px">
        <h1>{{ emoji }} {{ name }}</h1>
        <p>欢迎来到我的领地。想找什么？</p>
        <ul>
            <li><a href="/files?name=readme.txt" style="color:#0ff">/files</a> - 文件服务</li>
            <li><a href="/search?q=龙虾" style="color:#0ff">/search</a> - 搜索文章</li>
            <li><a href="/ping?host=localhost" style="color:#0ff">/ping</a> - Ping 服务</li>
            <li><a href="/admin" style="color:#0ff">/admin</a> - 管理后台</li>
            <li><a href="/fetch?url=http://example.com" style="color:#0ff">/fetch</a> - URL 抓取</li>
            <li><a href="/health" style="color:#0ff">/health</a> - 健康状态</li>
        </ul>
    </body>
    </html>
    """, name=lobster_name, emoji=lobster_emoji)


# Flag 更新线程
def flag_updater():
    """定期从文件重读 flag 到数据库"""
    while True:
        time.sleep(30)
        try:
            init_db()
        except:
            pass

def run_server():
    """启动 web 服务"""
    # 创建 public 目录和示例文件
    os.makedirs('/app/public', exist_ok=True)
    with open('/app/public/readme.txt', 'w') as f:
        f.write("欢迎来到龙虾服务器！这里没有 flag，真的。")
    with open('/app/public/about.txt', 'w') as f:
        f.write("我是一只有梦想的龙虾。")
    
    # 初始化 flag
    if not os.path.exists(FLAG_PATH):
        with open(FLAG_PATH, 'w') as f:
            f.write("FLAG{waiting_for_referee}")
    
    # 初始化数据库
    init_db()
    
    # 启动 flag 更新线程
    t = threading.Thread(target=flag_updater, daemon=True)
    t.start()
    
    # 启动 Flask
    app.run(host='0.0.0.0', port=5000, threaded=True)

if __name__ == '__main__':
    run_server()
