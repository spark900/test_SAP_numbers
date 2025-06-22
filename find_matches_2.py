import os
import json
import re
import argparse
from typing import List, Dict, Any
import PyPDF2


def normalize_value(value: Any) -> str:
    """
    Normalizes a JSON field value to lowercase string without punctuation.
    """
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return re.sub(r'[^\w\s-]', '', value.lower())
    return str(value).lower()


class JSONLoader:
    """
    Loads and normalizes JSON entries for matching.
    """
    def __init__(self, json_path: str, field_weights: Dict[str, float]):
        self.json_path = json_path
        self.field_weights = field_weights
        self.entries: List[Dict[str, Any]] = []
        self.sum_weights = sum(field_weights.values())

    def load(self) -> None:
        with open(self.json_path, encoding='utf-8') as f:
            data = json.load(f)

        for entry in data:
            if not entry.get('Delivery Note Number'):
                continue
            norm = {field: normalize_value(entry.get(field))
                    for field in self.field_weights if entry.get(field) is not None}
            # extract delivery date YYYY-MM-DD
            date_val = normalize_value(entry.get('Delivery Note Date', ''))[:10]
            self.entries.append({'original': entry, 'normalized': norm, 'date': date_val})


class PDFExtractor:
    """
    Extracts text from each page of a single PDF.
    """
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_pages(self) -> List[str]:
        try:
            with open(self.pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return [(page.extract_text() or '').lower() for page in reader.pages]
        except Exception as e:
            print(f"Error reading PDF {self.pdf_path}: {e}")
            return []


class ProbabilityScorer:
    """
    Scores one JSON entry against one PDF page using hierarchical rules and field weights.
    """
    RULE_POINTS = [
        (lambda e, t, n: e['normalized'].get('Vendor - Name 1') and \
                         e['normalized'].get('Delivery Note Number') and \
                         e['normalized'].get('Vendor - Name 1') in t and \
                         e['normalized'].get('Delivery Note Number') in t and \
                         f"page {n} of" in t, 20),
        (lambda e, t, n: e['normalized'].get('Vendor - Name 1') and \
                         e['normalized'].get('Delivery Note Number') and \
                         e['normalized'].get('Vendor - Name 1') in t and \
                         e['normalized'].get('Delivery Note Number') in t, 18),
        (lambda e, t, n: e['normalized'].get('Vendor - Address - Street') and \
                         e['normalized'].get('Delivery Note Number') and \
                         e['normalized'].get('Vendor - Address - Street') in t and \
                         e['normalized'].get('Delivery Note Number') in t, 18),
        (lambda e, t, n: e['normalized'].get('Delivery Note Number') and \
                         e['normalized'].get('Delivery Note Date') and \
                         e['normalized'].get('Delivery Note Number') in t and \
                         e['date'] and e['date'] in t, 18),
        (lambda e, t, n: e['normalized'].get('Delivery Note Number') and \
                         e['date'] and e['date'] in t, 12),
        (lambda e, t, n: e['normalized'].get('Delivery Note Number') and \
                         e['normalized'].get('Delivery Note Number') in t, 10),
        (lambda e, t, n: e['normalized'].get('Vendor - Name 1') and \
                         e['normalized'].get('Vendor - Name 1') in t, 2),
    ]

    def __init__(self, field_weights: Dict[str, float]):
        self.field_weights = field_weights
        self.sum_weights = sum(field_weights.values())

    def score_page_entry(self, entry: Dict[str, Any], page_text: str, page_num: int) -> float:
        # Hierarchical rules
        for cond, pts in self.RULE_POINTS:
            try:
                if cond(entry, page_text, page_num):
                    return pts / 20.0
            except Exception:
                continue
        # Fallback: individual field matching
        m = 0.0
        norm = entry['normalized']
        for field, w in self.field_weights.items():
            v = norm.get(field)
            if v and v in page_text:
                m += w
        return m / self.sum_weights


def main():
    parser = argparse.ArgumentParser(
        description="Map each PDF page to best JSON entry, then compute inter-page probabilities."
    )
    parser.add_argument('-f', '--pdf-file', required=True, help='Single PDF file')
    parser.add_argument('-j', '--json-path', required=True, help='JSON metadata file')
    args = parser.parse_args()

    # Field weights
    field_weights = {
        'Delivery Note Number': 10,
        'Delivery Note Date': 8,
        'Purchase Order Number': 4,
        'MBLNR': 3,
        'Vendor - Name 1': 5,
        'Vendor - Name 2': 1,
        'Vendor - Address - Street': 3,
        'Vendor - Address - Number': 2,
        'Vendor - Address - ZIP Code': 3,
        'Vendor - Address - City': 3,
        'Vendor - Address - Country': 2,
        'Vendor - Address - Region': 1,
        'MJAHR': 2
    }

    # Load JSON entries
    loader = JSONLoader(args.json_path, field_weights)
    loader.load()

    # Extract PDF pages
    pages = PDFExtractor(args.pdf_file).extract_pages()
    n = len(pages)
    print(f"PDF '{os.path.basename(args.pdf_file)}' mit {n} Seiten analysiert.")

    # Score each page vs each entry
    scorer = ProbabilityScorer(field_weights)
    scores = [[0.0] * len(loader.entries) for _ in range(n)]
    for i, text in enumerate(pages):
        for ei, entry in enumerate(loader.entries):
            scores[i][ei] = scorer.score_page_entry(entry, text, i+1)

    # Map each page to best entry
    best_mapping = []  # list of tuples (entry_idx, score)
    print("\nSeiten-Mapping zu JSON-Einträgen:")
    for i in range(n):
        best_ei, best_score = max(enumerate(scores[i]), key=lambda x: x[1])
        entry = loader.entries[best_ei]['original']
        dn = entry.get('Delivery Note Number')
        print(f"Seite {i+1} → Eintrag '{dn}' mit {best_score*100:.1f}%")
        best_mapping.append((best_ei, best_score))

    # Compute inter-page probabilities based on mapped entries
    print("\nInter-Seiten Wahrscheinlichkeiten:")
    for i in range(n):
        ei, si = best_mapping[i]
        for j in range(i+1, n):
            sj = scores[j][ei]
            p = min(si, sj)
            print(f"{i+1} --> {j+1} mit {p*100:.1f}%")

if __name__ == '__main__':
    main()