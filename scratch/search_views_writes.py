import os

dirs_to_search = ['dashboard/views']

for directory in dirs_to_search:
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    for idx, line in enumerate(lines, 1):
                        if 'open(' in line and any(m in line for m in ['"w"', "'w'", '"a"', "'a'"]):
                            print(f"{filepath}:{idx}: {line.strip()}")
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
