import re
import json
from datetime import datetime
from PyPDF2 import PdfReader

pdf_path = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\batch_6_2023_1\20230619_Bauhaus.pdf"
json_path = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\SAP_data.json"
output_path = "test_out_bauhaus.json"

# Extended regex patterns for fuzzy date recognition
date_patterns = [
    r'\b\d{1,2}/\d{1,2}/\d{4}(?:\s+\d{1,2}:\d{2}:\d{2}(?:AM|PM)?)?\b',  # 6/19/2023 or 6/19/2023 4:47:50AM
    r'\b\d{4}-\d{1,2}-\d{1,2}\b',                                      # 2023-06-19
    r'\b\d{8}\b',                                                      # 20230619
    r'\b\d{1,2}[.-]\d{1,2}[.-]\d{4}\b',                                # 19.06.2023
    r'\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b',                            # 19 June 2023
    r'\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b'                           # June 19, 2023
]

# Parse a string into a datetime.date (fuzzy)
def normalize_to_date(date_str):
    formats = [
        "%m/%d/%Y %I:%M:%S%p",  # 6/19/2023 4:47:50AM
        "%m/%d/%Y",             # 6/19/2023
        "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d",
        "%d.%m.%Y", "%d-%m-%Y",
        "%Y%m%d",
        "%d %B %Y", "%B %d %Y", "%B %d, %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

# Extract raw dates from PDF text
def extract_dates_from_pdf(path):
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() or '' for page in reader.pages)
    found = []
    for pattern in date_patterns:
        found.extend(re.findall(pattern, text))
    return found

# Convert extracted strings into datetime.date
def convert_to_dates(date_strs):
    result = set()
    for s in date_strs:
        date_obj = normalize_to_date(s)
        if date_obj:
            result.add(date_obj)
    return result

# Load SAP JSON and match dates
def match_with_sap_json(pdf_date_set):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    matches = []
    for entry in data:
        delivery_raw = entry.get("Delivery Note Date")
        if not delivery_raw:
            continue
        try:
            delivery_date = datetime.fromisoformat(delivery_raw).date()
        except ValueError:
            continue

        if delivery_date in pdf_date_set:
            matches.append({
                "MBLNR": entry["MBLNR"],
                "MJAHR": entry["MJAHR"],
                "Matched Date": str(delivery_date)
            })
    return matches

if __name__ == "__main__":
    try:
        extracted_raw = extract_dates_from_pdf(pdf_path)
        normalized_pdf_dates = convert_to_dates(extracted_raw)
        matched_results = match_with_sap_json(normalized_pdf_dates)

        with open(output_path, "w", encoding="utf-8") as f_out:
            json.dump(matched_results, f_out, indent=4, ensure_ascii=False)

        print(f"✅ Done. Found {len(matched_results)} match(es). Written to: {output_path}")

    except Exception as e:
        print(f"❌ Error: {e}")
