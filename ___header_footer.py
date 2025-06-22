import fitz
import json
import re

# Update paths according to your system
pdf_path = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\batch_1_2017_2018.pdf"
output_path = r"C:\projects\hackathon_ScienceHack\HeaderFooterOut_2017.json"

# Simplified and corrected regex patterns
NAME_PATTERN = r"[A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß]+"
COMPANY_PATTERN = r"(GmbH|AG|KG|UG|Inc\.?|LLC|Ltd\.?|SE|e\.V\.?|s\.r\.o|S\.A\.?)"
STREET_PATTERN = r"([A-Za-zäöüß\-]+\.?\s+)?(Straße|Str\.?|Strasse|Platz|Weg|Allee|Ring)\s+\d+[a-z]?"
ZIP_CITY_PATTERN = r"\d{4,5}\s+[A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[a-zäöüß\-]+)*"

CONTACT_REGEX = re.compile(
    rf"({NAME_PATTERN}|{COMPANY_PATTERN}|{STREET_PATTERN}|{ZIP_CITY_PATTERN})", 
    re.IGNORECASE
)

SEPARATORS = re.compile(r"[\-•·|/]{2,}")  # Common header separators

def extract_contact_blocks(page, region="top"):
    """Extract contact information blocks from header/footer regions"""
    page_rect = page.rect
    blocks = page.get_text("blocks")
    region_blocks = []
    
    # Define region boundaries (top 20% for header, bottom 20% for footer)
    y_threshold_top = page_rect.y0 + (page_rect.height * 0.20)
    y_threshold_bottom = page_rect.y1 - (page_rect.height * 0.20)
    
    for block in blocks:
        x0, y0, x1, y1, text, block_no, block_type = block[:7]
        
        # Filter to text blocks within target region
        if block_type != 0:  # Ignore image blocks
            continue
            
        if region == "top" and y0 < y_threshold_top:
            region_blocks.append(block)
        elif region == "bottom" and y1 > y_threshold_bottom:
            region_blocks.append(block)
    
    # Process blocks to find contact information
    contact_info = []
    current_group = []
    
    for block in sorted(region_blocks, key=lambda b: b[1]):  # Sort by vertical position
        text = block[4].strip()
        
        # Skip page numbers and dates
        if re.match(r"^(Seite|Page|\d{1,2}\s?[/.-]\s?\d{1,4}|\d{1,2}\.\d{1,2}\.\d{2,4})$", text, re.IGNORECASE):
            continue
            
        # Check for contact patterns or separators
        if CONTACT_REGEX.search(text) or SEPARATORS.search(text):
            # Clean and split multi-line blocks
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Group consecutive lines that form a complete address
            for line in lines:
                if CONTACT_REGEX.search(line):
                    current_group.append(line)
                elif current_group:  # Add separator lines only if between contact info
                    current_group.append(line)
            
            # If we have a complete group, add it to results
            if len(current_group) >= 2:  # At least name/company + address
                contact_info.append(" • ".join(current_group))
                current_group = []
    
    return contact_info if contact_info else ["no " + region + " found"]

def analyze_page_for_header_footer(page):
    """Analyze page layout to extract header and footer"""
    return {
        "header": extract_contact_blocks(page, "top"),
        "footer": extract_contact_blocks(page, "bottom")
    }

def main(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    output = {}
    
    for i, page in enumerate(doc):
        page_result = analyze_page_for_header_footer(page)
        output[f"page_{i+1}"] = page_result
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    
    print(f"Header/Footer extraction complete. Output saved to: {output_path}")

if __name__ == "__main__":
    main(pdf_path, output_path)