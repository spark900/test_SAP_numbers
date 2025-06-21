import os
import json
import re
import PyPDF2

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            return full_text.lower()  # Return normalized text for case-insensitive matching
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
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

YEAR_PATTERNS = [
    r'\b(20[0-3]\d)\b',  # Years from 2000-2039
    r'\b(19\d{2})\b'     # Years from 1900-1999
]

# Enhanced address patterns with common abbreviations - FIXED REGEX
ADDRESS_PATTERNS = {
    "STREET": [
        r'\b([a-zäöüß]+(?:[- ](?:[a-zäöüß]+))?\.?\s*\d{0,4}[a-z]?)\b',  # Fixed pattern
        r'\b([a-zäöüß]+(?:[- ](?:[a-zäöüß]+))?\.?\b'  # Street name only
    ],
    "CITY": [
        r'\b([a-z][a-zäöüß]+(?:[- ](?:[a-z][a-zäöüß]+))?)\b'  # City names
    ],
    "ZIP_CODE": [
        r'\b(\d{4,5})\b'  # ZIP codes (4-5 digits)
    ],
    "COUNTRY": [
        r'\b(deutschland|germany|österreich|austria|schweiz|switzerland)\b'
    ]
}

# Common street suffix abbreviations with enhanced matching
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
    r'\bstr\b': 'straße',  # Common abbreviation
    r'\bpl\b': 'platz',    # Common abbreviation
    r'\bstr\.\b': 'straße' # Abbreviation with dot
}

def extract_dates(text):
    dates = set()
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            # Normalize different date formats
            if re.match(r'\d{4}-\d{2}-\d{2}', match):
                dates.add(match)  # Already in YYYY-MM-DD format
            elif re.match(r'\d{2}\.\d{2}\.\d{4}', match):
                # Convert DD.MM.YYYY to YYYY-MM-DD
                d, m, y = match.split('.')
                dates.add(f"{y}-{m.zfill(2)}-{d.zfill(2)}")
            elif re.match(r'\d{4}\.\d{2}\.\d{2}', match):
                # Convert YYYY.MM.DD to YYYY-MM-DD
                y, m, d = match.split('.')
                dates.add(f"{y}-{m}-{d}")
            elif re.match(r'\d{2}/\d{2}/\d{4}', match):
                # Convert MM/DD/YYYY to YYYY-MM-DD
                m, d, y = match.split('/')
                dates.add(f"{y}-{m.zfill(2)}-{d.zfill(2)}")
            elif re.match(r'\d{4}/\d{2}/\d{2}', match):
                # Convert YYYY/MM/DD to YYYY-MM-DD
                y, m, d = match.split('/')
                dates.add(f"{y}-{m}-{d}")
            elif re.match(r'\d{8}', match):
                # Convert YYYYMMDD to YYYY-MM-DD
                dates.add(f"{match[:4]}-{match[4:6]}-{match[6:8]}")
            else:
                # Keep other formats as-is for now
                dates.add(match)
    return dates

def extract_years(text):
    years = set()
    for pattern in YEAR_PATTERNS:
        matches = re.findall(pattern, text)
        years.update(matches)
    return years

def extract_address_components(text):
    components = {
        "STREET": set(),
        "CITY": set(),
        "ZIP_CODE": set(),
        "COUNTRY": set()
    }
    
    # Extract street names
    for pattern in ADDRESS_PATTERNS["STREET"]:
        try:
            matches = re.findall(pattern, text)
            for match in matches:
                street_name = match.strip()
                # Normalize street suffixes
                for pattern, replacement in STREET_SUFFIXES.items():
                    street_name = re.sub(pattern, replacement, street_name, flags=re.IGNORECASE)
                components["STREET"].add(street_name)
        except re.error as e:
            print(f"Regex error with pattern '{pattern}': {str(e)}")
    
    # Extract cities
    for pattern in ADDRESS_PATTERNS["CITY"]:
        try:
            matches = re.findall(pattern, text)
            for match in matches:
                components["CITY"].add(match.strip())
        except re.error as e:
            print(f"Regex error with pattern '{pattern}': {str(e)}")
    
    # Extract ZIP codes
    for pattern in ADDRESS_PATTERNS["ZIP_CODE"]:
        try:
            matches = re.findall(pattern, text)
            components["ZIP_CODE"].update(matches)
        except re.error as e:
            print(f"Regex error with pattern '{pattern}': {str(e)}")
    
    # Extract countries
    for pattern in ADDRESS_PATTERNS["COUNTRY"]:
        try:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            components["COUNTRY"].update(match.strip().lower() for match in matches)
        except re.error as e:
            print(f"Regex error with pattern '{pattern}': {str(e)}")
    
    return components

# Load SAP data
sap_file = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\SAP_data.json"
with open(sap_file, encoding='utf-8') as f:
    sap_data = json.load(f)

# Define fields to match with their weights
field_weights = {
    "Delivery Note Number": 5,        # Highest weight as primary identifier
    "Delivery Note Date": 4,           # Important temporal marker
    "Vendor - Name 1": 4,              # Key vendor information
    "Vendor - Name 2": 2,
    "Vendor - Address - Street": 3,
    "Vendor - Address - Number": 2,
    "Vendor - Address - ZIP Code": 3,  # Higher weight as more unique
    "Vendor - Address - City": 3,
    "Vendor - Address - Country": 3,
    "Vendor - Address - Region": 2,
    "MJAHR": 3                        # Important temporal marker
}

# Preprocess SAP data
sap_entries = []
for entry in sap_data:
    if not entry.get("Delivery Note Number"):
        continue
    
    # Create normalized field values
    normalized_fields = {}
    for field in field_weights.keys():
        value = entry.get(field)
        if value is None:
            continue
            
        # Handle different data types
        if isinstance(value, (int, float)):
            normalized = str(value)
        elif isinstance(value, str):
            # Normalize string: lowercase, remove special characters except hyphens
            normalized = re.sub(r'[^\w\s-]', '', value.lower())
        else:
            normalized = str(value).lower()
            
        normalized_fields[field] = normalized
    
    # Add delivery year separately
    delivery_year = None
    if entry.get("Delivery Note Date"):
        try:
            delivery_year = entry["Delivery Note Date"][:4]  # Extract YYYY
        except:
            pass
    
    sap_entries.append({
        'entry': entry,
        'normalized': normalized_fields,
        'delivery_year': delivery_year
    })

# Set paths
pdf_folder = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\batch_6_2023_1"
output_path = r"C:\projects\hackathon_ScienceHack\output_comprehensive.json"

# Process PDFs
results = []
threshold = 8  # Minimum score threshold for a valid match

for filename in os.listdir(pdf_folder):
    if not filename.lower().endswith('.pdf'):
        continue
        
    pdf_path = os.path.join(pdf_folder, filename)
    pdf_text = extract_text_from_pdf(pdf_path)
    
    # Extract dates, years, and address components from PDF text
    extracted_dates = extract_dates(pdf_text)
    extracted_years = extract_years(pdf_text)
    extracted_address = extract_address_components(pdf_text)
    
    best_score = 0
    best_entry = None
    best_match_details = {}
    
    for sap_entry in sap_entries:
        score = 0
        match_details = {}
        
        # Score each field
        for field, normalized_value in sap_entry['normalized'].items():
            # Special handling for date field
            if field == "Delivery Note Date":
                # Extract date in YYYY-MM-DD format
                date_str = normalized_value[:10] if len(normalized_value) >= 10 else normalized_value
                
                # Check for exact date match
                if date_str in extracted_dates:
                    score += field_weights[field]
                    match_details[field] = f"Matched: {date_str}"
                else:
                    # Check for year match if full date not found
                    year_str = date_str[:4]
                    if year_str in extracted_years:
                        score += field_weights[field] * 0.7  # Partial credit for year match
                        match_details[field] = f"Partial: Year matched {year_str}"
                    else:
                        match_details[field] = "Not matched"
                continue
                
            # Special handling for MJAHR field (year)
            if field == "MJAHR":
                # Look for exact year match
                if normalized_value in extracted_years:
                    score += field_weights[field]
                    match_details[field] = f"Matched: {normalized_value}"
                else:
                    match_details[field] = "Not matched"
                continue
                
            # Special handling for address fields
            if field == "Vendor - Address - Street":
                # Normalize SAP street name for comparison
                sap_street = normalized_value
                for pattern, replacement in STREET_SUFFIXES.items():
                    sap_street = re.sub(pattern, replacement, sap_street, flags=re.IGNORECASE)
                
                # Check against extracted streets
                matched = False
                for street in extracted_address["STREET"]:
                    # Use flexible matching with normalization
                    norm_street = street
                    for pattern, replacement in STREET_SUFFIXES.items():
                        norm_street = re.sub(pattern, replacement, norm_street, flags=re.IGNORECASE)
                    
                    if sap_street == norm_street:
                        score += field_weights[field]
                        match_details[field] = f"Matched: {street}"
                        matched = True
                        break
                if not matched:
                    match_details[field] = "Not matched"
                continue
                
            if field == "Vendor - Address - City":
                # Check against extracted cities
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
                # Check against extracted countries
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
                # Check against extracted ZIP codes
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
                
            # Special handling for other numeric fields
            if field in ["Vendor - Address - Number"]:
                # Look for exact number matches
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
                # Try token-based matching for longer strings
                tokens = normalized_value.split()
                matched_tokens = sum(1 for token in tokens if token in pdf_text)
                
                if matched_tokens > 0:
                    # Partial match score based on token coverage
                    partial_score = field_weights[field] * (matched_tokens / len(tokens)) * 0.7
                    score += partial_score
                    match_details[field] = f"Partial ({matched_tokens}/{len(tokens)} tokens)"
                else:
                    match_details[field] = "Not matched"
        
        # Check if this is the best match so far
        if score > best_score:
            best_score = score
            best_entry = sap_entry
            best_match_details = match_details
    
    # Check if best score meets threshold
    if best_score >= threshold and best_entry:
        results.append({
            "filename": filename,
            "Delivery Note Number": best_entry['entry']["Delivery Note Number"],
            "MBLNR": best_entry['entry']["MBLNR"],
            "year": best_entry['delivery_year'],
            "match_score": best_score,
            "match_details": best_match_details
        })
        print(f"✅ Matched {filename} with score {best_score}")
    else:
        print(f"⚠️ No match for {filename} (best score: {best_score})")

# Save results
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print(f"\n✅ Matched {len(results)}/{len(os.listdir(pdf_folder))} files")
print(f"Results saved to {output_path}")