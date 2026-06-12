with open('dashboard/views/page_03_espace_travail.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for idx, line in enumerate(lines, 1):
    if '_update_run_checker' in line or '_lock_run' in line:
        print(f"{idx}: {line.strip()}")
