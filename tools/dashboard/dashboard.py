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
/* SMELTER design system: dark developer-tool palette (slate surfaces, green run
   accent), dense Swiss layout, subtle motion. Tokens first; components use tokens only. */
@font-face{font-family:"JetBrains Mono";src:url(/assets/fonts/JetBrainsMono-Regular.ttf) format("truetype");font-weight:400;font-display:swap}
@font-face{font-family:"JetBrains Mono";src:url(/assets/fonts/JetBrainsMono-Bold.ttf) format("truetype");font-weight:700;font-display:swap}
:root{
 color-scheme:dark;
 --bg:#0b1120;--surface:#0f172a;--raised:#151e31;--card:#1b2336;--hover:#222c42;--active:#2a3550;
 --border:#243049;--border-strong:#3a4762;--control-border:#3a4762;
 --text:#f1f5f9;--text-strong:#f8fafc;--muted:#94a3b8;--subtle:#64748b;
 --accent:#22c55e;--accent-hover:#4ade80;--accent-ink:#052e16;--accent-soft:#22c55e1f;--accent-line:#22c55e66;
 --info:#60a5fa;--info-soft:#60a5fa1f;--warning:#fbbf24;--warning-soft:#fbbf241a;--danger:#f87171;--danger-soft:#f871711f;
 --teal:#4ade80;--focus:#e2e8f0;
 --radius-sm:6px;--radius:8px;--radius-lg:12px;
 --space-1:4px;--space-2:8px;--space-3:12px;--space-4:16px;--space-5:20px;--space-6:24px;--space-8:32px;
 --control-h:34px;--header-h:48px;
 --font-sans:"IBM Plex Sans","Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,sans-serif;
 --font-mono:"JetBrains Mono","Cascadia Code",Consolas,ui-monospace,monospace;
 --shadow-pop:0 12px 32px #0009,0 0 0 1px #ffffff0d;
 --ease:cubic-bezier(.2,0,0,1);--fast:120ms;--normal:180ms;
 font:14px/1.55 var(--font-sans);
}
*{box-sizing:border-box}[hidden]{display:none!important}
html,body{margin:0;min-width:320px;height:100%;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}
body{overflow:hidden}
main{height:100dvh;display:flex;flex-direction:column;min-height:0}
h1,h2,h3,h4{line-height:1.3;letter-spacing:-.01em;font-weight:600;margin:0 0 var(--space-3);color:var(--text-strong)}
h1{font-size:15px}h2{font-size:20px}h3{font-size:16px}h4{font-size:14px}
p{margin:var(--space-2) 0 var(--space-3);overflow-wrap:anywhere}
small,.muted{color:var(--muted);font-size:12px}
a{color:var(--info);text-underline-offset:3px}

/* Controls */
button,input,select,textarea{font:inherit;color:inherit}
button{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:var(--control-h);border:1px solid var(--control-border);border-radius:var(--radius);padding:5px 12px;background:var(--raised);cursor:pointer;font-size:13px;font-weight:500;line-height:1.2;transition:background var(--fast) var(--ease),border-color var(--fast) var(--ease),color var(--fast) var(--ease)}
button:hover:not(:disabled){background:var(--hover);border-color:#4b5a78}
button:active:not(:disabled){background:var(--active)}
button:disabled{opacity:.45;cursor:not-allowed}
button.primary-button,.primary-button{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
.primary-button:hover:not(:disabled){background:var(--accent-hover);border-color:var(--accent-hover)}
.quiet-button{background:transparent;border-color:transparent}.quiet-button:hover:not(:disabled){background:var(--hover);border-color:transparent}
button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible,a:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
:focus-visible{scroll-margin-block:80px}
input:not([type=checkbox]):not([type=range]):not([type=file]):not([type=radio]),select,textarea{min-height:var(--control-h);background:var(--surface);border:1px solid var(--control-border);border-radius:var(--radius);padding:6px 10px;max-width:100%;font-size:13px;transition:border-color var(--fast) var(--ease)}
input:hover:not(:focus),select:hover:not(:focus),textarea:hover:not(:focus){border-color:#4b5a78}
input::placeholder,textarea::placeholder{color:var(--subtle);opacity:1}
textarea{line-height:1.55;resize:vertical}
input[type=checkbox],input[type=radio]{accent-color:var(--accent);width:16px;height:16px;flex-shrink:0;vertical-align:middle;margin:0 6px 0 0;cursor:pointer}
input[type=range]{accent-color:var(--accent)}
label{line-height:1.5}
summary{cursor:pointer;font-weight:500;min-height:28px;padding:4px 0}
pre,code,kbd{font-family:var(--font-mono);font-size:12px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-width:100%;overflow:auto;line-height:1.6}pre:empty{display:none}
.ui-icon{width:16px;height:16px;flex:0 0 auto;vertical-align:middle}
.eyebrow{font-size:11px;letter-spacing:.08em;font-weight:600;text-transform:uppercase;color:var(--muted);margin:0 0 var(--space-1)}
.field-caption{display:block;color:var(--muted);font-size:12px;margin:var(--space-3) 0 var(--space-1)}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.skip-link{position:fixed;left:16px;top:-100px;padding:8px 14px;background:var(--accent);color:var(--accent-ink);z-index:1000;border-radius:var(--radius)}.skip-link:focus{top:8px}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:#2a3550;border-radius:10px;border:2px solid transparent;background-clip:padding-box}::-webkit-scrollbar-track{background:transparent}
*{scrollbar-width:thin;scrollbar-color:#2a3550 transparent}

/* App header */
.appbar{height:var(--header-h);flex-shrink:0;display:flex;align-items:center;gap:var(--space-3);padding:0 var(--space-4);border-bottom:1px solid var(--border);background:var(--surface)}
.app-brand{display:flex;align-items:center;gap:10px;min-width:0}
.app-brand>.ui-icon{width:22px;height:22px;color:var(--accent)}
.app-brand h1{margin:0;letter-spacing:.12em;font-size:13px;font-weight:700}
.app-subtitle{margin:0;border-left:1px solid var(--border);padding-left:var(--space-3);font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.runtime-chip{margin-left:auto;display:inline-flex;align-items:center;gap:6px;font-size:12px;max-width:40%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border:1px solid var(--border);border-radius:999px;padding:3px 10px;color:var(--muted);background:var(--raised)}
.runtime-chip:before{content:'';width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px var(--accent-soft);flex-shrink:0}
.history-toggle,.history-scrim{display:none}
.panel{min-width:0}.panel:not(.active){scroll-margin-top:20px}

/* Shell: sidebar + workspace, flush panes separated by hairlines */
#shell{flex:1;min-height:0;display:grid;grid-template-columns:256px minmax(0,1fr);position:relative}
#leftbar{background:var(--surface);border-right:1px solid var(--border);padding:var(--space-3);display:flex;flex-direction:column;min-height:0;overflow:auto;gap:var(--space-1)}
#leftbar h2{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:var(--space-1) var(--space-2) var(--space-2);font-weight:600}
#leftbar>button{justify-content:flex-start;width:100%;background:var(--accent-soft);color:var(--accent);border-color:var(--accent-line);font-weight:600;margin-bottom:var(--space-2)}
#leftbar>button:hover:not(:disabled){background:#22c55e2e;border-color:var(--accent)}
#leftbar .field-caption{display:none}
#chatSearch{width:100%;font-size:13px}
.history-count{font-size:11px;color:var(--subtle);margin:var(--space-2) var(--space-2) 0}
#chatHistory{flex:1;min-height:80px}
.history-row{display:grid;grid-template-columns:minmax(0,1fr) 26px 26px;gap:2px;align-items:center;padding:2px;margin:1px 0;border-radius:var(--radius);border:1px solid transparent}
.history-row:hover{background:var(--hover)}
.history-row.selected{background:var(--active)}
.history-row.selected .history-title{color:var(--text-strong)}
.chat-open{display:block;background:transparent;border:0;padding:6px 8px;text-align:left;min-width:0;min-height:0}
.chat-open:hover:not(:disabled){background:transparent}
.history-title{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;color:var(--text)}
.chat-open small{display:block;margin-top:1px;font-size:11px;color:var(--subtle)}
.chat-action{min-width:26px;min-height:26px;padding:0;border:0;background:transparent;color:var(--subtle);font-size:15px;opacity:0;transition:opacity var(--fast)}
.history-row:hover .chat-action,.history-row.selected .chat-action,.chat-action:focus-visible{opacity:1}
.chat-action:hover:not(:disabled){color:var(--text);background:var(--active)}
.sidebar-note{color:var(--subtle);font-size:11px;border-top:1px solid var(--border);padding:var(--space-3) var(--space-2) 0;margin-top:var(--space-3)}

/* Workspace: toolbar, conversation column */
#workspace{background:var(--bg);display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden}
.workspace-toolbar{display:flex;align-items:center;gap:var(--space-2);flex-wrap:wrap;padding:var(--space-2) var(--space-4);border-bottom:1px solid var(--border);flex-shrink:0;background:var(--surface)}
.workspace-toolbar button{font-size:12px;padding:4px 10px;min-height:30px;background:transparent;border-color:transparent;color:var(--muted)}
.workspace-toolbar button:hover:not(:disabled){color:var(--text);background:var(--hover);border-color:transparent}
#taskAccessSummary{flex:1;min-width:190px;color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.workspace-toolbar .ui-icon{width:15px;height:15px}
.conversation-heading{display:flex;flex-direction:column;gap:2px;padding:var(--space-4) var(--space-6) var(--space-2);flex-shrink:0;width:100%;max-width:920px;margin:0 auto}
.conversation-caption{display:none}
#chatTitle{font-size:16px;margin:0;font-weight:600}
#chatlog{display:flex;flex-direction:column;gap:var(--space-5);flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;padding:var(--space-4) max(var(--space-6),calc((100% - 872px)/2)) var(--space-6)}

/* Messages: assistant text flows on the page; user turns are compact bubbles */
.message{max-width:100%;padding:0;border-radius:var(--radius-lg);flex-shrink:0;overflow-wrap:anywhere;min-width:0;line-height:1.65;font-size:14px}
.message-user{align-self:flex-end;max-width:min(80%,640px);background:var(--card);border:1px solid var(--border);padding:10px 14px}
.message-assistant{align-self:stretch;background:transparent;border:0;padding:0 2px}
.message-label{display:flex;align-items:center;justify-content:space-between;gap:var(--space-3);flex-wrap:wrap;color:var(--subtle);font-size:11px;font-weight:600;letter-spacing:.02em;margin-bottom:var(--space-1)}
.message-user .message-label{display:none}
.message-content{white-space:pre-wrap}
.copy-button{font-size:11px;min-height:24px;padding:2px 8px;background:transparent;border-color:transparent;color:var(--subtle);opacity:0;transition:opacity var(--fast)}
.message:hover .copy-button,.copy-button:focus-visible{opacity:1}
.copy-button:hover:not(:disabled){color:var(--text);background:var(--hover)}
.formatted-message p{color:inherit;white-space:pre-wrap;line-height:1.7;margin:6px 0}
.formatted-message ul,.formatted-message ol{padding-left:22px;margin:6px 0}.formatted-message li{margin:3px 0}
.formatted-message blockquote{border-left:2px solid var(--accent-line);padding-left:12px;margin-left:0;color:var(--muted)}
.formatted-message h1,.formatted-message h2,.formatted-message h3{font-size:15px;margin:14px 0 6px}
.formatted-message :not(pre)>code{background:var(--card);border:1px solid var(--border);padding:1px 5px;border-radius:4px;color:#bbf7d0;font-size:12px}
.code-block{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin:10px 0;background:#080d18}
.code-toolbar{display:flex;justify-content:space-between;align-items:center;padding:4px 6px 4px 12px;font-size:11px;background:var(--raised);color:var(--muted);border-bottom:1px solid var(--border);font-family:var(--font-mono)}
.code-toolbar button{min-height:24px;padding:2px 8px;font-size:11px;background:transparent;border-color:transparent}
.code-block pre{white-space:pre;margin:0;padding:12px 14px;overflow-x:auto}

/* Task status line above the composer */
.task-status{font-size:12px;color:var(--muted);min-height:22px;flex-shrink:0;margin:0 auto;padding:4px var(--space-6) 0;width:100%;max-width:920px;display:flex;gap:var(--space-2);align-items:center}
.task-status:before{content:'';width:6px;height:6px;border-radius:50%;background:var(--subtle);flex-shrink:0}
.task-status[data-state=ready]:before{background:var(--accent)}
.task-status[data-state=busy]:before{background:var(--info);animation:pulse 1.2s ease-in-out infinite}
.task-status[data-state=error]{color:var(--danger)}.task-status[data-state=error]:before{background:var(--danger)}
.task-status[data-state=warning]{color:var(--warning)}.task-status[data-state=warning]:before{background:var(--warning)}
@keyframes pulse{50%{opacity:.35}}

/* Composer: one-line auto-growing input; controls on a single row below */
#composer{display:grid;grid-template-columns:auto auto minmax(0,1fr) auto auto;grid-template-areas:"input input input input input" "attach engine chips stop send";gap:6px var(--space-2);align-items:center;padding:8px 8px 8px 10px;margin:4px auto var(--space-4);width:calc(100% - 2*var(--space-6));max-width:872px;border:1px solid var(--border-strong);border-radius:var(--radius-lg);background:var(--card);position:relative;flex-shrink:0;transition:border-color var(--fast) var(--ease),box-shadow var(--fast) var(--ease)}
#composer:focus-within{border-color:#52617f;box-shadow:0 0 0 3px #94a3b81a}
#chatinput{grid-area:input;width:100%;min-height:24px;height:auto;max-height:200px;resize:none;background:transparent;border:0;padding:4px 4px;font-size:14px;line-height:1.55;overflow-y:auto}
#chatinput:focus-visible{outline:none}
#composer>.attachment-control{grid-area:attach}
#composer>.composer-engine{grid-area:engine;display:inline-flex;align-items:center;gap:0;font-size:0;color:var(--muted)}
.composer-engine select{font-size:12px;min-height:28px;height:28px;padding:2px 26px 2px 10px;border-radius:999px;background:var(--raised);border-color:var(--border);color:var(--text);cursor:pointer}
.composer-chips{grid-area:chips;display:flex;align-items:center;gap:6px;min-width:0;overflow:hidden}
.composer-chip{display:inline-flex;align-items:center;gap:5px;max-width:240px;min-height:28px;height:28px;padding:2px 10px;border-radius:999px;border:1px solid var(--border);background:var(--raised);color:var(--muted);font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.composer-chip:hover:not(:disabled){color:var(--text)}
.composer-chip[data-state=granted]{color:var(--accent);border-color:var(--accent-line);background:var(--accent-soft)}
.composer-chip[data-state=warning]{color:var(--warning);border-color:#fbbf2466;background:var(--warning-soft)}
.composer-chip[data-state=busy]{color:var(--info);border-color:#60a5fa66;background:var(--info-soft)}
.composer-chip>span{overflow:hidden;text-overflow:ellipsis}
#composer>#sendButton,#composer>button.send-button{grid-area:send}
#composer>.stop-button{grid-area:stop}
#composer>button{min-height:32px;height:32px}
#composer>button.send-button{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600;padding:4px 14px}
#composer>button.send-button:hover:not(:disabled){background:var(--accent-hover);border-color:var(--accent-hover)}
#composer>.stop-button{background:transparent;color:var(--muted)}
#composer>.reconnect-button{grid-area:chips;justify-self:end}
.composer-hint{display:none}
.attachment-control{display:flex;align-items:center;gap:6px;position:relative}
.attachment-add{width:28px;height:28px;min-height:28px;padding:4px;border-radius:999px;background:transparent;border-color:var(--border)}
.attachment-menu{position:absolute;left:0;bottom:40px;width:300px;max-width:calc(100vw - 48px);padding:6px;border:1px solid var(--border-strong);border-radius:var(--radius-lg);background:var(--card);box-shadow:var(--shadow-pop);z-index:20}
.attachment-menu>p{color:var(--subtle);font-size:11px;letter-spacing:.08em;text-transform:uppercase;padding:6px 10px;margin:0}
.attachment-menu button{display:flex;flex-direction:column;align-items:flex-start;width:100%;padding:8px 10px;border:0;background:transparent;gap:2px;text-align:left}
.attachment-menu button:hover:not(:disabled){background:var(--hover)}
.attachment-menu strong{font-size:13px}.attachment-menu small{font-size:11px}
.attachment-chip{display:inline-flex;align-items:center;gap:4px;max-width:200px;border:1px solid var(--border);border-radius:999px;padding:1px 2px 1px 10px;font-size:12px;background:var(--raised)}
.attachment-chip>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.attachment-chip button{padding:0 6px;min-height:22px;height:22px;background:transparent;border:0;font-size:15px}

/* Per-send access popover anchored to the composer */
.access-popover{position:absolute;right:0;bottom:calc(100% + 8px);width:min(460px,calc(100vw - 32px));max-height:min(70dvh,560px);overflow:auto;padding:var(--space-3) var(--space-4);border:1px solid var(--border-strong);border-radius:var(--radius-lg);background:var(--card);box-shadow:var(--shadow-pop);z-index:30;font-size:13px}
.access-popover h3{font-size:13px;margin:0 0 var(--space-2)}
.access-popover label{display:flex;align-items:flex-start;gap:6px;margin:6px 0;font-size:13px}
.access-popover .popover-section{border-top:1px solid var(--border);padding-top:var(--space-2);margin-top:var(--space-2)}
.access-popover .popover-actions{display:flex;justify-content:space-between;align-items:center;gap:var(--space-2);margin-top:var(--space-3)}

.access-popover #pythonTools{border:0;padding:0}.access-popover #pythonTools>summary{display:none}
.access-popover #pythonTools>label{margin:4px 0}.access-popover #pythonTools p{margin:6px 0 2px}
.access-popover #inventoryRoot{margin:0 0 4px}
#reaDiagnostics{margin-top:var(--space-5)}

/* Empty state */
.workbench-empty{margin:auto;max-width:640px;text-align:center;padding:var(--space-6) var(--space-3);flex-shrink:0}
.empty-mark{display:grid;place-items:center;margin:0 auto var(--space-3);background:var(--accent-soft);color:var(--accent);width:40px;height:40px;border:1px solid var(--accent-line);border-radius:10px}
.empty-mark .ui-icon{width:22px;height:22px}
.workbench-empty h2{font-size:22px;margin-bottom:var(--space-2)}
.workbench-empty>p:not(.eyebrow){color:var(--muted);max-width:52ch;margin:0 auto var(--space-4);font-size:13px}
.workbench-empty .eyebrow{color:var(--accent)}
.starter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--space-2);margin-top:var(--space-5)}
.starter-card{display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;text-align:left;gap:4px;padding:var(--space-3);background:var(--surface);border-color:var(--border);border-radius:var(--radius-lg);min-height:0}
.starter-card:hover:not(:disabled){background:var(--raised);border-color:var(--border-strong)}
.starter-card>.ui-icon{color:var(--accent);width:18px;height:18px;margin-bottom:4px}
.starter-card strong{font-size:13px}.starter-card span{font-size:12px;line-height:1.5;color:var(--muted);font-weight:400}
.workbench-empty .empty-boundary{font-size:11px;margin-top:var(--space-4);color:var(--subtle)}

/* Host resource footer */
#sysfooter{padding:4px var(--space-4);flex-shrink:0;font-size:11px;color:var(--subtle);max-height:110px;overflow:auto;border-top:1px solid var(--border);background:var(--surface)}
.resource-details>summary{font-size:11px;padding:0;min-height:22px;color:var(--muted)}
.resource-grid{display:flex;gap:var(--space-4);align-items:center;flex-wrap:wrap}
.resource-grid>span{display:inline-flex;gap:6px;min-width:0;overflow-wrap:anywhere}
.resource-grid strong{color:var(--muted);font-weight:500}
.resource-grid button{padding:1px 8px;min-height:22px;font-size:11px;margin-left:auto;background:transparent;border-color:transparent;color:var(--muted)}

/* Notices */
#skillNotice{display:flex;align-items:center;gap:var(--space-2);flex-wrap:wrap;padding:6px var(--space-4);border-bottom:1px solid #fbbf2433;color:var(--warning);background:var(--warning-soft);font-size:12px}
#skillNoticeText{flex:1;min-width:130px}
#skillNotice button{margin:0;background:transparent;min-height:26px;font-size:12px;border-color:#fbbf2466;color:var(--warning)}
.notifications{position:fixed;z-index:100;bottom:20px;right:20px;width:min(420px,calc(100vw - 32px))}
.notification{display:flex;align-items:flex-start;gap:var(--space-3);border:1px solid #f8717166;border-radius:var(--radius-lg);padding:var(--space-3);background:#2a1620;box-shadow:var(--shadow-pop);font-size:13px}
.notification>span{flex:1;overflow-wrap:anywhere}.notification>button{border:0;background:transparent;padding:2px;min-height:24px}

/* Settings: modal with grouped navigation */
.settings-screen{width:min(1240px,96vw);height:min(860px,92dvh);max-width:none;max-height:none;padding:0;background:var(--surface);color:var(--text);border:1px solid var(--border-strong);border-radius:var(--radius-lg);overflow:hidden;box-shadow:0 24px 80px #000c}
dialog::backdrop{background:#020617b8;backdrop-filter:blur(3px)}
.settings-header{height:60px;display:flex;align-items:center;gap:var(--space-4);padding:0 var(--space-4) 0 var(--space-5);border-bottom:1px solid var(--border)}
.settings-header>div{min-width:0;display:flex;align-items:baseline;gap:var(--space-3)}
.settings-header .eyebrow{display:none}
.settings-header h2{font-size:16px;margin:0}
.settings-current{font-size:12px;color:var(--muted);margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.settings-search{margin-left:auto;width:260px}
.settings-header button{flex-shrink:0;font-size:12px}
#rightbar{display:grid;grid-template-columns:232px minmax(0,1fr);height:calc(100% - 60px);min-height:0}
.settings-nav{background:var(--bg);padding:var(--space-3) var(--space-2);overflow:auto;border-right:1px solid var(--border)}
.settings-nav-group{margin-bottom:var(--space-4)}
.settings-nav-group h3{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--subtle);margin:var(--space-2) var(--space-3) var(--space-1);font-weight:600}
.settings-nav-group[data-group=Debugging] h3{color:var(--warning)}
.settings-nav .navbtn{display:flex;justify-content:flex-start;width:100%;text-align:left;border:1px solid transparent;background:transparent;padding:5px 10px;border-radius:var(--radius-sm);font-size:13px;min-height:30px;color:var(--muted);margin:1px 0;font-weight:500}
.settings-nav .navbtn:hover:not(:disabled){background:var(--hover);color:var(--text);border-color:transparent}
.settings-nav .navbtn.active{background:var(--active);color:var(--text-strong);border-color:transparent;box-shadow:inset 2px 0 0 var(--accent)}
.settings-no-results{color:var(--muted);font-size:12px;padding:0 10px}
.settings-content{overflow:auto;padding:var(--space-5) var(--space-6);min-width:0}
.settings-content>.panel{display:none;margin:0;padding:0;border:0;background:transparent;max-width:880px}
.settings-content>.panel.active{display:block}
.settings-content p{font-size:13px;max-width:80ch;line-height:1.6;color:var(--muted)}
.settings-content h2{font-size:18px}.settings-content h3{font-size:16px}.settings-content h4{font-size:14px;margin-top:var(--space-5)}
.settings-content label{font-size:13px}
.settings-content button{margin:4px 6px 4px 0}
.settings-content input:not([type=checkbox]),.settings-content textarea{max-width:100%}
.settings-content pre{border:1px solid var(--border);background:var(--bg);padding:var(--space-3);border-radius:var(--radius);max-height:360px;color:var(--muted)}
.settings-content .ext{display:flex;align-items:center;justify-content:space-between;gap:var(--space-4);padding:var(--space-3) 0;border-bottom:1px solid var(--border)}
.settings-content .ext p{margin:2px 0 0;color:var(--muted);font-size:12px}
.runtime-field{display:grid;grid-template-columns:minmax(160px,240px) minmax(0,220px);align-items:center;gap:var(--space-3);margin:var(--space-2) 0}
.runtime-field input[type=number]{width:100%}
.settings-section-picker{display:none}
.section-heading p{color:var(--muted);margin-bottom:var(--space-4)}
#pythonTools{border:1px solid var(--border);border-radius:var(--radius);padding:var(--space-3) var(--space-4)}
#pythonTools>summary{font-size:13px;margin-bottom:var(--space-2)}
#pythonTools>label{display:flex;align-items:flex-start;gap:6px;margin:6px 0}
#pythonTools>br{display:none}
#inventoryRoot{width:100%!important;margin-bottom:var(--space-2)}
#pythonTools p{font-size:12px;color:var(--muted)}
#openCodeTaskAccess{padding:var(--space-3) var(--space-4);border:1px solid var(--border);border-radius:var(--radius)}
#openCodeTaskAccess>label{display:block;margin:var(--space-2) 0}
.effective-task-context{padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg);color:var(--muted);font-size:12px;font-family:var(--font-mono)}

/* Tables (skills, locations, components) */
.skills-toolbar,.locations-toolbar{display:flex;gap:6px;align-items:center;flex-wrap:wrap;position:sticky;top:calc(-1*var(--space-5));padding:var(--space-2) 0;background:var(--surface);z-index:3;margin-bottom:var(--space-1)}
.skills-toolbar input,.locations-toolbar input{margin-left:auto;min-width:180px;flex:1;max-width:260px}
.skills-toolbar button:first-child{color:var(--accent);border-color:var(--accent-line);background:var(--accent-soft)}
.skills-notice,.locations-status,.locations-note,.skills-taskbar{color:var(--muted);font-size:12px}
.skills-table-wrap,.locations-table-wrap,.component-table-wrap{border:1px solid var(--border);border-radius:var(--radius);overflow:auto;margin:var(--space-3) 0}
.skills-table,.locations-table,.component-table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}
.skills-table th,.locations-table th,.component-table th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;background:var(--raised);color:var(--muted);text-align:left;padding:8px 10px;white-space:nowrap;font-weight:600}
.skills-table td,.locations-table td,.component-table td{padding:8px 10px;border-top:1px solid var(--border);vertical-align:middle}
.skills-table tr:hover td,.locations-table tr:hover td{background:var(--raised)}
.skills-table th:first-child,.skills-table td:first-child,.locations-table td:first-child{width:40px}
.skills-table .skill-name,.locations-table .location-name{display:block;font-weight:600;background:transparent;border:0;padding:0;text-align:left;color:var(--text);min-height:24px;font-size:13px}
.skills-table td>small,.locations-table td>small{display:block;font-size:11px;margin-top:2px}
.skill-description{max-width:330px;color:var(--muted);line-height:1.5}
.status-badge{display:inline-flex;align-items:center;gap:5px;padding:1px 7px;font-size:11px;line-height:1.6;border-radius:999px;background:var(--raised);color:var(--muted);border:1px solid var(--border);white-space:normal}
.status-badge:before{content:'';width:5px;height:5px;border-radius:50%;background:currentColor;flex-shrink:0}
.status-badge.good{color:var(--accent);background:var(--accent-soft);border-color:transparent}
.status-badge.warn{color:var(--warning);background:var(--warning-soft);border-color:transparent}
.status-badge.bad{color:var(--danger);background:var(--danger-soft);border-color:transparent}
.status-badge.accent{color:var(--info);background:var(--info-soft);border-color:transparent}
.skill-group td{background:var(--raised)!important}
.collection-toggle{background:transparent;border:0;padding:2px 0;justify-content:flex-start;font-size:13px}
.collection-count{color:var(--muted);font-size:11px;margin-left:6px}
.skills-taskbar{display:flex;gap:var(--space-4);flex-wrap:wrap;align-items:center;padding:var(--space-3) 0;border-top:1px solid var(--border)}
.skills-taskbar label{display:flex;align-items:center;gap:6px}
.skill-detail{padding:var(--space-3);background:var(--bg);border-bottom:1px solid var(--border)}.skill-detail p{font-size:12px}.skill-detail pre{max-height:320px}
.locations-state{display:flex;align-items:center;gap:var(--space-3);flex-wrap:wrap;font-size:12px;color:var(--muted)}
.location-path{font-family:var(--font-mono);font-size:12px;min-width:180px;max-width:320px;overflow-wrap:anywhere;word-break:break-word;color:var(--muted)}
.location-operations{font-size:12px;color:var(--muted);min-width:90px}
.component-toolbar,.component-actions{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.component-toolbar{margin:var(--space-4) 0}
.component-table{min-width:760px}.component-table caption{text-align:left;padding:10px;color:var(--muted);font-size:12px}
.component-table tbody th{width:19%;font-size:13px;text-transform:none;letter-spacing:0;background:transparent;color:var(--text);vertical-align:top}
.component-table td{vertical-align:top}.component-table td:nth-child(3){width:33%}
.component-table small{display:block;line-height:1.5;margin-top:4px;font-weight:400}
.component-actions button{min-height:28px;padding:3px 9px;font-size:12px}
.component-state{display:inline-block;padding:1px 8px;border-radius:999px;background:var(--warning-soft);color:var(--warning);font-size:11px;text-transform:capitalize}
.component-state-running,.component-state-loaded,.component-state-ready,.component-state-on_demand,.component-state-available{background:var(--accent-soft);color:var(--accent)}
.component-state-missing,.component-state-unavailable,.component-state-blocked{background:var(--danger-soft);color:var(--danger)}

/* Dialogs */
.import-dialog,.chat-dialog,.location-dialog,.folder-dialog{background:var(--surface);color:var(--text);border:1px solid var(--border-strong);border-radius:var(--radius-lg);padding:var(--space-5);max-width:min(94vw,780px);max-height:90dvh;overflow:auto;box-shadow:0 24px 80px #000c}
.chat-dialog{width:440px}
.chat-dialog label,.location-dialog>label{display:block;font-size:13px;margin:var(--space-3) 0}
.chat-dialog input,.import-dialog>input,.location-dialog>label>input{display:block;width:100%;margin-top:6px}
.dialog-actions{display:flex;justify-content:flex-end;gap:var(--space-2);flex-wrap:wrap;margin-top:var(--space-5);padding-top:var(--space-3);border-top:1px solid var(--border)}
.dialog-error{color:var(--danger);font-size:13px}
.import-dialog pre{max-height:300px}
.import-candidates{border:1px solid var(--border);padding:var(--space-2);border-radius:var(--radius);max-height:280px;overflow:auto}.import-candidates label{display:block;margin:6px}
.import-dialog .dialog-actions button:last-child{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.location-path-editor{display:flex;gap:var(--space-2);margin-top:6px}.location-path-editor input{flex:1;min-width:0}
.location-editor-flags{display:flex;gap:var(--space-5);flex-wrap:wrap;padding:var(--space-3) 0}
.location-operation-choices{border:1px solid var(--border);border-radius:var(--radius);display:flex;gap:var(--space-4);flex-wrap:wrap;padding:var(--space-3)}
.location-operation-choices legend{font-size:11px;color:var(--muted);padding:0 6px}
.location-advanced{margin:var(--space-4) 0}.location-advanced p{font-size:12px;color:var(--muted)}.location-advanced textarea{width:100%}
.folder-dialog{width:820px}.folder-dialog p{font-size:12px;color:var(--muted)}
.folder-address{display:flex;gap:var(--space-2);margin:var(--space-3) 0}.folder-address input{flex:1;min-width:0}
.folder-breadcrumbs{display:flex;flex-wrap:wrap;align-items:center;gap:2px;margin:var(--space-2) 0}
.folder-breadcrumbs button{background:transparent;border:0;padding:2px 6px;font-size:12px;min-height:24px}
.folder-breadcrumbs button+button:before{content:'/';color:var(--subtle);margin-right:6px}
.folder-layout{display:grid;grid-template-columns:160px minmax(0,1fr);gap:var(--space-3);min-height:220px}
.folder-shortcuts{display:flex;flex-direction:column;gap:4px}
.folder-shortcuts button{justify-content:flex-start;text-align:left;font-size:12px;background:transparent;overflow-wrap:anywhere}
.folder-list{border:1px solid var(--border);border-radius:var(--radius);max-height:300px;overflow:auto;min-height:200px;background:var(--bg)}
.folder-entry{display:flex;align-items:center;justify-content:flex-start;gap:var(--space-2);width:100%;border:0;border-bottom:1px solid var(--border);border-radius:0;background:transparent;padding:8px 10px;text-align:left;font-size:13px}
.folder-entry>span:nth-child(2){flex:1;overflow-wrap:anywhere}
.folder-icon,.folder-chevron{color:var(--accent)}
.folder-empty{padding:var(--space-4)}
.folder-filters{display:flex;align-items:center;gap:var(--space-3);margin:var(--space-3) 0}.folder-filters input[type=search]{flex:1;min-width:0}
.folder-hidden{font-size:12px;display:flex;align-items:center;gap:5px}
.folder-dialog>[role=status]{min-height:22px}

/* Tool receipts, file activity, model cards inside the conversation */
.execution-cards{align-self:stretch;margin:0;padding:var(--space-3) var(--space-4);border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface)}
.execution-cards h3{font-size:13px;color:var(--accent)}.execution-cards p{font-size:12px;color:var(--muted)}
.execution-card{padding:var(--space-3);border:1px solid var(--border);border-radius:var(--radius);margin:var(--space-2) 0;background:var(--bg)}
.execution-error{border-color:#f8717166;background:var(--danger-soft)}.execution-warning{border-color:#fbbf2466;background:var(--warning-soft)}
.execution-path{font-family:var(--font-mono);font-size:11px;overflow-wrap:anywhere;color:var(--muted)}
.execution-card pre{max-height:320px;font-size:11px}
.file-activity{width:100%;padding:var(--space-3) var(--space-4);border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface)}
.file-activity h3{font-size:14px}.file-activity-note{font-size:12px;color:var(--muted)}
.file-activity-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:var(--space-3)}
.file-work-card{border:1px solid var(--border);border-radius:var(--radius);padding:var(--space-3);background:var(--bg);min-width:0}
.file-work-card h4{font-size:13px;overflow-wrap:anywhere;font-family:var(--font-mono)}
.file-work-status{font-size:11px;color:var(--muted)}
.file-work-card[data-state=saved]{border-color:var(--accent-line)}.file-work-card[data-state=error]{border-color:#f8717166}
.file-work-card summary{font-size:12px}
.file-original-code,.file-work-card details pre{max-height:240px;font-size:11px;background:#080d18;padding:10px;border-radius:var(--radius-sm)}
.file-code-label{display:block;font-size:12px;margin-top:var(--space-3)}.file-code-label span{display:block;color:var(--muted);font-size:11px}
.file-updated-code{width:100%;min-height:200px;background:#080d18!important;font:12px/1.6 var(--font-mono);white-space:pre;overflow:auto}
.file-work-error{color:var(--danger)}
.message:has(.model-card){width:100%;max-width:100%}
.model-card{margin:var(--space-2) 0 0;border:1px solid var(--border);border-radius:var(--radius-lg);padding:var(--space-4);background:var(--surface);min-width:0}
.model-card h3{font-size:14px}.model-card p{font-size:12px;color:var(--muted)}.model-card pre{max-height:260px}
.model-stage{width:100%;margin:var(--space-3) 0;border-radius:var(--radius);overflow:hidden;background:var(--raised)}.model-stage:empty{display:none}
.model-stage model-viewer{display:block;width:100%;height:400px;max-height:50dvh;background:var(--raised)}
.model-actions{display:flex;flex-wrap:wrap;gap:6px;margin:var(--space-3) 0}.model-actions button{font-size:12px}
.animation-panel{padding-top:var(--space-3);margin-top:var(--space-3);border-top:1px solid var(--border);display:flex;gap:var(--space-2);align-items:center;flex-wrap:wrap}
.animation-panel h4,.animation-panel>p{flex-basis:100%;margin:0}
.animation-panel select,.animation-panel input:not([type=range]){min-width:160px;flex:1}
.animation-panel input[type=range]{flex-basis:60%}.animation-panel span{font-size:12px;color:var(--muted)}.animation-panel button{font-size:12px}

/* First-run bootstrap */
#bootstrap{max-width:560px;width:calc(100% - 32px);margin:12vh auto;padding:var(--space-6);background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:auto}
#bootstrap h2{font-size:18px}#bootstrap input{width:100%;margin:6px 0 var(--space-3)}
#bootstrap #dbselect{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
#bootstrap #dbstatus{font-size:11px;color:var(--subtle);max-height:200px}
#error{color:var(--danger)}

@media(max-width:1100px){
 #shell{grid-template-columns:224px minmax(0,1fr)}.starter-grid{gap:6px}.settings-search{width:200px}.settings-content{padding:var(--space-4)}
 #rightbar{grid-template-columns:200px minmax(0,1fr)}
 .skills-toolbar input,.locations-toolbar input{max-width:none;flex-basis:100%;margin:6px 0 0}
}
@media(max-width:800px){
 .appbar{padding:0 var(--space-3);gap:var(--space-2)}.app-brand>.ui-icon{display:none}.app-subtitle{display:none}.runtime-chip{max-width:55%}
 .history-toggle{display:inline-flex;width:34px;padding:6px;background:transparent;border-color:transparent}
 .history-scrim{position:absolute;inset:0;z-index:8;background:#020617b8;border:0;border-radius:0;padding:0}
 #shell{display:block}
 #leftbar{position:absolute;left:0;top:0;bottom:0;width:min(300px,86%);z-index:9;display:none;box-shadow:12px 0 44px #000a}
 #shell.history-open #leftbar{display:flex}#shell.history-open .history-scrim{display:block}
 #workspace{height:100%}
 .workspace-toolbar{padding:6px var(--space-3)}#taskAccessSummary{flex-basis:100%;order:3}
 .conversation-heading{padding:var(--space-3) var(--space-3) 0}
 #chatlog{padding:var(--space-3);gap:var(--space-4)}
 .message-user{max-width:92%}
 .task-status{padding:4px var(--space-3) 0}
 #composer{width:calc(100% - 2*var(--space-3));margin:4px auto var(--space-3);grid-template-columns:auto minmax(0,1fr) auto auto;grid-template-areas:"input input input input" "attach engine stop send" "chips chips chips chips"}
 .composer-chips{flex-wrap:wrap}
 .starter-grid{grid-template-columns:1fr}
 .settings-screen{width:100vw;height:100dvh;border:0;border-radius:0}
 .settings-header{height:auto;min-height:56px;padding:var(--space-2) var(--space-3);flex-wrap:wrap;gap:var(--space-2)}
 .settings-search{order:3;width:100%;margin:0}
 #rightbar{display:flex;flex-direction:column;height:calc(100% - 104px)}
 .settings-nav{display:none}.settings-section-picker{display:block;width:calc(100% - 32px);margin:var(--space-3) var(--space-4) 0;flex-shrink:0}
 .settings-content{padding:var(--space-4);flex:1}
 .runtime-field{grid-template-columns:1fr}
 .settings-content input:not([type=checkbox]),.settings-content select,.settings-content textarea{font-size:16px}
 .locations-table,.skills-table{min-width:660px}
 .location-dialog,.folder-dialog,.chat-dialog,.import-dialog{padding:var(--space-4);max-width:96vw;max-height:94dvh}
 .folder-layout{grid-template-columns:1fr}.folder-shortcuts{flex-direction:row;flex-wrap:wrap}
}
@media(pointer:coarse){
 button,.composer-chip,.composer-engine select{min-height:44px}
 .chat-action,.copy-button{opacity:1;min-width:36px;min-height:36px}
 #composer>button,.attachment-add{min-height:44px;height:44px}
 input[type=checkbox],input[type=radio]{width:22px;height:22px}
}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
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
<label style="display:block"><input id="opencodeAgentApprove" type="checkbox"> Allow OpenCode for this dashboard session: a confined, no-network container with read-only code and only the tools approved here. Native shell, delegation and external MCP stay denied.</label>
<label style="display:block"><input id="keepTaskAccess" type="checkbox"> Keep these tool permissions for following sends until you untick this or reload the page.</label>
<p>Selecting OpenCode enables its runtime and built-in MCP transport. The saved engine starts automatically with the GUI after session and database checks. The connection check is optional diagnostics. Configure the OpenCode image once in Confined execution. Selected skills and approved built-in MCP tools are forwarded; images and external MCP servers are unsupported.</p>
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
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; font-src 'self'; connect-src 'self' blob: data:; img-src 'self' blob: data:; worker-src 'self' blob:")
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
        # Remove the persistent OpenCode container with the dashboard.
        import opencode_pool
        opencode_pool.stop(force=True)
        server.server_close()

if __name__ == "__main__":
    main()
