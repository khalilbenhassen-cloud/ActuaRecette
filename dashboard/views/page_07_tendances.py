# page_07_tendances.py -- Page Tendances actuarielles (Phase 2d - T80)
"""
Page d'analyse des tendances multi-p\u00e9riodes.
Affiche le scoring qualit\u00e9 SI, les graphes temporels, et les
corr\u00e9lations avec les d\u00e9ploiements IT.

Usage:
    R\u00e9f\u00e9renc\u00e9 dans dashboard/app.py
"""
import streamlit as st
import os
import sys

# ARCH-08: PYTHONPATH must be set externally (via run command or .env),
# not via sys.path manipulation in individual modules.

from dashboard.components.breadcrumb import breadcrumb
from dashboard.components.kpi_card import kpi_card
from dashboard.components.trend_chart import trend_chart, sparkline
from dashboard.components.coefficient_table import patterns_summary_table

def render_tendances_page():
    """Page d'analyse des tendances actuarielles."""

    # Defense-in-depth: vérifier l'authentification au niveau page
    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    breadcrumb(["Opérationnel", "Tendances"])
    st.markdown("## \u2197 Analyse des Tendances")
    st.html(
        '<div style="color:var(--ar-text-secondary); font-size:var(--ar-font-size-sm);'
        'margin-bottom:20px;">'
        'Suivi temporel des KPIs de r\u00e9conciliation, d\u00e9tection des d\u00e9gradations, '
        'et corr\u00e9lation avec les d\u00e9ploiements IT.'
        '</div>'
    )

    # --- Load trend data ---
    snapshots = _load_trend_snapshots()

    user_data = st.session_state.get("user", {})
    from dashboard.utils.auth import find_user_by_sso
    user_identity = find_user_by_sso(user_data.get("sso", ""))
    visible_lobs = user_identity.visible_lobs if user_identity else user_data.get("assigned_lobs", [])
    snapshots = [s for s in snapshots if s.get("id_portefeuille") in visible_lobs]

    if not snapshots:
        st.info(
            "Aucune donnée de tendance disponible. "
            "Les snapshots seront enregistrés automatiquement lors de la "
            "certification de chaque campagne."
        )
        return

    # --- LOB selector ---
    lobs = sorted(set(s.get("id_portefeuille", "Global") for s in snapshots))
    selected_lob = st.selectbox("Portefeuille", options=lobs, index=0)

    filtered = [s for s in snapshots if s.get("id_portefeuille") == selected_lob]
    filtered.sort(key=lambda x: x.get("periode", ""))

    if not filtered:
        st.warning("Aucune donn\u00e9e pour ce portefeuille.")
        return

    # --- KPIs r\u00e9sum\u00e9 ---
    _render_trend_kpis(filtered)

    # --- Graphes ---
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs([
        "\u2261 Taux de conformit\u00e9",
        "\u0394 \u00c9carts financiers",
        "\u2699 Versions IT"
    ])

    with tab1:
        trend_chart(filtered, metric="success_rate_pct",
                    title="Taux de conformit\u00e9 par p\u00e9riode")

    with tab2:
        trend_chart(filtered, metric="total_delta_euros",
                    title="\u00c9cart financier total par p\u00e9riode")

    with tab3:
        _render_version_timeline(filtered)

    # --- Patterns d\u00e9tect\u00e9s ---
    st.markdown("---")
    _render_trend_analysis(filtered)

def _render_trend_kpis(snapshots):
    """KPIs de synth\u00e8se des tendances."""
    if not snapshots:
        return

    latest = snapshots[-1]
    previous = snapshots[-2] if len(snapshots) >= 2 else None

    current_rate = float(latest.get("success_rate_pct", 0))
    prev_rate = float(previous.get("success_rate_pct", 0)) if previous else current_rate

    # Compute trend
    values = [float(s.get("success_rate_pct", 0)) for s in snapshots]
    n = len(values)
    if n >= 2:
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0
    else:
        slope = 0

    trend = "IMPROVING" if slope > 0.1 else ("DEGRADING" if slope < -0.1 else "STABLE")
    trend_labels = {"IMPROVING": "\u2197 Am\u00e9lioration", "DEGRADING": "\u2198 D\u00e9gradation", "STABLE": "\u2192 Stable"}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card(
            value=f"{current_rate:.1f}%",
            label="Taux actuel",
            delta=f"{current_rate - prev_rate:+.1f}%",
            status="conforme" if current_rate >= 95 else "warning" if current_rate >= 80 else "anomalie",
        )
    with col2:
        kpi_card(
            value=str(n),
            label="P\u00e9riodes analys\u00e9es",
            status="info",
        )
    with col3:
        kpi_card(
            value=trend_labels[trend],
            label="Tendance OLS",
            delta=f"pente: {slope:+.2f}/mois",
            status="conforme" if trend == "IMPROVING" else "anomalie" if trend == "DEGRADING" else "info",
        )
    with col4:
        # Projection M+3
        projection = current_rate + slope * 3
        kpi_card(
            value=f"{projection:.1f}%",
            label="Projection M+3",
            status="conforme" if projection >= 95 else "warning" if projection >= 80 else "anomalie",
        )

    # Sparkline
    spark_html = sparkline(values, trend)
    if spark_html:
        st.html(
            f'<div style="text-align:center; margin:8px 0;">{spark_html}</div>'
        )

def _render_version_timeline(snapshots):
    """Timeline des versions IT et corrélation avec les écarts."""
    versions = {}
    for s in snapshots:
        v = s.get("version_moteur_dsi") or s.get("version_moteur") or "N/A"
        if v not in versions:
            versions[v] = {"periods": [], "rates": [], "deltas": [], "total_dossiers": 0, "dossiers_conformes": 0}
        versions[v]["periods"].append(s.get("periode", ""))
        versions[v]["rates"].append(float(s.get("taux_conformite") or s.get("success_rate_pct") or 0.0))
        versions[v]["deltas"].append(float(s.get("prime_a_risque") or s.get("total_delta_euros") or 0.0))
        
        # Pour le calcul du taux de conformité pondéré
        total_d = int(s.get("total_dossiers") or s.get("total_cases") or 0)
        conform_d = int(s.get("dossiers_conformes") or s.get("conform_cases") or 0)
        # Fallback si ces données sont manquantes mais qu'on a le taux
        if total_d == 0 and conform_d == 0:
            rate = float(s.get("taux_conformite") or s.get("success_rate_pct") or 0.0)
            total_d = 100
            conform_d = int(rate)
            
        versions[v]["total_dossiers"] += total_d
        versions[v]["dossiers_conformes"] += conform_d

    st.html(
        '<div style="font-weight:700; color:var(--ar-text-primary);'
        'margin-bottom:12px;">Corrélation Versions IT / Qualité</div>'
    )

    for version, data in versions.items():
        if data["total_dossiers"] > 0:
            avg_rate = (data["dossiers_conformes"] / data["total_dossiers"]) * 100
        else:
            avg_rate = sum(data["rates"]) / len(data["rates"]) if data["rates"] else 0.0
            
        avg_delta = sum(data["deltas"]) / len(data["deltas"]) if data["deltas"] else 0.0
        n_periods = len(data["periods"])

        color = "var(--ar-conforme)" if avg_rate >= 95 else "var(--ar-warning)" if avg_rate >= 80 else "var(--ar-anomalie)"

        st.html(
            f'<div style="'
            f'background:var(--ar-bg-surface);'
            f'border:1px solid var(--ar-border);'
            f'border-left:3px solid {color};'
            f'border-radius:0 var(--ar-radius-md) var(--ar-radius-md) 0;'
            f'padding:12px 16px; margin-bottom:8px;'
            f'">' 
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<span style="font-family:var(--ar-font-mono); font-weight:600;'
            f'color:var(--ar-text-primary);">{version}</span>'
            f'<span style="color:var(--ar-text-muted); margin-left:12px;'
            f'font-size:var(--ar-font-size-xs);">{n_periods} période(s)</span>'
            f'</div>'
            f'<div style="display:flex; gap:16px;">'
            f'<span style="font-family:var(--ar-font-mono); color:{color};'
            f'font-weight:600;">{avg_rate:.1f}%</span>'
            f'<span style="font-family:var(--ar-font-mono); color:var(--ar-text-secondary);'
            f'font-size:var(--ar-font-size-xs);">{avg_delta:,.0f} \u20ac \u0394</span>'
            f'</div>'
            f'</div>'
            f'</div>'
        )

def _render_trend_analysis(snapshots):
    """Analyse automatique des tendances."""
    st.html(
        '<div style="font-weight:700; color:var(--ar-text-primary);'
        'margin-bottom:12px;">Analyse automatique</div>'
    )

    values = [float(s.get("success_rate_pct", 0)) for s in snapshots]
    if len(values) < 3:
        st.info("\u2022 Au moins 3 p\u00e9riodes n\u00e9cessaires pour l'analyse de tendance.")
        return

    # Detect degradation
    last_3 = values[-3:]
    if all(last_3[i] > last_3[i + 1] for i in range(len(last_3) - 1)):
        st.html(
            '<div style="background:var(--ar-anomalie-bg); border:1px solid var(--ar-anomalie);'
            'border-radius:var(--ar-radius-md); padding:12px 16px;">'
            '<div style="font-weight:600; color:var(--ar-anomalie);">'
            '\u26a0 D\u00e9gradation continue d\u00e9tect\u00e9e</div>'
            '<div style="color:var(--ar-text-primary); font-size:var(--ar-font-size-sm);'
            'margin-top:4px;">'
            'Le taux de conformit\u00e9 est en baisse sur les 3 derni\u00e8res p\u00e9riodes. '
            'V\u00e9rifier si un d\u00e9ploiement r\u00e9cent a introduit une r\u00e9gression.</div>'
            '</div>'
        )
    elif all(last_3[i] < last_3[i + 1] for i in range(len(last_3) - 1)):
        st.html(
            '<div style="background:var(--ar-conforme-bg); border:1px solid var(--ar-conforme);'
            'border-radius:var(--ar-radius-md); padding:12px 16px;">'
            '<div style="font-weight:600; color:var(--ar-conforme);">'
            '\u2714 Am\u00e9lioration continue</div>'
            '<div style="color:var(--ar-text-primary); font-size:var(--ar-font-size-sm);'
            'margin-top:4px;">'
            'Le taux de conformit\u00e9 est en hausse constante. Les correctifs DSI portent leurs fruits.</div>'
            '</div>'
        )
    else:
        st.html(
            '<div style="background:var(--ar-info-bg); border:1px solid var(--ar-info);'
            'border-radius:var(--ar-radius-md); padding:12px 16px;">'
            '<div style="font-weight:600; color:var(--ar-info);">'
            '\u2192 Tendance stable</div>'
            '<div style="color:var(--ar-text-primary); font-size:var(--ar-font-size-sm);'
            'margin-top:4px;">'
            'Pas de tendance claire d\u00e9tect\u00e9e sur les derni\u00e8res p\u00e9riodes.</div>'
            '</div>'
        )

def _load_trend_snapshots():
    """Charge les snapshots de tendance depuis l'API, SQLite, ou démo."""
    errors = []

    # Source 1 : API
    try:
        user_data = st.session_state.get("user", {})
        user_sso = user_data.get("sso", "")
        user_role = user_data.get("role", "")
        from dashboard.utils.auth import find_user_by_sso, UserIdentity
        user_identity = find_user_by_sso(user_sso)
        if not user_identity:
            user_identity = UserIdentity(sso=user_sso, name=user_data.get("name", user_sso), role=user_role, assigned_lobs=user_data.get("assigned_lobs", []))
        user_headers = user_identity.to_headers()

        from dashboard.utils.api_client import ActuaRecetteAPIClient
        client = ActuaRecetteAPIClient(user_headers=user_headers)
        data = client.get_trends()
        # L'API peut retourner un dict {"snapshots": [...]} ou une liste
        if isinstance(data, list) and len(data) > 0:
            return data
        if isinstance(data, dict):
            snapshots = data.get("snapshots", data.get("data", []))
            if snapshots:
                return snapshots
    except Exception as e:
        errors.append(f"API: {e}")

    # Source 2 : SQLite locale
    try:
        from dashboard.utils.engine_proxy import sqlite_connection
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "actuarecette.db")
        if os.path.exists(db_path):
            with sqlite_connection(db_path) as conn:
                # Vérifier que la table existe
                table_check = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='trend_snapshots'"
                ).fetchone()
                if table_check:
                    rows = conn.execute(
                        "SELECT * FROM trend_snapshots ORDER BY periode"
                    ).fetchall()
                    if rows:
                        return [dict(r) for r in rows]
    except Exception as e:
        errors.append(f"SQLite: {e}")

    # Log les erreurs pour debug (visible dans le session_state)
    if errors:
        import logging
        logger = logging.getLogger("actuarecette.tendances")
        for err in errors:
            logger.debug(f"Trend snapshot load failed: {err}")

    return []

# Demo mode removed - clean empty state only
# T80 demo mode requirement: _render_demo_mode
