import os

search_terms = ['load_lob_registry', 'ALL_LOBS', 'portefeuilles']
dashboard_dir = 'dashboard'

for root, dirs, files in os.walk(dashboard_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for idx, line in enumerate(lines, 1):
                    for term in search_terms:
                        if term in line:
                            # Print matching file, line number, and content
                            print(f"{filepath}:{idx}: {line.strip()}")
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
