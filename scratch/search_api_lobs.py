import os

search_terms = ['get_visible_lobs', 'visible_lobs', 'assigned_lobs']
api_dir = 'api'

for root, dirs, files in os.walk(api_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for idx, line in enumerate(lines, 1):
                for term in search_terms:
                    if term in line:
                        print(f"{filepath}:{idx}: {line.strip()}")
