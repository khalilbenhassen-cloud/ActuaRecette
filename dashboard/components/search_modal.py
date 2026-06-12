# search_modal.py — Omnibar Search Component
# Phase 2c — Recherche globale dynamique (runs, LOBs, campagnes, pages)
"""
Usage:
    from dashboard.components.search_modal import _build_search_index, _NAV_PAGES, _TYPE_ICONS
"""
import html
import streamlit as st
from typing import List, Dict, Any

def _build_search_index(history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Build a flat searchable index from run history.
    
    Adapté à la structure réelle des runs:
    - run_id, run_name, timestamp, success_rate_pct, fatal_defects,
      total_cases, total_absolute_delta_euros, final_status
    """
    items = []
    seen_statuses = set()
    
    for h in history:
        run_id = h.get("run_id", "")
        run_name = h.get("run_name", run_id)
        ts = h.get("timestamp", "")[:10]
        success_pct = h.get("success_rate_pct", None)
        fatal = h.get("fatal_defects", 0)
        final_status = h.get("final_status", "")
        total_cases = h.get("total_cases", 0)
        
        # Format status for display
        status_display = final_status if final_status else "—"
        pct_display = f"{success_pct}%" if success_pct is not None else ""
        
        detail_parts = [ts]
        if pct_display:
            detail_parts.append(pct_display)
        if status_display != "—":
            detail_parts.append(status_display)
        if fatal:
            detail_parts.append(f"⚠ {fatal} anomalie(s)")
        
        items.append({
            "type": "run",
            "id": run_id,
            "label": run_name if run_name != run_id else run_id,
            "detail": " · ".join(detail_parts),
            "search_text": f"{run_id} {run_name} {ts} {final_status}".lower(),
            "page": "detail_run",
        })
        
        # Index by final_status (as category)
        if final_status and final_status not in seen_statuses:
            seen_statuses.add(final_status)
            status_runs = [r for r in history if r.get("final_status") == final_status]
            items.append({
                "type": "statut",
                "id": final_status,
                "label": final_status,
                "detail": f"{len(status_runs)} run(s)",
                "search_text": final_status.lower(),
                "page": "cockpit",
            })
    
    return items

_TYPE_ICONS = {
    "run": "▶️",
    "statut": "🏷️",
    "page": "📄",
}

_TYPE_LABELS = {
    "run": "Run",
    "statut": "Statut",
    "page": "Page",
}

# Navigation pages for quick access
_NAV_PAGES = [
    {"type": "page", "id": "cockpit", "label": "Cockpit", "detail": "Tableau de bord principal", "search_text": "cockpit tableau bord", "page": "cockpit"},
    {"type": "page", "id": "conformite", "label": "Conformité", "detail": "Analyse de conformité", "search_text": "conformite analyse", "page": "conformite"},
    {"type": "page", "id": "espace_travail", "label": "Espace de Travail", "detail": "Gestion des recettes", "search_text": "espace travail recettes", "page": "espace_travail"},
    {"type": "page", "id": "detail_run", "label": "Détail Run", "detail": "Détails d'exécution", "search_text": "detail run execution", "page": "detail_run"},
    {"type": "page", "id": "tendances", "label": "Tendances", "detail": "Analyse temporelle", "search_text": "tendances analyse temporelle", "page": "tendances"},
    {"type": "page", "id": "jira", "label": "Générateur Jira", "detail": "Création de tickets", "search_text": "jira ticket generateur", "page": "jira"},
    {"type": "page", "id": "audit", "label": "Registre d'Audit", "detail": "Journal des actions", "search_text": "audit registre journal", "page": "audit"},
]

def render_search_results(history: List[Dict[str, Any]]):
    """Render grouped search results inside a popover. Called from cockpit."""
    
    query = st.text_input(
        "Recherche",
        placeholder="Tapez un ID de run, nom de LOB, page...",
        key="omnibar_query",
        label_visibility="collapsed",
    )
    
    # Build index
    index = _build_search_index(history) + _NAV_PAGES
    
    # Filter dynamically
    if query:
        q = query.lower()
        results = [
            item for item in index
            if q in item.get("search_text", "").lower()
            or q in item["label"].lower()
            or q in item.get("detail", "").lower()
            or q in item.get("id", "").lower()
        ]
    else:
        # Default: show pages + first 3 runs
        pages = [i for i in index if i["type"] == "page"]
        runs = [i for i in index if i["type"] == "run"][:3]
        statuts = [i for i in index if i["type"] == "statut"][:3]
        results = pages + statuts + runs
    
    if not results and query:
        safe_query = html.escape(query)
        st.html(
            '<div style="text-align:center;padding:1.5rem;color:var(--ar-text-muted);">'
            f'🔍 Aucun résultat pour "<b>{safe_query}</b>"</div>'
        )
        return
    
    # Group by type
    grouped = {}
    for item in results:
        t = item["type"]
        if t not in grouped:
            grouped[t] = []
        grouped[t].append(item)
    
    # Render order: pages first, then statuts, then runs
    type_order = ["page", "statut", "run"]
    for type_key in type_order:
        items = grouped.get(type_key, [])
        if not items:
            continue
        
        icon = _TYPE_ICONS.get(type_key, "📌")
        type_label = _TYPE_LABELS.get(type_key, type_key.title())
        
        st.html(
            f'<div style="font-size:0.62rem;font-weight:700;color:var(--ar-text-muted);'
            f'text-transform:uppercase;letter-spacing:0.08em;padding:10px 0 4px 0;'
            f'border-bottom:1px solid var(--ar-border);margin-bottom:4px;">'
            f'{icon} {type_label}s</div>'
        )
        
        for item in items[:5]:
            if st.button(
                f'{item["label"]}  ·  {item.get("detail", "")}',
                key=f"sr_{item['type']}_{item['id']}",
                use_container_width=True,
                type="secondary",
            ):
                if item["type"] == "run":
                    st.session_state["selected_run_id"] = item["id"]
                st.session_state["current_page"] = item["page"]
                st.rerun()
