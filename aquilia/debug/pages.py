"""
Aquilia Debug Pages — React-style error pages with MongoDB color palette.

Self-contained HTML/CSS/JS generators. No external dependencies.
All styles and scripts are inlined for zero-config rendering.

Color Palette (MongoDB Atlas):
  - Primary Green:  #00ED64
  - Dark BG:        #001E2B
  - Dark Surface:   #023430
  - Dark Card:      #112733
  - Light BG:       #F9FBFA
  - Light Surface:  #FFFFFF
  - Light Card:     #E8EDEB
  - Text Dark:      #FFFFFF
  - Text Light:     #001E2B
  - Accent:         #00684A
  - Error Red:      #CF4A22
  - Warning Yellow: #FFC010
  - Info Blue:      #016BF8
"""

from __future__ import annotations

import html
import inspect
import linecache
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# CSS Styles — MongoDB Atlas theme, dark/light mode
# ============================================================================

_BASE_CSS = r"""
:root {
  /* MongoDB Atlas Dark */
  --mg-green: #00ED64;
  --mg-green-dark: #00684A;
  --mg-green-light: #71F6BA;
  --mg-dark-bg: #001E2B;
  --mg-dark-surface: #023430;
  --mg-dark-card: #112733;
  --mg-dark-border: #1C3A40;
  --mg-dark-text: #E8EDEB;
  --mg-dark-text-muted: #889397;
  /* MongoDB Atlas Light */
  --mg-light-bg: #F9FBFA;
  --mg-light-surface: #FFFFFF;
  --mg-light-card: #E8EDEB;
  --mg-light-border: #C1C7C6;
  --mg-light-text: #001E2B;
  --mg-light-text-muted: #5C6C75;
  /* Semantic */
  --mg-error: #CF4A22;
  --mg-error-bg: #FCEEE9;
  --mg-warning: #FFC010;
  --mg-info: #016BF8;
  --mg-info-light: #E1F7FF;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', 'Cascadia Code', 'Consolas', 'Monaco', monospace;
  line-height: 1.6;
  transition: background-color 0.3s ease, color 0.3s ease;
}

/* ---- Dark Mode (default) ---- */
body.dark {
  background: var(--mg-dark-bg);
  color: var(--mg-dark-text);
}
body.dark .aq-header { background: linear-gradient(135deg, #001E2B 0%, #023430 100%); border-bottom: 2px solid var(--mg-green); }
body.dark .aq-card { background: var(--mg-dark-card); border: 1px solid var(--mg-dark-border); }
body.dark .aq-card:hover { border-color: var(--mg-green-dark); }
body.dark .aq-tab { color: var(--mg-dark-text-muted); border-bottom: 2px solid transparent; }
body.dark .aq-tab.active { color: var(--mg-green); border-bottom-color: var(--mg-green); }
body.dark .aq-tab:hover { color: var(--mg-green-light); }
body.dark .aq-code-block { background: #0A1A22; border: 1px solid var(--mg-dark-border); }
body.dark .aq-code-line.highlight { background: rgba(0,237,100,0.08); }
body.dark .aq-code-line.error-line { background: rgba(207,74,34,0.2); border-left: 3px solid var(--mg-error); }
body.dark .aq-badge { background: var(--mg-dark-surface); color: var(--mg-green); border: 1px solid var(--mg-green-dark); }
body.dark .aq-table th { background: var(--mg-dark-surface); color: var(--mg-green); }
body.dark .aq-table td { border-top: 1px solid var(--mg-dark-border); }
body.dark .aq-frame { border-left: 3px solid var(--mg-dark-border); }
body.dark .aq-frame.active { border-left-color: var(--mg-green); background: rgba(0,237,100,0.03); }
body.dark .aq-frame:hover { border-left-color: var(--mg-green-dark); }
body.dark .aq-text-muted { color: var(--mg-dark-text-muted); }
body.dark .aq-input { background: #0A1A22; border: 1px solid var(--mg-dark-border); color: var(--mg-dark-text); }
body.dark .aq-locals-key { color: var(--mg-green); }
body.dark .aq-locals-val { color: var(--mg-dark-text-muted); }

/* ---- Light Mode ---- */
body.light {
  background: var(--mg-light-bg);
  color: var(--mg-light-text);
}
body.light .aq-header { background: linear-gradient(135deg, #FFFFFF 0%, #E8EDEB 100%); border-bottom: 2px solid var(--mg-green-dark); }
body.light .aq-card { background: var(--mg-light-surface); border: 1px solid var(--mg-light-border); }
body.light .aq-card:hover { border-color: var(--mg-green-dark); }
body.light .aq-tab { color: var(--mg-light-text-muted); border-bottom: 2px solid transparent; }
body.light .aq-tab.active { color: var(--mg-green-dark); border-bottom-color: var(--mg-green-dark); }
body.light .aq-tab:hover { color: var(--mg-green-dark); }
body.light .aq-code-block { background: #F4F6F5; border: 1px solid var(--mg-light-border); }
body.light .aq-code-line.highlight { background: rgba(0,104,74,0.06); }
body.light .aq-code-line.error-line { background: rgba(207,74,34,0.1); border-left: 3px solid var(--mg-error); }
body.light .aq-badge { background: #E1F7E8; color: var(--mg-green-dark); border: 1px solid var(--mg-green-dark); }
body.light .aq-table th { background: var(--mg-light-card); color: var(--mg-green-dark); }
body.light .aq-table td { border-top: 1px solid var(--mg-light-border); }
body.light .aq-frame { border-left: 3px solid var(--mg-light-border); }
body.light .aq-frame.active { border-left-color: var(--mg-green-dark); background: rgba(0,104,74,0.03); }
body.light .aq-frame:hover { border-left-color: var(--mg-green-dark); }
body.light .aq-text-muted { color: var(--mg-light-text-muted); }
body.light .aq-input { background: #FFFFFF; border: 1px solid var(--mg-light-border); color: var(--mg-light-text); }
body.light .aq-locals-key { color: var(--mg-green-dark); }
body.light .aq-locals-val { color: var(--mg-light-text-muted); }

/* ---- Layout ---- */
.aq-container { max-width: 1200px; margin: 0 auto; padding: 0 24px 48px; }

.aq-header {
  padding: 28px 0;
  margin-bottom: 32px;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(12px);
}
.aq-header-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; display: flex; justify-content: space-between; align-items: center; }

.aq-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}
.aq-logo-icon {
  width: 36px; height: 36px;
  background: var(--mg-green);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 18px; color: var(--mg-dark-bg);
}
.aq-logo-text { font-size: 18px; font-weight: 700; letter-spacing: -0.5px; }

/* Theme Toggle */
.aq-theme-toggle {
  width: 56px; height: 28px;
  background: var(--mg-dark-surface);
  border-radius: 14px;
  cursor: pointer;
  position: relative;
  border: 2px solid var(--mg-green-dark);
  transition: background 0.3s;
}
body.light .aq-theme-toggle { background: var(--mg-light-card); }

.aq-theme-toggle::after {
  content: '';
  position: absolute;
  width: 20px; height: 20px;
  border-radius: 50%;
  background: var(--mg-green);
  top: 2px; left: 2px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}
body.light .aq-theme-toggle::after { transform: translateX(28px); }

.aq-theme-icons {
  display: flex; justify-content: space-between; align-items: center;
  width: 100%; height: 100%; padding: 0 5px;
  font-size: 12px; position: relative; z-index: 1; pointer-events: none;
}

/* Error Banner */
.aq-error-banner {
  padding: 24px 32px;
  border-radius: 12px;
  margin-bottom: 24px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
body.dark .aq-error-banner { background: linear-gradient(135deg, rgba(207,74,34,0.15) 0%, rgba(207,74,34,0.05) 100%); border: 1px solid rgba(207,74,34,0.3); }
body.light .aq-error-banner { background: var(--mg-error-bg); border: 1px solid rgba(207,74,34,0.2); }

.aq-error-icon { font-size: 32px; flex-shrink: 0; line-height: 1; }
.aq-error-type { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 6px; }
body.dark .aq-error-type { color: #FF8C6B; }
body.light .aq-error-type { color: var(--mg-error); }
.aq-error-message { font-size: 15px; opacity: 0.9; word-break: break-word; }

/* Tabs */
.aq-tabs { display: flex; gap: 0; margin-bottom: 24px; border-bottom: 1px solid; overflow-x: auto; }
body.dark .aq-tabs { border-color: var(--mg-dark-border); }
body.light .aq-tabs { border-color: var(--mg-light-border); }
.aq-tab {
  padding: 10px 20px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.2s;
  white-space: nowrap;
  user-select: none;
}
.aq-tab-panel { display: none; }
.aq-tab-panel.active { display: block; }

/* Cards */
.aq-card {
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  transition: border-color 0.2s;
}

/* Code Block */
.aq-code-block {
  border-radius: 8px;
  overflow: hidden;
  font-size: 13px;
  line-height: 1.7;
  margin: 12px 0;
}
.aq-code-line {
  display: flex;
  padding: 1px 16px 1px 0;
  transition: background 0.2s;
}
.aq-code-line:hover { opacity: 0.95; }
.aq-line-no {
  display: inline-block;
  width: 52px;
  text-align: right;
  padding-right: 16px;
  user-select: none;
  flex-shrink: 0;
}
body.dark .aq-line-no { color: #445963; }
body.light .aq-line-no { color: #889397; }
.aq-line-code { flex: 1; white-space: pre; overflow-x: auto; }

/* Stack Frame */
.aq-frame {
  padding: 14px 18px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.aq-frame-file { font-size: 13px; font-weight: 600; }
.aq-frame-info { font-size: 12px; margin-top: 2px; }
body.dark .aq-frame-info { color: var(--mg-dark-text-muted); }
body.light .aq-frame-info { color: var(--mg-light-text-muted); }
.aq-frame-code { display: none; margin-top: 12px; }
.aq-frame.active .aq-frame-code { display: block; }

/* Tables */
.aq-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.aq-table th { text-align: left; padding: 10px 14px; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
.aq-table td { padding: 10px 14px; word-break: break-all; }
.aq-table td:first-child { font-weight: 600; white-space: nowrap; width: 30%; }

/* Locals */
.aq-locals-item { padding: 6px 0; font-size: 13px; display: flex; gap: 8px; }
.aq-locals-key { font-weight: 700; flex-shrink: 0; }
.aq-locals-val { word-break: break-all; }

/* Badge */
.aq-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

/* Search */
.aq-search-bar { margin-bottom: 20px; }
.aq-input {
  width: 100%;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}
.aq-input:focus { border-color: var(--mg-green); }

/* Status code badges */
.aq-status-4xx { background: var(--mg-warning); color: var(--mg-dark-bg); font-weight: 700; }
.aq-status-5xx { background: var(--mg-error); color: #fff; font-weight: 700; }
.aq-status-2xx { background: var(--mg-green); color: var(--mg-dark-bg); font-weight: 700; }

/* ---- HTTP Error Page ---- */
.aq-http-error-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px 24px;
}
.aq-http-status {
  font-size: 120px;
  font-weight: 900;
  letter-spacing: -6px;
  line-height: 1;
  margin-bottom: 12px;
}
body.dark .aq-http-status { color: var(--mg-green); text-shadow: 0 0 60px rgba(0,237,100,0.3); }
body.light .aq-http-status { color: var(--mg-green-dark); }
.aq-http-title { font-size: 28px; font-weight: 700; margin-bottom: 12px; letter-spacing: -0.5px; }
.aq-http-detail { font-size: 15px; max-width: 560px; margin-bottom: 32px; }
body.dark .aq-http-detail { color: var(--mg-dark-text-muted); }
body.light .aq-http-detail { color: var(--mg-light-text-muted); }
.aq-http-meta {
  font-size: 12px;
  padding: 16px 32px;
  border-radius: 12px;
  margin-top: 16px;
}
body.dark .aq-http-meta { background: var(--mg-dark-card); border: 1px solid var(--mg-dark-border); color: var(--mg-dark-text-muted); }
body.light .aq-http-meta { background: var(--mg-light-surface); border: 1px solid var(--mg-light-border); color: var(--mg-light-text-muted); }

/* ---- Welcome Page ---- */
.aq-welcome-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px 24px;
}
.aq-welcome-logo {
  width: 120px; height: 120px;
  background: linear-gradient(135deg, var(--mg-green) 0%, var(--mg-green-dark) 100%);
  border-radius: 28px;
  display: flex; align-items: center; justify-content: center;
  font-size: 56px; font-weight: 900; color: var(--mg-dark-bg);
  margin-bottom: 32px;
  box-shadow: 0 20px 60px rgba(0,237,100,0.3);
  animation: aq-float 3s ease-in-out infinite;
}
@keyframes aq-float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-12px); }
}
.aq-welcome-title { font-size: 42px; font-weight: 800; letter-spacing: -2px; margin-bottom: 12px; }
body.dark .aq-welcome-title span { color: var(--mg-green); }
body.light .aq-welcome-title span { color: var(--mg-green-dark); }
.aq-welcome-subtitle { font-size: 17px; margin-bottom: 48px; }
body.dark .aq-welcome-subtitle { color: var(--mg-dark-text-muted); }
body.light .aq-welcome-subtitle { color: var(--mg-light-text-muted); }

.aq-welcome-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
  max-width: 900px;
  width: 100%;
  margin-bottom: 48px;
  text-align: left;
}
.aq-welcome-card {
  padding: 24px;
  border-radius: 16px;
  transition: transform 0.2s, border-color 0.2s;
}
.aq-welcome-card:hover { transform: translateY(-4px); }
body.dark .aq-welcome-card { background: var(--mg-dark-card); border: 1px solid var(--mg-dark-border); }
body.dark .aq-welcome-card:hover { border-color: var(--mg-green-dark); }
body.light .aq-welcome-card { background: var(--mg-light-surface); border: 1px solid var(--mg-light-border); }
body.light .aq-welcome-card:hover { border-color: var(--mg-green-dark); }
.aq-welcome-card-icon { font-size: 28px; margin-bottom: 12px; }
.aq-welcome-card-title { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
.aq-welcome-card-desc { font-size: 13px; }
body.dark .aq-welcome-card-desc { color: var(--mg-dark-text-muted); }
body.light .aq-welcome-card-desc { color: var(--mg-light-text-muted); }

.aq-welcome-code {
  max-width: 600px;
  width: 100%;
  text-align: left;
  padding: 24px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.8;
  margin-bottom: 32px;
}
body.dark .aq-welcome-code { background: #0A1A22; border: 1px solid var(--mg-dark-border); }
body.light .aq-welcome-code { background: #F4F6F5; border: 1px solid var(--mg-light-border); }
.aq-welcome-code .kw { color: var(--mg-info); }
.aq-welcome-code .fn { color: var(--mg-green); }
body.light .aq-welcome-code .fn { color: var(--mg-green-dark); }
.aq-welcome-code .st { color: var(--mg-warning); }
.aq-welcome-code .cm { color: var(--mg-dark-text-muted); }
body.light .aq-welcome-code .cm { color: var(--mg-light-text-muted); }

.aq-welcome-footer { font-size: 13px; }
body.dark .aq-welcome-footer { color: var(--mg-dark-text-muted); }
body.light .aq-welcome-footer { color: var(--mg-light-text-muted); }
.aq-welcome-footer a { color: var(--mg-green); text-decoration: none; font-weight: 600; }
body.light .aq-welcome-footer a { color: var(--mg-green-dark); }
.aq-welcome-footer a:hover { text-decoration: underline; }

/* Scrollbar */
body.dark ::-webkit-scrollbar { width: 8px; height: 8px; }
body.dark ::-webkit-scrollbar-track { background: var(--mg-dark-bg); }
body.dark ::-webkit-scrollbar-thumb { background: var(--mg-dark-border); border-radius: 4px; }
body.dark ::-webkit-scrollbar-thumb:hover { background: var(--mg-green-dark); }
"""

# ============================================================================
# JavaScript — tab switching, frame toggling, theme toggle, search
# ============================================================================

_BASE_JS = r"""
(function() {
  // Theme toggle
  const saved = localStorage.getItem('aq-theme') || 'dark';
  document.body.className = saved;

  window.aqToggleTheme = function() {
    const next = document.body.className === 'dark' ? 'light' : 'dark';
    document.body.className = next;
    localStorage.setItem('aq-theme', next);
  };

  // Tab switching
  window.aqSwitchTab = function(tabId) {
    document.querySelectorAll('.aq-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.aq-tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
    document.getElementById('panel-' + tabId).classList.add('active');
  };

  // Frame toggling
  window.aqToggleFrame = function(el) {
    const wasActive = el.classList.contains('active');
    // Collapse all frames
    document.querySelectorAll('.aq-frame').forEach(f => f.classList.remove('active'));
    if (!wasActive) el.classList.add('active');
  };

  // Search/filter in request info
  window.aqFilterTable = function(inputEl, tableId) {
    const filter = inputEl.value.toLowerCase();
    const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(filter) ? '' : 'none';
    });
  };

  // Copy traceback
  window.aqCopyTraceback = function() {
    const tb = document.getElementById('raw-traceback');
    if (tb) {
      navigator.clipboard.writeText(tb.textContent).then(() => {
        const btn = document.getElementById('copy-btn');
        if (btn) { btn.textContent = '✓ Copied!'; setTimeout(() => { btn.textContent = '📋 Copy Traceback'; }, 2000); }
      });
    }
  };
})();
"""


# ============================================================================
# Utility — source extraction, HTML escaping, syntax highlighting
# ============================================================================

def _esc(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text), quote=True)


def _read_source_lines(filename: str, lineno: int, context: int = 7) -> List[Tuple[int, str, bool]]:
    """Read source lines around a given line number.

    Returns list of (line_number, source_text, is_error_line).
    """
    lines: List[Tuple[int, str, bool]] = []
    start = max(1, lineno - context)
    end = lineno + context + 1

    for i in range(start, end):
        line = linecache.getline(filename, i)
        if line:
            lines.append((i, line.rstrip('\n'), i == lineno))
        elif i <= lineno:
            # Might be past end of file
            continue

    return lines


def _syntax_highlight_line(code: str) -> str:
    """Very minimal Python syntax highlighting using CSS classes."""
    import re

    escaped = _esc(code)

    # Keywords
    keywords = (
        r'\b(def|class|import|from|return|if|elif|else|for|while|try|except|'
        r'finally|with|as|raise|yield|async|await|pass|break|continue|'
        r'and|or|not|in|is|lambda|None|True|False|self)\b'
    )
    escaped = re.sub(keywords, r'<span style="color:var(--mg-info)">\1</span>', escaped)

    # Strings (simple — single/double quoted)
    escaped = re.sub(
        r'(&quot;.*?&quot;|&#x27;.*?&#x27;|&quot;&quot;&quot;.*?&quot;&quot;&quot;)',
        r'<span style="color:var(--mg-warning)">\1</span>',
        escaped,
    )

    # Comments
    escaped = re.sub(
        r'(#.*)$',
        r'<span style="color:var(--mg-dark-text-muted)">\1</span>',
        escaped,
    )

    # Numbers
    escaped = re.sub(
        r'\b(\d+\.?\d*)\b',
        r'<span style="color:var(--mg-green)">\1</span>',
        escaped,
    )

    return escaped


def _format_code_block(lines: List[Tuple[int, str, bool]]) -> str:
    """Render source lines into an HTML code block."""
    if not lines:
        return '<div class="aq-code-block"><div class="aq-code-line"><span class="aq-line-code">(source not available)</span></div></div>'

    parts = ['<div class="aq-code-block">']
    for lineno, code, is_error in lines:
        cls = "aq-code-line error-line" if is_error else "aq-code-line highlight"
        parts.append(
            f'<div class="{cls}">'
            f'<span class="aq-line-no">{lineno}</span>'
            f'<span class="aq-line-code">{_syntax_highlight_line(code)}</span>'
            f'</div>'
        )
    parts.append('</div>')
    return '\n'.join(parts)


def _format_locals_section(frame_locals: Dict[str, Any]) -> str:
    """Render local variables for a stack frame."""
    if not frame_locals:
        return '<div class="aq-text-muted" style="padding:8px 0;font-size:13px;">No local variables</div>'

    parts = ['<div style="max-height:300px;overflow-y:auto;padding:8px 0;">']
    for key, value in sorted(frame_locals.items()):
        if key.startswith('__') and key.endswith('__'):
            continue
        try:
            val_repr = repr(value)
            if len(val_repr) > 300:
                val_repr = val_repr[:300] + '…'
        except Exception:
            val_repr = '<unrepresentable>'
        parts.append(
            f'<div class="aq-locals-item">'
            f'<span class="aq-locals-key">{_esc(key)}</span>'
            f'<span class="aq-locals-val">= {_esc(val_repr)}</span>'
            f'</div>'
        )
    parts.append('</div>')
    return '\n'.join(parts)


# ============================================================================
# Traceback extraction
# ============================================================================

def _extract_frames(exc: BaseException) -> List[Dict[str, Any]]:
    """Extract stack frames from an exception with source and locals."""
    frames: List[Dict[str, Any]] = []

    tb = exc.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        lineno = tb.tb_lineno
        filename = frame.f_code.co_filename
        func_name = frame.f_code.co_name

        # Get source lines
        source_lines = _read_source_lines(filename, lineno)

        # Get locals (filtered)
        local_vars = {}
        if frame.f_locals:
            for k, v in frame.f_locals.items():
                if not (k.startswith('__') and k.endswith('__')):
                    local_vars[k] = v

        # Short path
        short_filename = filename
        try:
            cwd = os.getcwd()
            if filename.startswith(cwd):
                short_filename = os.path.relpath(filename, cwd)
        except Exception:
            pass

        frames.append({
            'filename': filename,
            'short_filename': short_filename,
            'lineno': lineno,
            'func_name': func_name,
            'source_lines': source_lines,
            'locals': local_vars,
            'is_app_code': not ('site-packages' in filename or 'lib/python' in filename),
        })

        tb = tb.tb_next

    return frames


# ============================================================================
# Request info extraction
# ============================================================================

def _extract_request_info(request: Any) -> Dict[str, Any]:
    """Extract displayable info from an Aquilia Request object."""
    if request is None:
        return {}

    info: Dict[str, Any] = {}

    try:
        # Method + path
        info['method'] = getattr(request, 'method', 'GET')
        info['path'] = getattr(request, 'path', '/')
        info['query_string'] = getattr(request, 'query_string', '')

        # Headers
        headers = {}
        if hasattr(request, 'headers'):
            h = request.headers
            if hasattr(h, 'items'):
                headers = dict(h.items())
            elif isinstance(h, dict):
                headers = h
        info['headers'] = headers

        # Cookies
        cookies = {}
        if hasattr(request, 'cookies') and request.cookies:
            if isinstance(request.cookies, dict):
                cookies = request.cookies
            elif hasattr(request.cookies, 'items'):
                cookies = dict(request.cookies.items())
        info['cookies'] = cookies

        # Query params
        query_params = {}
        if hasattr(request, 'query_params'):
            qp = request.query_params
            if isinstance(qp, dict):
                query_params = qp
            elif hasattr(qp, 'items'):
                query_params = dict(qp.items())
        info['query_params'] = query_params

        # Client
        info['client'] = getattr(request, 'client', None)

        # Scheme
        info['scheme'] = getattr(request, 'scheme', 'http')

        # State
        state = {}
        if hasattr(request, 'state') and isinstance(request.state, dict):
            state = request.state
        info['state'] = state

    except Exception:
        pass

    return info


# ============================================================================
# Main Renderers
# ============================================================================

class DebugPageRenderer:
    """Renders beautiful debug pages for Aquilia."""

    @staticmethod
    def render_exception(
        exc: BaseException,
        request: Any = None,
        *,
        aquilia_version: str = "",
    ) -> str:
        """Render a full React-style debug exception page."""
        return render_debug_exception_page(exc, request, aquilia_version=aquilia_version)

    @staticmethod
    def render_http_error(
        status_code: int,
        message: str = "",
        detail: str = "",
        request: Any = None,
        *,
        aquilia_version: str = "",
    ) -> str:
        """Render a styled HTTP error page."""
        return render_http_error_page(status_code, message, detail, request, aquilia_version=aquilia_version)

    @staticmethod
    def render_welcome(*, aquilia_version: str = "") -> str:
        """Render the Aquilia starter welcome page."""
        return render_welcome_page(aquilia_version=aquilia_version)


# ============================================================================
# render_debug_exception_page
# ============================================================================

def render_debug_exception_page(
    exc: BaseException,
    request: Any = None,
    *,
    aquilia_version: str = "",
) -> str:
    """
    Render a beautiful React-style debug exception page.

    Features:
    - Full traceback with clickable stack frames
    - Source code context with syntax highlighting per frame
    - Local variables inspector
    - Request info (headers, cookies, query params)
    - Dark/light mode toggle
    - Copy traceback button
    - MongoDB Atlas color palette
    """
    exc_type = type(exc).__qualname__
    exc_module = type(exc).__module__
    exc_message = str(exc)
    raw_traceback = traceback.format_exception(type(exc), exc, exc.__traceback__)
    raw_tb_text = ''.join(raw_traceback)

    frames = _extract_frames(exc)
    request_info = _extract_request_info(request) if request else {}

    # Fault metadata
    fault_info = ""
    if hasattr(exc, 'domain'):
        domain_val = getattr(exc.domain, 'value', str(exc.domain)) if hasattr(exc.domain, 'value') else str(exc.domain)
        fault_info += f'<span class="aq-badge" style="margin-right:8px;">Domain: {_esc(domain_val)}</span>'
    if hasattr(exc, 'code') and exc.code:
        fault_info += f'<span class="aq-badge" style="margin-right:8px;">Code: {_esc(str(exc.code))}</span>'
    if hasattr(exc, 'severity'):
        sev_val = getattr(exc.severity, 'value', str(exc.severity)) if hasattr(exc.severity, 'value') else str(exc.severity)
        fault_info += f'<span class="aq-badge">Severity: {_esc(sev_val)}</span>'

    # Build stack frames HTML
    frames_html = _build_frames_html(frames)

    # Build request info HTML
    request_html = _build_request_html(request_info)

    # Version
    version_display = f'v{aquilia_version}' if aquilia_version else ''

    # Raw traceback for copy
    raw_tb_escaped = _esc(raw_tb_text)

    # Python version
    py_version = f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(exc_type)}: {_esc(exc_message[:80])}</title>
  <style>{_BASE_CSS}</style>
</head>
<body class="dark">
  <!-- Header -->
  <div class="aq-header">
    <div class="aq-header-inner">
      <div class="aq-logo">
        <div class="aq-logo-icon">A</div>
        <span class="aq-logo-text">Aquilia Debug {_esc(version_display)}</span>
      </div>
      <div style="display:flex;align-items:center;gap:16px;">
        <span class="aq-text-muted" style="font-size:12px;">Python {py_version}</span>
        <div class="aq-theme-toggle" onclick="aqToggleTheme()">
          <div class="aq-theme-icons"><span>🌙</span><span>☀️</span></div>
        </div>
      </div>
    </div>
  </div>

  <div class="aq-container">
    <!-- Error Banner -->
    <div class="aq-error-banner">
      <div class="aq-error-icon">💥</div>
      <div style="flex:1;">
        <div class="aq-error-type">
          {_esc(exc_type)}
          {f'<span class="aq-text-muted" style="font-size:14px;font-weight:400;margin-left:8px;">({_esc(exc_module)})</span>' if exc_module != 'builtins' else ''}
        </div>
        <div class="aq-error-message">{_esc(exc_message)}</div>
        {f'<div style="margin-top:10px;">{fault_info}</div>' if fault_info else ''}
      </div>
      <button id="copy-btn" onclick="aqCopyTraceback()" style="
        background:var(--mg-green-dark);color:#fff;border:none;border-radius:8px;
        padding:8px 16px;cursor:pointer;font-size:12px;font-weight:600;font-family:inherit;
        white-space:nowrap;transition:background 0.2s;
      " onmouseover="this.style.background='var(--mg-green)';this.style.color='var(--mg-dark-bg)'" onmouseout="this.style.background='var(--mg-green-dark)';this.style.color='#fff'">📋 Copy Traceback</button>
    </div>

    <!-- Tabs -->
    <div class="aq-tabs">
      <div class="aq-tab active" data-tab="traceback" onclick="aqSwitchTab('traceback')">Traceback</div>
      <div class="aq-tab" data-tab="request" onclick="aqSwitchTab('request')">Request</div>
      <div class="aq-tab" data-tab="raw" onclick="aqSwitchTab('raw')">Raw</div>
    </div>

    <!-- Traceback Panel -->
    <div id="panel-traceback" class="aq-tab-panel active">
      <div style="margin-bottom:12px;font-size:13px;" class="aq-text-muted">
        {len(frames)} frame{'s' if len(frames) != 1 else ''} — click to expand source &amp; locals
      </div>
      {frames_html}
    </div>

    <!-- Request Panel -->
    <div id="panel-request" class="aq-tab-panel">
      {request_html if request_html else '<div class="aq-card"><p class="aq-text-muted">No request information available.</p></div>'}
    </div>

    <!-- Raw Traceback Panel -->
    <div id="panel-raw" class="aq-tab-panel">
      <div class="aq-card">
        <pre id="raw-traceback" style="white-space:pre-wrap;word-break:break-word;font-size:13px;line-height:1.7;margin:0;">{raw_tb_escaped}</pre>
      </div>
    </div>
  </div>

  <script>{_BASE_JS}</script>
</body>
</html>"""


def _build_frames_html(frames: List[Dict[str, Any]]) -> str:
    """Build HTML for stack frames (most recent last, reversed for display)."""
    parts = []
    reversed_frames = list(reversed(frames))

    for i, frame in enumerate(reversed_frames):
        is_first = i == 0
        active_cls = "aq-frame active" if is_first else "aq-frame"
        app_badge = '<span class="aq-badge" style="margin-left:8px;font-size:10px;">APP</span>' if frame['is_app_code'] else ''

        code_html = _format_code_block(frame['source_lines'])
        locals_html = _format_locals_section(frame['locals'])

        parts.append(f"""
        <div class="{active_cls}" onclick="aqToggleFrame(this)">
          <div class="aq-frame-file">
            {_esc(frame['short_filename'])}:{frame['lineno']} in <strong>{_esc(frame['func_name'])}</strong>
            {app_badge}
          </div>
          <div class="aq-frame-info">{_esc(frame['filename'])}</div>
          <div class="aq-frame-code">
            {code_html}
            <div style="margin-top:12px;">
              <div style="font-size:12px;font-weight:700;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;" class="aq-text-muted">Local Variables</div>
              {locals_html}
            </div>
          </div>
        </div>""")

    return '\n'.join(parts)


def _build_request_html(request_info: Dict[str, Any]) -> str:
    """Build HTML for request info panel."""
    if not request_info:
        return ''

    method = request_info.get('method', 'GET')
    path = request_info.get('path', '/')
    scheme = request_info.get('scheme', 'http')
    query_string = request_info.get('query_string', '')
    client = request_info.get('client', None)

    sections = []

    # Overview
    sections.append(f"""
    <div class="aq-card">
      <div style="font-size:16px;font-weight:700;margin-bottom:12px;">Request Overview</div>
      <table class="aq-table">
        <tbody>
          <tr><td>Method</td><td><span class="aq-badge">{_esc(method)}</span></td></tr>
          <tr><td>Path</td><td>{_esc(path)}</td></tr>
          <tr><td>Scheme</td><td>{_esc(scheme)}</td></tr>
          {f'<tr><td>Query String</td><td>{_esc(query_string)}</td></tr>' if query_string else ''}
          {f'<tr><td>Client</td><td>{_esc(str(client))}</td></tr>' if client else ''}
        </tbody>
      </table>
    </div>""")

    # Headers
    headers = request_info.get('headers', {})
    if headers:
        rows = ''.join(
            f'<tr><td>{_esc(str(k))}</td><td>{_esc(str(v))}</td></tr>'
            for k, v in sorted(headers.items())
        )
        sections.append(f"""
    <div class="aq-card">
      <div style="font-size:16px;font-weight:700;margin-bottom:8px;">Headers</div>
      <div class="aq-search-bar">
        <input class="aq-input" type="text" placeholder="Filter headers…" oninput="aqFilterTable(this, 'headers-table')">
      </div>
      <table class="aq-table" id="headers-table">
        <thead><tr><th>Header</th><th>Value</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>""")

    # Query Params
    query_params = request_info.get('query_params', {})
    if query_params:
        rows = ''.join(
            f'<tr><td>{_esc(str(k))}</td><td>{_esc(str(v))}</td></tr>'
            for k, v in sorted(query_params.items())
        )
        sections.append(f"""
    <div class="aq-card">
      <div style="font-size:16px;font-weight:700;margin-bottom:12px;">Query Parameters</div>
      <table class="aq-table">
        <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>""")

    # Cookies
    cookies = request_info.get('cookies', {})
    if cookies:
        rows = ''.join(
            f'<tr><td>{_esc(str(k))}</td><td>{_esc(str(v))}</td></tr>'
            for k, v in sorted(cookies.items())
        )
        sections.append(f"""
    <div class="aq-card">
      <div style="font-size:16px;font-weight:700;margin-bottom:12px;">Cookies</div>
      <table class="aq-table">
        <thead><tr><th>Cookie</th><th>Value</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>""")

    # State
    state = request_info.get('state', {})
    if state:
        rows = ''.join(
            f'<tr><td>{_esc(str(k))}</td><td>{_esc(str(v))}</td></tr>'
            for k, v in sorted(state.items())
        )
        sections.append(f"""
    <div class="aq-card">
      <div style="font-size:16px;font-weight:700;margin-bottom:12px;">Request State</div>
      <table class="aq-table">
        <thead><tr><th>Key</th><th>Value</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>""")

    return '\n'.join(sections)


# ============================================================================
# render_http_error_page
# ============================================================================

_HTTP_STATUS_INFO = {
    400: ("Bad Request", "The server cannot process this request due to malformed syntax or invalid parameters.", "🚫"),
    401: ("Unauthorized", "Authentication is required to access this resource. Please provide valid credentials.", "🔒"),
    403: ("Forbidden", "You don't have permission to access this resource. Check your authorization.", "⛔"),
    404: ("Not Found", "The requested resource could not be found on this server. Check the URL and try again.", "🔍"),
    405: ("Method Not Allowed", "The HTTP method used is not supported for this endpoint.", "🚧"),
    408: ("Request Timeout", "The server timed out waiting for the request. Please try again.", "⏱️"),
    409: ("Conflict", "The request conflicts with the current state of the resource.", "⚡"),
    422: ("Unprocessable Entity", "The request was well-formed but contains semantic errors.", "📋"),
    429: ("Too Many Requests", "You have exceeded the rate limit. Please slow down and try again later.", "🏎️"),
    500: ("Internal Server Error", "An unexpected error occurred on the server. The team has been notified.", "💥"),
    502: ("Bad Gateway", "The server received an invalid response from an upstream server.", "🔗"),
    503: ("Service Unavailable", "The server is temporarily unable to handle the request. Please try again shortly.", "🔧"),
    504: ("Gateway Timeout", "The upstream server failed to respond in time.", "⏳"),
}


def render_http_error_page(
    status_code: int,
    message: str = "",
    detail: str = "",
    request: Any = None,
    *,
    aquilia_version: str = "",
) -> str:
    """
    Render a styled HTTP error page for debug mode.

    Shows the status code, human-readable message, request details,
    and helpful tips — all with MongoDB Atlas theming.
    """
    info = _HTTP_STATUS_INFO.get(status_code, ("Error", "An error occurred.", "❌"))
    title = message or info[0]
    description = detail or info[1]
    icon = info[2]

    # Status class
    if 400 <= status_code < 500:
        status_cls = "aq-status-4xx"
    elif status_code >= 500:
        status_cls = "aq-status-5xx"
    else:
        status_cls = "aq-status-2xx"

    # Request context
    req_method = ""
    req_path = ""
    req_time = ""
    if request:
        req_method = getattr(request, 'method', '')
        req_path = getattr(request, 'path', '')

    import datetime
    req_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    version_display = f'v{aquilia_version}' if aquilia_version else ''

    # Tips based on status
    tips = {
        400: "Check request body format and required parameters.",
        401: "Include a valid Authorization header or session cookie.",
        403: "Verify your role/permissions for this resource.",
        404: "Run <code>aq routes</code> to list all registered routes.",
        405: "Check the allowed HTTP methods for this endpoint.",
        500: "Check the server logs for the full traceback.",
    }
    tip = tips.get(status_code, "")
    tip_html = f'<div style="margin-top:16px;font-size:13px;padding:12px 20px;border-radius:8px;text-align:left;max-width:500px;" class="aq-http-meta">💡 <strong>Tip:</strong> {tip}</div>' if tip else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{status_code} {_esc(title)}</title>
  <style>{_BASE_CSS}</style>
</head>
<body class="dark">
  <!-- Header -->
  <div class="aq-header" style="position:fixed;top:0;left:0;right:0;">
    <div class="aq-header-inner">
      <div class="aq-logo">
        <div class="aq-logo-icon">A</div>
        <span class="aq-logo-text">Aquilia {_esc(version_display)}</span>
      </div>
      <div class="aq-theme-toggle" onclick="aqToggleTheme()">
        <div class="aq-theme-icons"><span>🌙</span><span>☀️</span></div>
      </div>
    </div>
  </div>

  <div class="aq-http-error-page">
    <div style="font-size:48px;margin-bottom:16px;">{icon}</div>
    <div class="aq-http-status">{status_code}</div>
    <div class="aq-http-title">{_esc(title)}</div>
    <div class="aq-http-detail">{_esc(description)}</div>

    {'<div class="aq-http-meta"><span style="margin-right:16px;"><strong>Method:</strong> ' + _esc(req_method) + '</span><span style="margin-right:16px;"><strong>Path:</strong> ' + _esc(req_path) + '</span><span><strong>Time:</strong> ' + _esc(req_time) + '</span></div>' if req_method else '<div class="aq-http-meta"><span><strong>Time:</strong> ' + _esc(req_time) + '</span></div>'}

    {tip_html}

    <div style="margin-top:24px;">
      <span class="aq-badge {status_cls}" style="font-size:13px;padding:6px 16px;">{status_code} {_esc(title)}</span>
    </div>
  </div>

  <script>{_BASE_JS}</script>
</body>
</html>"""


# ============================================================================
# render_welcome_page
# ============================================================================

def render_welcome_page(*, aquilia_version: str = "") -> str:
    """
    Render the Aquilia starter welcome page.

    Shown when debug mode is on and no routes are matched on the root path.
    Like Django's rocket page or React's spinning logo page.
    """
    version_display = f'v{aquilia_version}' if aquilia_version else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to Aquilia</title>
  <style>{_BASE_CSS}</style>
</head>
<body class="dark">
  <!-- Header -->
  <div class="aq-header" style="position:fixed;top:0;left:0;right:0;">
    <div class="aq-header-inner">
      <div class="aq-logo">
        <div class="aq-logo-icon">A</div>
        <span class="aq-logo-text">Aquilia {_esc(version_display)}</span>
      </div>
      <div class="aq-theme-toggle" onclick="aqToggleTheme()">
        <div class="aq-theme-icons"><span>🌙</span><span>☀️</span></div>
      </div>
    </div>
  </div>

  <div class="aq-welcome-page">
    <!-- Logo -->
    <div class="aq-welcome-logo">A</div>

    <div class="aq-welcome-title">Welcome to <span>Aquilia</span></div>
    <div class="aq-welcome-subtitle">
      The production-ready async Python web framework. You're seeing this page because <code style="padding:2px 8px;border-radius:4px;background:rgba(0,237,100,0.1);color:var(--mg-green);font-size:14px;">debug=True</code> and no routes are configured yet.
    </div>

    <!-- Feature Cards -->
    <div class="aq-welcome-grid">
      <div class="aq-welcome-card">
        <div class="aq-welcome-card-icon">⚡</div>
        <div class="aq-welcome-card-title">Async-First</div>
        <div class="aq-welcome-card-desc">Built on ASGI with native async/await support. Handles thousands of concurrent connections effortlessly.</div>
      </div>
      <div class="aq-welcome-card">
        <div class="aq-welcome-card-icon">🧩</div>
        <div class="aq-welcome-card-title">Modular Architecture</div>
        <div class="aq-welcome-card-desc">Manifest-driven modules with dependency resolution, auto-discovery, and scoped dependency injection.</div>
      </div>
      <div class="aq-welcome-card">
        <div class="aq-welcome-card-icon">🛡️</div>
        <div class="aq-welcome-card-title">Fault Handling</div>
        <div class="aq-welcome-card-desc">Typed fault domains, circuit breakers, retry patterns, and beautiful debug pages — errors are data, not surprises.</div>
      </div>
      <div class="aq-welcome-card">
        <div class="aq-welcome-card-icon">🔐</div>
        <div class="aq-welcome-card-title">Auth & Sessions</div>
        <div class="aq-welcome-card-desc">OAuth2/OIDC, MFA, RBAC/ABAC authorization, and cryptographic session management — all built in.</div>
      </div>
      <div class="aq-welcome-card">
        <div class="aq-welcome-card-icon">🔄</div>
        <div class="aq-welcome-card-title">Flow Routing</div>
        <div class="aq-welcome-card-desc">Typed flow-first routing with composable pipelines, middleware chains, and effect-aware request processing.</div>
      </div>
      <div class="aq-welcome-card">
        <div class="aq-welcome-card-icon">📦</div>
        <div class="aq-welcome-card-title">CLI Toolkit</div>
        <div class="aq-welcome-card-desc">Generate workspaces, modules, controllers, and services with the <code>aq</code> CLI. Zero config required.</div>
      </div>
    </div>

    <!-- Quick Start Code -->
    <div class="aq-welcome-code">
      <div style="font-size:12px;font-weight:700;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;" class="aq-text-muted">Quick Start</div>
      <div><span class="cm"># Create a new module</span></div>
      <div><span class="fn">$</span> aq add module <span class="st">hello</span></div>
      <div style="margin-top:12px;"><span class="cm"># Or create a controller manually</span></div>
      <div><span class="kw">from</span> aquilia <span class="kw">import</span> Controller, GET, Response, RequestCtx</div>
      <div style="margin-top:8px;"><span class="kw">class</span> <span class="fn">HelloController</span>(Controller):</div>
      <div>    prefix = <span class="st">"/"</span></div>
      <div style="margin-top:4px;">    <span class="kw">@</span><span class="fn">GET</span>(<span class="st">"/"</span>)</div>
      <div>    <span class="kw">async def</span> <span class="fn">index</span>(self, ctx: RequestCtx):</div>
      <div>        <span class="kw">return</span> Response.json({{<span class="st">"message"</span>: <span class="st">"Hello, Aquilia!"</span>}})</div>
    </div>

    <div class="aq-welcome-footer">
      Built with 💚 by the Aquilia Team &nbsp;·&nbsp;
      <a href="https://github.com/aquilia/aquilia">GitHub</a> &nbsp;·&nbsp;
      <a href="https://aquilia.dev/docs">Documentation</a>
    </div>
  </div>

  <script>{_BASE_JS}</script>
</body>
</html>"""
