with open(r'dashboard\streamlit_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = [
    '                        c_down1, c_down2 = st.columns(2)\n',
    '                        with c_down1:\n',
    '                            try:\n',
    '                                witness_bytes = generate_witness_zip("data/uat_runs", run_id)\n',
    '                                st.download_button(\n',
    '                                    label="📦 Kit Témoin (ZIP)",\n',
    '                                    data=witness_bytes,\n',
    '                                    file_name=f"kit_temoin_{run_id}.zip",\n',
    '                                    mime="application/zip",\n',
    '                                    key="download_witness_zip",\n',
    '                                    use_container_width=True\n',
    '                                )\n',
    '                            except Exception as e:\n',
    '                                st.error(f"Erreur kit témoin : {e}")\n',
    '                        with c_down2:\n',
    '                            try:\n',
    '                                pdf_bytes = get_pdf_report_bytes(run_id, run_name, kpis, anomalies, audit_trail)\n',
    '                                st.download_button(\n',
    '                                    label="📥 Note de Synthèse (PDF)",\n',
    '                                    data=pdf_bytes,\n',
    '                                    file_name=f"note_synthese_{run_id}.pdf",\n',
    '                                    mime="application/pdf",\n',
    '                                    key="download_pdf_report",\n',
    '                                    use_container_width=True\n',
    '                                )\n',
    '                            except Exception as e:\n',
    '                                st.error(f"Erreur rapport PDF : {e}")\n'
]

lines[2296:2302] = new_lines

with open(r'dashboard\streamlit_app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Replacement completed successfully!")
