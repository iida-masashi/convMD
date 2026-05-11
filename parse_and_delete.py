import re
import os

list_file = "/Users/masashi/Documents/Obsidian Vault/理論・研究/99_管理/非研究対象ファイル候補一覧.md"
base_dir = "/Users/masashi/Documents/Obsidian Vault"

if not os.path.exists(list_file):
    print("List file not found.")
    exit()

with open(list_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract links format: [[path/to/file.md|alias]] or just path/to/file.md
# We'll just look for lines starting with '- ' and extract the text.
lines = content.split('\n')
files_to_delete = []

for line in lines:
    if line.startswith("- "):
        # Remove list marker
        item = line[2:].strip()
        # Handle Obsidian links [[path|alias]] or [[path]]
        match = re.search(r'\[\[(.*?)\]\]', item)
        if match:
            inner = match.group(1)
            path = inner.split('|')[0] # Get the path part
            files_to_delete.append(path)
        else:
            # It might just be the filename
            files_to_delete.append(item)

total_deleted = 0
for file_path in files_to_delete:
    full_path = os.path.join(base_dir, file_path)
    # If the path extracted doesn't have an exact match, try to find it by name
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            print(f"Deleted: {full_path}")
            total_deleted += 1
        except Exception as e:
            print(f"Failed to delete {full_path}: {e}")
    else:
        # Try to find by filename alone just in case the directory was wrong
        filename = os.path.basename(file_path)
        # some don't have .md
        if not filename.endswith('.md'):
            if not "&" in filename: # skip weird ones for now
                filename += ".md"
        
        import glob
        search_path = os.path.join(base_dir, "**", filename)
        matches = glob.glob(search_path, recursive=True)
        for match in matches:
             try:
                 os.remove(match)
                 print(f"Deleted (fuzzy match): {match}")
                 total_deleted += 1
             except:
                 pass

print(f"\nTotal files deleted: {total_deleted}")
