# keyboard_shortcuts.py \u2014 Raccourcis clavier power users (Phase 4)
"""
Injecte des raccourcis clavier dans l'app Streamlit via JavaScript.

Raccourcis :
  Ctrl+N  \u2192  Nouvelle recette (navigue vers l'espace de travail)
  Ctrl+S  \u2192  Soumettre le run en cours
  Ctrl+/  \u2192  Affiche l'aide raccourcis

Usage:
    from dashboard.components.keyboard_shortcuts import inject_keyboard_shortcuts
    inject_keyboard_shortcuts()
"""
import streamlit as st

# Keyboard shortcut definitions
SHORTCUTS = [
    {"keys": "Ctrl + K", "action": "Recherche rapide", "icon": "🔍"},
    {"keys": "Ctrl + N", "action": "Nouvelle recette", "icon": "\u2795"},
    {"keys": "Ctrl + S", "action": "Soumettre le run", "icon": "\u2191"},
    {"keys": "Ctrl + /", "action": "Aide raccourcis", "icon": "\u2753"},
    {"keys": "Ctrl + H", "action": "Retour cockpit", "icon": "\u2302"},
]

def inject_keyboard_shortcuts():
    """Injecte le listener JavaScript pour les raccourcis clavier."""
    import streamlit.components.v1 as components
    components.html(
        _SHORTCUT_JS,
        height=1
    )

def render_shortcut_help():
    """Affiche la palette d'aide raccourcis clavier."""
    rows = ""
    for s in SHORTCUTS:
        rows += (
            f'<div style="display:flex; justify-content:space-between; '
            f'padding:6px 0; border-bottom:1px solid var(--ar-border);">'
            f'<span style="color:var(--ar-text-secondary);">{s["icon"]} {s["action"]}</span>'
            f'<span class="ar-kbd">{s["keys"]}</span>'
            f'</div>'
        )

    st.html(
        f'<div style="'
        f'background:var(--ar-bg-surface);'
        f'border:1px solid var(--ar-border);'
        f'border-radius:var(--ar-radius-lg);'
        f'padding:16px 20px;'
        f'margin:8px 0;'
        f'box-shadow:var(--ar-shadow-md);'
        f'">'
        f'<div style="font-weight:700; color:var(--ar-text-primary); '
        f'margin-bottom:8px; font-size:var(--ar-font-size-md);">'
        f'\u2328 Raccourcis clavier</div>'
        f'{rows}'
        f'</div>'
    )

_SHORTCUT_JS = """
<script>
(function() {
    const doc = (window.parent && window.parent.document !== document) ? window.parent.document : document;
    const win = (window.parent && window.parent !== window) ? window.parent : window;

    if (win._arShortcutsInstalled) return;
    win._arShortcutsInstalled = true;

    // Helper: find element across Streamlit's DOM
    function findEl(selector) {
        return doc.querySelector(selector);
    }

    // Helper: click a Streamlit sidebar button by its key
    function clickNavButton(keyName) {
        // Streamlit renders buttons inside div.st-key-{key} > button
        var container = findEl('.st-key-' + keyName);
        if (container) {
            var btn = container.querySelector('button');
            if (btn) { btn.click(); return true; }
        }
        return false;
    }

    doc.addEventListener('keydown', function(e) {
        // Ctrl+K -> Focus search omnibar
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            var searchContainer = findEl('.st-key-omnibar_query');
            if (searchContainer) {
                var input = searchContainer.querySelector('input');
                if (input) { input.focus(); input.select(); return; }
            }
            // Fallback: try to open the search popover first
            var searchBtn = findEl('.st-key-pb_search_trigger button');
            if (searchBtn) { searchBtn.click(); }
        }

        // Ctrl+N -> Nouvelle recette (Espace de Travail)
        if (e.ctrlKey && e.key === 'n') {
            e.preventDefault();
            clickNavButton('nav_espace_travail');
        }

        // Ctrl+H -> Home / Cockpit
        if (e.ctrlKey && e.key === 'h') {
            e.preventDefault();
            clickNavButton('nav_cockpit');
        }

        // Ctrl+/ -> Show shortcut help toast
        if (e.ctrlKey && e.key === '/') {
            e.preventDefault();
            var existing = doc.getElementById('ar-shortcut-toast');
            if (existing) { existing.remove(); return; }

            var toast = doc.createElement('div');
            toast.id = 'ar-shortcut-toast';
            toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;' +
                'background:var(--ar-bg-surface,#fff);border:1px solid var(--ar-border,#E2E8F0);' +
                'border-radius:12px;padding:16px 20px;box-shadow:0 8px 32px rgba(0,0,0,0.12);' +
                'font-family:var(--ar-font-sans,sans-serif);min-width:220px;' +
                'animation:slideUp 0.3s ease-out;';
            toast.innerHTML = '<div style="font-weight:700;margin-bottom:8px;color:var(--ar-text-primary,#0F172A)">' +
                '⌨ Raccourcis clavier</div>' +
                '<div style="font-size:0.82rem;color:var(--ar-text-secondary,#475569);line-height:1.8">' +
                '<kbd style="background:#F1F5F9;padding:2px 6px;border-radius:4px;font-size:0.75rem">Ctrl+K</kbd> Recherche<br>' +
                '<kbd style="background:#F1F5F9;padding:2px 6px;border-radius:4px;font-size:0.75rem">Ctrl+N</kbd> Nouvelle recette<br>' +
                '<kbd style="background:#F1F5F9;padding:2px 6px;border-radius:4px;font-size:0.75rem">Ctrl+H</kbd> Cockpit<br>' +
                '<kbd style="background:#F1F5F9;padding:2px 6px;border-radius:4px;font-size:0.75rem">Ctrl+/</kbd> Cette aide</div>';
            toast.onclick = function() { toast.remove(); };
            doc.body.appendChild(toast);
            setTimeout(function() {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.3s';
                setTimeout(function() { toast.remove(); }, 300);
            }, 5000);
        }
    });
})();
</script>
"""
