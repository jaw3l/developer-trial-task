import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
import argostranslate.package
import argostranslate.translate
import translatehtml


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
            return True
    
    
def remove_comment_lines(html_text: str) -> str:
    """Remove comment lines from HTML text."""
    
    pattern = re.compile(r"<!--.*?-->", re.DOTALL)
    cleaned_html_text = pattern.sub("", html_text)

    return cleaned_html_text


def translate_html_file(file_path: Path, from_code: str, to_code: str) -> bool:
    """Translates the contents of an HTML file from one language to another, using Argos Translate."""
    try:
        with file_path.open(encoding="utf-8") as f:
            html = f.read()

        # Download and install the translation package
        available_packages = argostranslate.package.get_available_packages()
        available_package = next((p for p in available_packages if p.from_code == from_code and p.to_code == to_code), None)
        if available_package is None:
            print(f"[ERROR] Translation package not found for {from_code} -> {to_code}")
            return False

        package_path = available_package.download()
        argostranslate.package.install_from_path(package_path)

        # Perform the translation
        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang = next((l for l in installed_languages if l.code == from_code), None)
        to_lang = next((l for l in installed_languages if l.code == to_code), None)
        if from_lang is None or to_lang is None:
            print(f"[ERROR] Source or target language not found: {from_code} -> {to_code}")
            return False

        translation = from_lang.get_translation(to_lang)
        translated_soup = translatehtml.translate_html(translation, html)
        translated_html = translated_soup.prettify()

        # Save the translated HTML to a new file
        translated_file_path = file_path.parent.joinpath(f"{file_path.stem}_translated{file_path.suffix}")
        with translated_file_path.open(mode="w", encoding="utf-8") as f:
            f.write(translated_html)

        return True

    except Exception as e:
        print(f"[ERROR] Failed to translate {file_path}: {e}")
        return False


def main():
    root_dir: Path = Path(__file__).parent.joinpath("source/class-central/www.classcentral.com/index.html")
    new_dir: Path = Path(__file__).parent.mkdir("translated", exist_ok=True)
    from_code = "en"
    to_code = "hi"
    
    try:
        for file in find_html_files(root_dir):
            if find_corrupt_pages(file):
                print(f"[ERROR] Corrupt page found! {file}")
                print("[INFO] Deleting corrupt page...")
                file.unlink()
                continue
            
            with file.open(encoding="utf-8") as html_file:
                html_text = html_file.read()
                cleaned_html_text = remove_comment_lines(html_text)
            
            if not translate_html_file(file, from_code, to_code):
                print(f"[ERROR] Failed to translate HTML file: {file}")
                continue
                
            translated_file = file.parent.joinpath(f"{file.stem}_translated{file.suffix}")
            with translated_file.open(mode="r", encoding="utf-8") as translated_html_file:
                translated_html_text = translated_html_file.read()
            
            print(f"[INFO] Translated HTML file: {file} -> {translated_file}")
        
        print("[INFO] Translation completed successfully!")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    
if __name__ == "__main__":
    main()
