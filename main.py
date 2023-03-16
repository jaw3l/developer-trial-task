import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from googletrans import Translator


def exclude_tags(tag):
    """Exclude tags from the list of tags."""
    
    list_of_tags = ["script", "style"]
    return tag.name not in list_of_tags


def find_html_files(root_dir: Path) -> list:
    """Find all HTML files in the root directory."""

    return list(root_dir.glob("**/*.html"))


def find_corrupt_pages(file: Path) -> bool:
    """Find corrupt pages."""
    
    # Check if the page is empty
    if os.stat(file).st_size == 0:
        print(f"Empty HTML file: {file}")
        return True
    
    with file.open(encoding="utf-8") as html_file:
        try:
            # Parse HTML file using BeautifulSoup
            parsed_html = BeautifulSoup(html_file.read(), "html.parser")
            
            # Check if the page is an XML feed
            if parsed_html.find("rss") is not None or parsed_html.find("feed") is not None:
                print(f"XML feed found: {file}")
                return True
            
            # Check if h2 header contains "Checking if the site connection is secure" text
            h2_header = parsed_html.find("h2")
            if h2_header and "Checking if the site connection is secure" in h2_header.get_text():
                print(f"Page blocked by Cloudflare: {file}")
                return True
            
            return False  # Parsing successful, file is not corrupt
        
        except Exception as e:
            print(f"Error parsing HTML file {file}: {e}")
            return True  # Parsing failed, file is corrupt
    

def find_strings(tag):
    """Find strings inside suitable HTML tags."""
    
    if tag.string is None:
        return
    if tag.string.isspace():
        return
    
    # Create regex pattern for "50M", "4,180", "1.5K", "1.5M", "1.5B", "1200+"
    pattern = re.compile(r"(\d+([,.]\d+)?)([MKBP+])")
    if pattern.search(tag.string):
        return
    
    return tag.string


def translate_strings(string):
    """Translate strings to Hindi using Google Translate."""
    
    translator = Translator()
    translation = translator.translate(string, src="en", dest="hi")
    return translation.text


def replace_string(file: Path, old_string: str, new_string: str):
    """Replace the old string with the new string in the file."""
    
    with file.open("r", encoding="utf-8") as f:
        content = f.read()
    
    content = content.replace(old_string, new_string)
    
    with file.open("w", encoding="utf-8") as f:
        f.write(content)


def main():
    root_dir = Path(__file__).parent.joinpath("source/class-central/www.classcentral.com/index.html")
    
    try:
        for file in find_html_files(root_dir):
            if find_corrupt_pages(file):
                print(f"[ERROR] Corrupt page found! {file}")
                print("[INFO] Deleting corrupt page...")
                file.unlink()
                continue
            
            with file.open("r", encoding="utf-8") as f:
                html = f.read()
            
            soup = BeautifulSoup(html, "lxml")
            
            for tag in soup.find_all(exclude_tags):
                string = find_strings(tag)
                if string:
                    translation = translate_strings(string)
                    replace_string(file, string, translation)
                    print(f"[INFO] Translated: {string} -> {translation}")
        
        print("[INFO] Translation completed successfully!")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    
if __name__ == "__main__":
    main()
