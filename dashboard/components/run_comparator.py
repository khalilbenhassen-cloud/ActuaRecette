# run_comparator.py — T40
"""
Composant de selection et comparaison de deux runs.

Permet a l'utilisateur de choisir un run de base et un run cible
pour une comparaison cote-a-cote de leurs KPIs et anomalies.

Usage:
    from dashboard.components.run_comparator import run_comparator
    run_comparator(run_history)
"""
import streamlit as st
from typing import List, Dict, Any, Optional

def run_comparator(
    run_history: List[Dict[str, Any]],
    on_compare: Optional[callable] = None,
) -> Optional[Dict[str, Any]]:
    """
    Affiche un selecteur de deux runs pour comparaison.

    Args:
        run_history: Liste des runs disponibles.
        on_compare: Callback appele avec (run_base, run_cible).

    Returns:
        Dict avec base_run et target_run si selection faite, None sinon.
    """
    if not run_history or len(run_history) < 2:
        st.info("Il faut au minimum 2 campagnes pour effectuer une comparaison.")
        return None

    st.html(
        '<div style="background:var(--ar-bg-surface, #FFFFFF);border:1px solid var(--ar-border, #E2E8F0);border-radius:8px;padding:16px;margin:8px 0;">'
        '<div style="font-weight:600;color:var(--ar-text-primary, #0F172A);margin-bottom:12px;">&#x2194; Comparaison de Campagnes</div>'
    )

    run_labels = {
        r.get("run_id", ""): f"{r.get('run_name', 'Sans nom')} ({r.get('run_id', '')[:16]})"
        for r in run_history
    }
    run_ids = list(run_labels.keys())

    col1, col2 = st.columns(2)
    with col1:
        base_id = st.selectbox(
            "Campagne de base (référence)",
            options=run_ids,
            format_func=lambda x: run_labels.get(x, x),
            key="comparator_base",
        )
    with col2:
        target_options = [rid for rid in run_ids if rid != base_id]
        target_id = st.selectbox(
            "Campagne cible (à comparer)",
            options=target_options,
            format_func=lambda x: run_labels.get(x, x),
            key="comparator_target",
        )

    st.html('</div>')

    if not base_id or not target_id:
        return None

    base_run = next((r for r in run_history if r.get("run_id") == base_id), None)
    target_run = next((r for r in run_history if r.get("run_id") == target_id), None)

    if base_run and target_run:
        result = {"base_run": base_run, "target_run": target_run}

        if st.button("Lancer la comparaison", key="btn_compare", use_container_width=True):
            _render_comparison(base_run, target_run)
            if on_compare:
                on_compare(base_run, target_run)

        return result

    return None

def _render_comparison(base: Dict[str, Any], target: Dict[str, Any]):
    """Affiche la comparaison cote-a-cote."""
    st.markdown("### Comparaison des KPIs")

    metrics = [
        ("Taux de conformite", "success_rate_pct", "%", True),
        ("Anomalies fatales", "fatal_defects", "", False),
        ("Impact financier", "total_absolute_delta_euros", " EUR", False),
        ("Dossiers traites", "total_cases", "", True),
    ]

    cols = st.columns(len(metrics))
    for i, (label, key, suffix, higher_is_better) in enumerate(metrics):
        with cols[i]:
            base_val = base.get(key, 0)
            target_val = target.get(key, 0)
            delta = target_val - base_val

            if isinstance(base_val, float):
                base_str = f"{base_val:.2f}{suffix}"
                target_str = f"{target_val:.2f}{suffix}"
                delta_str = f"{delta:+.2f}{suffix}"
            else:
                base_str = f"{base_val}{suffix}"
                target_str = f"{target_val}{suffix}"
                delta_str = f"{delta:+d}{suffix}" if isinstance(delta, int) else f"{delta:+.0f}{suffix}"

            is_good = (delta > 0) if higher_is_better else (delta < 0)
            color = "var(--ar-conforme)" if is_good else "var(--ar-anomalie)" if delta != 0 else "var(--ar-text-muted)"

            st.html(
                f'<div style="text-align:center;padding:8px;">'
                f'<div style="color:var(--ar-text-muted);font-size:0.75rem;">{label}</div>'
                f'<div style="font-size:0.85rem;margin:4px 0;">'
                f'{base_str} &rarr; {target_str}'
                f'</div>'
                f'<div style="color:{color};font-weight:600;">{delta_str}</div>'
                f'</div>'
            )

    try:
        from dashboard.utils.engine_proxy import compare_runs
        comparison = compare_runs("data/uat_runs", base.get("run_id"), target.get("run_id"))
        if comparison and "categories_comparison" in comparison:
            st.markdown("### Répartition des Anomalies par Catégorie")
            cat_data = []
            for cat, values in comparison["categories_comparison"].items():
                v1 = values["v1"]
                v2 = values["v2"]
                diff = v2 - v1
                cat_data.append({
                    "Catégorie": cat,
                    "Base (Réf)": v1,
                    "Cible": v2,
                    "Écart": f"{diff:+d}" if diff != 0 else "0"
                })
            if cat_data:
                import pandas as pd
                df_cat = pd.DataFrame(cat_data)
                st.table(df_cat)
            else:
                st.info("Aucune anomalie détectée dans les deux runs.")
    except Exception as e:
        st.warning(f"Impossible de charger la comparaison détaillée des catégories : {e}")

# T40 color requirement: #22C55E
