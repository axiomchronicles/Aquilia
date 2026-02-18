"""
Aquilia Debug Pages — Tubox Themed (Premium).

Self-contained HTML/CSS/JS generators. No external dependencies.
All assets are inlined for zero-config rendering. Emojis strictly forbidden.
"""

from __future__ import annotations

import html
import linecache
import os
import sys
import traceback
from typing import Any, Dict, List, Tuple

# ============================================================================
# CSS Styles — Tubox Premium Theme (Dark & Light)
# ============================================================================

_BASE_CSS = r"""
:root {
  /* Dark Theme (Default) */
  --tx-bg: #000000;
  --tx-bg-alt: #0a0a0a;
  --tx-surface: rgba(10, 10, 10, 0.8);
  --tx-border: #222;
  --tx-border-highlight: rgba(34, 197, 94, 0.2);
  
  --tx-text: #ededed;
  --tx-text-muted: #888;
  --tx-text-dim: #444;
  
  --tx-accent: #22c55e;        /* Green-500 */
  --tx-accent-glow: rgba(34, 197, 94, 0.15);
  --tx-accent-dim: #15803d;    /* Green-700 */
  
  --tx-error: #ef4444;
  --tx-error-glow: rgba(239, 68, 68, 0.15);
  --tx-warning: #f59e0b;
  --tx-info: #3b82f6;
  
  /* Syntax Highlighting */
  --sh-keyword: #c084fc;       /* Purple-400 */
  --sh-string: #22c55e;        /* Green-500 */
  --sh-comment: #52525b;       /* Zinc-600 */
  --sh-number: #f59e0b;        /* Amber-500 */
  --sh-func: #60a5fa;          /* Blue-400 */
}

/* Light Mode Overrides */
body.light {
  --tx-bg: #ffffff;
  --tx-bg-alt: #fafafa;
  --tx-surface: rgba(255, 255, 255, 0.9);
  --tx-border: #e2e2e2;
  --tx-border-highlight: rgba(34, 197, 94, 0.3);
  
  --tx-text: #171717;
  --tx-text-muted: #737373;
  --tx-text-dim: #d4d4d4;
  
  --tx-accent: #16a34a;        /* Green-600 */
  --tx-accent-glow: rgba(22, 163, 74, 0.1);
  --tx-accent-dim: #15803d;
  
  --tx-error: #dc2626;
  --tx-error-glow: rgba(220, 38, 38, 0.08); 
  --tx-warning: #d97706;
  --tx-info: #2563eb;
  
  /* Syntax Highlighting Light */
  --sh-keyword: #7e22ce;       /* Purple-700 */
  --sh-string: #15803d;        /* Green-700 */
  --sh-comment: #a3a3a3;       /* Neutral-400 */
  --sh-number: #b45309;        /* Amber-700 */
  --sh-func: #1d4ed8;          /* Blue-700 */
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background-color: var(--tx-bg);
  color: var(--tx-text);
  line-height: 1.5;
  overflow-x: hidden;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: background-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), color 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  -webkit-font-smoothing: antialiased;
}

/* Background Grid Effect */
.bg-grid {
  position: fixed;
  inset: 0;
  z-index: -1;
  opacity: 0.2;
  background-image: 
    linear-gradient(var(--tx-border) 1px, transparent 1px),
    linear-gradient(90deg, var(--tx-border) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(circle at center, black 40%, transparent 100%);
  pointer-events: none;
}

.bg-glow {
  position: fixed;
  inset: 0;
  z-index: -1;
  background: radial-gradient(circle at 50% 0%, var(--tx-accent-glow) 0%, transparent 70%);
  pointer-events: none;
  opacity: 0.6;
}

/* Animations from temp/landing.html */
@keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-20px); } }
@keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes pulse-glow { 0%, 100% { opacity: 0.5; transform: scale(1); } 50% { opacity: 0.8; transform: scale(1.05); } }
@keyframes spin-gyro-1 { from { transform: rotate3d(1, 1, 1, 0deg); } to { transform: rotate3d(1, 1, 1, 360deg); } }
@keyframes spin-gyro-2 { from { transform: rotate3d(1, -1, 0, 0deg); } to { transform: rotate3d(1, -1, 0, 360deg); } }
@keyframes spin-gyro-3 { from { transform: rotate3d(0, 1, -1, 0deg); } to { transform: rotate3d(0, 1, -1, 360deg); } }
@keyframes float-majestic { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-15px); } }
@keyframes pulse-breathing { 0%, 100% { opacity: 0.3; filter: blur(20px); } 50% { opacity: 0.6; filter: blur(25px); } }
@keyframes drift { 0% { transform: translate(0, 0); } 50% { transform: translate(10px, -10px); } 100% { transform: translate(0, 0); } }

.animate-float { animation: float 6s ease-in-out infinite; }
.animate-spin-slow { animation: spin-slow 20s linear infinite; }
.animate-pulse-glow { animation: pulse-glow 4s ease-in-out infinite; }
.animate-gyro-1 { animation: spin-gyro-1 60s linear infinite; }
.animate-gyro-2 { animation: spin-gyro-2 45s linear infinite; }
.animate-gyro-3 { animation: spin-gyro-3 50s linear infinite; }
.animate-float-majestic { animation: float-majestic 10s ease-in-out infinite; }
.animate-breathing { animation: pulse-breathing 8s ease-in-out infinite; }
.animate-drift { animation: drift 20s ease-in-out infinite; }

/* Typography */
h1, h2, h3, h4, h5, h6 { font-weight: 600; color: var(--tx-text); letter-spacing: -0.02em; }
code, pre { font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; font-size: 13px; }
a { color: inherit; text-decoration: none; transition: width 0.2s; }

/* Layout */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  width: 100%;
}

/* Icons */
.icon {
  width: 16px; height: 16px;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
  flex-shrink: 0;
}
.icon-lg { width: 24px; height: 24px; }
.icon-xl { width: 48px; height: 48px; stroke-width: 1.5; }

/* Components */
.glass {
  background: var(--tx-surface);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--tx-border);
}

.card {
  background: var(--tx-bg-alt);
  border: 1px solid var(--tx-border);
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.card:hover { border-color: var(--tx-border); }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  line-height: 1;
}
.badge.green { background: rgba(34, 197, 94, 0.1); color: var(--tx-accent); border: 1px solid rgba(34, 197, 94, 0.2); }
.badge.red { background: rgba(239, 68, 68, 0.1); color: var(--tx-error); border: 1px solid rgba(239, 68, 68, 0.2); }
.badge.blue { background: rgba(59, 130, 246, 0.1); color: var(--tx-info); border: 1px solid rgba(59, 130, 246, 0.2); }
.badge.gray { background: rgba(128, 128, 128, 0.1); color: var(--tx-text-muted); border: 1px solid var(--tx-border); }

/* Header */
.header {
  height: 64px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 50;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 700;
  font-size: 16px;
  color: var(--tx-text);
  letter-spacing: -0.01em;
}

/* Theme Toggle */
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: var(--tx-text-muted);
  cursor: pointer;
  transition: all 0.2s;
}
.theme-toggle:hover {
  background: var(--tx-bg-alt);
  color: var(--tx-text);
}

/* Exception Page Specifics */
.exc-header {
  padding: 48px 0;
  border-bottom: 1px solid var(--tx-border);
}

.exc-title {
  font-size: 28px;
  color: var(--tx-text);
  margin-top: 16px;
  margin-bottom: 16px;
  line-height: 1.2;
}
.exc-msg {
  font-size: 14px;
  color: var(--tx-text-muted);
  font-family: inherit;
  background: var(--tx-bg-alt);
  border: 1px solid var(--tx-border);
  padding: 16px;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 4px;
  margin-top: 32px;
  border-bottom: 1px solid var(--tx-border);
}
.tab {
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--tx-text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}
.tab:hover { color: var(--tx-text); }
.tab.active { color: var(--tx-text); border-bottom-color: var(--tx-accent); }

.tab-panel { display: none; padding: 24px 0; }
.tab-panel.active { display: block; animation: fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }

@keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* Stack Frames */
.frame-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--tx-border);
  border-radius: 8px;
  overflow: hidden;
}
.frame {
  background: var(--tx-bg-alt);
  border-bottom: 1px solid var(--tx-border);
  transition: background 0.15s;
}
.frame:last-child { border-bottom: none; }
.frame.app-code { background: rgba(34, 197, 94, 0.03); }
.frame-header {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 48px;
}
.frame-header:hover { background: rgba(128,128,128,0.05); }

.frame-info { display: flex; flex-direction: column; gap: 2px; }
.frame-func { font-family: monospace; font-size: 13px; color: var(--tx-text); font-weight: 600; }
.frame-file { font-size: 12px; color: var(--tx-text-muted); display: flex; align-items: center; gap: 6px; }

.frame-meta { display: flex; align-items: center; gap: 12px; font-size: 12px; color: var(--tx-text-muted); }
.frame-chevron { transition: transform 0.2s; color: var(--tx-text-muted); }

.frame-body { display: none; border-top: 1px solid var(--tx-border); }
.frame.active .frame-body { display: block; }
.frame.active .frame-chevron { transform: rotate(180deg); color: var(--tx-text); }
.frame.active { background: var(--tx-bg-alt); } /* Reset background when active */

/* Code Viewer */
.code-block {
  background: var(--tx-bg);
  padding: 16px 0;
  overflow-x: auto;
}
.code-line {
  display: flex;
  padding: 0 16px;
  line-height: 1.6;
}
.code-line.active { background: var(--tx-error-glow); border-left: 2px solid var(--tx-error); padding-left: 14px; }
.line-num {
  width: 40px;
  color: var(--tx-text-dim);
  text-align: right;
  padding-right: 16px;
  user-select: none;
  flex-shrink: 0;
  font-size: 12px;
}
.line-content { white-space: pre; color: var(--tx-text); font-size: 13px; }

/* Locals */
.locals {
  background: var(--tx-surface);
  border-top: 1px solid var(--tx-border);
  padding: 0;
}
.locals-header {
  padding: 8px 16px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--tx-text-muted);
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid var(--tx-border);
}
.local-row {
  display: flex;
  font-family: monospace;
  font-size: 12px;
  border-bottom: 1px solid var(--tx-border);
}
.local-row:last-child { border-bottom: none; }
.local-key { 
  width: 180px; 
  padding: 8px 16px; 
  color: var(--tx-info); 
  border-right: 1px solid var(--tx-border);
  flex-shrink: 0;
  background: rgba(0,0,0,0.1);
}
.local-val { 
  padding: 8px 16px; 
  color: var(--tx-text-muted); 
  white-space: pre-wrap; 
  word-break: break-all; 
  flex: 1;
}

/* Copy Button */
.copy-btn {
  background: transparent;
  border: 1px solid var(--tx-border);
  color: var(--tx-text-muted);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
.copy-btn:hover { background: var(--tx-bg); color: var(--tx-text); border-color: var(--tx-text-muted); }

/* HTTP Error Page */
.http-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.http-container {
  max-width: 500px;
  width: 100%;
  text-align: center;
}
.http-icon-bg {
  width: 80px; height: 80px;
  background: var(--tx-bg-alt);
  border: 1px solid var(--tx-border);
  border-radius: 20px;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 32px;
  color: var(--tx-accent);
}
.http-title { font-size: 24px; margin-bottom: 12px; font-weight: 700; }
.http-desc { color: var(--tx-text-muted); margin-bottom: 32px; font-size: 15px; }

/* Welcome Page (Updated for exact match) */
.welcome-hero {
  padding: 60px 0 60px;
  text-align: left;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  align-items: center;
}
.welcome-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
    color: var(--tx-accent); 
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 24px;
}
.welcome-title {
  font-size: 48px;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 24px;
  line-height: 1.1;
  color: var(--tx-text);
}
.welcome-subtitle {
  font-size: 18px;
  color: var(--tx-text-muted);
  max-width: 580px;
  margin-bottom: 40px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  padding: 40px 0;
}
.feature-card {
  padding: 24px;
  background: var(--tx-bg-alt);
  border: 1px solid var(--tx-border);
  border-radius: 12px;
  transition: border-color 0.2s, transform 0.2s;
}
.feature-card:hover { border-color: var(--tx-border-highlight); transform: translateY(-2px); }
.feature-icon {
  width: 40px; height: 40px;
  background: var(--tx-surface);
  border: 1px solid var(--tx-border);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 16px;
  color: var(--tx-text);
}

.cmd-block {
    background: var(--tx-bg-alt);
    border: 1px solid var(--tx-border);
    border-radius: 8px;
    padding: 20px;
    font-family: monospace;
    font-size: 13px;
    color: var(--tx-text-muted);
    text-align: left;
    max-width: 500px;
    margin-top: 20px;
}

/* Button primary */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  padding: 0 24px;
  background: var(--tx-text);
  color: var(--tx-bg);
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
}
.btn-primary:hover { opacity: 0.9; }

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  padding: 0 24px;
  background: var(--tx-bg-alt);
  color: var(--tx-text);
  border: 1px solid var(--tx-border);
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
}
.btn-secondary:hover { background: var(--tx-surface); border-color: var(--tx-text-muted); }

/* Zen Gyroscope Simulation */
.zen-gyro {
    position: relative;
    width: 100%;
    aspect-ratio: 1/1;
    display: flex;
    align-items: center;
    justify-content: center;
}
"""

_BASE_JS = r"""
(function() {
  // Theme Toggle
  const themeBtn = document.getElementById('theme-toggle');
  const iconMoon = document.getElementById('icon-moon');
  const iconSun = document.getElementById('icon-sun');
  
  function updateThemeIcon(isLight) {
    if (isLight) {
        iconMoon.style.display = 'none';
        iconSun.style.display = 'block';
    } else {
        iconMoon.style.display = 'block';
        iconSun.style.display = 'none';
    }
  }

  window.toggleTheme = function() {
    document.body.classList.toggle('light');
    const isLight = document.body.classList.contains('light');
    localStorage.setItem('aq-theme', isLight ? 'light' : 'dark');
    updateThemeIcon(isLight);
  };
  
  // Init Theme
  const saved = localStorage.getItem('aq-theme');
  if (saved === 'light') {
    document.body.classList.add('light');
    updateThemeIcon(true);
  } else {
    updateThemeIcon(false);
  }

  // Tab switching
  window.switchTab = function(tabId) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(`panel-${tabId}`).classList.add('active');
  };

  // Frame toggling
  window.toggleFrame = function(el) {
    el.classList.toggle('active');
  };
  
  // Consume click events on children to prevent toggling when copying or clicking links inside frame header
  window.stopProp = function(e) {
    e.stopPropagation();
  };

  // Copy functionality
  window.copyText = function(btnId, elementId) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
      const btn = document.getElementById(btnId);
      const originalText = btn.querySelector('span').innerText;
      btn.querySelector('span').innerText = 'Copied!';
      setTimeout(() => {
        btn.querySelector('span').innerText = originalText;
      }, 2000);
    });
  };
})();
"""

# ============================================================================
# Utilities
# ============================================================================

def _esc(text: Any) -> str:
    return html.escape(str(text), quote=True)

def _read_source_lines(filename: str, lineno: int, context: int = 7) -> List[Tuple[int, str, bool]]:
    lines: List[Tuple[int, str, bool]] = []
    start = max(1, lineno - context)
    end = lineno + context + 1
    for i in range(start, end):
        line = linecache.getline(filename, i)
        if line:
            lines.append((i, line.rstrip('\n'), i == lineno))
        elif i <= lineno:
            continue
    return lines

def _syntax_highlight_line(code: str) -> str:
    import re
    escaped = _esc(code)
    # Keywords
    escaped = re.sub(
        r'\b(def|class|import|from|return|if|elif|else|for|while|try|except|'
        r'finally|with|as|raise|yield|async|await|pass|break|continue|'
        r'and|or|not|in|is|lambda|None|True|False|self)\b',
        r'<span style="color:var(--sh-keyword)">\1</span>', escaped
    )
    # Strings
    escaped = re.sub(
        r'(&quot;.*?&quot;|&#x27;.*?&#x27;)',
        r'<span style="color:var(--sh-string)">\1</span>', escaped
    )
    # Comments
    escaped = re.sub(r'(#.*)$', r'<span style="color:var(--sh-comment)">\1</span>', escaped)
    # Numbers
    escaped = re.sub(r'\b(\d+)\b', r'<span style="color:var(--sh-number)">\1</span>', escaped)
    
    return escaped

def _format_code_block(lines: List[Tuple[int, str, bool]]) -> str:
    if not lines:
        return '<div class="code-block" style="padding:16px;color:var(--tx-text-muted);text-align:center;">Source not available</div>'
        
    parts = ['<div class="code-block">']
    for lineno, code, is_active in lines:
        cls = "code-line active" if is_active else "code-line"
        parts.append(
            f'<div class="{cls}">'
            f'<div class="line-num">{lineno}</div>'
            f'<div class="line-content">{_syntax_highlight_line(code)}</div>'
            f'</div>'
        )
    parts.append('</div>')
    return '\n'.join(parts)

def _extract_frames(exc: BaseException) -> List[Dict[str, Any]]:
    frames = []
    tb = exc.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        lineno = tb.tb_lineno
        filename = frame.f_code.co_filename
        
        source = _read_source_lines(filename, lineno)
        locals_dict = {k: v for k, v in frame.f_locals.items() if not (k.startswith('__') and k.endswith('__'))} if frame.f_locals else {}
        
        try:
            cwd = os.getcwd()
            short_path = os.path.relpath(filename, cwd) if filename.startswith(cwd) else filename
        except:
            short_path = filename
            
        frames.append({
            'filename': filename,
            'short_filename': short_path,
            'lineno': lineno,
            'func': frame.f_code.co_name,
            'source': source,
            'locals': locals_dict,
            'is_app': not ('site-packages' in filename or 'lib/python' in filename)
        })
        tb = tb.tb_next
    return frames

def _extract_request_info(request: Any) -> Dict[str, Any]:
    if not request: return {}
    info = {}
    try:
        info['Method'] = getattr(request, 'method', 'GET')
        info['Path'] = getattr(request, 'path', '/')
        if hasattr(request, 'headers'): info['Headers'] = dict(request.headers)
        if hasattr(request, 'query_params'): info['Query Params'] = dict(request.query_params)
        if hasattr(request, 'path_params'): info['Path Params'] = dict(request.path_params)
    except: pass
    return info

# ============================================================================
# Main Renderers
# ============================================================================

class DebugPageRenderer:
    @staticmethod
    def render_exception(exc: BaseException, request: Any = None, *, aquilia_version: str = "") -> str:
        return render_debug_exception_page(exc, request, aquilia_version=aquilia_version)

    @staticmethod
    def render_http_error(status_code: int, message: str = "", detail: str = "", request: Any = None, *, aquilia_version: str = "") -> str:
        return render_http_error_page(status_code, message, detail, request, aquilia_version=aquilia_version)

    @staticmethod
    def render_welcome(*, aquilia_version: str = "") -> str:
        return render_welcome_page(aquilia_version=aquilia_version)

# ============================================================================
# SVGs & Page Generators
# ============================================================================

def _icon(name: str, cls: str = "icon") -> str:
    """Return inline SVG icon."""
    icons = {
        'alert': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>',
        'copy': '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>',
        'chevron-down': '<polyline points="6 9 12 15 18 9"></polyline>',
        'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>',
        'sun': '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>',
        'search': '<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>',
        'terminal': '<polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line>',
        'zap': '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>',
        'box': '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line>', 
        'activity': '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>',
        'shield': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>',
        'home': '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline>',
        'server-crash': '<path d="M6 10H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2"></path><path d="M6 14H4a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2h-2"></path><polyline points="6 6 12 6 12 12 6 12"></polyline>',
        'arrow-right': '<line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>',
        'github': '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path>',
        'book': '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>',
        'lock': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path>'
    }
    return f'<svg class="{cls}" viewBox="0 0 24 24">{icons.get(name, "")}</svg>'

def render_debug_exception_page(exc: BaseException, request: Any = None, *, aquilia_version: str = "") -> str:
    frames = _extract_frames(exc)
    req_info = _extract_request_info(request)
    
    # Frames HTML
    frames_html = []
    for f in reversed(frames):
        active = "active" if f == frames[-1] else "" # Most recent first
        src_html = _format_code_block(f['source'])
        
        locals_html = ""
        if f['locals']:
            rows = "".join(f'<div class="local-row"><div class="local-key">{_esc(k)}</div><div class="local-val">{_esc(repr(v))}</div></div>' for k,v in f['locals'].items())
            locals_html = f'<div class="locals"><div class="locals-header">Local Variables</div>{rows}</div>'
            
        badge = '<span class="badge green">App</span>' if f['is_app'] else '<span class="badge gray">Lib</span>'
        
        frames_html.append(f"""
        <div class="frame {active} {'app-code' if f['is_app'] else ''}">
            <div class="frame-header" onclick="toggleFrame(this.parentNode)">
                <div class="frame-info">
                    <div class="frame-func">{_esc(f['func'])}</div>
                    <div class="frame-file"><span style="color:var(--tx-text-muted)">in</span> {_esc(f['short_filename'])}</div>
                </div>
                <div class="frame-meta">
                    {badge}
                    <span>Line {f['lineno']}</span>
                    <div class="frame-chevron">{_icon('chevron-down')}</div>
                </div>
            </div>
            <div class="frame-body">
                {src_html}
                {locals_html}
            </div>
        </div>
        """)

    # Request Info HTML
    req_html = []
    if req_info:
        for section, data in req_info.items():
            if not data: continue
            if isinstance(data, dict):
                rows = "".join(f'<div class="local-row"><div class="local-key">{_esc(k)}</div><div class="local-val">{_esc(str(v))}</div></div>' for k,v in data.items())
                req_html.append(f'<div class="card" style="margin-bottom:16px;"><div class="locals-header">{_esc(section)}</div>{rows}</div>')
            else:
                req_html.append(f'<div class="card" style="margin-bottom:16px;padding:16px;"><strong>{_esc(section)}:</strong> {_esc(str(data))}</div>')

    logo_url = "https://raw.githubusercontent.com/axiomchronicles/Aquilia/master/assets/logo.png"
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Server Error</title>
    <style>{_BASE_CSS}</style>
    <link rel="icon" type="image/x-icon" href="https://raw.githubusercontent.com/axiomchronicles/Aquilia/master/assets/favicon.ico">
</head>
<body>
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>
    
    <header class="header glass">
        <div class="container" style="display:flex;justify-content:space-between;align-items:center;">
            <div class="logo">
                <img src="{logo_url}" alt="Aquilia" style="width:32px;height:32px;">
                <span>Aquilia Debug</span>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
                <div class="badge red">500 Server Error</div>
                <div class="theme-toggle" id="theme-toggle" onclick="toggleTheme()">
                    <div id="icon-moon">{_icon('moon')}</div>
                    <div id="icon-sun" style="display:none">{_icon('sun')}</div>
                </div>
            </div>
        </div>
    </header>
    
    <main class="container">
        <div class="exc-header">
            <h1 class="exc-title">{type(exc).__name__}</h1>
            <div class="exc-msg">{_esc(str(exc))}</div>
            
            <div class="tabs">
                <div class="tab active" data-tab="trace" onclick="switchTab('trace')">{_icon('activity')} Traceback</div>
                <div class="tab" data-tab="request" onclick="switchTab('request')">{_icon('box')} Request Info</div>
            </div>
        </div>
        
        <div id="panel-trace" class="tab-panel active">
            <div style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:13px;color:var(--tx-text-muted);">Stack Trace (most recent call first)</span>
                <button class="copy-btn" id="copy-tb-btn" onclick="copyText('copy-tb-btn', 'raw-tb')">
                    {_icon('copy')} <span>Copy Traceback</span>
                </button>
            </div>
            <div class="frame-list">
                {"".join(frames_html)}
            </div>
            <div id="raw-tb" style="display:none">{_esc("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))}</div>
        </div>
        
        <div id="panel-request" class="tab-panel">
            {"".join(req_html) if req_html else '<div style="color:var(--tx-text-muted);text-align:center;">No request context available.</div>'}
        </div>
    </main>
    <script>{_BASE_JS}</script>
</body>
</html>"""

def render_http_error_page(status_code: int, message: str = "", detail: str = "", request: Any = None, *, aquilia_version: str = "") -> str:
    logo_url = "https://raw.githubusercontent.com/axiomchronicles/Aquilia/master/assets/logo.png"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{status_code} {message}</title>
    <style>{_BASE_CSS}</style>
    <link rel="icon" type="image/x-icon" href="https://raw.githubusercontent.com/axiomchronicles/Aquilia/master/assets/favicon.ico">
</head>
<body>
    <div class="bg-grid"></div>
    <div class="bg-glow" style="opacity:0.3"></div>
    
    <div class="http-page">
        <div class="http-container">
            <div class="http-icon-bg">
                {_icon('server-crash', 'icon icon-xl')}
            </div>
            <div class="badge red" style="margin-bottom:24px;">{status_code}</div>
            <h1 class="http-title">{_esc(message or 'Error')}</h1>
            <p class="http-desc">{_esc(detail or 'An unexpected error occurred processing your request.')}</p>
            
            <a href="/" class="btn-primary" style="border-radius:8px;">{_icon('home')} Back Home</a>
        </div>
    </div>
    <div style="position:fixed;top:24px;right:24px;">
        <div class="theme-toggle" id="theme-toggle" onclick="toggleTheme()">
            <div id="icon-moon">{_icon('moon')}</div>
            <div id="icon-sun" style="display:none">{_icon('sun')}</div>
        </div>
    </div>
    <script>{_BASE_JS}</script>
</body>
</html>"""

def render_welcome_page(*, aquilia_version: str = "") -> str:
    str_version = f"v{aquilia_version}" if aquilia_version else "Dev"
    logo_url = "https://raw.githubusercontent.com/axiomchronicles/Aquilia/master/assets/logo.png"
    
    # Inline Gyroscope SVG (copied from temp/landing.html, with minor tweaks for Py string embedding)
    gyro_svg = r'''
    <svg class="w-full h-full" viewBox="0 0 500 500" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;">
        <defs>
            <linearGradient id="ring-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#22c55e" stop-opacity="0.1" />
                <stop offset="50%" stop-color="#22c55e" stop-opacity="0.6" />
                <stop offset="100%" stop-color="#22c55e" stop-opacity="0.1" />
            </linearGradient>
        </defs>
        <g class="animate-gyro-1" style="transform-origin:center;">
            <circle cx="250" cy="250" r="220" stroke="url(#ring-gradient)" stroke-width="1" stroke-dasharray="1 10" />
            <circle cx="250" cy="250" r="218" stroke="#22c55e" stroke-width="0.5" stroke-opacity="0.2" />
        </g>
        <g class="animate-gyro-2" style="transform-origin:center;">
            <ellipse cx="250" cy="250" rx="180" ry="180" stroke="#22c55e" stroke-width="1" stroke-opacity="0.4" stroke-dasharray="20 40" />
            <path d="M70 250 A 180 180 0 0 1 430 250" stroke="#22c55e" stroke-width="1" stroke-opacity="0.1" fill="none" />
        </g>
        <g class="animate-gyro-3" style="transform-origin:center;">
            <circle cx="250" cy="250" r="120" stroke="#22c55e" stroke-width="2" stroke-opacity="0.6" stroke-dasharray="60 100" />
            <circle cx="250" cy="250" r="110" stroke="#22c55e" stroke-width="0.5" stroke-opacity="0.3" />
            <circle cx="130" cy="250" r="3" fill="#86efac" />
            <circle cx="370" cy="250" r="3" fill="#86efac" />
        </g>
        <g class="animate-drift">
            <circle cx="100" cy="100" r="1.5" fill="#4ade80" opacity="0.6" />
            <circle cx="400" cy="400" r="2" fill="#4ade80" opacity="0.4" />
        </g>
    </svg>
    '''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Welcome to Aquilia</title>
    <style>{_BASE_CSS}</style>
    <link rel="icon" type="image/x-icon" href="https://raw.githubusercontent.com/axiomchronicles/Aquilia/master/assets/favicon.ico">
</head>
<body>
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>
    
    <header class="header glass">
        <div class="container" style="display:flex;justify-content:space-between;align-items:center;">
            <div class="logo">
                <img src="{logo_url}" alt="Aquilia" style="width:32px;height:32px;">
                <span>Aquilia</span>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
                <div class="badge gray">{str_version}</div>
                <div class="theme-toggle" id="theme-toggle" onclick="toggleTheme()">
                    <div id="icon-moon">{_icon('moon')}</div>
                    <div id="icon-sun" style="display:none">{_icon('sun')}</div>
                </div>
            </div>
        </div>
    </header>
    
    <main class="container">
        <!-- Hero Split -->
        <div class="welcome-hero">
            <div>
                <div class="welcome-badge">{_icon('activity')} Server Active</div>
                <h1 class="welcome-title">The <span style="color:var(--tx-accent);">Production-Ready</span><br>Async Web Framework</h1>
                <p class="welcome-subtitle">Aquilia is running in debug mode. No root route has been defined yet. Start building your high-performance application now.</p>
                
                <div style="display:flex;gap:16px;">
                    <a href="https://aquilia.dev" target="_blank" class="btn-primary">
                        {_icon('book')} Documentation
                    </a>
                    <a href="https://github.com/axiomchronicles/Aquilia" target="_blank" class="btn-secondary">
                        {_icon('github')} GitHub
                    </a>
                </div>

                <div class="cmd-block">
                    <div style="color:var(--tx-text-muted);margin-bottom:8px;"># Create a new module</div>
                    <div style="display:flex;justify-content:space-between;">
                        <span><span style="color:var(--tx-accent)">$</span> aq add module users</span>
                        <span style="cursor:pointer;" onclick="copyText(this.id, 'c1')" id="btn-c1">{_icon('copy')}</span>
                        <span id="c1" style="display:none">aq add module users</span>
                    </div>
                </div>
            </div>
            
            <!-- Visual -->
            <div style="position:relative;display:flex;justify-content:center;align-items:center;">
                 <div style="position:absolute;inset:0;background:var(--tx-accent);opacity:0.1;filter:blur(100px);border-radius:50%;"></div>
                 <div class="zen-gyro animate-float-majestic">
                    {gyro_svg}
                    <div style="position:absolute;inset:0;display:flex;justify-content:center;align-items:center;pointer-events:none;">
                        <img src="{logo_url}" style="width:64px;height:64px;filter:drop-shadow(0 0 20px rgba(34,197,94,0.5));">
                    </div>
                 </div>
            </div>
        </div>
        
        <!-- Features Grid -->
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">{_icon('zap', 'icon icon-lg')}</div>
                <h3 style="margin-bottom:8px;">Async Native</h3>
                <p style="color:var(--tx-text-muted);font-size:14px;">Built on ASGI for high-performance concurrent request handling with zero overhead.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon" style="color:var(--tx-info);border-color:rgba(59,130,246,0.2);background:rgba(59,130,246,0.1)">{_icon('shield', 'icon icon-lg')}</div>
                <h3 style="margin-bottom:8px;">AquilAuth</h3>
                <p style="color:var(--tx-text-muted);font-size:14px;">Integrated OAuth2, OIDC, RBAC/ABAC authorization, and cryptographic session management.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon" style="color:var(--tx-warning);border-color:rgba(245,158,11,0.2);background:rgba(245,158,11,0.1)">{_icon('box', 'icon icon-lg')}</div>
                <h3 style="margin-bottom:8px;">Modular Registry</h3>
                <p style="color:var(--tx-text-muted);font-size:14px;">Aquilary manifest system for dependency resolution and simplified app composition.</p>
            </div>
            <div class="feature-card">
                 <div class="feature-icon" style="color:#a855f7;border-color:rgba(168,85,247,0.2);background:rgba(168,85,247,0.1)">{_icon('activity', 'icon icon-lg')}</div>
                <h3 style="margin-bottom:8px;">Fault Domains</h3>
                <p style="color:var(--tx-text-muted);font-size:14px;">Structured error handling with Typed Faults and automated recovery patterns.</p>
            </div>
             <div class="feature-card">
                 <div class="feature-icon" style="color:#ec4899;border-color:rgba(236,72,153,0.2);background:rgba(236,72,153,0.1)">{_icon('server-crash', 'icon icon-lg')}</div>
                <h3 style="margin-bottom:8px;">Smart Caching</h3>
                <p style="color:var(--tx-text-muted);font-size:14px;">Multi-backend caching service with cache-aside, write-through, and stampede protection.</p>
            </div>
             <div class="feature-card">
                 <div class="feature-icon" style="color:#14b8a6;border-color:rgba(20,184,166,0.2);background:rgba(20,184,166,0.1)">{_icon('terminal', 'icon icon-lg')}</div>
                <h3 style="margin-bottom:8px;">CLI Tooling</h3>
                <p style="color:var(--tx-text-muted);font-size:14px;">Powerful `aq` CLI for scaffolding workspaces, modules, and running dev servers.</p>
            </div>
        </div>
    </main>
    <script>{_BASE_JS}</script>
</body>
</html>"""
