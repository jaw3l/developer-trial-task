import os
import re
import time
import translatehtml
from pathlib import Path
from bs4 import BeautifulSoup, PageElement
import argostranslate.package
import argostranslate.translate
from googletrans import Translator


def find_html_files(root_dir: Path) -> list:
    """Find all HTML files in the root directory."""

    if not root_dir.is_dir():
        raise ValueError("Root directory is not a directory")

    return list(root_dir.glob("**/*.html"))


def find_corrupt_pages(file: Path) -> bool:
    """Find corrupt pages."""

    try:
        with file.open(encoding="utf-8") as html_file:
            # Check if the page is empty
            if os.stat(file).st_size == 0:
                print(f"Empty HTML file: {file}")
                return True

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

    except FileNotFoundError:
        print(f"File not found: {file}")
        return True

    except Exception as e:
        print(f"Error parsing HTML file {file}: {e}")
        return True


def remove_comment_lines(html_text: str) -> str:
    """Remove comment lines from HTML text."""
    
    if not html_text:
        return ""

    pattern = re.compile(r"<!--.*?-->", re.DOTALL | re.MULTILINE)
    cleaned_html_text = pattern.sub("", html_text)

    return cleaned_html_text


def find_strings(tag: PageElement):
    """Find strings inside suitable HTML tags."""
    
    if tag.name == "img" and tag.get("alt") is not None:
        return tag
    
    if tag.name == "input" and tag.get("placeholder") is not None:
        return tag
        
    if tag.string is None:
        return
    
    if tag.string.isspace():
        return

    # Check if the word is in Hindi language
    for word in tag.string:
        if any('\u0900' <= char <= '\u097f' for char in word):
            return
    
    return tag

def translate_strings(text: str, max_retries: int = 3, timeout: int = 2) -> str:
    """Translate strings to Hindi using Google Translate."""

    translator = Translator()
    retries = 0
    while retries < max_retries:
        try:
            translation = translator.translate(text, src="en", dest="hi")
            return translation.text
        except Exception as e:
            print(f"Error while translating retrying after {timeout} seconds.")
            time.sleep(timeout)
            retries += 1
    print("Maximum number of retries reached.")
    exit()

def post_processing(file: Path):
    """Post-processing of translated HTML files."""
    
    # Fixing the doctype declaration
    source_text = "एचटीएमएल"
    target_text = "<!DOCTYPE html>"
    with file.open(mode="r+", encoding="utf-8") as f:
        file_content = f.read()
        if source_text in file_content:
            file_content = file_content.replace(source_text, target_text)
            f.seek(0)
            f.write(file_content)
            f.truncate()
            print(f"Doctype declaration is fixed.")
            
    with file.open(mode="r+", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        
        tags_to_check = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "a", "li", "td", "th", "title", "input", "img"]
        
        for tag in soup.find_all(tags_to_check):
            filtered_tag = find_strings(tag)
            if filtered_tag:
                if tag.name == "input":
                    translated_string = translate_strings(tag.get("placeholder"))
                    print(f"Replacing {tag.get('placeholder')} --> {translated_string}")
                    tag["placeholder"] = translated_string
                    continue
                
                if tag.name == "img":
                    translated_string = translate_strings(tag.get("alt"))
                    print(f"Replacing {tag.get('alt')} --> {translated_string}")
                    tag["alt"] = translated_string
                    continue
                
                translated_string = translate_strings(tag.string)
                print(f"Replacing {tag.string} --> {translated_string}")
                tag.string.replace_with(translated_string)
                
        
        # Prettyfying the HTML file using BeautifulSoup
        pretty_html = soup.prettify()
        
        # Replace the file's content with the prettified version
        f.seek(0)
        f.write(pretty_html)
        f.truncate()
        


    print(f"Post-processing complete for {file}")


def main():
    from_code = "en"
    to_code = "hi"
    target_dir = Path(__file__).parent.joinpath("target")

    # Create target directory if it does not exist
    if not target_dir.exists():
        target_dir.mkdir()

    # Download and install Argos Translate package
    available_packages = argostranslate.package.get_available_packages()
    available_package = list(
        filter(
            lambda x: x.from_code == from_code and x.to_code == to_code, available_packages
        )
    )[0]
    download_path = available_package.download()
    argostranslate.package.install_from_path(download_path)

    # Get installed languages
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = list(filter(lambda x: x.code == from_code, installed_languages))[0]
    to_lang = list(filter(lambda x: x.code == to_code, installed_languages))[0]

    # Find all HTML files in the root directory
    root_dir = Path(__file__).parent.joinpath("source/class-central/www.classcentral.com/")
    html_files = find_html_files(root_dir)

    for html_file in html_files:
        # Check for corrupt pages
        if find_corrupt_pages(html_file):
            print(f"Corrupt page found: {html_file}")
            continue

        # Translate HTML file
        with html_file.open(encoding="utf-8") as f:
            html_text = f.read()
            cleaned_html_text = remove_comment_lines(html_text)
            translated_html_text = translatehtml.translate_html(from_lang.get_translation(to_lang), cleaned_html_text)

        # Write translated HTML to target file
        target_file = target_dir.joinpath(html_file.name)
        with target_file.open(mode="w+", encoding="utf-8") as f:
            f.write(str(translated_html_text))

        print(f"Translated {html_file} to {to_code} and wrote to {target_file}")
        
        # Post-processing
        post_processing(target_file)
        
if __name__ == "__main__":
    main()
    # post_processing(Path(__file__).parent.joinpath("target/about.html"))
