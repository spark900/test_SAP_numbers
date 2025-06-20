# app.py
import argparse
import json
import os
import tempfile
import shutil

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF (fitz) ist erforderlich, bitte installieren: pip install pymupdf")

from find_similarities import analyze_folder


def extract_pdf_to_images(pdf_path, output_dir, dpi=300):
    doc = fitz.open(pdf_path)
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(dpi=dpi)
        img_filename = f"page_{page_index+1:04d}.png"
        pix.save(os.path.join(output_dir, img_filename))
    return output_dir


def main():
    parser = argparse.ArgumentParser(
        description="Gruppiert zusammengehörige Seiten eines PDFs oder Bild-Ordners"
    )
    parser.add_argument("path", help="PDF-Datei oder Bild-Ordner")
    parser.add_argument("--threshold", type=int, default=5, help="Clustering-Schwelle")
    args = parser.parse_args()

    path = args.path
    threshold = args.threshold
    temp_dir = None

    if os.path.isfile(path) and path.lower().endswith('.pdf'):
        temp_dir = tempfile.mkdtemp(prefix='pdf_pages_')
        try:
            extract_pdf_to_images(path, temp_dir)
            analyze_path = temp_dir
        except Exception as e:
            print(f"PDF-Konvertierung fehlgeschlagen: {e}")
            shutil.rmtree(temp_dir)
            return
    elif os.path.isdir(path):
        analyze_path = path
    else:
        print(f"Fehler: '{path}' ist kein PDF oder Verzeichnis.")
        return

    result = analyze_folder(analyze_path, threshold)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if temp_dir:
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    main()
