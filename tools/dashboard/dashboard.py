#!/usr/bin/env python3
"""SMELTER local dashboard with explicit per-message tool permissions."""
import argparse
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "setup"))
from check_requirements import scan
from extensions import catalog, set_enabled
from workflows import definitions, plan
from reports import attach_inputs, list_reports, save_report
from execution import inspect_archive
from media import inspect_media
from blender import inspect_blender
from ollama import list_models
from model_preferences import configured_status
from opencode import inspect_opencode
from opencode_provider import provider_preview
from opencode_deploy import deploy_isolated_config
from opencode_validate import validate_staged_config
from database import select_database
from config_store import load_config, save_config
from startup import startup_report
from system_status import system_status
from component_controls import manager as component_manager, close_all as close_components
from chats import list_chats, create_chat, read_chat, add_note, rename_chat, delete_chat
from skill_manager import remove_skill, set_skill_enabled
from github_skill_discovery import discover_github_skill, discover_github_repository, install_discovered_skill
from skill_collections import install_collection
from aero_classifier import classify_task
from rea_connection import package_status as rea_package_status
from chat_jobs import JOBS
from skill_runtime import initialize as initialize_skills, monitor as skill_monitor, tools_status
from runtime_settings import load_runtime, save_runtime
from mcp_connections import status as mcp_status, save_config as save_mcp_config, exchange as mcp_exchange
from python_tools import permissions as validate_tool_permissions
from model_assets import rename_animation, attach_model, model_path, viewer_bundle, viewer_status

STATE = ROOT / ".smelter" / "extensions.json"
STATE_LOCK = threading.RLock()
REPORTS = ROOT / ".smelter" / "reports"
MODEL_PREFS = ROOT / ".smelter" / "model_preferences.json"
HTML = r"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMELTER · Dashboard</title><style>
:root{
 color-scheme:dark;
 --bg:#0d1117;--surface:#141c26;--raised:#1b2735;--border:#35465a;--control-border:#52677e;
 --text:#edf2f8;--muted:#a3b2c5;--accent:#ffb169;--accent-ink:#211407;--teal:#8cdecf;
 --danger:#ffabb2;--warning:#ffd18b;--focus:#b1deff;--radius:12px;
 --space-1:4px;--space-2:8px;--space-3:12px;--space-4:16px;--space-6:24px;--space-8:32px;
 font:16px/1.6 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
*{box-sizing:border-box} [hidden]{display:none!important} html,body{margin:0;min-width:320px;height:100%;background:var(--bg);color:var(--text)}
body{overflow:hidden}main{height:100dvh;max-width:1920px;margin:0 auto;padding:0 24px;display:flex;flex-direction:column;min-height:0}
h1,h2,h3,h4{line-height:1.25;letter-spacing:-.025em;font-weight:650;margin:0 0 16px}h1{font-size:20px}h2{font-size:26px}h3{font-size:20px}h4{font-size:16px}
p{margin:8px 0 16px;overflow-wrap:anywhere}small,.muted{color:var(--muted);font-size:13px}
button,input,select,textarea{font:inherit;color:inherit}button{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:40px;border:1px solid var(--control-border);border-radius:9px;padding:8px 14px;background:var(--raised);cursor:pointer;font-size:14px;font-weight:550;transition:background .15s,border-color .15s,color .15s}
button:hover:not(:disabled){background:#283a4e;border-color:#87a0bb}button:active:not(:disabled){background:#334a62}button:disabled{opacity:.45;cursor:not-allowed}
button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible,a:focus-visible{outline:3px solid var(--focus);outline-offset:3px}
:focus-visible{scroll-margin-block:100px}button.primary-button,.primary-button{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.primary-button:hover:not(:disabled){background:#ffc58e;border-color:#ffc58e}.quiet-button{background:transparent}
input:not([type=checkbox]):not([type=range]):not([type=file]),select,textarea{min-height:42px;background:#101720;border:1px solid var(--control-border);border-radius:8px;padding:9px 12px;max-width:100%;font-size:15px}
input::placeholder,textarea::placeholder{color:#9caec2;opacity:1}textarea{line-height:1.6;resize:vertical}input[type=checkbox]{accent-color:var(--teal);width:24px;height:24px;flex-shrink:0;vertical-align:middle;margin:0 5px 0 0;cursor:pointer}
input[type=range]{accent-color:var(--accent);min-height:36px}label{line-height:1.6}summary{cursor:pointer;font-weight:550;min-height:36px;padding:6px 0}
a{color:#a8d8ff;text-underline-offset:3px}pre,code{font-family:"Cascadia Code","SFMono-Regular",Consolas,monospace;font-size:13px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-width:100%;overflow:auto;line-height:1.65}pre:empty{display:none}.ui-icon{width:20px;height:20px;flex:0 0 auto;vertical-align:middle}
.eyebrow{font-size:11px;letter-spacing:.14em;font-weight:700;color:var(--accent);margin:0 0 8px}.field-caption{display:block;color:var(--muted);font-size:13px;margin:14px 0 7px}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.skip-link{position:fixed;left:24px;top:-100px;padding:12px 18px;background:var(--accent);color:var(--accent-ink);z-index:1000;border-radius:8px}.skip-link:focus{top:12px}
.appbar{height:78px;flex-shrink:0;display:flex;align-items:center;gap:16px}.app-brand{display:flex;align-items:center;gap:12px;min-width:0}.app-brand>.ui-icon{width:32px;height:32px;color:var(--accent)}
.app-brand h1{margin:0;letter-spacing:.08em;font-size:18px}.app-subtitle{margin:0;border-left:1px solid var(--border);padding-left:16px;font-size:12px;color:var(--muted)}
.runtime-chip{margin-left:auto;font-size:12px;max-width:35%;overflow-wrap:anywhere;border:1px solid var(--border);border-radius:100px;padding:5px 12px;color:var(--teal);background:#132825}
.history-toggle,.history-scrim{display:none}.panel{min-width:0}.panel:not(.active){scroll-margin-top:20px}
#shell{flex:1;min-height:0;display:grid;grid-template-columns:252px minmax(0,1fr);gap:24px;position:relative}
#leftbar{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px 14px;display:flex;flex-direction:column;min-height:0;overflow:auto}
#leftbar h2{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:2px 8px 18px}
#leftbar>button{justify-content:flex-start;width:100%;background:#2e241a;color:#ffd2aa;border-color:#705337;margin-bottom:8px}
#leftbar .field-caption{margin-left:7px;font-size:12px}#chatSearch{width:100%;font-size:13px}.history-count{font-size:12px;color:var(--muted);margin:12px 7px}
#chatHistory{flex:1;min-height:80px}.history-row{display:grid;grid-template-columns:minmax(0,1fr) 28px 28px;gap:2px;align-items:center;padding:4px;margin:4px 0;border-radius:9px;border:1px solid transparent}
.history-row:hover{background:#1e2b3a}.history-row.selected{background:#243348;border-color:#4b6585}.chat-open{display:block;background:transparent;border:0;padding:8px;text-align:left;min-width:0}
.history-title{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.chat-open small{display:block;margin-top:4px;font-size:11px}
.chat-action{min-width:28px;min-height:32px;padding:2px;border:0;background:transparent;color:var(--muted);font-size:18px}.sidebar-note{color:var(--muted);font-size:12px;border-top:1px solid var(--border);padding:16px 8px 0;margin-top:20px}
#workspace{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);display:flex;flex-direction:column;min-width:0;min-height:0;padding:0 24px 20px;overflow:hidden}
.workspace-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:14px 0;border-bottom:1px solid var(--border);flex-shrink:0}.workspace-toolbar button{font-size:12px;padding:7px 10px;min-height:36px;background:transparent}
#taskAccessSummary{flex:1;min-width:190px;color:var(--muted);font-size:12px;overflow-wrap:anywhere}.workspace-toolbar .ui-icon{width:16px;height:16px}
.conversation-heading{display:flex;flex-direction:column;gap:5px;padding:22px 0 12px;flex-shrink:0}.conversation-caption{font-size:11px;color:var(--muted);letter-spacing:.1em;text-transform:uppercase}#chatTitle{font-size:22px;margin:0}
#chatlog{display:flex;flex-direction:column;gap:20px;flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;padding:12px 8px 28px;scrollbar-width:thin}
.message{max-width:90%;padding:18px 20px;border-radius:14px;flex-shrink:0;overflow-wrap:anywhere;min-width:0;line-height:1.75}
.message-user{align-self:flex-end;background:#253b52;border:1px solid #4a6a8d;border-bottom-right-radius:4px}.message-assistant{align-self:flex-start;background:#1b2735;border:1px solid #384d63;border-bottom-left-radius:4px}
.message-label{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;color:#c5d4e6;font-size:12px;font-weight:650;margin-bottom:12px}.message-content{white-space:pre-wrap}.copy-button{font-size:11px;min-height:30px;padding:3px 8px;background:transparent}
.formatted-message p{color:inherit;white-space:pre-wrap;line-height:1.75;margin:9px 0}.formatted-message ul,.formatted-message ol{padding-left:24px}.formatted-message li{margin:6px 0}.formatted-message blockquote{border-left:3px solid var(--teal);padding-left:14px;margin-left:0;color:var(--muted)}
.formatted-message :not(pre)>code{background:#101820;padding:3px 6px;border-radius:5px;color:#c0eedf}.code-block{border:1px solid #4a6077;border-radius:9px;overflow:hidden;margin:14px 0;background:#0e151e}
.code-toolbar{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;font-size:12px;background:#26364a;color:#c5d4e6}.code-block pre{white-space:pre;margin:0;padding:16px;overflow-x:auto}
#composer{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:12px;border:1px solid #647c97;border-radius:14px;background:#1c2b3b;position:relative;flex-shrink:0;box-shadow:0 6px 18px #0002}
#chatinput{order:-1;flex-basis:100%;width:100%;min-height:78px;max-height:180px;resize:vertical;background:transparent;border:0;padding:6px 8px;font-size:16px}
#composer>.composer-engine{font-size:12px;color:var(--muted);margin-right:auto}.composer-engine select{font-size:12px;background:transparent;min-height:36px;border-color:transparent;padding:6px}
#composer>button{min-height:40px}#composer>button:first-of-type{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.composer-hint{font-size:11px;color:#b3c0d0;flex-basis:100%;padding:2px 7px}.task-status{font-size:13px;min-height:26px;flex-shrink:0;margin:8px 2px;display:flex;gap:8px;align-items:center}
.task-status:before{content:'';width:7px;height:7px;border-radius:50%;background:#8eabc8;flex-shrink:0}.task-status[data-state=ready]:before{background:var(--teal)}.task-status[data-state=error]{color:var(--danger)}.task-status[data-state=warning]{color:var(--warning)}
#sysfooter{padding:10px 0;flex-shrink:0;font-size:12px;color:var(--muted);max-height:115px;overflow:auto}.resource-details>summary{font-size:12px;padding:0;min-height:24px}
.resource-grid{display:flex;gap:16px;align-items:center;flex-wrap:wrap}.resource-grid>span{display:inline-flex;gap:7px;min-width:0;overflow-wrap:anywhere}.resource-grid strong{color:#d6e2f0;font-weight:500}.resource-grid button{padding:2px 8px;min-height:28px;font-size:11px;margin-left:auto;background:transparent}
.workbench-empty{margin:auto;max-width:780px;text-align:center;padding:28px 12px}.empty-mark{display:grid;place-items:center;margin:0 auto 22px;background:#34281c;color:var(--accent);width:64px;height:64px;border:1px solid #775739;border-radius:18px}
.empty-mark .ui-icon{width:34px;height:34px}.workbench-empty h2{font-size:clamp(24px,3vw,36px);margin-bottom:14px}.workbench-empty>p:not(.eyebrow){color:var(--muted);max-width:55ch;margin:0 auto 24px}
.starter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:32px}.starter-card{display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;text-align:left;gap:12px;padding:20px;background:#192431;border-color:#40566e;border-radius:12px}
.starter-card>.ui-icon{color:var(--accent);width:24px;height:24px}.starter-card strong{font-size:14px}.starter-card span{font-size:13px;line-height:1.6;color:var(--muted)}.workbench-empty .empty-boundary{font-size:12px;margin-top:24px}
.attachment-control{display:flex;align-items:center;gap:8px;position:relative}.attachment-add{width:40px;height:40px;min-height:40px;padding:8px;border-radius:9px;background:transparent}
.attachment-menu{position:absolute;left:0;bottom:52px;width:320px;max-width:calc(100vw - 60px);padding:8px;border:1px solid #647c97;border-radius:12px;background:#223246;box-shadow:0 16px 48px #0008;z-index:20}
.attachment-menu>p{color:var(--muted);font-size:11px;letter-spacing:.12em;padding:6px 12px;margin:0}.attachment-menu button{display:flex;flex-direction:column;align-items:flex-start;width:100%;padding:12px;border:0;background:transparent;gap:4px;text-align:left}
.attachment-menu strong{font-size:14px}.attachment-menu small{font-size:12px}.attachment-chip{display:inline-flex;align-items:center;gap:6px;max-width:220px;border:1px solid #607d9d;border-radius:7px;padding:3px 6px 3px 10px;font-size:12px}
.attachment-chip>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.attachment-chip button{padding:1px 5px;min-height:30px;background:transparent;border:0;font-size:20px}
.settings-screen{width:min(1320px,96vw);height:min(960px,94dvh);max-width:none;max-height:none;padding:0;background:var(--surface);color:var(--text);border:1px solid #5b728d;border-radius:16px;overflow:hidden;box-shadow:0 30px 100px #0008}
dialog::backdrop{background:#030810c9;backdrop-filter:blur(4px)}.settings-header{height:116px;display:flex;align-items:center;gap:24px;padding:20px 28px;border-bottom:1px solid var(--border)}
.settings-header>div{min-width:210px}.settings-header .eyebrow{margin:0 0 4px;font-size:10px}.settings-header h2{font-size:24px;margin:0}.settings-current{font-size:12px;color:var(--muted);margin:4px 0 0}
.settings-search{margin-left:auto;width:280px}.settings-header button{flex-shrink:0;font-size:13px}#rightbar{display:grid;grid-template-columns:240px minmax(0,1fr);height:calc(100% - 116px);min-height:0}
.settings-nav{background:#101720;padding:18px 14px;overflow:auto;border-right:1px solid var(--border);scrollbar-width:thin}.settings-nav-group{margin-bottom:22px}.settings-nav-group h3{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:8px 10px}
.settings-nav .navbtn{display:flex;justify-content:flex-start;width:100%;text-align:left;border:1px solid transparent;background:transparent;padding:9px 12px;border-radius:7px;font-size:13px;min-height:40px;color:#c2d0e0;margin:3px 0}
.settings-nav .navbtn.active{background:#3b2b1b;color:#ffd4ae;border-color:#705337}.settings-nav .navbtn:hover{background:#243449}.settings-no-results{color:var(--muted);font-size:13px}
.settings-content{overflow:auto;padding:28px 32px;min-width:0;scrollbar-width:thin}.settings-content>.panel{display:none;margin:0;padding:0;border:0;background:transparent}.settings-content>.panel.active{display:block}
.settings-content p{font-size:14px;max-width:85ch;line-height:1.7}.settings-content h2{font-size:26px}.settings-content h3{font-size:21px}.settings-content h4{font-size:16px;margin-top:24px}
.settings-content label{font-size:14px}.settings-content button{margin:4px 6px 4px 0}.settings-content input:not([type=checkbox]),.settings-content textarea{max-width:100%}
.settings-content pre{border:1px solid var(--border);background:#0d151f;padding:16px;border-radius:9px;max-height:400px}.settings-content .ext{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:18px 0;border-bottom:1px solid var(--border)}
.settings-content .ext p{margin:6px 0 0;color:var(--muted);font-size:13px}.runtime-field{display:block;margin:20px 0}.runtime-field input[type=number]{display:block;width:100%;margin-top:7px}
#pythonTools{border:1px solid var(--border);border-radius:10px;padding:14px 18px}#pythonTools>summary{font-size:15px;margin-bottom:12px}#pythonTools>label{display:inline-flex;align-items:flex-start;gap:7px;margin:10px 0}
#pythonTools>br{display:none}#pythonTools>label:has(#approveRea),#pythonTools>label:has(#approveFrontendWorkspace){display:flex}#inventoryRoot{width:100%!important;margin-bottom:12px}#pythonTools p{font-size:13px;color:var(--muted)}
#openCodeTaskAccess{padding:20px;border:1px solid var(--border);border-radius:10px}#openCodeTaskAccess>label{display:block;margin:16px 0}
#skillNotice{padding:12px 18px;border:1px solid #82663e;border-radius:9px;color:var(--warning);background:#322818;margin-bottom:12px;font-size:13px}#skillNotice button{margin-left:10px;background:transparent;min-height:32px;font-size:12px}
.settings-section-picker{display:none}.section-heading p{color:var(--muted);margin-bottom:24px}
.skills-toolbar,.locations-toolbar{display:flex;gap:6px;align-items:center;flex-wrap:wrap;position:sticky;top:-28px;padding:12px 0;background:var(--surface);z-index:3;margin-bottom:8px}
.skills-toolbar input,.locations-toolbar input{margin-left:auto;min-width:180px;flex:1;max-width:280px}.skills-toolbar button:first-child{color:var(--accent);border-color:#83603e;background:#302419}
.skills-notice,.locations-status,.locations-note,.skills-taskbar{color:var(--muted);font-size:13px}.skills-table-wrap,.locations-table-wrap{border:1px solid #435b75;border-radius:10px;overflow:auto;scrollbar-width:thin;margin:16px 0}
.skills-table,.locations-table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}.skills-table th,.locations-table th{font-size:10px;text-transform:uppercase;letter-spacing:.08em;background:#223044;color:#bdcee2;text-align:left;padding:14px 12px;white-space:nowrap}
.skills-table td,.locations-table td{padding:14px 12px;border-top:1px solid var(--border);vertical-align:middle}.skills-table tr:hover td,.locations-table tr:hover td{background:#1e2e40}
.skills-table th:first-child,.skills-table td:first-child,.locations-table td:first-child{width:46px}.skills-table .skill-name,.locations-table .location-name{display:block;font-weight:650;background:transparent;border:0;padding:0;text-align:left;color:var(--text);min-height:32px;font-size:13px}
.skills-table td>small,.locations-table td>small{display:block;font-size:11px;margin-top:4px}.skill-description{max-width:330px;color:var(--muted);line-height:1.6}.status-badge{display:inline-flex;align-items:center;gap:6px;padding:3px 7px;font-size:11px;line-height:1.5;border-radius:5px;background:#2c3c50;color:#dae5f3;white-space:normal}
.status-badge:before{content:'';width:5px;height:5px;border-radius:50%;background:currentColor;flex-shrink:0}.status-badge.good{color:#a4f1da;background:#153b30}.status-badge.warn{color:#ffe0a4;background:#49381d}.status-badge.bad{color:#ffc1c5;background:#4b242c}.status-badge.accent{color:#b9dbff;background:#213c5d}
.skill-group td{background:#243044!important}.collection-toggle{background:transparent;border:0;padding:4px 0;justify-content:flex-start;font-size:13px}.collection-count{color:var(--muted);font-size:11px;margin-left:8px}
.skills-taskbar{display:flex;gap:16px;flex-wrap:wrap;align-items:center;padding:16px 0;border-top:1px solid var(--border)}.skills-taskbar label{display:flex;align-items:center;gap:7px}
.skill-detail{padding:18px;background:#111e2a;border-bottom:1px solid var(--border)}.skill-detail p{font-size:13px}.skill-detail pre{max-height:350px}
.locations-state{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--muted)}.location-path{font-family:Consolas,monospace;font-size:12px;min-width:180px;max-width:320px;overflow-wrap:anywhere;word-break:break-word;color:#bdcee2}.location-operations{font-size:12px;color:var(--muted);min-width:90px}
.import-dialog,.chat-dialog,.location-dialog,.folder-dialog{background:var(--surface);color:var(--text);border:1px solid #607b98;border-radius:14px;padding:28px;max-width:min(94vw,820px);max-height:90dvh;overflow:auto;box-shadow:0 28px 90px #0008}
.chat-dialog{width:480px}.chat-dialog label,.location-dialog>label{display:block;font-size:14px;margin:18px 0}.chat-dialog input,.import-dialog>input,.location-dialog>label>input{display:block;width:100%;margin-top:7px}
.dialog-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:24px;padding-top:16px;border-top:1px solid var(--border)}.dialog-error{color:var(--danger);font-size:14px}
.import-dialog pre{max-height:300px}.import-candidates{border:1px solid var(--border);padding:12px;border-radius:9px;max-height:280px;overflow:auto}.import-candidates label{display:block;margin:10px}.import-dialog .dialog-actions button:last-child{background:var(--accent);color:var(--accent-ink)}
.location-path-editor{display:flex;gap:8px;margin-top:7px}.location-path-editor input{flex:1;min-width:0}.location-editor-flags{display:flex;gap:20px;flex-wrap:wrap;padding:14px 0}.location-operation-choices{border:1px solid var(--border);border-radius:8px;display:flex;gap:16px;flex-wrap:wrap;padding:14px}.location-operation-choices legend{font-size:12px;color:var(--muted);padding:0 6px}
.location-advanced{margin:18px 0}.location-advanced p{font-size:13px;color:var(--muted)}.location-advanced textarea{width:100%}.folder-dialog{width:860px}.folder-dialog p{font-size:13px;color:var(--muted)}
.folder-address{display:flex;gap:8px;margin:16px 0}.folder-address input{flex:1;min-width:0}.folder-breadcrumbs{display:flex;flex-wrap:wrap;align-items:center;gap:4px;margin:12px 0}.folder-breadcrumbs button{background:transparent;border:0;padding:4px 6px;font-size:12px;min-height:30px}
.folder-breadcrumbs button+button:before{content:'/';color:var(--muted);margin-right:6px}.folder-layout{display:grid;grid-template-columns:170px minmax(0,1fr);gap:14px;min-height:220px}
.folder-shortcuts{display:flex;flex-direction:column;gap:6px}.folder-shortcuts button{justify-content:flex-start;text-align:left;font-size:12px;background:transparent;overflow-wrap:anywhere}
.folder-list{border:1px solid #49627e;border-radius:8px;max-height:300px;overflow:auto;min-height:200px;background:#0f1925}.folder-entry{display:flex;align-items:center;justify-content:flex-start;gap:10px;width:100%;border:0;border-bottom:1px solid var(--border);border-radius:0;background:transparent;padding:12px;text-align:left;font-size:14px}
.folder-entry>span:nth-child(2){flex:1;overflow-wrap:anywhere}.folder-icon,.folder-chevron{color:var(--accent)}.folder-empty{padding:20px}.folder-filters{display:flex;align-items:center;gap:14px;margin:14px 0}.folder-filters input[type=search]{flex:1;min-width:0}.folder-hidden{font-size:12px;display:flex;align-items:center;gap:5px}.folder-dialog>[role=status]{min-height:24px}
.execution-cards{align-self:stretch;margin:0 0 10px;padding:18px;border:1px solid var(--border);border-radius:12px;background:#111b26}.execution-cards h3{font-size:15px;color:var(--teal)}.execution-cards p{font-size:13px}.execution-card{padding:14px;border:1px solid #405b71;border-radius:8px;margin:12px 0;background:#192b38}
.execution-error{border-color:#aa6471;background:#33232d}.execution-warning{border-color:var(--warning);background:#30291f}.execution-path{font-family:Consolas,monospace;font-size:12px;overflow-wrap:anywhere;color:var(--muted)}.execution-card pre{max-height:360px;font-size:12px}
.file-activity{width:100%;padding:18px;border:1px solid var(--border);border-radius:12px;background:#14212e}.file-activity h3{font-size:16px}.file-activity-note{font-size:13px;color:var(--muted)}.file-activity-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:14px}
.file-work-card{border:1px solid #4b627b;border-radius:9px;padding:16px;background:#101a26;min-width:0}.file-work-card h4{font-size:14px;overflow-wrap:anywhere}.file-work-status{font-size:12px;color:var(--muted)}
.file-work-card[data-state=saved]{border-color:#5caa93}.file-work-card[data-state=error]{border-color:#cb7f8c}.file-work-card summary{font-size:13px}.file-original-code,.file-work-card details pre{max-height:240px;font-size:12px;background:#0d151f;padding:10px}
.file-code-label{display:block;font-size:13px;margin-top:12px}.file-code-label span{display:block;color:var(--muted);font-size:11px}.file-updated-code{width:100%;min-height:200px;background:#0a121b!important;font:12px/1.6 Consolas,monospace;white-space:pre;overflow:auto}.file-work-error{color:var(--danger)}
.message:has(.model-card){width:100%;max-width:100%}.model-card{margin:10px 0 0;border:1px solid #4b6785;border-radius:10px;padding:18px;background:#111e2b;min-width:0}.model-card h3{font-size:17px}.model-card p{font-size:13px;color:var(--muted)}.model-card pre{max-height:280px}
.model-stage{width:100%;margin:14px 0;border-radius:9px;overflow:hidden;background:#233348}.model-stage:empty{display:none}.model-stage model-viewer{display:block;width:100%;height:420px;max-height:50dvh;background:#233348}
.model-actions{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.model-actions button{font-size:12px}.animation-panel{padding-top:18px;margin-top:18px;border-top:1px solid var(--border);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.animation-panel h4,.animation-panel>p{flex-basis:100%;margin:0}.animation-panel select,.animation-panel input:not([type=range]){min-width:160px;flex:1}.animation-panel input[type=range]{flex-basis:60%}.animation-panel span{font-size:12px;color:var(--muted)}.animation-panel button{font-size:12px}
.notifications{position:fixed;z-index:100;bottom:24px;right:24px;width:min(460px,calc(100vw - 32px))}.notification{display:flex;align-items:flex-start;gap:12px;border:1px solid #b87380;border-radius:10px;padding:16px;background:#3b2531;box-shadow:0 10px 30px #0006;font-size:14px}.notification>span{flex:1;overflow-wrap:anywhere}.notification>button{border:0;background:transparent;padding:4px;min-height:28px}
#bootstrap{max-width:680px;width:100%;margin:40px auto;padding:28px;background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:auto}#bootstrap input{width:100%;margin:8px 0 16px}#error{color:var(--danger)}
@media(max-width:1100px){
 main{padding:0 16px}#shell{grid-template-columns:220px minmax(0,1fr);gap:16px}#workspace{padding:0 18px 18px}.app-subtitle{max-width:220px;font-size:11px}.starter-grid{gap:8px}.starter-card{padding:14px}.settings-search{width:240px}.settings-content{padding:24px}#rightbar{grid-template-columns:210px minmax(0,1fr)}
 .skills-toolbar input,.locations-toolbar input{max-width:none;flex-basis:100%;margin:8px 0 0}.skills-toolbar,.locations-toolbar{top:-24px}
}
@media(max-width:800px){
 main{padding:0 12px}.appbar{height:66px;gap:10px}.app-brand>.ui-icon{display:none}.app-brand h1{font-size:16px}.app-subtitle{display:none}.runtime-chip{font-size:10px;max-width:48%;padding:5px 9px}
 .history-toggle{display:inline-flex;width:40px;padding:8px;background:transparent}.history-scrim{position:absolute;inset:0;z-index:8;background:#02060bbd;border:0;border-radius:12px;padding:0}
 #shell{display:block}#leftbar{position:absolute;left:0;top:0;bottom:0;width:min(310px,86%);z-index:9;display:none;border-color:#6985a3;box-shadow:12px 0 44px #0008}#shell.history-open #leftbar{display:flex}#shell.history-open .history-scrim{display:block}
 #workspace{height:100%;padding:0 14px 14px}.workspace-toolbar{gap:6px;padding:10px 0}#taskAccessSummary{flex-basis:100%;font-size:11px}.workspace-toolbar button{font-size:12px;min-height:38px}
 .conversation-heading{padding:16px 0 8px}#chatTitle{font-size:20px}#chatlog{padding:8px 0 20px;gap:16px}.message{max-width:96%;padding:14px;font-size:15px}.message-label{font-size:11px}
 .workbench-empty{padding:14px 4px}.workbench-empty h2{font-size:26px}.workbench-empty>p:not(.eyebrow){font-size:14px}.starter-grid{grid-template-columns:1fr;margin-top:22px}.starter-card{display:grid;grid-template-columns:24px 1fr;gap:4px 12px;padding:14px}.starter-card>.ui-icon{grid-row:1/3}.starter-card span{grid-column:2;font-size:12px}
 #composer>.composer-engine{order:2;flex-basis:100%;font-size:12px}.composer-hint{order:3}#chatinput{min-height:66px}#composer{padding:10px;gap:8px}#composer>button{margin-left:0}#composer>button:first-of-type{margin-left:auto}
 #sysfooter{max-height:110px;font-size:11px}.resource-grid{gap:8px 16px;padding:8px 0}.resource-grid>span{font-size:11px}.resource-grid button{margin-left:0}.resource-details>summary{min-height:32px;padding-top:4px}
 .settings-screen{width:100vw;height:100dvh;border:0;border-radius:0}.settings-header{height:140px;padding:16px;gap:12px;flex-wrap:wrap}.settings-header>div{min-width:0;flex:1}.settings-header .eyebrow{font-size:9px}.settings-header h2{font-size:22px}.settings-header button{font-size:12px}
 .settings-search{order:3;width:100%;margin:0}.settings-current{font-size:11px}#rightbar{display:flex;flex-direction:column;height:calc(100% - 140px)}.settings-nav{display:none}.settings-section-picker{display:block;width:calc(100% - 32px);margin:16px 16px 0;flex-shrink:0}
 .settings-content{padding:24px 16px;flex:1}.settings-content h2{font-size:23px}.settings-content p{font-size:14px}.settings-content input:not([type=checkbox]),.settings-content select,.settings-content textarea{font-size:16px}
 .skills-toolbar,.locations-toolbar{top:-24px}.skills-taskbar{align-items:flex-start;gap:12px}.skills-taskbar label{flex-basis:100%}.locations-table,.skills-table{min-width:680px}.locations-table-wrap,.skills-table-wrap{max-width:100%;overscroll-behavior-x:contain}
 .location-dialog,.folder-dialog,.chat-dialog,.import-dialog{padding:20px;max-width:96vw;max-height:94dvh}.folder-layout{grid-template-columns:1fr}.folder-shortcuts{flex-direction:row;flex-wrap:wrap}.folder-shortcuts button{font-size:11px}.folder-list{max-height:250px}
 .folder-filters{flex-wrap:wrap}.folder-filters input[type=search]{flex-basis:100%}.location-editor-flags{gap:12px}.location-operation-choices{gap:12px}.notifications{bottom:16px;right:16px}.model-card{padding:12px}.model-stage model-viewer{height:300px}
 button{min-height:44px}.chat-action{min-width:32px;min-height:36px}.copy-button{min-height:32px}.attachment-add{min-width:44px;height:44px}.history-row{grid-template-columns:minmax(0,1fr) 36px 36px}.empty-mark{width:52px;height:52px;margin-bottom:14px}
}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}

/* Content-first refinements after desktop/mobile screenshot review. */
.workbench-empty{flex-shrink:0;padding:20px 12px}.empty-mark{width:48px;height:48px;margin-bottom:14px;border-radius:12px}.empty-mark .ui-icon{width:28px;height:28px}
.workbench-empty h2{font-size:28px}.workbench-empty>p:not(.eyebrow){font-size:14px;margin-bottom:16px}.starter-grid{margin-top:22px}.starter-card{padding:16px;gap:8px}.workbench-empty .empty-boundary{margin-top:18px;font-size:12px}
#chatinput{height:84px}#skillNotice{display:flex;align-items:center;gap:8px;flex-wrap:wrap}#skillNoticeText{flex:1;min-width:130px}#skillNotice button{margin:0}
.effective-task-context{padding:12px 14px;border:1px solid var(--border);border-radius:8px;background:#0e1721;color:var(--muted)}
@media(max-width:800px){
 #chatinput{height:72px;min-height:64px}#composer>.composer-engine{display:flex;align-items:center;gap:8px}#composer>.composer-engine select{flex:1;min-width:0}
 .conversation-caption{display:none}.conversation-heading{padding:14px 0 8px}.task-status{font-size:12px;margin:6px 2px}.workbench-empty{padding:12px 4px}
 #skillNotice{font-size:11px;padding:7px 10px;gap:6px}#skillNoticeText{min-width:100px}#skillNotice button{font-size:11px;padding:4px 8px;min-height:34px}
 .resource-grid{padding-bottom:6px}#sysfooter{padding-bottom:max(8px,env(safe-area-inset-bottom))}.workbench-empty h2{font-size:24px}
}

.component-toolbar,.component-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.component-toolbar{margin:20px 0}.component-table-wrap{overflow:auto;border:1px solid var(--border);border-radius:12px}.component-table{width:100%;border-collapse:collapse;text-align:left;min-width:780px}.component-table caption{text-align:left;padding:14px;color:var(--muted);font-size:13px}.component-table th,.component-table td{padding:14px;vertical-align:top;border-top:1px solid var(--border)}.component-table thead{background:#1b2735}.component-table tbody th{width:19%}.component-table td:nth-child(3){width:33%}.component-table small{display:block;line-height:1.5;margin-top:6px;font-weight:400}.component-actions button{min-height:36px;padding:6px 10px;font-size:12px}.component-state{display:inline-block;padding:2px 9px;border-radius:20px;background:#30251d;color:var(--warning);font-size:12px;text-transform:capitalize}.component-state-running,.component-state-loaded,.component-state-ready,.component-state-on_demand,.component-state-available{background:#16352e;color:var(--teal)}.component-state-missing,.component-state-unavailable,.component-state-blocked{background:#422630;color:var(--danger)}
</style><main><h1>SMELTER</h1><p>V1.7 · Scoped local workbench</p>
<section class="panel"><h2>Extensions</h2><p>Extensions are disabled by default. Activation only records configuration; execution permissions remain ungranted.</p>
<button id="refresh">Rescan tools</button><p id="error"></p><div id="items">Loading…</div></section>
<section class="panel"><h2>Workflow planner</h2><p>Preview ordered steps and dependency checks. Dry run only — no tools execute.</p>
<select id="workflow" style="padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:7px"></select>
<p><label for="inputs">Optional absolute input paths (one per line; maximum 16)</label></p>
<textarea id="inputs" rows="3" style="width:100%;box-sizing:border-box;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:7px;padding:10px" placeholder="C:\path\to\asset"></textarea>
<p><button id="plan">Preview and save dry run</button> <button id="history">Refresh report history</button></p>
<pre id="historyout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="planout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: archive inspection</h2><p>Read-only 7-Zip listing. Select an existing archive and explicitly approve each run. No extraction or file changes.</p>
<input id="archivepath" style="width:100%;box-sizing:border-box;padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e" placeholder="C:\archives\example.zip">
<p><label><input id="approve" type="checkbox"> I approve running 7-Zip to list this archive only.</label></p>
<button id="inspect">Inspect archive (read only)</button><pre id="inspectout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: media inspection</h2><p>Read-only FFprobe metadata inspection. Approve each run; no transcoding or generated files.</p>
<input id="mediapath" style="width:100%;box-sizing:border-box;padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e" placeholder="C:\media\sample.mp4">
<p><label><input id="mediaapprove" type="checkbox"> I approve FFprobe reading this media file's metadata only.</label></p>
<button id="mediainspect">Inspect media (read only)</button><pre id="mediaout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: Blender capability</h2><p>Check the Blender executable and version only. No project loading, Python scripts, or asset modification.</p>
<p><label><input id="blenderapprove" type="checkbox"> I approve launching Blender with --version only.</label></p>
<button id="blenderinspect">Check Blender version</button><pre id="blenderout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Local AI: Ollama / Qwen</h2><p>Discover models already installed in your local Ollama service. No downloads, prompts, or model execution.</p>
<button id="ollamascan">Discover local models</button>
<p><label>Role <select id="modelrole"><option value="reasoning">Reasoning</option><option value="lightweight">Lightweight · configuration only</option></select></label>
<label> Installed model <select id="modelchoice"></select></label></p>
<button id="modelsave">Save model preference</button><pre id="modelout"></pre><pre id="ollamaout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>OpenCode agent readiness</h2><p>Installation discovery does not start an agent. Managed connection checks below start a temporary inspection container without submitting a model task.</p>
<button id="opencodecheck">Check OpenCode</button> <button id="providerpreview">Preview Ollama provider config</button>
<p><label><input id="deployapprove" type="checkbox"> I approve creating an isolated OpenCode configuration in .smelter only.</label></p>
<button id="providerdeploy">Deploy isolated config (create only)</button> <button id="providervalidate">Validate staged config</button>
<pre id="validateout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre>
<h3>Managed OpenCode · scoped agent</h3><p>Uses an owned, no-network container and a read-only snapshot of the sibling V2 workspace. The local-model relay submits prompts only after a task is approved.</p>
<button id="opencodeServerCheck">Check managed OpenCode</button><pre id="opencodeServerStatus" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre>
<label>Verified local model <select id="opencodeAgentModel" aria-label="OpenCode local model"></select></label>
<label style="display:block"><input id="opencodeAgentApprove" type="checkbox"> Allow one confined OpenCode session with selected skills and the tools approved for this Send. Native source access stays read-only; native shell, delegation and arbitrary external MCP are denied.</label>
<p>Configure a reviewed OpenCode image in Confined execution, check the managed server, then approve one task. Selected skills and approved built-in MCP tools are forwarded. Native source access stays read-only; images and external MCP servers are unsupported.</p>
<pre id="deployout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="providerout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="opencodeout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section id="bootstrap" class="panel" hidden><h2 id="startupHeading">SMELTER startup</h2><div id="databaseSetup"><p>Choose an absolute directory for persistent SQLite storage. Existing JSON configuration files remain untouched.</p><input id="dbdirectory" placeholder="D:\SMELTER-Data"><button id="dbselect">Initialize database</button></div><div id="authRecovery" hidden><p>This page is not authorized for the running dashboard. Use the current launch URL printed in its terminal. Restarting the server changes the token; database initialization will not fix authorization.</p><label>Current launch URL or token<input id="sessionToken" type="password" autocomplete="off" spellcheck="false" aria-label="Current launch URL or token"></label><button id="sessionReconnect">Reconnect session</button></div><button id="dbretry">Retry checks</button><pre id="dbstatus" style="white-space:pre-wrap"></pre></section>
<script src="/assets/session-auth.js"></script><script src="/assets/mcp-ui.js"></script><script src="/assets/turntable.js"></script><script src="/assets/model-animations.js"></script><script src="/assets/model-preview.js"></script><script src="/assets/chat-renderer.js"></script><script src="/assets/file-activity.js"></script><script src="/assets/opencode-agent-ui.js"></script><script src="/assets/skills-ui.js"></script><script src="/assets/attachments-ui.js"></script><script src="/assets/workbench-ui.js"></script><script src="/assets/settings-ui.js"></script><script src="/assets/location-browser.js"></script><script src="/assets/locations-ui.js"></script><script src="/assets/access-ui.js"></script><script src="/assets/operations-ui.js"></script><script src="/assets/system-components.js"></script><script src="/assets/dashboard-shell.js"></script></main></html>"""

def handler(token: str):
    from dashboard_api import ApiRoutes,Context
    class Handler(ApiRoutes,BaseHTTPRequestHandler):
        app=Context(globals())
        def handle(self):
            try:
                super().handle()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True
        def reply(self, status, data, content_type="application/json"):
            body = data if isinstance(data, bytes) else data.encode() if isinstance(data, str) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; connect-src 'self' blob: data:; img-src 'self' blob: data:; worker-src 'self' blob:")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True
        def authorized(self):
            origin = self.headers.get("Origin")
            expected = "http://127.0.0.1:" + str(self.server.server_port)
            supplied = self.headers.get("X-Smelter-Token", "")
            return supplied.isascii() and secrets.compare_digest(supplied, token) and (not origin or origin == expected)
    return Handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    initialize_skills(ROOT)
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(token))
    url = f"http://127.0.0.1:{server.server_port}/#token={token}"
    print("SMELTER dashboard:", url)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        close_components()
        server.server_close()

if __name__ == "__main__":
    main()
