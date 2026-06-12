"""
api/routes/exports.py — PDF/Kit/Witness exports
================================================

Endpoints:
  GET /runs/{run_id}/export-pdf
  GET /runs/{run_id}/export-kit
  GET /runs/{run_id}/export-witness
"""

import os
import json
import io
import tempfile
import zipfile

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from api.api_auth_middleware import get_visible_lobs

from src.anomaly_manager import (
    load_global_audit_trail,
    generate_witness_zip,
    translate_technical_error,
)

HISTORY_DIR = "data/uat_runs"

router = APIRouter(tags=["Exports"])

@router.get("/runs/{run_id}/export-pdf")
def export_pdf_endpoint(run_id: str, request: Request):
    """
    T84 -- Genere et telecharge le rapport PDF de synthese cote serveur.
    Inclut KPIs, anomalies, Root Cause, DQ, et registre d'audit.
    """
    try:
        from api.api_auth_middleware import validate_safe_id
        safe_id = validate_safe_id(run_id, "run_id")

        # Load run data
        run_file = os.path.join(HISTORY_DIR, f"{safe_id}.json")
        if not os.path.exists(run_file):
            raise HTTPException(status_code=404, detail=f"Run introuvable : {safe_id}")

        with open(run_file, "r", encoding="utf-8") as f:
            run_data = json.load(f)

        # LOB access check
        visible_lobs = get_visible_lobs(request)
        run_lob = run_data.get("lob_id", "LOB_AUTO_PART")
        if run_lob not in visible_lobs:
            raise HTTPException(
                status_code=403,
                detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
            )

        run_name = run_data.get("run_name", "Campagne de Recette")
        kpis = run_data.get("kpis", {})
        anomalies = run_data.get("anomalies", [])

        # Load audit trail
        audit_trail = load_global_audit_trail("data/audit_log.json")
        run_audit = [e for e in audit_trail if e.get("run_id") == safe_id]

        # Optional: Root Cause data
        root_cause = run_data.get("root_cause", None)

        # Optional: DQ report
        dq_report = run_data.get("dq_report", None)

        # Generate PDF via src/pdf_generator
        from src.pdf_generator import generate_pdf_report

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        generate_pdf_report(
            run_id=safe_id,
            run_name=run_name,
            kpis=kpis,
            anomalies=anomalies,
            audit_trail=run_audit,
            output_path=tmp_path,
            root_cause=root_cause,
            dq_report=dq_report,
        )

        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()

        # Cleanup temp file
        os.remove(tmp_path)

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="rapport_{safe_id}.pdf"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        translated = translate_technical_error(e)
        raise HTTPException(status_code=500, detail=translated)

@router.get("/runs/{run_id}/export-kit")
def export_kit_endpoint(run_id: str, request: Request):
    """
    T86 -- Genere et telecharge le Kit Temoin consolide (ZIP) contenant :
    - Rapport PDF de synthese
    - CSV Reference + Production
    - Rapport DQ JSON
    - Extrait du journal d'audit (JSON)
    - Metadata du run (JSON)
    """
    try:
        from api.api_auth_middleware import validate_safe_id
        safe_id = validate_safe_id(run_id, "run_id")

        # Load run data
        run_file = os.path.join(HISTORY_DIR, f"{safe_id}.json")
        if not os.path.exists(run_file):
            raise HTTPException(status_code=404, detail=f"Run introuvable : {safe_id}")

        with open(run_file, "r", encoding="utf-8") as f:
            run_data = json.load(f)

        # LOB access check
        visible_lobs = get_visible_lobs(request)
        run_lob = run_data.get("lob_id", "LOB_AUTO_PART")
        if run_lob not in visible_lobs:
            raise HTTPException(
                status_code=403,
                detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
            )

        run_name = run_data.get("run_name", "Campagne de Recette")
        kpis = run_data.get("kpis", {})
        anomalies = run_data.get("anomalies", [])

        # Build ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:

            # 1. Run metadata
            zf.writestr(
                f"{safe_id}/metadata.json",
                json.dumps(run_data, indent=2, ensure_ascii=False, default=str),
            )

            # 2. Audit trail extract
            audit_trail = load_global_audit_trail("data/audit_log.json")
            run_audit = [e for e in audit_trail if e.get("run_id") == safe_id]
            zf.writestr(
                f"{safe_id}/audit_trail.json",
                json.dumps(run_audit, indent=2, ensure_ascii=False, default=str),
            )

            # 3. CSV datasets (if saved)
            datasets_dir = "data/saved_datasets"
            for suffix in ["_ref.csv", "_prod.csv"]:
                csv_path = os.path.join(datasets_dir, f"{safe_id}{suffix}")
                if os.path.exists(csv_path):
                    zf.write(csv_path, f"{safe_id}/{safe_id}{suffix}")

            # 4. DQ report (if exists)
            dq_report = run_data.get("dq_report")
            if dq_report:
                zf.writestr(
                    f"{safe_id}/dq_report.json",
                    json.dumps(dq_report, indent=2, ensure_ascii=False, default=str),
                )

            # 5. PDF report
            try:
                from src.pdf_generator import generate_pdf_report

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = tmp.name

                generate_pdf_report(
                    run_id=safe_id,
                    run_name=run_name,
                    kpis=kpis,
                    anomalies=anomalies,
                    audit_trail=run_audit,
                    output_path=tmp_path,
                    root_cause=run_data.get("root_cause"),
                    dq_report=dq_report,
                )

                zf.write(tmp_path, f"{safe_id}/rapport_synthese.pdf")
                os.remove(tmp_path)
            except Exception as pdf_err:
                # PDF generation is best-effort; kit ships without it
                zf.writestr(
                    f"{safe_id}/pdf_generation_error.txt",
                    f"Erreur generation PDF : {pdf_err}",
                )

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="kit_temoin_{safe_id}.zip"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        translated = translate_technical_error(e)
        raise HTTPException(status_code=500, detail=translated)

@router.get("/runs/{run_id}/export-witness")
def export_witness_zip_endpoint(run_id: str, request: Request):
    """
    Endpoint générant et téléchargeant le kit témoin ZIP pour la DSI.
    """
    try:
        # LOB access check
        from api.api_auth_middleware import validate_safe_id
        safe_id = validate_safe_id(run_id, "run_id")
        run_file = os.path.join(HISTORY_DIR, f"{safe_id}.json")
        if os.path.exists(run_file):
            with open(run_file, "r", encoding="utf-8") as f:
                run_data = json.load(f)
            visible_lobs = get_visible_lobs(request)
            run_lob = run_data.get("lob_id", "LOB_AUTO_PART")
            if run_lob not in visible_lobs:
                raise HTTPException(
                    status_code=403,
                    detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
                )

        zip_bytes = generate_witness_zip(HISTORY_DIR, run_id)

        # Renvoi direct du flux d'octets ZIP en StreamingResponse
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=kit_temoin_{run_id}.zip"}
        )
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        translated = translate_technical_error(e)
        raise HTTPException(
            status_code=500,
            detail=translated
        )
