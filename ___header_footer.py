import fitz  # pip install PyMuPDF you got to install this module first
import json

# Set paths
pdf_path = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\batch_7_2023_2024.pdf"
output_path = r"C:\projects\hackathon_ScienceHack\HeaderFooterOut.json"

def extract_lines_from_page(page, n=3):
    """Return the first and last n text lines from a PDF page."""
    blocks = page.get_text("blocks")
    blocks_sorted = sorted(blocks, key=lambda b: b[1])
    lines = [b[4].strip() for b in blocks_sorted if b[4].strip()]
    return lines[:n], lines[-n:]

def is_probably_header(lines):
    """Basic heuristic: check if there's consistent non-empty content at top."""
    return len([line for line in lines if line.strip()]) > 0

def is_probably_footer(lines):
    """Basic heuristic: check if there's consistent non-empty content at bottom."""
    return len([line for line in lines if line.strip()]) > 0

def main(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    results = {}

    for i, page in enumerate(doc):
        first_lines, last_lines = extract_lines_from_page(page)

        has_header = is_probably_header(first_lines)
        has_footer = is_probably_footer(last_lines)

        results[f"page_{i+1}"] = {
            "header": first_lines if has_header else "no header found",
            "footer": last_lines if has_footer else "no footer found"
        }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"Header/Footer detection per page complete. Output saved to: {output_path}")

if __name__ == "__main__":
    main(pdf_path, output_path)
