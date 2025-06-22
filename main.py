# main.py
import os
import argparse
from check_logo import (
    detect_logo_across_pdfs
)

def find_logo(logo_path: str, target_path: str, threshold: float = 0.8):
    """
    Wrapper-Funktion:
    - Wenn target_path ein Verzeichnis ist, durchsucht alle PDFs darin.
    - Wenn target_path eine einzelne PDF-Datei ist, überprüft nur diese.
    Gibt eine Liste der PDF-Pfade zurück, die das Logo enthalten.
    """
    if os.path.isdir(target_path):
        pdf_files = [
            os.path.join(target_path, fname)
            for fname in os.listdir(target_path)
            if fname.lower().endswith('.pdf')
        ]
    elif os.path.isfile(target_path) and target_path.lower().endswith('.pdf'):
        pdf_files = [target_path]
    else:
        raise ValueError(f"'{target_path}' ist weder ein PDF noch ein Verzeichnis")

    matches = detect_logo_across_pdfs(logo_path, pdf_files, threshold=threshold)
    return matches

def main():
    parser = argparse.ArgumentParser(description="Logo-Erkennung in PDF-Dokumenten")
    parser.add_argument("logo", help="Pfad zum Logo-Bild (z.B. logo.png)")
    parser.add_argument("target", help="PDF-Datei oder Verzeichnis mit PDFs")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Matching-Schwelle (Standard: 0.8)"
    )
    args = parser.parse_args()

    found = find_logo(args.logo, args.target, threshold=args.threshold)
    if found:
        print("Logo gefunden in den folgenden PDFs:")
        for pdf in found:
            print(" -", pdf)
    else:
        print("Logo wurde in keinem der angegebenen PDFs gefunden.")

if __name__ == "__main__":
    main()
