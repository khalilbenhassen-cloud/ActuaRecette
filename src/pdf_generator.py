import os
import datetime
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_pdf_report(
    run_id: str,
    run_name: str,
    kpis: Dict[str, Any],
    anomalies: List[Dict[str, Any]],
    audit_trail: List[Dict[str, Any]],
    output_path: str,
    root_cause: List[Dict[str, Any]] = None,
    dq_report: Dict[str, Any] = None,
    governance_data: dict = None,
) -> str:
    """
    Génère un rapport de synthèse PDF (Note de Synthèse ACPR) intégrant :
    - Les KPIs de la campagne
    - La typologie des écarts
    - Le diagnostic Root Cause (Phase 2d)
    - Le score Data Quality (Phase 2c)
    - Le registre des visas (Maker-Checker)
    - La signature cryptographique SHA-256 de non-répudiation.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Configuration du document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1B4079'),
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1B4079'),
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )
    
    bold_body_style = ParagraphStyle(
        'BoldBodyCustom',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    mono_style = ParagraphStyle(
        'MonospaceCustom',
        parent=body_style,
        fontName='Courier-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A'),
        backColor=colors.HexColor('#F8FAFC'),
        borderColor=colors.HexColor('#E2E8F0'),
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=12
    )

    story = []
    
    # Header Banner
    story.append(Paragraph("ACTUARECETTE - SYSTÈME D'INFORMATION", ParagraphStyle('SubHeaderText', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#64748B'), spaceAfter=2)))
    story.append(Paragraph("NOTE DE SYNTHÈSE DE RÉCONCILIATION RÉGLEMENTAIRE", title_style))
    if governance_data and governance_data.get('certification_number'):
        story.append(Paragraph(f"N° de certification : {governance_data['certification_number']}", bold_body_style))
        if governance_data.get('periode_arrete'):
            story.append(Paragraph(f"Période d'arrêté : {governance_data['periode_arrete']}", body_style))
    story.append(Spacer(1, 10))
    
    # Section 1: Informations Générales
    story.append(Paragraph("1. INFORMATIONS GÉNÉRALES", h2_style))
    
    now = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
    run_date = kpis.get("timestamp", now)
    
    # Extraction du visa validation
    validation_status = kpis.get("final_status", "BROUILLON")
    checker_name = "--"
    maker_name = "Karim Benali"
    signature_hash = "--"
    approver_name = None
    
    for entry in audit_trail:
        if entry.get("run_id") == run_id:
            if entry.get("action") in ["APPROVED", "REJECTED"]:
                validation_status = "CERTIFIÉ" if entry["action"] == "APPROVED" else "REJETÉ"
                checker_name = entry.get("validator_name", "--")
                if entry.get("signature_hash"):
                    signature_hash = entry["signature_hash"]
            elif entry.get("action") == "CREATED_AND_CALCULATED":
                maker_name = entry.get("validator_name", "Karim Benali")
    if governance_data:
        maker_name = governance_data.get('maker_name', maker_name)
        checker_name = governance_data.get('checker_name', checker_name)
        approver_name = governance_data.get('approver_name', approver_name)
                
    info_data = [
        [Paragraph("<b>Campagne :</b>", body_style), Paragraph(run_name, body_style),
         Paragraph("<b>Identifiant Campagne :</b>", body_style), Paragraph(run_id, body_style)],
        [Paragraph("<b>Date d'exécution :</b>", body_style), Paragraph(run_date, body_style),
         Paragraph("<b>Version Moteur DSI :</b>", body_style), Paragraph("ActuaRecette-v3.4", body_style)],
        [Paragraph("<b>Statut Réglementaire :</b>", body_style), Paragraph(f"<b>{validation_status}</b>", bold_body_style),
         Paragraph("<b>Maker (Actuaire) :</b>", body_style), Paragraph(maker_name, body_style)],
    ]
    if approver_name:
        info_data.append(
            [Paragraph("<b>Approbateur (Approver) :</b>", body_style), Paragraph(approver_name, body_style),
             Paragraph("", body_style), Paragraph("", body_style)]
        )
    
    info_table = Table(info_data, colWidths=[120, 140, 120, 140])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # Section 2: Indicateurs Clés de Réconciliation (KPIs)
    story.append(Paragraph("2. TABLEAU DE BORD DE RÉCONCILIATION COMPTABLE", h2_style))
    
    success_rate = kpis.get("success_rate_pct", 0.0)
    conform_cases = kpis.get("conform_cases", 0)
    total_cases = kpis.get("total_cases", 0)
    fatal_defects = kpis.get("fatal_defects", 0)
    total_delta = kpis.get("total_absolute_delta_euros", 0.0)
    max_deviation = kpis.get("max_deviation_euros", 0.0)
    
    kpi_data = [
        [Paragraph("<b>Métrique d'Audit</b>", bold_body_style), Paragraph("<b>Valeur Constatée</b>", bold_body_style), Paragraph("<b>Seuil de Matérialité / Conforme</b>", bold_body_style)],
        [Paragraph("Taux de Réconciliation Fonctionnelle", body_style), Paragraph(f"<b>{success_rate:.2f}%</b>", body_style), Paragraph("100.00% (Stricte)", body_style)],
        [Paragraph("Volume de dossiers certifiés", body_style), Paragraph(f"{conform_cases} / {total_cases} assurés", body_style), Paragraph("--", body_style)],
        [Paragraph("Défauts d'intégration (Hors Tolérance)", body_style), Paragraph(f"<b>{fatal_defects}</b> cas", body_style), Paragraph("0 anomalies", body_style)],
        [Paragraph("Exposition financière totale (À Risque)", body_style), Paragraph(f"<b>{total_delta:,.2f} €</b>", body_style), Paragraph("Seuil portefeuille : 0.20%", body_style)],
        [Paragraph("Écart maximal unitaire constaté", body_style), Paragraph(f"{max_deviation:.2f} €", body_style), Paragraph("Tolérance unitaire : 0.05 €", body_style)]
    ]
    
    kpi_table = Table(kpi_data, colWidths=[200, 150, 170])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    
    story.append(kpi_table)
    story.append(Spacer(1, 15))
    
    # Section 3: Typologie des anomalies (si existantes)
    section_num = 3
    if anomalies:
        story.append(Paragraph(f"{section_num}. TYPOLOGIE DES ÉCARTS ET ANOMALIES IDENTIFIÉES", h2_style))
        story.append(Paragraph("Les anomalies ci-dessous dépassent la tolérance unitaire d'arrondi fixée et nécessitent un correctif de la part de la DSI.", body_style))
        
        anom_header = [
            Paragraph("<b>Identifiant</b>", bold_body_style), 
            Paragraph("<b>Valeur Réf</b>", bold_body_style), 
            Paragraph("<b>Valeur Prod</b>", bold_body_style), 
            Paragraph("<b>Écart (€)</b>", bold_body_style), 
            Paragraph("<b>Catégorie d'anomalie</b>", bold_body_style)
        ]
        anom_rows = [anom_header]
        
        # Afficher au maximum les 8 pires anomalies pour ne pas surcharger le PDF
        for a in anomalies[:8]:
            # Fallback dynamique : cherche les colonnes réf/prod quel que soit le domaine
            val_ref = a.get('PRIME_REF', a.get('PRIME_ACTU', a.get('ref_value', 0.0)))
            val_prod = a.get('PRIME_DSI', a.get('prod_value', 0.0))
            anom_rows.append([
                Paragraph(str(a.get("ID_CLIENT", a.get("id", "--"))), body_style),
                Paragraph(f"{val_ref:.2f} €", body_style),
                Paragraph(f"{val_prod:.2f} €", body_style),
                Paragraph(f"{a.get('abs_deviation', 0.0):+.2f} €", body_style),
                Paragraph(a.get("anomaly_category", "Non classifié"), body_style)
            ])
            
        anom_table = Table(anom_rows, colWidths=[90, 80, 80, 80, 190])
        anom_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FFF1F2')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FDA4AF')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FFFBFB')])
        ]))
        story.append(anom_table)
        if len(anomalies) > 8:
            story.append(Paragraph(f"<i>* Note : {len(anomalies) - 8} autres anomalies détectées ne sont pas affichées dans ce document papier.</i>", ParagraphStyle('Footnote', fontName='Helvetica-Oblique', fontSize=8, spaceBefore=4)))
        story.append(Spacer(1, 15))
        section_num += 1

    # Section: Règles de contrôle appliquées (Governance V3)
    if governance_data and governance_data.get('applied_rules'):
        story.append(Paragraph(f"{section_num}. RÈGLES DE CONTRÔLE APPLIQUÉES", h2_style))
        rules_header = [
            Paragraph('<b>ID</b>', bold_body_style),
            Paragraph('<b>Règle</b>', bold_body_style),
            Paragraph('<b>Domaine</b>', bold_body_style),
            Paragraph('<b>Sévérité</b>', bold_body_style),
            Paragraph('<b>Version</b>', bold_body_style),
            Paragraph('<b>Réf. Réglementaire</b>', bold_body_style),
        ]
        rules_rows = [rules_header]
        for r in governance_data['applied_rules']:
            label_text = f"<b>{r.get('label', '')}</b>"
            formula = r.get('formule_theorique', '')
            if formula:
                label_text += f"<br/><i>Formule :</i> <font face='Courier' size='7'>{formula}</font>"
            cond = r.get('condition_application', '')
            if cond:
                label_text += f"<br/><i>Cond. :</i> <font face='Courier' size='7'>{cond}</font>"
                
            rules_rows.append([
                Paragraph(str(r.get('rule_id', '')), body_style),
                Paragraph(label_text, body_style),
                Paragraph(str(r.get('domain', '')), body_style),
                Paragraph(str(r.get('severity', '')), body_style),
                Paragraph(str(r.get('version', '')), body_style),
                Paragraph(str(r.get('regulatory_ref', '')), body_style),
            ])
        rules_table = Table(rules_rows, colWidths=[55, 130, 55, 55, 40, 185])
        rules_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EFF6FF')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#93C5FD')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(rules_table)
        story.append(Spacer(1, 15))
        section_num += 1

    # Section: Limites et insuffisances (Governance V3)
    if governance_data and governance_data.get('limitations'):
        story.append(Paragraph(f"{section_num}. LIMITES ET INSUFFISANCES IDENTIFIÉES", h2_style))
        for lim in governance_data['limitations']:
            cat = lim.get('category', '')
            comment = lim.get('comment', '')
            text = f"<b>• {cat}</b>"
            if comment:
                text += f" — {comment}"
            story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 15))
        section_num += 1

    # Section Root Cause (Phase 2d)
    if root_cause:
        story.append(Paragraph(f"{section_num}. DIAGNOSTIC ROOT CAUSE — PATTERNS SYSTÉMIQUES", h2_style))
        story.append(Paragraph(
            "L'analyse automatique des coefficients actuariels a détecté les patterns systémiques suivants. "
            "Chaque pattern est accompagné d'une recommandation corrective pour la DSI.",
            body_style
        ))

        rc_header = [
            Paragraph("<b>Coefficient</b>", bold_body_style),
            Paragraph("<b>Pattern</b>", bold_body_style),
            Paragraph("<b>Dossiers</b>", bold_body_style),
            Paragraph("<b>Impact (€)</b>", bold_body_style),
        ]
        rc_rows = [rc_header]

        for pat in root_cause[:6]:
            rc_rows.append([
                Paragraph(str(pat.get("coefficient", "--")), body_style),
                Paragraph(str(pat.get("pattern", "--")), body_style),
                Paragraph(str(pat.get("nb_dossiers_affectes", 0)), body_style),
                Paragraph(f"{pat.get('impact_total_euros', 0):+,.2f} €", body_style),
            ])

        rc_table = Table(rc_rows, colWidths=[130, 130, 80, 130])
        rc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEF3C7')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F59E0B')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFFBEB')]),
        ]))
        story.append(rc_table)

        # Recommendations
        for pat in root_cause[:3]:
            rec = pat.get("recommandation", "")
            if rec:
                story.append(Paragraph(
                    f"<b>→ {pat.get('coefficient', '')} :</b> {rec}",
                    body_style
                ))

        story.append(Spacer(1, 15))
        section_num += 1

    # Section DQ Score (Phase 2c)
    if dq_report and dq_report.get("score_global") is not None:
        story.append(Paragraph(f"{section_num}. SCORE QUALITÉ DES DONNÉES (DATA QUALITY)", h2_style))

        score = dq_report.get("score_global", 0)
        verdict = dq_report.get("verdict", "NON_CALCULÉ")
        story.append(Paragraph(
            f"Score global : <b>{score:.1f}%</b> — Verdict : <b>{verdict}</b>",
            bold_body_style
        ))

        dims = dq_report.get("dimensions", {})
        if dims:
            dq_header = [
                Paragraph("<b>Dimension</b>", bold_body_style),
                Paragraph("<b>Poids</b>", bold_body_style),
                Paragraph("<b>Score</b>", bold_body_style),
            ]
            dq_rows = [dq_header]
            dim_names = {
                "completude": "Complétude", "conformite": "Conformité",
                "coherence": "Cohérence", "unicite": "Unicité", "fraicheur": "Fraîcheur"
            }
            for key, dim in dims.items():
                dq_rows.append([
                    Paragraph(dim_names.get(key, key), body_style),
                    Paragraph(f"{dim.get('poids', 0) * 100:.0f}%", body_style),
                    Paragraph(f"{dim.get('score', 0):.1f}%", body_style),
                ])
            dq_table = Table(dq_rows, colWidths=[180, 100, 100])
            dq_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECFDF5')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#6EE7B7')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(dq_table)

        story.append(Spacer(1, 15))
        section_num += 1

    # Section N: Signature et Non-répudiation (Maker-Checker)
    story.append(Paragraph(f"{section_num}. REGISTRE DES VISAS DE CONFORMITÉ & SIGNATURE CRYPTOGRAPHIQUE", h2_style))
    story.append(Paragraph("Ce visa électronique certifie l'exécution conforme du protocole de réconciliation actuarielle. Tout changement ultérieur des calculs invalidera la signature ci-dessous.", body_style))
    
    sig_data = [
        [Paragraph("<b>Visa de l'Analyste (Maker) :</b>", body_style), Paragraph(f"{maker_name} (Analyste Actuariel)<br/>Statut : SOUMIS POUR SIGNATURE", body_style)],
        [Paragraph("<b>Visa du Validateur (Checker) :</b>", body_style), Paragraph(f"{checker_name} (Validateur Actuariat)<br/>Statut : {validation_status}", body_style)]
    ]
    if approver_name:
        sig_data.append(
            [Paragraph("<b>Visa de l'Approbateur (Approver) :</b>", body_style), Paragraph(f"{approver_name} (Approbateur Actuariat)<br/>Statut : {validation_status}", body_style)]
        )
    sig_table = Table(sig_data, colWidths=[200, 320])
    sig_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 10))
    
    # Hash Box — prefer governance_data integrity_hash over audit trail
    if governance_data and governance_data.get('integrity_hash'):
        signature_hash = governance_data['integrity_hash']
    story.append(Paragraph("<b>PREUVE DE VALIDATION CRYPTOGRAPHIQUE (SHA-256 HASH) :</b>", bold_body_style))
    story.append(Paragraph(signature_hash, mono_style))
    
    # Footnote réglementaire
    story.append(Paragraph("Note établie en conformité avec la réglementation prudentielle Solvabilité II - Contrôles de Qualité des Données et Piste d'Audit Interne.", ParagraphStyle('RegFootnote', fontName='Helvetica-Oblique', fontSize=7.5, leading=10, textColor=colors.HexColor('#64748B'), spaceBefore=20)))
    
    doc.build(story)
    return os.path.abspath(output_path)

