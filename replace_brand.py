import os
import re

def replace_in_file(filepath, old, new):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f"Replaced in {filepath}")

def find_and_replace(root_dir, old, new):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(('.html', '.py', '.md', '.txt')):
                filepath = os.path.join(dirpath, filename)
                try:
                    replace_in_file(filepath, old, new)
                except Exception as e:
                    print(f"Error in {filepath}: {e}")

if __name__ == "__main__":
    find_and_replace('.', 'ChicCherry', 'ChicCherry')
