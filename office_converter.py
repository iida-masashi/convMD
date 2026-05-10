import os
import sys

def convert_office_file(file_path, output_dir="misc_posts"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Attempting to convert {file_path} using MarkItDown...")
    
    try:
        from markitdown import MarkItDown
    except ImportError:
        print("\n[ERROR] MarkItDown library is not installed or not available in this Python environment.")
        print("Note: MarkItDown requires Python 3.10 or higher. You are currently running this script with an older Python.")
        print("Please run this tool using the newly installed Python 3.11:")
        print("/opt/homebrew/bin/python3.11 web_to_md_tool/main.py <file_path>\n")
        return None

    try:
        md = MarkItDown()
        result = md.convert(file_path)
        md_content = result.text_content
        
        filename = os.path.basename(file_path)
        name, _ = os.path.splitext(filename)
        out_filename = f"{name}.md"
        out_path = os.path.join(output_dir, out_filename)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print(f"Successfully converted {file_path} to {out_path}")
        return out_path
    except Exception as e:
        print(f"Failed to convert {file_path}: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python office_converter.py <path_to_file>")
        sys.exit(1)
    
    convert_office_file(sys.argv[1])
