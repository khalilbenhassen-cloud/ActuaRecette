import os

search_terms = ['runs_execution']
dirs_to_search = ['src', 'api', 'dashboard']

for directory in dirs_to_search:
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    for idx, line in enumerate(lines, 1):
                        for term in search_terms:
                            if term in line:
                                print(f"{filepath}:{idx}: {line.strip()}")
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
