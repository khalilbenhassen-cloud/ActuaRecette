import os
from src.pdf_generator import generate_pdf_report

def test():
    run_id = "run_test_pdf"
    run_name = "Automobile Particuliers - Run Test"
    kpis = {
        "timestamp": "2026-06-02T12:00:00",
        "final_status": "CONFORME",
        "success_rate_pct": 100.0,
        "conform_cases": 100,
        "total_cases": 100,
        "fatal_defects": 0,
        "total_absolute_delta_euros": 0.0,
        "max_deviation_euros": 0.0
    }
    anomalies = []
    audit_trail = [
        {
            "run_id": run_id,
            "action": "APPROVED",
            "validator_name": "Sophie Martin",
            "signature_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
    ]
    output_path = "scratch/test_report.pdf"
    generate_pdf_report(run_id, run_name, kpis, anomalies, audit_trail, output_path)
    print("PDF generated successfully at:", os.path.abspath(output_path))
    assert os.path.exists(output_path)

if __name__ == "__main__":
    test()
