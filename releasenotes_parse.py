import re

def parse_release_note(file_path):
    project_names = []
    pattern = re.compile(r'<project name="([^"]+)"')
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                name = match.group(1)
                if not name.startswith("LT-"):
                    continue
                if name.startswith("LT-HCS/"):
                    continue
                if name.endswith('.git'):
                    name = name[:-4]
                project_names.append(name)
    return project_names
