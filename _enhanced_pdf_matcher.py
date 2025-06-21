import os
import json
import re
import PyPDF2
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Set, Tuple, Optional

class EnhancedPDFMatcher:
    def __init__(self):
        self.setup_patterns()
        
    def setup_patterns(self):
        """Initialize regex patterns for data extraction"""
        self.DATE_PATTERNS = [
            r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*(?:am|pm)?\b',  # With time
            r'\b\d{4}[/.-]\d{2}[/.-]\d{2}\b',       # YYYY-MM-DD variants
            r'\b\d{2}[/.-]\d{2}[/.-]\d{4}\b',       # DD/MM/YYYY variants
            r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{4}\b',   # M/D/YYYY variants
            r'\b\d{1,2}\s+[A-Za-z]{3,10}\s+\d{4}\b',  # 01 January 2023
            r'\b[A-Za-z]{3,10}\s+\d{1,2},?\s+\d{4}\b',  # January 01, 2023
            r'\b\d{8}\b'                             # YYYYMMDD
        ]
        
        self.ZIP_PATTERNS = [
            r'\b\d{4,5}\b',          # Standard 4-5 digit ZIP (DE/AT/US)
            r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b',  # Canadian format (A1A 1A1)
            r'\b\d{5}[.-]\d{4}\b',   # US extended ZIP (12345-6789)
            r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b'  # UK format (SW1A 1AA)
        ]
        
        self.DELIVERY_NOTE_PATTERNS = [
            r'liefernummer[:\s]*([^\n\r\s]+(?:\s+[^\n\r\s]+)*)',
            r'delivery\s*note\s*number[:\s]*([^\n\r\s]+(?:\s+[^\n\r\s]+)*)',
            r'delivery\s*number[:\s]*([^\n\r\s]+(?:\s+[^\n\r\s]+)*)',
            r'note\s*number[:\s]*([^\n\r\s]+(?:\s+[^\n\r\s]+)*)',
            r'number[:\s]*([^\n\r\s]+(?:\s+[^\n\r\s]+)*)',
        ]

    def normalize_text_for_fuzzy(self, text: str) -> str:
        """Normalize text for fuzzy matching"""
        if not text:
            return ""
        # Convert to lowercase and remove special characters, dots, spaces
        normalized = re.sub(r'[.\s\-_/\\]', '', str(text).lower())
        # Remove other special characters except alphanumeric
        normalized = re.sub(r'[^\w]', '', normalized)
        return normalized

    def fuzzy_match_enhanced(self, str1: str, str2: str, threshold: float = 0.8) -> Tuple[bool, float]:
        """Enhanced fuzzy matching with stricter thresholds to avoid false matches"""
        if not str1 or not str2:
            return False, 0.0
        
        str1_lower = str1.lower().strip()
        str2_lower = str2.lower().strip()
        
        # Direct match - highest confidence
        if str1_lower == str2_lower:
            return True, 1.0
        
        # Substring match - high confidence
        if str1_lower in str2_lower or str2_lower in str1_lower:
            # But only if the substring is significant (at least 60% of the shorter string)
            min_len = min(len(str1_lower), len(str2_lower))
            max_len = max(len(str1_lower), len(str2_lower))
            if min_len / max_len >= 0.6:
                return True, 0.9
        
        # Original strings ratio
        original_ratio = SequenceMatcher(None, str1_lower, str2_lower).ratio()
        
        # Normalized strings (without dots, spaces, etc.)
        norm1 = self.normalize_text_for_fuzzy(str1)
        norm2 = self.normalize_text_for_fuzzy(str2)
        normalized_ratio = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Token-based matching for multi-word strings
        tokens1 = set(str1_lower.split())
        tokens2 = set(str2_lower.split())
        token_overlap = 0
        if tokens1 and tokens2:
            common_tokens = tokens1.intersection(tokens2)
            # Only count meaningful token overlaps
            if common_tokens:
                # Filter out very short tokens (like 'de', 'a', etc.)
                meaningful_common = [t for t in common_tokens if len(t) > 2]
                if meaningful_common:
                    token_overlap = len(meaningful_common) / min(len(tokens1), len(tokens2))
        
        # Take the best ratio but be more conservative
        best_ratio = max(original_ratio, normalized_ratio, token_overlap)
        
        # Apply stricter threshold for fuzzy matches
        return best_ratio >= threshold, best_ratio

    def extract_text_from_pdf_by_page(self, pdf_path: str) -> List[str]:
        """Extract text from each page of a PDF separately"""
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                page_texts = []
                num_pages = len(reader.pages)
                print(f"Processing PDF with {num_pages} pages...")
                
                for i in range(num_pages):
                    page = reader.pages[i]
                    text = page.extract_text()
                    page_texts.append(text.lower() if text else "")
                return page_texts
        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            return []

    def extract_dates(self, text: str) -> Set[str]:
        """Extract and normalize dates from text"""
        raw_dates = set()
        for pattern in self.DATE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            raw_dates.update(matches)

        normalized_dates = set()
        date_formats = [
            "%m/%d/%Y %I:%M:%S%p",  # 6/19/2023 4:47:50AM
            "%m/%d/%Y",             # 6/19/2023
            "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d",
            "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y",
            "%Y%m%d",
            "%d %B %Y", "%B %d %Y", "%B %d, %Y"
        ]

        for raw_date in raw_dates:
            raw_date = raw_date.strip()
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(raw_date, fmt)
                    normalized_dates.add(dt.date().isoformat())
                    break
                except ValueError:
                    continue

        return normalized_dates

    def extract_delivery_notes(self, text: str) -> Set[str]:
        """Extract delivery note numbers using multiple patterns"""
        delivery_notes = set()
        
        for pattern in self.DELIVERY_NOTE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean up the match
                clean_match = re.sub(r'[^\w\-._]', ' ', match.strip())
                clean_match = ' '.join(clean_match.split())  # Remove extra spaces
                if clean_match and len(clean_match) > 1:
                    delivery_notes.add(clean_match)
        
        return delivery_notes

    def extract_address_components(self, text: str) -> Dict[str, Set[str]]:
        """Extract address components with fuzzy matching only"""
        components = {
            "STREET": set(),
            "CITY": set(), 
            "ZIP_CODE": set(),
            "COUNTRY": set()
        }
        
        # Extract streets - simplified without suffix normalization
        street_patterns = [
            r'\b([a-zäöüß]+(?:[.\s-](?:[a-zäöüß]+))*\.?\s*\d{0,4}[a-z]?)\b',
            r'\b(\d+(?:st|nd|rd|th)?)\s+([a-zäöüß]+(?:[.\s-](?:[a-zäöüß]+))*)\b'
        ]
        
        for pattern in street_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    street_name = ' '.join(match).strip()
                else:
                    street_name = match.strip()
                
                if len(street_name) > 3:  # Filter out very short matches
                    components["STREET"].add(street_name)
        
        # Extract cities (improved pattern)
        city_pattern = r'\b([A-Za-zäöüß][a-zäöüß]{2,}(?:[.\s-](?:[A-Za-zäöüß][a-zäöüß]+))*)\b'
        matches = re.findall(city_pattern, text)
        for match in matches:
            city = match.strip()
            if len(city) > 2 and not city.isdigit():
                components["CITY"].add(city)
        
        # Extract ZIP codes
        for pattern in self.ZIP_PATTERNS:
            matches = re.findall(pattern, text)
            components["ZIP_CODE"].update(matches)
        
        # Extract countries - simplified without normalization
        country_pattern = r'\b([A-Za-z]{4,})\b'  # Simple country name pattern
        matches = re.findall(country_pattern, text)
        for match in matches:
            country = match.strip().lower()
            if len(country) > 3:  # Only meaningful country names
                components["COUNTRY"].add(country)
        
        return components

    def preprocess_sap_data(self, sap_data: List[Dict]) -> List[Dict]:
        """Preprocess SAP data for matching"""
        field_weights = {
            "Delivery Note Number": 10,  # Increased weight for delivery note
            "Delivery Note Date": 5,     # Increased weight for date
            "Vendor - Name 1": 4,
            "Vendor - Name 2": 2,
            "Vendor - Address - Street": 4,
            "Vendor - Address - Number": 2,
            "Vendor - Address - ZIP Code": 4,  # Increased weight for ZIP
            "Vendor - Address - City": 4,      # Increased weight for city
            "Vendor - Address - Country": 1,
            "Vendor - Address - Region": 1,
        }
        
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
                    normalized = str(value).lower()
                elif isinstance(value, str):
                    normalized = re.sub(r'[^\w\s\-.]', '', value.lower())
                else:
                    normalized = str(value).lower()
                    
                # Special handling for dates
                if field == "Delivery Note Date":
                    # Extract just the date part from datetime strings
                    if 'T' in normalized:
                        normalized = normalized.split('T')[0]
                
                normalized_fields[field] = normalized
            
            sap_entries.append({
                'entry': entry,
                'normalized': normalized_fields,
                'weights': field_weights
            })
        
        return sap_entries

    def match_page_to_sap(self, pdf_text: str, sap_entries: List[Dict], page_num: int) -> Optional[Dict]:
        """Match a PDF page to SAP entries with stricter fuzzy matching"""
        extracted_dates = self.extract_dates(pdf_text)
        extracted_delivery_notes = self.extract_delivery_notes(pdf_text)
        extracted_address = self.extract_address_components(pdf_text)
        
        best_score = 0
        best_entry = None
        best_match_details = {}
        
        for sap_entry in sap_entries:
            score = 0
            match_details = {}
            
            for field, normalized_value in sap_entry['normalized'].items():
                field_weight = sap_entry['weights'][field]
                
                # Date matching with stricter criteria
                if field == "Delivery Note Date":
                    date_str = normalized_value[:10] if len(normalized_value) >= 10 else normalized_value
                    if date_str in extracted_dates:
                        score += field_weight
                        match_details[field] = f"Exact match: {date_str}"
                    else:
                        # Fuzzy date matching with higher threshold
                        for extracted_date in extracted_dates:
                            is_match, ratio = self.fuzzy_match_enhanced(date_str, extracted_date, 0.85)
                            if is_match:
                                score += field_weight * ratio
                                match_details[field] = f"Fuzzy match: {extracted_date} (ratio: {ratio:.3f})"
                                break
                        else:
                            match_details[field] = "Not matched"
                    continue
                
                # Delivery Note Number matching - most critical field
                if field == "Delivery Note Number":
                    matched = False
                    for extracted_note in extracted_delivery_notes:
                        is_match, ratio = self.fuzzy_match_enhanced(normalized_value, extracted_note, 0.85)
                        if is_match:
                            score += field_weight * ratio
                            match_details[field] = f"Fuzzy match: '{extracted_note}' (ratio: {ratio:.3f})"
                            matched = True
                            break
                    
                    if not matched:
                        # Fallback to simple text search with exact match only
                        if normalized_value in pdf_text:
                            score += field_weight * 0.9
                            match_details[field] = f"Text found: {normalized_value}"
                        else:
                            match_details[field] = "Not matched"
                    continue
                
                # Street matching with higher threshold
                if field == "Vendor - Address - Street":
                    matched = False
                    for doc_street in extracted_address["STREET"]:
                        is_match, ratio = self.fuzzy_match_enhanced(normalized_value, doc_street, 0.75)
                        if is_match:
                            score += field_weight * ratio
                            match_details[field] = f"Fuzzy match: '{doc_street}' (ratio: {ratio:.3f})"
                            matched = True
                            break
                    
                    if not matched:
                        match_details[field] = "Not matched"
                    continue
                
                # City matching with higher threshold
                if field == "Vendor - Address - City":
                    matched = False
                    for city in extracted_address["CITY"]:
                        is_match, ratio = self.fuzzy_match_enhanced(normalized_value, city, 0.85)
                        if is_match:
                            score += field_weight * ratio
                            match_details[field] = f"Fuzzy match: '{city}' (ratio: {ratio:.3f})"
                            matched = True
                            break
                    
                    if not matched:
                        match_details[field] = "Not matched"
                    continue
                
                # Country matching - simplified
                if field == "Vendor - Address - Country":
                    matched = False
                    for country in extracted_address["COUNTRY"]:
                        is_match, ratio = self.fuzzy_match_enhanced(normalized_value, country, 0.8)
                        if is_match:
                            score += field_weight * ratio
                            match_details[field] = f"Fuzzy match: '{country}' (ratio: {ratio:.3f})"
                            matched = True
                            break
                    
                    if not matched:
                        match_details[field] = "Not matched"
                    continue
                
                # ZIP Code matching - exact match preferred
                if field == "Vendor - Address - ZIP Code":
                    matched = False
                    for zip_code in extracted_address["ZIP_CODE"]:
                        if normalized_value == zip_code:
                            score += field_weight
                            match_details[field] = f"Exact match: {zip_code}"
                            matched = True
                            break
                        else:
                            # Allow fuzzy matching for ZIP codes too
                            is_match, ratio = self.fuzzy_match_enhanced(normalized_value, zip_code, 0.9)
                            if is_match:
                                score += field_weight * ratio
                                match_details[field] = f"Fuzzy match: {zip_code} (ratio: {ratio:.3f})"
                                matched = True
                                break
                    
                    if not matched:
                        match_details[field] = "Not matched"
                    continue
                
                # Generic field matching with stricter fuzzy support
                if normalized_value in pdf_text:
                    score += field_weight
                    match_details[field] = f"Exact match: {normalized_value}"
                else:
                    # Try fuzzy matching for text fields with higher threshold
                    words = pdf_text.split()
                    best_word_match = 0
                    best_word = ""
                    
                    for word in words:
                        if len(word) > 4:  # Only check longer words
                            is_match, ratio = self.fuzzy_match_enhanced(normalized_value, word, 0.8)
                            if is_match and ratio > best_word_match:
                                best_word_match = ratio
                                best_word = word
                    
                    if best_word_match > 0:
                        score += field_weight * best_word_match * 0.7
                        match_details[field] = f"Fuzzy match: '{best_word}' (ratio: {best_word_match:.3f})"
                    else:
                        match_details[field] = "Not matched"
            
            if score > best_score:
                best_score = score
                best_entry = sap_entry
                best_match_details = match_details
        
        return {
            'score': best_score,
            'entry': best_entry,
            'details': best_match_details,
            'extracted_data': {
                'dates': extracted_dates,
                'delivery_notes': extracted_delivery_notes,
                'address': extracted_address
            }
        } if best_entry else None

    def process_pdf(self, pdf_path: str, sap_file: str, output_path: str, threshold: float = 15.0):
        """Main processing function with higher default threshold"""
        print("Loading SAP data...")
        with open(sap_file, 'r', encoding='utf-8') as f:
            sap_data = json.load(f)
        
        print("Preprocessing SAP data...")
        sap_entries = self.preprocess_sap_data(sap_data)
        print(f"Loaded {len(sap_entries)} SAP entries")
        
        print("Extracting PDF text...")
        pdf_texts = self.extract_text_from_pdf_by_page(pdf_path)
        if not pdf_texts:
            print("No pages extracted from PDF. Exiting.")
            return
        
        print(f"Processing {len(pdf_texts)} pages...")
        
        results = []
        for page_num, pdf_text in enumerate(pdf_texts, start=1):
            print(f"Processing page {page_num}...")
            
            match_result = self.match_page_to_sap(pdf_text, sap_entries, page_num)
            
            if match_result and match_result['score'] >= threshold:
                entry = match_result['entry']['entry']
                uid = f"{entry['MBLNR']}_{entry['MJAHR']}"
                
                result = {
                    "page_number": page_num,
                    "Delivery Note Number": entry["Delivery Note Number"],
                    "UID": uid,
                    "match_score": match_result['score'],
                    "match_details": match_result['details'],
                    # "extracted_data": {
                    #     "dates": list(match_result['extracted_data']['dates']),
                    #     "delivery_notes": list(match_result['extracted_data']['delivery_notes']),
                    #     "streets": list(match_result['extracted_data']['address']['STREET']),
                    #     "cities": list(match_result['extracted_data']['address']['CITY']),
                    #     "zip_codes": list(match_result['extracted_data']['address']['ZIP_CODE']),
                    #     "countries": list(match_result['extracted_data']['address']['COUNTRY'])
                    # }
                }
                
                results.append(result)
                print(f"✓ Matched page {page_num} with score {match_result['score']:.2f}")
            else:
                score = match_result['score'] if match_result else 0
                print(f"✗ No match for page {page_num} (best score: {score:.2f})")
                result = {
                    "page_number": page_num,
                    "UID": "NONE FOUND IN SAP JSON"
                }
                results.append(result)
            
        
        # Save results
        print(f"Saving results to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Matched: {len(results)}/{len(pdf_texts)} pages")
        print(f"Success rate: {len(results)/len(pdf_texts)*100:.1f}%")
        print(f"Results saved to: {output_path}")
        
        return results


def main():
    print("="*80)
    print("IMPROVED PDF MATCHER")
    print("="*80)
    
    # Get file paths from user input
    pdf_path = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\batch_7_2023_2024.pdf"
    sap_file = r"C:\projects\hackathon_ScienceHack\BECONEX_challenge_materials_samples\SAP_data.json"
    output_path = r"C:\projects\hackathon_ScienceHack\output_2024.json"
    
    if not pdf_path or not sap_file or not output_path:
        print("Error: All file paths are required")
        return
    
    print(f"\nPDF file: {pdf_path}")
    print(f"SAP file: {sap_file}")
    print(f"Output file: {output_path}")
    
    # Ask for threshold
    try:
        threshold_input = input("\nEnter matching threshold (default 15.0, higher = stricter): ").strip()
        threshold = float(threshold_input) if threshold_input else 15.0
    except ValueError:
        threshold = 15.0
    
    print(f"Using threshold: {threshold}")
    print("="*80)
    
    # Initialize matcher
    matcher = EnhancedPDFMatcher()
    
    # Process PDF
    try:
        results = matcher.process_pdf(
            pdf_path,
            sap_file, 
            output_path,
            threshold
        )
        
        # Display summary
        # NOT NEEDED
        # if results:
        #     print(f"\nTop matches:")
        #     for result in sorted(results, key=lambda x: x['match_score'], reverse=True)[:5]:
        #         print(f"  Page {result['page_number']}: {result['Delivery Note Number']} (score: {result['match_score']:.2f})")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()