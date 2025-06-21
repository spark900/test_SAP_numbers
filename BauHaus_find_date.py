import re
from PyPDF2 import PdfReader

# Path to the PDF file
pdf_path = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\batch_6_2023_1\20230619_Bauhaus.pdf"

# Regular expressions to match different date formats
date_patterns = [
    r'\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b',               # 19.06.2023 or 19/06/2023 or 19-06-23
    r'\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b',                 # 2023-06-19 or 2023.06.19
    r'\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}\b',             # 19 June 2023
    r'\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b',             # June 19, 2023 or June 19 2023
    r'\b\d{8}\b'                                          # 20230619 (compact format)
]

def extract_text_from_pdf(pdf_path):
    text = ""
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def find_dates(text):
    found_dates = []
    for pattern in date_patterns:
        found_dates += re.findall(pattern, text)
    return found_dates

if __name__ == "__main__":
    try:
        text = extract_text_from_pdf(pdf_path)
        dates = find_dates(text)
        if dates:
            print("Found dates:")
            for d in dates:
                print(d)
        else:
            print("No dates found.")
    except Exception as e:
        print(f"Error: {e}")
