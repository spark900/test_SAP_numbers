import os
import json
import re
import PyPDF2
import numpy as np
import sys

def extract_text_from_pdf_page(pdf_path, page_num):
    """Extracts text from a single page of a PDF."""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if 0 <= page_num < len(reader.pages):
                page = reader.pages[page_num]
                text = page.extract_text()
                if text:
                    return text.lower()
    except Exception as e:
        print(f"Error processing page {page_num} of {pdf_path}: {str(e)}")
    return ""

# Enhanced date extraction patterns
DATE_PATTERNS = [
    r'\b\d{4}-\d{2}-\d{2}\b',       # YYYY-MM-DD
    r'\b\d{2}\.\d{2}\.\d{4}\b',     # DD.MM.YYYY
    r'\b\d{4}\.\d{2}\.\d{2}\b',     # YYYY.MM.DD
    r'\b\d{2}/\d{2}/\d{4}\b',       # MM/DD/YYYY
    r'\b\d{4}/\d{2}/\d{2}\b',       # YYYY/MM/DD
    r'\b\d{1,2}\s+[A-Za-z]{3,10}\s+\d{4}\b',  # 01 January 2023
    r'\b[A-Za-z]{3,10}\s+\d{1,2},\s+\d{4}\b',  # January 01, 2023
    r'\b\d{8}\b'                     # YYYYMMDD
]

def extract_dates(text):
    """Extracts and normalizes dates from text."""
    dates = set()
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            # Normalize different date formats to YYYY-MM-DD
            if re.match(r'\d{4}-\d{2}-\d{2}', match):
                dates.add(match)
            elif re.match(r'\d{2}\.\d{2}\.\d{4}', match):
                d, m, y = match.split('.')
                dates.add(f"{y}-{m.zfill(2)}-{d.zfill(2)}")
            elif re.match(r'\d{4}\.\d{2}\.\d{2}', match):
                y, m, d = match.split('.')
                dates.add(f"{y}-{m}-{d}")
            elif re.match(r'\d{2}/\d{2}/\d{4}', match):
                m, d, y = match.split('/')
                dates.add(f"{y}-{m.zfill(2)}-{d.zfill(2)}")
            elif re.match(r'\d{4}/\d{2}/\d{2}', match):
                y, m, d = match.split('/')
                dates.add(f"{y}-{m}-{d}")
            elif re.match(r'\d{8}', match):
                dates.add(f"{match[:4]}-{match[4:6]}-{match[6:8]}")
            else:
                dates.add(match)
    return dates

def get_document_details(text, sap_entries):
    """
    Finds the best matching SAP entry for a given text (a PDF page)
    and returns the details of that entry. This is used to identify
    the 'owner' of a page.
    """
    best_score = -1
    best_entry = None

    for sap_entry in sap_entries:
        score = 0
        # Simple scoring based on presence of key identifiers
        if sap_entry['normalized'].get("Delivery Note Number") and sap_entry['normalized']["Delivery Note Number"] in text:
            score += 5
        if sap_entry['normalized'].get("Vendor - Name 1") and sap_entry['normalized']["Vendor - Name 1"] in text:
            score += 4

        if score > best_score:
            best_score = score
            best_entry = sap_entry

    return best_entry

def calculate_match_score(text1, text2, page1_details):
    """
    Calculates the match score between two pages based on the provided criteria.
    `page1_details` is the SAP entry corresponding to the first page.
    """
    if not page1_details:
        return 0

    score = 0
    details = page1_details['normalized']

    company = details.get("Vendor - Name 1", "")
    order_no = details.get("Delivery Note Number", "") # Using Delivery Note as a proxy for order/PO
    address = details.get("Vendor - Address - Street", "") # Simplified address check
    date = details.get("Delivery Note Date", "")

    # Convert date to a common format for checking
    if date:
        date = date[:10] # Assume YYYY-MM-DD format

    # Flags for checking criteria
    has_company = company and company in text1 and company in text2
    has_order_no = order_no and order_no in text1 and order_no in text2
    has_address = address and address in text1 and address in text2
    has_date = date and date in text1 and date in text2
    is_page_1 = "page 1 of" in text1 or "seite 1 von" in text1

    # Apply scoring rules
    if has_company and has_order_no and is_page_1:
        score = 20
    elif has_company and has_order_no:
        score = 18
    elif has_address and has_order_no:
        score = 18
    elif has_order_no and has_date:
        score = 18
    elif has_order_no and has_date: # Assuming delivery number is the same as order number
        score = 12
    elif has_order_no: # Delivery number alone
        score = 10
    elif has_order_no: # Order/PO/Delivery note number alone
        score = 8
    elif has_company:
        score = 2

    # Normalize the score to be between 0 and 1
    return score / 20.0

# --- Main Execution ---

# !!! WICHTIG: PFADE AKTUALSIEREN !!!
pdf_path = "Path here"
sap_file_path = "PATH here"


# Überprüfen, ob die Dateien existieren
if not os.path.exists(pdf_path):
    print(f"FEHLER: Die PDF-Datei wurde nicht unter '{pdf_path}' gefunden. Bitte überprüfen Sie den Pfad.")
    sys.exit()
if not os.path.exists(sap_file_path):
    print(f"FEHLER: Die JSON-Datei wurde nicht unter '{sap_file_path}' gefunden. Bitte überprüfen Sie den Pfad.")
    sys.exit()


# Laden und Vorverarbeiten der SAP-Daten
with open(sap_file_path, encoding='utf-8') as f:
    sap_data = json.load(f)

sap_entries = []
for entry in sap_data:
    if not entry.get("Delivery Note Number"):
        continue
    normalized_fields = {}
    for field, value in entry.items():
        if value is None:
            continue
        if isinstance(value, (int, float)):
            normalized = str(value)
        else:
            normalized = re.sub(r'[^\w\s-]', '', str(value).lower())
        normalized_fields[field] = normalized
    sap_entries.append({'entry': entry, 'normalized': normalized_fields})


# 1. Initialisierung
# Extrahieren des Textes von jeder Seite der PDF
all_pages_text = []
try:
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for i in range(len(reader.pages)):
            text = extract_text_from_pdf_page(pdf_path, i)
            all_pages_text.append(text)
except Exception as e:
    print(f"Ein Fehler ist beim Lesen der PDF aufgetreten: {e}")
    sys.exit()

num_pages = len(all_pages_text)
#print(all_pages_text)
if num_pages == 0:
    print("Es konnte kein Text aus der PDF extrahiert werden.")
    sys.exit()

# Identifizieren des 'Eigentümers' (am besten passender SAP-Eintrag) für jede Seite
page_owners = [get_document_details(text, sap_entries) for text in all_pages_text]

# 2. & 3. Paarweises Scoring und Wahrscheinlichkeitsmatrix
# Initialisieren einer leeren Wahrscheinlichkeitsmatrix
prob_matrix = np.zeros((num_pages, num_pages))

# Füllen der Matrix mit Scores
for i in range(num_pages):
    for j in range(num_pages):
        if i == j:
            continue # Eine Seite wird nicht mit sich selbst abgeglichen.

        owner_details_i = page_owners[i]
        text_i = all_pages_text[i]
        text_j = all_pages_text[j]

        score = calculate_match_score(text_i, text_j, owner_details_i)
        prob_matrix[i, j] = score

# 4. & 5. Paarauswahl und Ausgabe
print("Seiten-zu-Seiten-Übereinstimmungswahrscheinlichkeiten:")
for i in range(num_pages):
    if np.sum(prob_matrix[i]) > 0:
        best_match_idx = np.argmax(prob_matrix[i])
        best_match_prob = prob_matrix[i, best_match_idx]

        if best_match_prob > 0:
            print(f"{i+1} -> {best_match_idx+1} mit {best_match_prob*100:.2f}% Wahrscheinlichkeit")