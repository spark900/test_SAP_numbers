import os
import json
import re
import PyPDF2
from datetime import datetime
from difflib import SequenceMatcher

def load_results(json_file):
    """Load matching results from JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading results: {e}")
        return []

def load_sap_data(sap_file):
    """Load SAP data from JSON file"""
    try:
        with open(sap_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading SAP data: {e}")
        return []

def extract_text_from_pdf_by_page(pdf_path):
    """Extract text from each page of PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            page_texts = []
            for i in range(len(reader.pages)):
                page = reader.pages[i]
                text = page.extract_text()
                page_texts.append(text.lower() if text else "")
            return page_texts
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return []

def normalize_text_for_fuzzy(text):
    """Normalize text for fuzzy matching by removing dots, spaces, and special chars"""
    if not text:
        return ""
    # Remove dots, spaces, hyphens, underscores
    normalized = re.sub(r'[.\s\-_]', '', str(text).lower())
    # Remove other special characters except alphanumeric
    normalized = re.sub(r'[^\w]', '', normalized)
    return normalized

def fuzzy_match_enhanced(str1, str2, threshold=0.75):
    """Enhanced fuzzy matching that considers dots and spaces"""
    if not str1 or not str2:
        return False, 0.0
    
    # Original strings
    original_ratio = SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    # Normalized strings (without dots, spaces, etc.)
    norm1 = normalize_text_for_fuzzy(str1)
    norm2 = normalize_text_for_fuzzy(str2)
    normalized_ratio = SequenceMatcher(None, norm1, norm2).ratio()
    
    # Take the higher ratio
    best_ratio = max(original_ratio, normalized_ratio)
    
    return best_ratio >= threshold, best_ratio

def display_matches(results, sap_data, pdf_texts):
    """Display detailed matching information"""
    
    print("="*80)
    print("DETAILED MATCHING RESULTS")
    print("="*80)
    
    # Create SAP lookup dictionary
    sap_lookup = {}
    for entry in sap_data:
        if entry.get("Delivery Note Number"):
            sap_lookup[entry["Delivery Note Number"]] = entry
    
    for i, result in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"MATCH {i}: PAGE {result['page_number']}")
        print(f"{'='*60}")
        
        delivery_note = result.get("Delivery Note Number")
        uid = result.get("UID")
        score = result.get("match_score", 0)
        
        print(f"Delivery Note Number: {delivery_note}")
        print(f"UID: {uid}")
        print(f"Match Score: {score:.2f}")
        
        # Get corresponding SAP entry
        sap_entry = sap_lookup.get(delivery_note)
        if not sap_entry:
            print("WARNING: SAP entry not found!")
            continue
            
        print(f"\nSAP ENTRY DETAILS:")
        print(f"  MBLNR: {sap_entry.get('MBLNR')}")
        print(f"  MJAHR: {sap_entry.get('MJAHR')}")
        print(f"  Vendor Name 1: {sap_entry.get('Vendor - Name 1')}")
        print(f"  Street: {sap_entry.get('Vendor - Address - Street')}")
        print(f"  Number: {sap_entry.get('Vendor - Address - Number')}")
        print(f"  ZIP: {sap_entry.get('Vendor - Address - ZIP Code')}")
        print(f"  City: {sap_entry.get('Vendor - Address - City')}")
        print(f"  Country: {sap_entry.get('Vendor - Address - Country')}")
        
        # Show PDF text excerpt
        pdf_page_text = pdf_texts[result['page_number'] - 1] if result['page_number'] <= len(pdf_texts) else ""
        print(f"\nPDF PAGE TEXT (first 300 chars):")
        print("-" * 40)
        print(pdf_page_text[:300] + "..." if len(pdf_page_text) > 300 else pdf_page_text)
        
        # Show match details
        match_details = result.get("match_details", {})
        print(f"\nFIELD MATCHING DETAILS:")
        print("-" * 40)
        
        for field, detail in match_details.items():
            status = "✓" if "Matched" in detail or "Partial" in detail else "✗"
            print(f"  {status} {field}: {detail}")
        
        # Perform enhanced fuzzy analysis
        print(f"\nFUZZY MATCHING ANALYSIS:")
        print("-" * 40)
        
        # Test delivery note fuzzy matching
        if delivery_note:
            delivery_patterns = [
                r'liefernummer[:\s]*([^\n\r]+)',
                r'delivery\s*number[:\s]*([^\n\r]+)',
                r'number[:\s]*([^\n\r]+)',
            ]
            
            found_delivery_numbers = []
            for pattern in delivery_patterns:
                matches = re.findall(pattern, pdf_page_text, re.IGNORECASE)
                found_delivery_numbers.extend(matches)
            
            print(f"  Delivery Note '{delivery_note}' analysis:")
            for found in found_delivery_numbers:
                found_clean = found.strip()
                is_match, ratio = fuzzy_match_enhanced(delivery_note, found_clean)
                match_status = "✓ MATCH" if is_match else "✗ NO MATCH"
                print(f"    vs '{found_clean}' -> {ratio:.3f} ({match_status})")
        
        # Test address fuzzy matching
        sap_street = sap_entry.get('Vendor - Address - Street', '')
        if sap_street:
            street_patterns = [
                r'([a-zäöüß]+(?:[.\s-](?:[a-zäöüß]+))*\.?\s*\d{0,4}[a-z]?)',
            ]
            
            found_streets = []
            for pattern in street_patterns:
                matches = re.findall(pattern, pdf_page_text, re.IGNORECASE)
                found_streets.extend(matches)
            
            print(f"  Street '{sap_street}' analysis:")
            for found in found_streets:
                found_clean = found.strip()
                is_match, ratio = fuzzy_match_enhanced(sap_street, found_clean)
                match_status = "✓ MATCH" if is_match else "✗ NO MATCH"
                print(f"    vs '{found_clean}' -> {ratio:.3f} ({match_status})")

def main():
    # File paths
    results_file = r"C:\projects\hackathon_ScienceHack\dummy_out.json"
    sap_file = r"C:\projects\hackathon_ScienceHack\DUMMY_SAP.json"
    pdf_file = r"C:\projects\hackathon_ScienceHack\dummy_invoices.pdf"
    
    print("Loading data...")
    
    # Load results
    results = load_results(results_file)
    if not results:
        print("No results found!")
        return
    
    # Load SAP data
    sap_data = load_sap_data(sap_file)
    if not sap_data:
        print("No SAP data found!")
        return
    
    # Load PDF texts
    pdf_texts = extract_text_from_pdf_by_page(pdf_file)
    if not pdf_texts:
        print("No PDF text extracted!")
        return
    
    print(f"Loaded {len(results)} results, {len(sap_data)} SAP entries, {len(pdf_texts)} PDF pages")
    
    # Display detailed matches
    display_matches(results, sap_data, pdf_texts)
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total matches found: {len(results)}")
    print(f"Total PDF pages: {len(pdf_texts)}")
    print(f"Match rate: {len(results)/len(pdf_texts)*100:.1f}%")

if __name__ == "__main__":
    main()