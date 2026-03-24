"""
╔══════════════════════════════════════════════════════════════════════╗
║              🖥 ADMIN PANEL — GroupHelp Bot                         ║
║         Веб-панель администратора на Flask                           ║
╚══════════════════════════════════════════════════════════════════════╝

ЗАПУСК:
    python admin_panel.py

Открой в браузере: http://localhost:5000
Логин: admin / Пароль: admin123  (измени в ADMIN_CREDENTIALS)
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, flash
import asyncio
import json
import os
from datetime import datetime
from functools import wraps

# Импортируем наш db модуль
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as database

app = Flask(__name__)
app.secret_key = "ИЗМЕНИ_ЭТОТ_СЕКРЕТ_НА_СЛУЧАЙНУЮ_СТРОКУ"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  КОНФИГ ПАНЕЛИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ADMIN_CREDENTIALS = {
    "admin":  "admin123",    # Логин: Пароль — ИЗМЕНИ!
    "owner2": "securepass2", # Второй владелец
}

PANEL_TITLE = "GroupHelp Admin"

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HTML ШАБЛОНЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BASE_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} — {{ panel_title }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e1a;--bg2:#0f1629;--bg3:#151e35;--card:#1a2440;
  --border:#1f2d4a;--accent:#3b82f6;--accent2:#6366f1;
  --green:#22c55e;--red:#ef4444;--yellow:#f59e0b;--purple:#a855f7;
  --text:#e2e8f0;--text2:#94a3b8;--text3:#64748b;
  --sidebar-w:260px;
}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex}
/* SIDEBAR */
.sidebar{width:var(--sidebar-w);background:var(--bg2);border-right:1px solid var(--border);
  display:flex;flex-direction:column;position:fixed;height:100vh;overflow-y:auto;z-index:100}
.sidebar-header{padding:24px 20px;border-bottom:1px solid var(--border)}
.sidebar-logo{display:flex;align-items:center;gap:12px}
.logo-icon{width:40px;height:40px;background:linear-gradient(135deg,var(--accent),var(--accent2));
  border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px}
.logo-text{font-size:16px;font-weight:700;color:var(--text)}
.logo-sub{font-size:11px;color:var(--text3);margin-top:2px}
.sidebar-nav{padding:16px 12px;flex:1}
.nav-section{margin-bottom:8px}
.nav-section-title{font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;
  letter-spacing:1px;padding:8px 10px 4px}
.nav-link{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:10px;
  color:var(--text2);text-decoration:none;font-size:13.5px;font-weight:500;transition:all .15s;margin-bottom:2px}
.nav-link:hover{background:var(--bg3);color:var(--text)}
.nav-link.active{background:linear-gradient(135deg,rgba(59,130,246,.15),rgba(99,102,241,.15));
  color:var(--accent);border:1px solid rgba(59,130,246,.2)}
.nav-link .icon{font-size:16px;width:20px;text-align:center}
.nav-badge{margin-left:auto;background:var(--red);color:#fff;font-size:10px;
  padding:2px 7px;border-radius:20px;font-weight:600}
.sidebar-footer{padding:16px;border-top:1px solid var(--border)}
.user-badge{display:flex;align-items:center;gap:10px;padding:10px;background:var(--bg3);
  border-radius:10px}
.user-avatar{width:32px;height:32px;background:linear-gradient(135deg,var(--accent),var(--purple));
  border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px}
.user-name{font-size:13px;font-weight:600}
.user-role{font-size:11px;color:var(--text3)}
/* MAIN */
.main{margin-left:var(--sidebar-w);flex:1;display:flex;flex-direction:column;min-height:100vh}
.topbar{padding:16px 28px;background:var(--bg2);border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50}
.page-title{font-size:18px;font-weight:700}
.page-sub{font-size:12px;color:var(--text3);margin-top:2px}
.topbar-actions{display:flex;align-items:center;gap:12px}
.btn{display:inline-flex;align-items:center;gap:7px;padding:8px 16px;border-radius:9px;
  font-size:13px;font-weight:600;cursor:pointer;border:none;transition:all .15s;text-decoration:none}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{background:#2563eb}
.btn-danger{background:var(--red);color:#fff}.btn-danger:hover{background:#dc2626}
.btn-success{background:var(--green);color:#fff}.btn-success:hover{background:#16a34a}
.btn-ghost{background:var(--bg3);color:var(--text2);border:1px solid var(--border)}
.btn-ghost:hover{color:var(--text);border-color:var(--accent)}
.btn-sm{padding:5px 12px;font-size:12px}
.btn-warn{background:var(--yellow);color:#000}.btn-warn:hover{background:#d97706}
.content{padding:28px;flex:1}
/* CARDS */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;
  position:relative;overflow:hidden;transition:transform .15s}
.stat-card:hover{transform:translateY(-2px)}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.stat-card.blue::before{background:linear-gradient(90deg,var(--accent),var(--accent2))}
.stat-card.green::before{background:linear-gradient(90deg,var(--green),#86efac)}
.stat-card.red::before{background:linear-gradient(90deg,var(--red),#f87171)}
.stat-card.yellow::before{background:linear-gradient(90deg,var(--yellow),#fcd34d)}
.stat-card.purple::before{background:linear-gradient(90deg,var(--purple),#c084fc)}
.stat-card.teal::before{background:linear-gradient(90deg,#14b8a6,#5eead4)}
.stat-icon{font-size:28px;margin-bottom:10px}
.stat-value{font-size:28px;font-weight:800;font-family:'JetBrains Mono',monospace}
.stat-label{font-size:12px;color:var(--text3);margin-top:3px;font-weight:500}
.stat-delta{font-size:11px;color:var(--green);margin-top:4px}
/* TABLE */
.table-card{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.table-header{padding:18px 24px;border-bottom:1px solid var(--border);display:flex;
  align-items:center;justify-content:space-between}
.table-title{font-size:15px;font-weight:700}
.table-controls{display:flex;gap:10px;align-items:center}
.search-input{padding:8px 14px;background:var(--bg3);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:13px;outline:none;width:200px}
.search-input:focus{border-color:var(--accent)}
.search-input::placeholder{color:var(--text3)}
table{width:100%;border-collapse:collapse}
th{padding:12px 16px;font-size:11px;font-weight:600;color:var(--text3);text-transform:uppercase;
  letter-spacing:.5px;text-align:left;background:var(--bg3);border-bottom:1px solid var(--border)}
td{padding:13px 16px;font-size:13.5px;border-bottom:1px solid var(--border);vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.02)}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;border-radius:20px;
  font-size:11px;font-weight:600}
.badge-green{background:rgba(34,197,94,.15);color:var(--green)}
.badge-red{background:rgba(239,68,68,.15);color:var(--red)}
.badge-yellow{background:rgba(245,158,11,.15);color:var(--yellow)}
.badge-blue{background:rgba(59,130,246,.15);color:var(--accent)}
.badge-purple{background:rgba(168,85,247,.15);color:var(--purple)}
.badge-gray{background:rgba(100,116,139,.15);color:var(--text3)}
/* FORMS */
.form-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.form-group{display:flex;flex-direction:column;gap:6px}
.form-group.full{grid-column:1/-1}
label{font-size:12px;font-weight:600;color:var(--text2)}
input,select,textarea{background:var(--bg3);border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-size:13.5px;padding:10px 14px;outline:none;width:100%;font-family:inherit}
input:focus,select:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(59,130,246,.1)}
textarea{resize:vertical;min-height:80px}
select option{background:var(--bg2)}
/* MODALS */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;
  display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.modal{background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:28px;width:520px;max-width:95vw;max-height:85vh;overflow-y:auto}
.modal-title{font-size:18px;font-weight:700;margin-bottom:20px;display:flex;
  align-items:center;justify-content:space-between}
.modal-close{background:var(--bg3);border:none;color:var(--text2);width:30px;height:30px;
  border-radius:50%;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center}
/* TABS */
.tabs{display:flex;gap:4px;margin-bottom:24px;background:var(--bg2);
  padding:4px;border-radius:10px;width:fit-content}
.tab{padding:8px 18px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;
  color:var(--text2);transition:all .15s;text-decoration:none}
.tab.active{background:var(--bg3);color:var(--text);box-shadow:0 1px 4px rgba(0,0,0,.3)}
.tab:hover:not(.active){color:var(--text)}
/* ALERTS */
.alert{padding:14px 18px;border-radius:10px;margin-bottom:20px;font-size:13.5px;
  display:flex;align-items:center;gap:10px}
.alert-success{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.2);color:var(--green)}
.alert-error{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:var(--red)}
.alert-info{background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.2);color:var(--accent)}
/* TOGGLE */
.toggle{position:relative;width:44px;height:24px;cursor:pointer}
.toggle input{display:none}
.toggle-track{position:absolute;inset:0;background:var(--bg3);border-radius:12px;
  border:1px solid var(--border);transition:.2s}
.toggle input:checked~.toggle-track{background:var(--accent);border-color:var(--accent)}
.toggle-thumb{position:absolute;top:2px;left:2px;width:18px;height:18px;background:#fff;
  border-radius:50%;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.3)}
.toggle input:checked~.toggle-track~.toggle-thumb,
.toggle input:checked+.toggle-track+.toggle-thumb{left:22px}
/* CHART */
.chart-container{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:20px;margin-bottom:24px}
.chart-title{font-size:14px;font-weight:600;margin-bottom:16px;color:var(--text2)}
.mini-chart{height:60px;display:flex;align-items:flex-end;gap:4px}
.bar{background:linear-gradient(0deg,var(--accent),var(--accent2));border-radius:4px 4px 0 0;
  min-width:20px;flex:1;transition:height .3s}
/* CODE */
.code{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--accent);
  background:var(--bg3);padding:2px 7px;border-radius:5px}
/* PAGINATION */
.pagination{display:flex;gap:6px;align-items:center;justify-content:center;padding:20px}
.page-btn{width:34px;height:34px;border-radius:8px;background:var(--bg3);border:1px solid var(--border);
  color:var(--text2);cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;
  text-decoration:none;transition:.15s}
.page-btn:hover,.page-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
/* EMPTY STATE */
.empty{text-align:center;padding:60px 20px;color:var(--text3)}
.empty-icon{font-size:48px;margin-bottom:16px}
.empty-text{font-size:15px;margin-bottom:8px;color:var(--text2)}
/* SCROLLBAR */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--text3)}
/* RESPONSIVE */
@media(max-width:768px){
  .sidebar{transform:translateX(-100%)}
  .main{margin-left:0}
  .stats-grid{grid-template-columns:1fr 1fr}
  .form-grid{grid-template-columns:1fr}
}
/* LIVE INDICATOR */
.live-dot{width:8px;height:8px;background:var(--green);border-radius:50%;
  animation:pulse 2s infinite;display:inline-block;margin-right:6px}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(1.3)}}
</style>
</head>
<body>
<nav class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">
      <div class="logo-icon">🛡</div>
      <div>
        <div class="logo-text">GroupHelp</div>
        <div class="logo-sub">Admin Panel v2.0</div>
      </div>
    </div>
  </div>
  <div class="sidebar-nav">
    <div class="nav-section">
      <div class="nav-section-title">Главное</div>
      <a href="/dashboard" class="nav-link {{ 'active' if active=='dashboard' }}">
        <span class="icon">📊</span> Дашборд
      </a>
      <a href="/bot-stats" class="nav-link {{ 'active' if active=='botstats' }}">
        <span class="icon">📈</span> Статистика
      </a>
    </div>
    <div class="nav-section">
      <div class="nav-section-title">Управление</div>
      <a href="/groups" class="nav-link {{ 'active' if active=='groups' }}">
        <span class="icon">💬</span> Группы
      </a>
      <a href="/users" class="nav-link {{ 'active' if active=='users' }}">
        <span class="icon">👥</span> Пользователи
      </a>
      <a href="/antispam" class="nav-link {{ 'active' if active=='antispam' }}">
        <span class="icon">🚨</span> Анти-Спам
        {% if pending_count and pending_count > 0 %}
        <span class="nav-badge">{{ pending_count }}</span>
        {% endif %}
      </a>
    </div>
    <div class="nav-section">
      <div class="nav-section-title">Данные</div>
      <a href="/warnings" class="nav-link {{ 'active' if active=='warnings' }}">
        <span class="icon">⚠️</span> Предупреждения
      </a>
      <a href="/actions" class="nav-link {{ 'active' if active=='actions' }}">
        <span class="icon">🗂</span> Действия
      </a>
      <a href="/eventlog" class="nav-link {{ 'active' if active=='eventlog' }}">
        <span class="icon">📋</span> Лог событий
      </a>
    </div>
    <div class="nav-section">
      <div class="nav-section-title">Система</div>
      <a href="/broadcast" class="nav-link {{ 'active' if active=='broadcast' }}">
        <span class="icon">📢</span> Рассылка
      </a>
      <a href="/settings-panel" class="nav-link {{ 'active' if active=='panelsettings' }}">
        <span class="icon">⚙️</span> Настройки панели
      </a>
    </div>
  </div>
  <div class="sidebar-footer">
    <div class="user-badge">
      <div class="user-avatar">👑</div>
      <div>
        <div class="user-name">{{ session.get('username','Admin') }}</div>
        <div class="user-role">Владелец бота</div>
      </div>
      <a href="/logout" style="margin-left:auto;color:var(--text3);font-size:14px;text-decoration:none">🚪</a>
    </div>
  </div>
</nav>
<main class="main">
  <div class="topbar">
    <div>
      <div class="page-title">{{ title }}</div>
      <div class="page-sub"><span class="live-dot"></span>Онлайн — {{ now }}</div>
    </div>
    <div class="topbar-actions">
      {% block topbar_actions %}{% endblock %}
      <a href="/dashboard" class="btn btn-ghost">🏠 Главная</a>
    </div>
  </div>
  <div class="content">
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for cat,msg in messages %}
    <div class="alert alert-{{ cat }}">{{ '✅' if cat=='success' else '❌' }} {{ msg }}</div>
    {% endfor %}{% endif %}{% endwith %}
    {% block content %}{% endblock %}
  </div>
</main>
</body></html>"""


LOGIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Вход — GroupHelp Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#0a0e1a;color:#e2e8f0;
  min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-bg{position:fixed;inset:0;background:radial-gradient(circle at 30% 50%,rgba(59,130,246,.08) 0%,transparent 60%),
  radial-gradient(circle at 70% 20%,rgba(99,102,241,.06) 0%,transparent 50%)}
.login-box{background:#1a2440;border:1px solid #1f2d4a;border-radius:20px;padding:40px;
  width:400px;position:relative;z-index:1}
.login-logo{text-align:center;margin-bottom:32px}
.login-icon{width:64px;height:64px;background:linear-gradient(135deg,#3b82f6,#6366f1);
  border-radius:18px;display:flex;align-items:center;justify-content:center;
  font-size:32px;margin:0 auto 12px}
.login-title{font-size:22px;font-weight:700}
.login-sub{font-size:13px;color:#64748b;margin-top:4px}
.form-group{margin-bottom:16px}
label{font-size:12px;font-weight:600;color:#94a3b8;display:block;margin-bottom:6px}
input{width:100%;background:#0f1629;border:1px solid #1f2d4a;border-radius:10px;
  color:#e2e8f0;font-size:14px;padding:12px 16px;outline:none;font-family:inherit}
input:focus{border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.1)}
.btn{width:100%;background:linear-gradient(135deg,#3b82f6,#6366f1);color:#fff;
  border:none;border-radius:10px;padding:13px;font-size:14px;font-weight:600;
  cursor:pointer;transition:.2s;margin-top:8px}
.btn:hover{opacity:.9;transform:translateY(-1px)}
.error{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);
  color:#ef4444;padding:12px;border-radius:8px;font-size:13px;margin-bottom:16px;text-align:center}
</style>
</head>
<body>
<div class="login-bg"></div>
<div class="login-box">
  <div class="login-logo">
    <div class="login-icon">🛡</div>
    <div class="login-title">GroupHelp Admin</div>
    <div class="login-sub">Панель управления ботом</div>
  </div>
  {% if error %}<div class="error">❌ {{ error }}</div>{% endif %}
  <form method="post">
    <div class="form-group">
      <label>Логин</label>
      <input type="text" name="username" placeholder="Введи логин" required autofocus>
    </div>
    <div class="form-group">
      <label>Пароль</label>
      <input type="password" name="password" placeholder="Введи пароль" required>
    </div>
    <button type="submit" class="btn">🔐 Войти в панель</button>
  </form>
</div>
</body></html>"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  РОУТЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        if ADMIN_CREDENTIALS.get(username) == password:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
        return render_template_string(LOGIN_HTML, error="Неверный логин или пароль")
    return render_template_string(LOGIN_HTML, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return redirect(url_for("dashboard"))


def render_page(title, active, content, **kwargs):
    stats = run_async(database.get_global_stats())
    pending = run_async(database.get_antispam_requests("pending"))
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    return render_template_string(
        BASE_HTML.replace("{% block content %}{% endblock %}", content)
                 .replace("{% block topbar_actions %}{% endblock %}", kwargs.get("topbar_actions", "")),
        title=title, panel_title=PANEL_TITLE, active=active,
        now=now, pending_count=len(pending), session=session, **kwargs
    )


# ── DASHBOARD ────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    stats     = run_async(database.get_global_stats())
    recent    = run_async(database.get_recent_events(20))
    top_grps  = run_async(database.get_top_groups(5))
    pending   = run_async(database.get_antispam_requests("pending"))
    actions   = run_async(database.get_recent_actions(10))

    content = f"""
<div class="stats-grid">
  <div class="stat-card blue">
    <div class="stat-icon">💬</div>
    <div class="stat-value">{stats.get('groups',0)}</div>
    <div class="stat-label">Групп подключено</div>
  </div>
  <div class="stat-card green">
    <div class="stat-icon">👥</div>
    <div class="stat-value">{stats.get('users',0)}</div>
    <div class="stat-label">Пользователей</div>
  </div>
  <div class="stat-card red">
    <div class="stat-icon">🔨</div>
    <div class="stat-value">{stats.get('bans',0)}</div>
    <div class="stat-label">Банов выдано</div>
  </div>
  <div class="stat-card yellow">
    <div class="stat-icon">⚠️</div>
    <div class="stat-value">{stats.get('warns',0)}</div>
    <div class="stat-label">Предупреждений</div>
  </div>
  <div class="stat-card purple">
    <div class="stat-icon">🔇</div>
    <div class="stat-value">{stats.get('mutes',0)}</div>
    <div class="stat-label">Мьютов</div>
  </div>
  <div class="stat-card teal">
    <div class="stat-icon">🚫</div>
    <div class="stat-value">{stats.get('spam',0)}</div>
    <div class="stat-label">Спама заблокировано</div>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px">
  <div class="table-card">
    <div class="table-header">
      <span class="table-title">🏆 Топ групп по активности</span>
    </div>
    <table>
      <thead><tr><th>#</th><th>Группа</th><th>События</th></tr></thead>
      <tbody>
        {"".join(f'<tr><td><span class="code">{i+1}</span></td><td>{g.get("title","—")}</td><td><span class="badge badge-blue">{g.get("events",0)}</span></td></tr>' for i,g in enumerate(top_grps))}
        {"<tr><td colspan='3' style='text-align:center;color:var(--text3);padding:20px'>Нет данных</td></tr>" if not top_grps else ""}
      </tbody>
    </table>
  </div>

  <div class="table-card">
    <div class="table-header">
      <span class="table-title">🚨 Заявки анти-спам ({len(pending)})</span>
      <a href="/antispam" class="btn btn-sm btn-ghost">Все заявки →</a>
    </div>
    <table>
      <thead><tr><th>ID</th><th>Пользователь</th><th>Статус</th></tr></thead>
      <tbody>
        {"".join(f'<tr><td><span class="code">#{r["id"]}</span></td><td>{r.get("full_name","?")}</td><td><span class="badge badge-yellow">⏳ Ожидает</span></td></tr>' for r in pending[:5])}
        {"<tr><td colspan='3' style='text-align:center;color:var(--text3);padding:20px'>Нет заявок</td></tr>" if not pending else ""}
      </tbody>
    </table>
  </div>
</div>

<div class="table-card">
  <div class="table-header">
    <span class="table-title">📋 Последние события</span>
    <a href="/eventlog" class="btn btn-sm btn-ghost">Полный лог →</a>
  </div>
  <table>
    <thead><tr><th>Время</th><th>Чат</th><th>Тип</th><th>User ID</th><th>Детали</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td style="color:var(--text3);font-size:12px">{r.get("created_at","")[:16]}</td>
        <td>{r.get("chat_title","") or r.get("chat_id","")}</td>
        <td>{_event_badge(r.get("event_type",""))}</td>
        <td><span class="code">{r.get("user_id","")}</span></td>
        <td style="color:var(--text3);font-size:12px">{(r.get("details","") or "")[:40]}</td>
      </tr>''' for r in recent)}
      {"<tr><td colspan='5' style='text-align:center;color:var(--text3);padding:30px'>Событий пока нет</td></tr>" if not recent else ""}
    </tbody>
  </table>
</div>
"""
    return render_page("Дашборд", "dashboard", content)


def _event_badge(event_type):
    map_ = {
        "ban":       ('<span class="badge badge-red">🔨 Бан</span>'),
        "unban":     ('<span class="badge badge-green">🔓 Разбан</span>'),
        "mute":      ('<span class="badge badge-purple">🔇 Мьют</span>'),
        "unmute":    ('<span class="badge badge-green">🔊 Размьют</span>'),
        "warn":      ('<span class="badge badge-yellow">⚠️ Варн</span>'),
        "kick":      ('<span class="badge badge-red">👢 Кик</span>'),
        "join":      ('<span class="badge badge-blue">➕ Вход</span>'),
        "leave":     ('<span class="badge badge-gray">🚪 Выход</span>'),
        "auto_warn": ('<span class="badge badge-yellow">🤖 Авто-варн</span>'),
        "start":     ('<span class="badge badge-green">▶️ Старт</span>'),
    }
    return map_.get(event_type, f'<span class="badge badge-gray">{event_type}</span>')


# ── ГРУППЫ ───────────────────────────────────────────────────

@app.route("/groups")
@login_required
def groups():
    all_groups = run_async(database.get_all_groups())
    search = request.args.get("q","").lower()
    if search:
        all_groups = [g for g in all_groups if search in (g.get("title","") or "").lower() or search in str(g.get("chat_id",""))]

    content = f"""
<div style="display:flex;gap:12px;margin-bottom:24px">
  <div class="stat-card blue" style="flex:1">
    <div class="stat-icon">💬</div>
    <div class="stat-value">{len(all_groups)}</div>
    <div class="stat-label">Всего групп</div>
  </div>
  <div class="stat-card green" style="flex:1">
    <div class="stat-icon">✅</div>
    <div class="stat-value">{sum(1 for g in all_groups if g.get("is_active"))}</div>
    <div class="stat-label">Активных</div>
  </div>
</div>
<div class="table-card">
  <div class="table-header">
    <span class="table-title">💬 Все группы</span>
    <form method="get" style="display:flex;gap:8px">
      <input class="search-input" name="q" value="{search}" placeholder="🔍 Поиск...">
      <button type="submit" class="btn btn-ghost btn-sm">Найти</button>
    </form>
  </div>
  <table>
    <thead><tr><th>ID</th><th>Название</th><th>Username</th><th>Дата входа</th><th>Статус</th><th>Действия</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td><span class="code">{g["chat_id"]}</span></td>
        <td><b>{g.get("title","—")}</b></td>
        <td style="color:var(--text3)">{"@"+g["username"] if g.get("username") else "—"}</td>
        <td style="font-size:12px;color:var(--text3)">{(g.get("joined_at") or "")[:16]}</td>
        <td>{"<span class='badge badge-green'>✅ Активна</span>" if g.get("is_active") else "<span class='badge badge-red'>❌ Неактивна</span>"}</td>
        <td>
          <a href="/group/{g["chat_id"]}" class="btn btn-sm btn-ghost">⚙️ Настройки</a>
          <a href="/group/{g["chat_id"]}/log" class="btn btn-sm btn-ghost" style="margin-left:4px">📋 Лог</a>
        </td>
      </tr>''' for g in all_groups)}
      {"<tr><td colspan='6'><div class='empty'><div class='empty-icon'>💬</div><div class='empty-text'>Групп пока нет</div></div></td></tr>" if not all_groups else ""}
    </tbody>
  </table>
</div>"""
    return render_page("Группы", "groups", content)


@app.route("/group/<int:chat_id>")
@login_required
def group_detail(chat_id):
    settings = run_async(database.get_group_settings(chat_id))
    notes    = run_async(database.get_all_notes(chat_id))
    filters  = run_async(database.get_filters(chat_id))
    bad_words = run_async(database.get_bad_words(chat_id))

    def tog_badge(val, default=True):
        v = settings.get(val, default)
        if isinstance(v, int): v = bool(v)
        return f'<span class="badge badge-{"green" if v else "red"}">{"✅ Вкл" if v else "❌ Выкл"}</span>'

    content = f"""
<div style="margin-bottom:20px">
  <a href="/groups" class="btn btn-ghost btn-sm">← Назад к группам</a>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px">
  <div class="form-card">
    <h3 style="margin-bottom:16px">⚙️ Настройки чата <span class="code">{chat_id}</span></h3>
    <form method="post" action="/group/{chat_id}/settings">
      <div style="display:grid;gap:12px">
        {"".join(f'''<div style="display:flex;align-items:center;justify-content:space-between;
          padding:12px;background:var(--bg3);border-radius:8px;border:1px solid var(--border)">
          <span style="font-size:13.5px">{label}</span>
          <span>{tog_badge(key, default)}</span>
          <label class="toggle" style="margin-left:8px">
            <input type="checkbox" name="{key}" {"checked" if settings.get(key, default) else ""} onchange="this.form.submit()">
            <span class="toggle-track"></span><span class="toggle-thumb"></span>
          </label>
        </div>''' for key, label, default in [
          ("welcome_enabled",   "👋 Приветствие", True),
          ("goodbye_enabled",   "👋 Прощание",    True),
          ("antiflood",         "🌊 Антифлуд",    True),
          ("antilinks",         "🔗 Антиссылки",  True),
          ("badwords",          "🤬 Фильтр слов", True),
          ("antispam_enabled",  "🚨 Антиспам",    True),
          ("log_actions",       "📋 Лог действий",True),
          ("antibot",           "🤖 Антибот",     False),
        ])}
        <div style="padding:12px;background:var(--bg3);border-radius:8px;border:1px solid var(--border)">
          <label style="font-size:13px;display:block;margin-bottom:6px">⚠️ Макс. варнов до бана</label>
          <select name="max_warns" onchange="this.form.submit()" style="width:120px">
            {" ".join(f'<option value="{v}" {"selected" if settings.get("max_warns",3)==v else ""}>{v}</option>' for v in [1,2,3,4,5,7,10])}
          </select>
        </div>
        <div style="padding:12px;background:var(--bg3);border-radius:8px;border:1px solid var(--border)">
          <label style="font-size:13px;display:block;margin-bottom:6px">🎯 Действие при варнах</label>
          <select name="warn_action" onchange="this.form.submit()">
            <option value="ban" {"selected" if settings.get("warn_action","ban")=="ban" else ""}>🔨 Бан</option>
            <option value="mute" {"selected" if settings.get("warn_action","ban")=="mute" else ""}>🔇 Мьют</option>
          </select>
        </div>
      </div>
    </form>
  </div>

  <div>
    <div class="form-card" style="margin-bottom:16px">
      <h3 style="margin-bottom:14px">📝 Приветствие</h3>
      <form method="post" action="/group/{chat_id}/welcome">
        <textarea name="welcome_text" rows="3" placeholder="Привет {{name}}! Добро пожаловать в {{chat}}">{settings.get("welcome_text","")}</textarea>
        <div style="margin-top:8px;font-size:11px;color:var(--text3)">Переменные: {{name}} {{username}} {{chat}} {{id}}</div>
        <button type="submit" class="btn btn-primary btn-sm" style="margin-top:10px">Сохранить</button>
      </form>
    </div>
    <div class="form-card" style="margin-bottom:16px">
      <h3 style="margin-bottom:14px">👋 Прощание</h3>
      <form method="post" action="/group/{chat_id}/goodbye">
        <textarea name="goodbye_text" rows="2" placeholder="{{name}} покинул(а) чат">{settings.get("goodbye_text","")}</textarea>
        <button type="submit" class="btn btn-primary btn-sm" style="margin-top:10px">Сохранить</button>
      </form>
    </div>
    <div class="form-card">
      <h3 style="margin-bottom:14px">📜 Правила</h3>
      <form method="post" action="/group/{chat_id}/rules">
        <textarea name="rules" rows="4" placeholder="1. Уважай участников...">{settings.get("rules","")}</textarea>
        <button type="submit" class="btn btn-primary btn-sm" style="margin-top:10px">Сохранить</button>
      </form>
    </div>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
  <div class="table-card">
    <div class="table-header">
      <span class="table-title">📝 Заметки ({len(notes)})</span>
    </div>
    <table>
      <thead><tr><th>Название</th><th>Текст</th></tr></thead>
      <tbody>
        {"".join(f'<tr><td><span class="code">#{n["name"]}</span></td><td style="font-size:12px;color:var(--text2)">{n["text"][:50]}</td></tr>' for n in notes)}
        {"<tr><td colspan='2' style='text-align:center;color:var(--text3);padding:20px'>Нет заметок</td></tr>" if not notes else ""}
      </tbody>
    </table>
  </div>
  <div class="table-card">
    <div class="table-header">
      <span class="table-title">🔒 Фильтры ({len(filters)})</span>
    </div>
    <table>
      <thead><tr><th>Слово</th><th>Ответ</th></tr></thead>
      <tbody>
        {"".join(f'<tr><td><span class="code">{f["keyword"]}</span></td><td style="font-size:12px;color:var(--text2)">{f["response"][:40]}</td></tr>' for f in filters)}
        {"<tr><td colspan='2' style='text-align:center;color:var(--text3);padding:20px'>Нет фильтров</td></tr>" if not filters else ""}
      </tbody>
    </table>
  </div>
</div>
"""
    return render_page(f"Группа {chat_id}", "groups", content)


@app.route("/group/<int:chat_id>/settings", methods=["POST"])
@login_required
def update_group_settings(chat_id):
    checkboxes = ["welcome_enabled","goodbye_enabled","antiflood","antilinks",
                  "badwords","antispam_enabled","log_actions","antibot"]
    for key in checkboxes:
        run_async(database.update_group_setting(chat_id, key, 1 if request.form.get(key) else 0))
    if request.form.get("max_warns"):
        run_async(database.update_group_setting(chat_id, "max_warns", int(request.form["max_warns"])))
    if request.form.get("warn_action"):
        run_async(database.update_group_setting(chat_id, "warn_action", request.form["warn_action"]))
    flash("Настройки сохранены!", "success")
    return redirect(url_for("group_detail", chat_id=chat_id))


@app.route("/group/<int:chat_id>/welcome", methods=["POST"])
@login_required
def update_welcome(chat_id):
    run_async(database.update_group_setting(chat_id, "welcome_text", request.form.get("welcome_text","")))
    flash("Приветствие обновлено!", "success")
    return redirect(url_for("group_detail", chat_id=chat_id))


@app.route("/group/<int:chat_id>/goodbye", methods=["POST"])
@login_required
def update_goodbye(chat_id):
    run_async(database.update_group_setting(chat_id, "goodbye_text", request.form.get("goodbye_text","")))
    flash("Прощание обновлено!", "success")
    return redirect(url_for("group_detail", chat_id=chat_id))


@app.route("/group/<int:chat_id>/rules", methods=["POST"])
@login_required
def update_rules(chat_id):
    run_async(database.update_group_setting(chat_id, "rules", request.form.get("rules","")))
    flash("Правила обновлены!", "success")
    return redirect(url_for("group_detail", chat_id=chat_id))


@app.route("/group/<int:chat_id>/log")
@login_required
def group_log(chat_id):
    events = run_async(database.get_recent_events(200))
    events = [e for e in events if str(e.get("chat_id","")) == str(chat_id)]
    content = f"""
<div style="margin-bottom:20px">
  <a href="/group/{chat_id}" class="btn btn-ghost btn-sm">← Назад к группе</a>
</div>
<div class="table-card">
  <div class="table-header"><span class="table-title">📋 Лог событий группы {chat_id}</span></div>
  <table>
    <thead><tr><th>Время</th><th>Тип</th><th>User ID</th><th>Детали</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td style="font-size:12px;color:var(--text3)">{e.get("created_at","")[:16]}</td>
        <td>{_event_badge(e.get("event_type",""))}</td>
        <td><span class="code">{e.get("user_id","")}</span></td>
        <td style="font-size:12px;color:var(--text3)">{e.get("details","")[:60]}</td>
      </tr>''' for e in events)}
      {"<tr><td colspan='4' style='text-align:center;padding:30px;color:var(--text3)'>Нет событий</td></tr>" if not events else ""}
    </tbody>
  </table>
</div>"""
    return render_page(f"Лог группы {chat_id}", "groups", content)


# ── ПОЛЬЗОВАТЕЛИ ─────────────────────────────────────────────

@app.route("/users")
@login_required
def users():
    page    = int(request.args.get("page", 1))
    search  = request.args.get("q", "").lower()
    limit   = 50
    offset  = (page - 1) * limit
    all_u   = run_async(database.get_all_users(limit=500))
    total   = len(all_u)
    if search:
        all_u = [u for u in all_u if search in (u.get("username","") or "").lower()
                 or search in (u.get("full_name","") or "").lower()
                 or search in str(u.get("user_id",""))]
    paginated = all_u[offset:offset+limit]
    pages = max(1, (len(all_u) + limit - 1) // limit)

    content = f"""
<div class="stat-card blue" style="margin-bottom:24px;max-width:200px">
  <div class="stat-icon">👥</div>
  <div class="stat-value">{total}</div>
  <div class="stat-label">Всего пользователей</div>
</div>
<div class="table-card">
  <div class="table-header">
    <span class="table-title">👥 Пользователи</span>
    <form method="get" style="display:flex;gap:8px">
      <input class="search-input" name="q" value="{search}" placeholder="🔍 Имя, username, ID...">
      <button type="submit" class="btn btn-ghost btn-sm">Найти</button>
    </form>
  </div>
  <table>
    <thead><tr><th>ID</th><th>Имя</th><th>Username</th><th>Первый раз</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td><span class="code">{u["user_id"]}</span></td>
        <td>{u.get("full_name","—")}</td>
        <td style="color:var(--text3)">{"@"+u["username"] if u.get("username") else "—"}</td>
        <td style="font-size:12px;color:var(--text3)">{(u.get("first_seen") or "")[:16]}</td>
      </tr>''' for u in paginated)}
      {"<tr><td colspan='4' style='text-align:center;padding:30px;color:var(--text3)'>Пользователей нет</td></tr>" if not paginated else ""}
    </tbody>
  </table>
  <div class="pagination">
    {"".join(f'<a href="?page={p}&q={search}" class="page-btn {"active" if p==page else ""}">{p}</a>' for p in range(1, pages+1))}
  </div>
</div>"""
    return render_page("Пользователи", "users", content)


# ── АНТИСПАМ ─────────────────────────────────────────────────

@app.route("/antispam")
@login_required
def antispam():
    tab     = request.args.get("tab", "pending")
    reqs    = run_async(database.get_antispam_requests(tab))
    counts  = {
        "pending":  len(run_async(database.get_antispam_requests("pending"))),
        "approved": len(run_async(database.get_antispam_requests("approved"))),
        "denied":   len(run_async(database.get_antispam_requests("denied"))),
    }

    def status_badge(s):
        m = {"pending": ("badge-yellow","⏳ Ожидает"), "approved": ("badge-green","✅ Одобрено"), "denied": ("badge-red","❌ Отказано")}
        cls, label = m.get(s, ("badge-gray", s))
        return f'<span class="badge {cls}">{label}</span>'

    content = f"""
<div class="tabs">
  <a href="?tab=pending"  class="tab {"active" if tab=="pending"  else ""}">⏳ Ожидают ({counts["pending"]})</a>
  <a href="?tab=approved" class="tab {"active" if tab=="approved" else ""}">✅ Одобрено ({counts["approved"]})</a>
  <a href="?tab=denied"   class="tab {"active" if tab=="denied"   else ""}">❌ Отказано ({counts["denied"]})</a>
</div>
<div class="table-card">
  <div class="table-header">
    <span class="table-title">🚨 Заявки анти-спам</span>
  </div>
  <table>
    <thead><tr><th>#</th><th>Пользователь</th><th>ID</th><th>Причина</th><th>Статус</th><th>Дата</th><th>Действия</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td><span class="code">#{r["id"]}</span></td>
        <td><b>{r.get("full_name","—")}</b><br><span style="font-size:11px;color:var(--text3)">@{r.get("username","—")}</span></td>
        <td><span class="code">{r["user_id"]}</span></td>
        <td style="font-size:12px;color:var(--text2);max-width:200px">{(r.get("reason",""))[:80]}</td>
        <td>{status_badge(r.get("status",""))}</td>
        <td style="font-size:12px;color:var(--text3)">{(r.get("created_at",""))[:16]}</td>
        <td>
          {"" if r["status"]!="pending" else f"""
          <form method="post" action="/antispam/{r["id"]}/approve" style="display:inline">
            <button type="submit" class="btn btn-success btn-sm">✅ Одобрить</button>
          </form>
          <form method="post" action="/antispam/{r["id"]}/deny" style="display:inline;margin-left:4px">
            <button type="submit" class="btn btn-danger btn-sm">❌ Отказать</button>
          </form>"""}
        </td>
      </tr>''' for r in reqs)}
      {"<tr><td colspan='7' style='text-align:center;padding:40px;color:var(--text3)'>Заявок нет</td></tr>" if not reqs else ""}
    </tbody>
  </table>
</div>"""
    return render_page("Анти-Спам заявки", "antispam", content)


@app.route("/antispam/<int:req_id>/approve", methods=["POST"])
@login_required
def approve_antispam(req_id):
    run_async(database.update_antispam_status(req_id, "approved"))
    run_async(database.inc_global_stat("antispam_granted"))
    flash(f"Заявка #{req_id} одобрена!", "success")
    return redirect(url_for("antispam"))


@app.route("/antispam/<int:req_id>/deny", methods=["POST"])
@login_required
def deny_antispam(req_id):
    run_async(database.update_antispam_status(req_id, "denied"))
    flash(f"Заявка #{req_id} отклонена.", "error")
    return redirect(url_for("antispam"))


# ── ПРЕДУПРЕЖДЕНИЯ ───────────────────────────────────────────

@app.route("/warnings")
@login_required
def warnings_page():
    import aiosqlite

    async def get_all_warns():
        async with aiosqlite.connect(database.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM warnings ORDER BY created_at DESC LIMIT 200"
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    warns = run_async(get_all_warns())

    content = f"""
<div class="table-card">
  <div class="table-header">
    <span class="table-title">⚠️ Предупреждения ({len(warns)})</span>
  </div>
  <table>
    <thead><tr><th>Чат ID</th><th>User ID</th><th>Мод ID</th><th>Причина</th><th>Дата</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td><span class="code">{w["chat_id"]}</span></td>
        <td><span class="code">{w["user_id"]}</span></td>
        <td><span class="code">{w["mod_id"] or "авто"}</span></td>
        <td style="font-size:12px;color:var(--text2)">{w.get("reason","")[:60]}</td>
        <td style="font-size:12px;color:var(--text3)">{w.get("created_at","")[:16]}</td>
      </tr>''' for w in warns)}
      {"<tr><td colspan='5' style='text-align:center;padding:40px;color:var(--text3)'>Предупреждений нет</td></tr>" if not warns else ""}
    </tbody>
  </table>
</div>"""
    return render_page("Предупреждения", "warnings", content)


# ── ДЕЙСТВИЯ ─────────────────────────────────────────────────

@app.route("/actions")
@login_required
def actions_page():
    acts = run_async(database.get_recent_actions(200))
    content = f"""
<div class="table-card">
  <div class="table-header">
    <span class="table-title">🗂 Действия модераторов ({len(acts)})</span>
  </div>
  <table>
    <thead><tr><th>Чат</th><th>Модератор</th><th>Цель</th><th>Действие</th><th>Причина</th><th>Дата</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td><span class="code">{a.get("chat_id","")}</span></td>
        <td><span class="code">{a.get("mod_id","")}</span></td>
        <td><span class="code">{a.get("target_id","")}</span></td>
        <td>{_event_badge(a.get("action_type",""))}</td>
        <td style="font-size:12px;color:var(--text2)">{a.get("reason","")[:50]}</td>
        <td style="font-size:12px;color:var(--text3)">{a.get("created_at","")[:16]}</td>
      </tr>''' for a in acts)}
    </tbody>
  </table>
</div>"""
    return render_page("Действия модераторов", "actions", content)


# ── ЛОГ СОБЫТИЙ ──────────────────────────────────────────────

@app.route("/eventlog")
@login_required
def eventlog():
    filter_type = request.args.get("type","")
    events = run_async(database.get_recent_events(500))
    if filter_type:
        events = [e for e in events if e.get("event_type") == filter_type]

    event_types = ["ban","unban","mute","unmute","warn","kick","join","leave","auto_warn","start"]
    content = f"""
<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px">
  <a href="/eventlog" class="btn btn-sm {"btn-primary" if not filter_type else "btn-ghost"}">Все</a>
  {"".join(f'<a href="?type={t}" class="btn btn-sm {"btn-primary" if filter_type==t else "btn-ghost"}">{t}</a>' for t in event_types)}
</div>
<div class="table-card">
  <div class="table-header">
    <span class="table-title">📋 Лог событий ({len(events)})</span>
  </div>
  <table>
    <thead><tr><th>Время</th><th>Чат</th><th>Тип</th><th>User ID</th><th>Детали</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td style="font-size:12px;color:var(--text3)">{e.get("created_at","")[:16]}</td>
        <td style="font-size:12px">{e.get("chat_title","") or e.get("chat_id","")}</td>
        <td>{_event_badge(e.get("event_type",""))}</td>
        <td><span class="code">{e.get("user_id","")}</span></td>
        <td style="font-size:12px;color:var(--text3)">{(e.get("details","") or "")[:60]}</td>
      </tr>''' for e in events)}
      {"<tr><td colspan='5' style='text-align:center;padding:40px;color:var(--text3)'>Событий нет</td></tr>" if not events else ""}
    </tbody>
  </table>
</div>"""
    return render_page("Лог событий", "eventlog", content)


# ── СТАТИСТИКА ───────────────────────────────────────────────

@app.route("/bot-stats")
@login_required
def bot_stats():
    stats  = run_async(database.get_global_stats())
    hist   = run_async(database.get_stats_history(14))
    top_g  = run_async(database.get_top_groups(10))

    content = f"""
<div class="stats-grid" style="margin-bottom:28px">
  <div class="stat-card blue"><div class="stat-icon">💬</div><div class="stat-value">{stats.get("groups",0)}</div><div class="stat-label">Групп</div></div>
  <div class="stat-card green"><div class="stat-icon">👥</div><div class="stat-value">{stats.get("users",0)}</div><div class="stat-label">Пользователей</div></div>
  <div class="stat-card red"><div class="stat-icon">🔨</div><div class="stat-value">{stats.get("bans",0)}</div><div class="stat-label">Банов</div></div>
  <div class="stat-card yellow"><div class="stat-icon">⚠️</div><div class="stat-value">{stats.get("warns",0)}</div><div class="stat-label">Варнов</div></div>
  <div class="stat-card purple"><div class="stat-icon">🔇</div><div class="stat-value">{stats.get("mutes",0)}</div><div class="stat-label">Мьютов</div></div>
  <div class="stat-card teal"><div class="stat-icon">🚫</div><div class="stat-value">{stats.get("spam",0)}</div><div class="stat-label">Спама</div></div>
</div>

<div class="table-card">
  <div class="table-header"><span class="table-title">🏆 Топ-10 активных групп</span></div>
  <table>
    <thead><tr><th>#</th><th>Группа</th><th>ID</th><th>Активность</th></tr></thead>
    <tbody>
      {"".join(f'''<tr>
        <td><b>{i+1}</b></td>
        <td>{g.get("title","—")}</td>
        <td><span class="code">{g.get("chat_id","")}</span></td>
        <td><span class="badge badge-blue">{g.get("events",0)} событий</span></td>
      </tr>''' for i,g in enumerate(top_g))}
    </tbody>
  </table>
</div>"""
    return render_page("Статистика", "botstats", content)


# ── РАССЫЛКА ─────────────────────────────────────────────────

@app.route("/broadcast", methods=["GET","POST"])
@login_required
def broadcast():
    result = None
    if request.method == "POST":
        text = request.form.get("text","")
        if text:
            result = f"✅ Сообщение подготовлено. Реализуй отправку через Telegram Bot API."

    content = f"""
<div class="form-card" style="max-width:600px">
  <h3 style="margin-bottom:20px">📢 Рассылка сообщений</h3>
  {"<div class='alert alert-success'>"+result+"</div>" if result else ""}
  <form method="post">
    <div class="form-group">
      <label>Текст сообщения (поддерживает HTML)</label>
      <textarea name="text" rows="6" placeholder="Введи текст рассылки..."></textarea>
    </div>
    <div class="form-group" style="margin-top:16px">
      <label>Кому отправить</label>
      <select name="target">
        <option value="all">📢 Все группы</option>
        <option value="users">👥 Все пользователи (в личку)</option>
      </select>
    </div>
    <div style="margin-top:16px;display:flex;gap:12px">
      <button type="submit" class="btn btn-primary">📢 Отправить рассылку</button>
      <a href="/dashboard" class="btn btn-ghost">Отмена</a>
    </div>
  </form>
</div>"""
    return render_page("Рассылка", "broadcast", content)


# ── НАСТРОЙКИ ПАНЕЛИ ─────────────────────────────────────────

@app.route("/settings-panel", methods=["GET","POST"])
@login_required
def panel_settings():
    if request.method == "POST":
        flash("Настройки сохранены!", "success")

    content = f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
  <div class="form-card">
    <h3 style="margin-bottom:20px">🔐 Смена пароля</h3>
    <form method="post">
      <div class="form-group">
        <label>Текущий пароль</label>
        <input type="password" name="old_pass" placeholder="Текущий пароль">
      </div>
      <div class="form-group">
        <label>Новый пароль</label>
        <input type="password" name="new_pass" placeholder="Новый пароль">
      </div>
      <div class="form-group">
        <label>Повтори новый пароль</label>
        <input type="password" name="confirm_pass" placeholder="Повтори пароль">
      </div>
      <button type="submit" class="btn btn-primary" style="margin-top:12px">Сменить пароль</button>
    </form>
  </div>

  <div class="form-card">
    <h3 style="margin-bottom:20px">ℹ️ Информация о системе</h3>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div style="background:var(--bg3);padding:12px;border-radius:8px;border:1px solid var(--border)">
        <div style="font-size:11px;color:var(--text3);margin-bottom:3px">БАЗА ДАННЫХ</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:13px">grouphelp.db (SQLite)</div>
      </div>
      <div style="background:var(--bg3);padding:12px;border-radius:8px;border:1px solid var(--border)">
        <div style="font-size:11px;color:var(--text3);margin-bottom:3px">ВЕБ-ПАНЕЛЬ</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:13px">Flask (port 5000)</div>
      </div>
      <div style="background:var(--bg3);padding:12px;border-radius:8px;border:1px solid var(--border)">
        <div style="font-size:11px;color:var(--text3);margin-bottom:3px">БОТ</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:13px">python-telegram-bot 20.7</div>
      </div>
      <div style="background:var(--bg3);padding:12px;border-radius:8px;border:1px solid var(--border)">
        <div style="font-size:11px;color:var(--text3);margin-bottom:3px">СТАТУС</div>
        <div><span class="live-dot"></span><span style="color:var(--green);font-size:13px">Онлайн</span></div>
      </div>
    </div>
  </div>
</div>"""
    return render_page("Настройки панели", "panelsettings", content)


# ── API ──────────────────────────────────────────────────────

@app.route("/api/stats")
@login_required
def api_stats():
    stats = run_async(database.get_global_stats())
    return jsonify(stats)


@app.route("/api/groups")
@login_required
def api_groups():
    groups = run_async(database.get_all_groups())
    return jsonify(groups)


@app.route("/api/antispam/pending")
@login_required
def api_antispam():
    reqs = run_async(database.get_antispam_requests("pending"))
    return jsonify({"count": len(reqs), "requests": reqs})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ЗАПУСК
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # Инициализируем БД при запуске панели
    run_async(database.init_db())
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  🛡  GroupHelp Admin Panel")
    print("  🌐  http://localhost:5000")
    print("  👤  Логин: admin")
    print("  🔑  Пароль: admin123")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    app.run(host="0.0.0.0", port=5000, debug=False)
