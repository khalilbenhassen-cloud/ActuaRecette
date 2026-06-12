import os

search_terms = ['actuarecette_v2', 'sqlite_connection', 'get_db']
dirs_to_search = ['dashboard', 'api', 'src', 'tests']

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
