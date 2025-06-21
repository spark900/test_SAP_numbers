import os
import json
import re
import PyPDF2
from difflib import SequenceMatcher

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as f: 
            reader = PyPDF2.PdfReader(f)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            return full_text.lower()
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return ""

DATE_PATTERNS = [
    r'\b\d{4}-\d{2}-\d{2}\b',       # YYYY-MM-DD
    r'\b\d{2}\.\d{2}\.\d{4}\b',     # DD.MM.YYYY
    r'\b\d{4}\.\d{2}\.\d{2}\b',     # YYYY.MM.DD
    r'\b\d{2}/\d{2}/\d{4}\b',       # MM/DD/YYYY
    r'\b\d{4}/\d{2}/\d{2}\b',       # YYYY/MM/DD
    r'\b\d{1,2}\s+[A-Za-z]{3,10}\s+\d{4}\b',  # 01 January 2023
    r'\b[A-Za-z]{3,10}\s+\d{1,2},\s+\d{4}\b',  # January 01, 2023
    r'\b\d{8}\b'                     # YYYYMMDDD
]

# Global ZIP code patterns
ZIP_PATTERNS = [
    r'\b\d{4,5}\b',          # Standard 4-5 digit ZIP (DE/AT)
    r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b',  # Canadian format (A1A 1A1)
    r'\b\d{5}-\d{4}\b',      # US extended ZIP (12345-6789)
    r'\b\d{5}\b',            # US basic ZIP
    r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b'  # UK format (SW1A 1AA)
]

# Enhanced street suffix handling with fuzzy matching
STREET_SUFFIXES = {
    r'\bstr(?:\.|aße)?\b': 'straße',
    r'\bstrasse\b': 'straße',
    r'\bpl(?:\.|atz)?\b': 'platz',
    r'\ballee\b': 'allee',
    r'\bweg\b': 'weg',
    r'\bg(?:\.|asse)?\b': 'gasse',
    r'\bch(?:\.|aussee)?\b': 'chaussee',
    r'\bblvd\b': 'boulevard',
    r'\bave\b': 'avenue',
    r'\bst(?:\.|reet)?\b': 'street',
    r'\brd\b': 'road',
    r'\bbr(?:\.|ücke)?\b': 'brücke',
    r'\bbruecke\b': 'brücke',
    r'\bprom(?:\.|enade)?\b': 'promenade',
    r'\bstr\b': 'straße',
    r'\bpl\b': 'platz',
    r'\bstr\.\b': 'straße',
    r'\bschlosspl\b': 'schlossplatz',
    r'\bburgstr\b': 'burgstraße'
}

def extract_dates(text):
    dates = set()
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            # Normalization logic remains the same
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

def extract_address_components(text):
    components = {
        "STREET": set(),
        "CITY": set(),
        "ZIP_CODE": set(),
        "COUNTRY": set()
    }
    
    # Extract street names with improved fuzzy matching
    street_pattern = r'\b([a-zäöüß]+(?:[- ](?:[a-zäöüß]+))?\.?\s*\d{0,4}[a-z]?)\b'
    matches = re.findall(street_pattern, text)
    for match in matches:
        street_name = match.strip()
        for pattern, replacement in STREET_SUFFIXES.items():
            street_name = re.sub(pattern, replacement, street_name, flags=re.IGNORECASE)
        components["STREET"].add(street_name)
    
    # Extract cities
    city_pattern = r'\b([a-z][a-zäöüß]+(?:[- ](?:[a-z][a-zäöüß]+))?)\b'
    matches = re.findall(city_pattern, text)
    for match in matches:
        components["CITY"].add(match.strip())
    
    # Extract global ZIP codes
    for pattern in ZIP_PATTERNS:
        matches = re.findall(pattern, text)
        components["ZIP_CODE"].update(matches)
    
    # Extract countries
    country_pattern = r'\b(deutschland|germany|österreich|austria|schweiz|switzerland|italia|italy|france|spanien|spain)\b'
    matches = re.findall(country_pattern, text, flags=re.IGNORECASE)
    components["COUNTRY"].update(match.strip().lower() for match in matches)
    
    return components

def fuzzy_match(str1, str2, threshold=0.8):
    """Fuzzy string matching using sequence matching"""
    return SequenceMatcher(None, str1, str2).ratio() >= threshold

# Load SAP data
sap_file = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\SAP_data.json"
with open(sap_file, encoding='utf-8') as f:
    sap_data = json.load(f)

# Define fields to match with weights
field_weights = {
    "Delivery Note Number": 5,
    "Delivery Note Date": 4,
    "Vendor - Name 1": 4,
    "Vendor - Name 2": 1,
    "Vendor - Address - Street": 3,
    "Vendor - Address - Number": 2,
    "Vendor - Address - ZIP Code": 3,
    "Vendor - Address - City": 3,
    "Vendor - Address - Country": 3,
    "Vendor - Address - Region": 1,
    #"MJAHR": 3
}

# Preprocess SAP data
sap_entries = []
for entry in sap_data:
    if not entry.get("Delivery Note Number"):
        continue
    
    normalized_fields = {}
    for field in field_weights.keys():
        value = entry.get(field)
        if value is None:
            continue
            
        if isinstance(value, (int, float)):
            normalized = str(value)
        elif isinstance(value, str):
            normalized = re.sub(r'[^\w\s-]', '', value.lower())
        else:
            normalized = str(value).lower()
            
        # Normalize street suffixes in SAP data too
        if field == "Vendor - Address - Street":
            for pattern, replacement in STREET_SUFFIXES.items():
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
            
        normalized_fields[field] = normalized
    
    sap_entries.append({
        'entry': entry,
        'normalized': normalized_fields
    })

# Set paths
pdf_folder = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\batch_6_2023_1"
output_path = r"C:\projects\hackathon_ScienceHack\output_comprehensive_2.json"

# Process PDFs
results = []
threshold = 8

for filename in os.listdir(pdf_folder):
    if not filename.lower().endswith('.pdf'):
        continue
        
    pdf_path = os.path.join(pdf_folder, filename)
    pdf_text = extract_text_from_pdf(pdf_path)
    
    extracted_dates = extract_dates(pdf_text)
    extracted_address = extract_address_components(pdf_text)
    
    best_score = 0
    best_entry = None
    best_match_details = {}
    
    for sap_entry in sap_entries:
        score = 0
        match_details = {}
        
        for field, normalized_value in sap_entry['normalized'].items():
            if field == "Delivery Note Date":
                date_str = normalized_value[:10] if len(normalized_value) >= 10 else normalized_value
                
                if date_str in extracted_dates:
                    score += field_weights[field]
                    match_details[field] = f"Matched: {date_str}"
                else:
                    match_details[field] = "Not matched"
                continue

            # MJAHR is not extracted from the document so this code isnt needed.
                
            # if field == "MJAHR":
            #     # Look for exact year match in dates
            #     year_str = normalized_value
            #     year_found = any(date.startswith(year_str) for date in extracted_dates)
                
            #     if year_found:
            #         score += field_weights[field]
            #         match_details[field] = f"Matched in date: {year_str}"
            #     else:
            #         match_details[field] = "Not matched"
            #     continue
                
            if field == "Vendor - Address - Street":
                sap_street = normalized_value
                matched = False
                
                for doc_street in extracted_address["STREET"]:
                    # Fuzzy match for abbreviated forms
                    if fuzzy_match(sap_street, doc_street) or \
                       sap_street in doc_street or \
                       doc_street in sap_street:
                        score += field_weights[field]
                        match_details[field] = f"Matched: {doc_street}"
                        matched = True
                        break
                        
                if not matched:
                    match_details[field] = "Not matched"
                continue
                
            if field == "Vendor - Address - City":
                sap_city = normalized_value
                matched = False
                for city in extracted_address["CITY"]:
                    if sap_city == city:
                        score += field_weights[field]
                        match_details[field] = f"Matched: {city}"
                        matched = True
                        break
                if not matched:
                    match_details[field] = "Not matched"
                continue
                
            if field == "Vendor - Address - Country":
                sap_country = normalized_value
                matched = False
                for country in extracted_address["COUNTRY"]:
                    if sap_country == country:
                        score += field_weights[field]
                        match_details[field] = f"Matched: {country}"
                        matched = True
                        break
                if not matched:
                    match_details[field] = "Not matched"
                continue
                
            if field == "Vendor - Address - ZIP Code":
                sap_zip = normalized_value
                matched = False
                for zip_code in extracted_address["ZIP_CODE"]:
                    if sap_zip == zip_code:
                        score += field_weights[field]
                        match_details[field] = f"Matched: {zip_code}"
                        matched = True
                        break
                if not matched:
                    match_details[field] = "Not matched"
                continue
                
            if field in ["Vendor - Address - Number"]:
                if re.search(rf'\b{re.escape(normalized_value)}\b', pdf_text):
                    score += field_weights[field]
                    match_details[field] = f"Matched: {normalized_value}"
                else:
                    match_details[field] = "Not matched"
                continue
                
            # Standard string matching
            if normalized_value in pdf_text:
                score += field_weights[field]
                match_details[field] = f"Matched: {normalized_value}"
            else:
                tokens = normalized_value.split()
                matched_tokens = sum(1 for token in tokens if token in pdf_text)
                
                if matched_tokens > 0:
                    partial_score = field_weights[field] * (matched_tokens / len(tokens)) * 0.7
                    score += partial_score
                    match_details[field] = f"Partial ({matched_tokens}/{len(tokens)} tokens)"
                else:
                    match_details[field] = "Not matched"
        
        if score > best_score:
            best_score = score
            best_entry = sap_entry
            best_match_details = match_details
    
    if best_score >= threshold and best_entry:
        uid = f"{best_entry['entry']['MBLNR']}_{best_entry['entry']['MJAHR']}"
        results.append({
            "filename": filename,
            "Delivery Note Number": best_entry['entry']["Delivery Note Number"],
            "UID": uid,
            "match_score": best_score,
            "match_details": best_match_details
        })
        print(f"Matched {filename} with score {best_score}")
    else:
        print(f"No match for {filename} (best score: {best_score})")

# Save results
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print(f"\nMatched {len(results)}/{len(os.listdir(pdf_folder))} files")
print(f"Results saved to {output_path}")