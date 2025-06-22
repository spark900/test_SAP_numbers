'''
import os
import json
import re
from typing import List, Dict, Tuple, Set, Any

import PyPDF2


class PDFExtractor:
    """
    Responsible for extracting text from a single PDF, page by page.
    """
    def __init__(self, pdf_path: str):
        """
        :param pdf_path: Path to the PDF file.
        """
        self.pdf_path = pdf_path

    def extract_pages(self) -> List[str]:
        """
        Extracts text from each page of the PDF.

        :return: List of page texts (normalized to lowercase).
        """
        try:
            with open(self.pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                texts: List[str] = []
                for page in reader.pages:
                    txt = page.extract_text() or ''
                    texts.append(txt.lower())
                return texts
        except Exception as e:
            print(f"Error reading {self.pdf_path}: {e}")
            return []


class JSONLoader:
    """
    Loads and normalizes JSON metadata entries for matching.
    """
    def __init__(self, json_path: str, field_weights: Dict[str, float]):
        """
        :param json_path: Path to the JSON file containing metadata entries.
        :param field_weights: Weights assigned to each field for scoring.
        """
        self.json_path = json_path
        self.field_weights = field_weights
        self.entries: List[Dict[str, Any]] = []

    def load(self) -> None:
        """
        Loads JSON file and normalizes specified fields.
        Populates self.entries with structures:
            {
              'original': {...},
              'normalized': {...},
              'delivery_year': str | None
            }
        """
        with open(self.json_path, encoding='utf-8') as f:
            data = json.load(f)

        for entry in data:
            if not entry.get('Delivery Note Number'):
                continue
            norm_fields: Dict[str, str] = {}
            for field in self.field_weights:
                val = entry.get(field)
                if val is None:
                    continue
                norm_fields[field] = self._normalize_value(val)

            year = None
            date = entry.get('Delivery Note Date')
            if date:
                year = date[:4]

            self.entries.append({
                'original': entry,
                'normalized': norm_fields,
                'delivery_year': year
            })

    def _normalize_value(self, value: Any) -> str:
        """
        Converts values to lowercase, string form, stripping special characters.
        """
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            cleaned = re.sub(r'[^\w\s-]', '', value.lower())
            return cleaned
        return str(value).lower()


class FeatureExtractor:
    """
    Extracts dates, years, and address components from page text.
    """
    DATE_PATTERNS = [
        r'\b\d{4}-\d{2}-\d{2}\b', r'\b\d{2}\.\d{2}\.\d{4}\b',
        r'\b\d{4}\.\d{2}\.\d{2}\b', r'\b\d{2}/\d{2}/\d{4}\b',
        r'\b\d{4}/\d{2}/\d{2}\b', r'\b\d{1,2}\s+[A-Za-z]{3,10}\s+\d{4}\b',
        r'\b[A-Za-z]{3,10}\s+\d{1,2},\s+\d{4}\b', r'\b\d{8}\b'
    ]
    YEAR_PATTERNS = [r'\b(20[0-3]\d)\b', r'\b(19\d{2})\b']
    ADDRESS_PATTERNS = {  # abbreviated for brevity
        # ... same as before ...
    }
    STREET_SUFFIXES = {  # abbreviated for brevity
        # ... same as before ...
    }

    @classmethod
    def extract_dates(cls, text: str) -> Set[str]:
        # implementation as before
        ...

    @classmethod
    def extract_years(cls, text: str) -> Set[str]:
        # implementation as before
        ...

    @classmethod
    def extract_address(cls, text: str) -> Dict[str, Set[str]]:
        # implementation as before
        ...


class ProbabilityCalculator:
    """
    Computes matching probabilities between JSON entries and PDF pages.
    """
    def __init__(self, field_weights: Dict[str, float], threshold: float = 0.8):
        self.field_weights = field_weights
        self.threshold = threshold

    def score_pair(self, entry: Dict[str, Any], page_text: str, page_num: int) -> float:
        # implementation as before
        ...

    def build_matrix(
        self,
        entries: List[Dict[str, Any]],
        all_pages: Dict[str, List[str]]
    ) -> Dict[Tuple[int, str, int], float]:
        matrix: Dict[Tuple[int, str, int], float] = {}
        for i, entry in enumerate(entries):
            for fname, pages in all_pages.items():
                for j, text in enumerate(pages, start=1):
                    matrix[(i, fname, j)] = self.score_pair(entry, text, j)
        return matrix


class PairSelector:
    """
    Selects the best mutual matches based on the probability matrix.
    """
    def __init__(self, threshold: float):
        self.threshold = threshold

    def select(self, matrix: Dict[Tuple[int, str, int], float]) -> List[Tuple[int, int, float]]:
        """
        Für jede Seite (hier page_num) wird der JSON-Eintrag mit der höchsten Score ausgewählt,
        sofern die Score >= threshold ist.

        :param matrix: Dict mit Keys (entry_idx, filename, page_num) und float-Scores (oder None)
        :return: Liste von Tuples (entry_idx, page_num, score)
        """
        # best[pnum] = (entry_idx, prob)
        best: Dict[int, Tuple[int, float]] = {}

        for (entry_idx, _fname, page_num), prob in matrix.items():
            # überspringen, wenn kein Score berechnet wurde
            if prob is None:
                continue

            prev = best.get(page_num)
            # wenn noch kein Eintrag oder neue Score ist höher
            if prev is None or prob > prev[1]:
                best[page_num] = (entry_idx, prob)

        matches: List[Tuple[int, int, float]] = []
        for page_num, (entry_idx, prob) in best.items():
            if prob >= self.threshold:
                matches.append((entry_idx, page_num, prob))

        return matches


class PDFAssembler:
    """
    Merges PDF pages into grouped documents based on matches from a single PDF.
    """
    def __init__(self, pdf_path: str, output_folder: str):
        self.pdf_path = pdf_path
        self.output_folder = output_folder

    def assemble(self, matches: List[Tuple[int, int, float]]) -> None:
        """
        :param matches: List of (entry_idx, page_num, score)
        """
        # Cluster pages by entry_idx
        clusters: Dict[int, List[int]] = {}
        for entry_idx, pnum, _prob in matches:
            clusters.setdefault(entry_idx, []).append(pnum)

        for entry_idx, pages in clusters.items():
            writer = PyPDF2.PdfWriter()
            reader = PyPDF2.PdfReader(self.pdf_path)
            for pnum in pages:
                writer.add_page(reader.pages[pnum - 1])
            out_name = f"group_{entry_idx}.pdf"
            out_path = os.path.join(self.output_folder, out_name)
            with open(out_path, 'wb') as f_out:
                writer.write(f_out)
            print(f"Saved grouped PDF: {out_path}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="PDF-JSON pairing für ein einzelnes PDF"
    )
    parser.add_argument('--pdf-file', '-f', required=True, help='Pfad zur einzelnen PDF-Datei')
    parser.add_argument('--json-path', '-j', required=True, help='Pfad zur SAP_data.json')
    parser.add_argument('--output-folder', '-o', required=True, help='Zielordner für die Gruppendateien')
    parser.add_argument('--threshold', '-t', type=float, default=0.8, help='Schwellenwert 0–1')
    args = parser.parse_args()

    # Step 1: Extract pages
    extractor = PDFExtractor(args.pdf_file)
    pages = extractor.extract_pages()
    filename = os.path.basename(args.pdf_file)
    all_pages = {filename: pages}

    # Step 2: Load JSON
    field_weights = {  # wie zuvor definiert
        'Delivery Note Number': 5,
        'Delivery Note Date': 4,
        'Purchase Order Number': 4,
        'MBLNR': 3,
        'Vendor - Name 1': 4,
        'Vendor - Name 2': 1,
        'Vendor - Address - Street': 3,
        'Vendor - Address - Number': 2,
        'Vendor - Address - ZIP Code': 3,
        'Vendor - Address - City': 3,
        'Vendor - Address - Country': 2,
        'Vendor - Address - Region': 1,
        'MJAHR': 2
    }
    loader = JSONLoader(args.json_path, field_weights)
    loader.load()

    # Step 3: Compute probability matrix
    calc = ProbabilityCalculator(field_weights, threshold=args.threshold)
    matrix = calc.build_matrix(loader.entries, all_pages)

    # Step 4: Select pairs for single PDF
    selector = PairSelector(threshold=args.threshold)
    matches = selector.select(matrix)

    # Step 5: Assemble grouped pages
    assembler = PDFAssembler(args.pdf_file, args.output_folder)
    assembler.assemble(matches)
    print("Processing complete.")
    '''


import os
import re
import argparse
from typing import List
import PyPDF2
from difflib import SequenceMatcher


def compute_similarity(text1: str, text2: str) -> float:
    """
    Compute a similarity ratio between two texts using SequenceMatcher.
    Returns a float between 0 and 1.
    """
    return SequenceMatcher(None, text1, text2).ratio()


class PDFExtractor:
    """
    Extracts text from each page of a single PDF file.
    """
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_pages(self) -> List[str]:
        """
        Reads the PDF and returns a list where each element is the page text (lowercased).
        """
        try:
            with open(self.pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                pages: List[str] = []
                for page in reader.pages:
                    text = page.extract_text() or ''
                    pages.append(text.lower())
                return pages
        except Exception as e:
            print(f"Error reading {self.pdf_path}: {e}")
            return []


def main():
    parser = argparse.ArgumentParser(
        description="Compute page-to-page similarity for a single PDF"
    )
    parser.add_argument(
        '--pdf-file', '-f', required=True,
        help='Path to the PDF file to analyze'
    )
    args = parser.parse_args()

    extractor = PDFExtractor(args.pdf_file)
    pages = extractor.extract_pages()

    if not pages:
        print("No pages extracted. Exiting.")
        return

    num_pages = len(pages)
    print(f"Analyzing {num_pages} pages in '{os.path.basename(args.pdf_file)}'...\n")

    # Compare each page to every other page (i < j)
    for i in range(num_pages):
        for j in range(i + 1, num_pages):
            sim = compute_similarity(pages[i], pages[j])
            print(f"{i+1} --> {j+1} mit {sim*100:.1f}%")


if __name__ == '__main__':
    main()