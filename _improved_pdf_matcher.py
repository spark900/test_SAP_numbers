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
        self.setup_country_mappings()
        self.setup_street_suffixes()
        
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
    
    def setup_country_mappings(self):
        """Setup comprehensive country name mappings"""
        self.COUNTRY_MAPPINGS = {
            # Germany variants
            'germany': ['germany', 'deutschland', 'allemagne', 'alemania', 'germania', 'niemcy', 'german', 'de'],
            # USA variants  
            'usa': ['usa', 'us', 'united states', 'united states of america', 'america', 'estados unidos', 'vereinigte staaten'],
            # Austria variants
            'austria': ['austria', 'österreich', 'autriche', 'oostenrijk', 'austria-hungary'],
            # Switzerland variants
            'switzerland': ['switzerland', 'schweiz', 'suisse', 'svizzera', 'suiza', 'szwajcaria'],
            # France variants
            'france': ['france', 'frankreich', 'francia', 'frankrijk', 'francja'],
            # Italy variants
            'italy': ['italy', 'italien', 'italia', 'italie', 'włochy'],
            # Spain variants
            'spain': ['spain', 'spanien', 'españa', 'espagne', 'spanje', 'hiszpania'],
            # UK variants
            'uk': ['uk', 'united kingdom', 'great britain', 'britain', 'england', 'scotland', 'wales', 'northern ireland'],
            # Canada variants
            'canada': ['canada', 'kanada'],
            # Poland variants
            'poland': ['poland', 'polen', 'pologne', 'polonia', 'polska']
        }
        
        # Create reverse mapping for quick lookup
        self.country_reverse_map = {}
        for standard, variants in self.COUNTRY_MAPPINGS.items():
            for variant in variants:
                self.country_reverse_map[variant.lower()] = standard
    
    def setup_street_suffixes(self):
        """Setup street suffix mappings with fuzzy matching support"""
        self.STREET_SUFFIXES = {
            # German street suffixes
            r'\bstr(?:\.|aße|asse)?\b': 'straße',
            r'\bstrasse\b': 'straße',
            r'\bpl(?:\.|atz)?\b': 'platz',
            r'\ballee\b': 'allee',
            r'\bweg\b': 'weg',
            r'\bg(?:\.|asse)?\b': 'gasse',
            r'\bch(?:\.|aussee)?\b': 'chaussee',
            r'\bbr(?:\.|ücke)?\b': 'brücke',
            r'\bbruecke\b': 'brücke',
            r'\bprom(?:\.|enade)?\b': 'promenade',
            # English street suffixes
            r'\bst(?:\.|reet)?\b': 'street',
            r'\bave(?:\.|nue)?\b': 'avenue',
            r'\brd\b': 'road',
            r'\bblvd\b': 'boulevard',
            r'\bln\b': 'lane',
            r'\bdr\b': 'drive',
            r'\bct\b': 'court',
            r'\bpl\b': 'place',
        }

    def normalize_text_for_fuzzy(self, text: str) -> str:
        """Normalize text for fuzzy matching"""
        if not text:
            return ""
        # Convert to lowercase and remove special characters, dots, spaces
        normalized = re.sub(r'[.\s\-_/\\]', '', str(text).lower())
        # Remove other special characters except alphanumeric
        normalized = re.sub(r'[^\w]', '', normalized)
        return normalized

    def fuzzy_match_enhanced(self, str1: str, str2: str, threshold: float = 0.75) -> Tuple[bool, float]:
        """Enhanced fuzzy matching considering dots, spaces, and special characters"""
        if not str1 or not str2:
            return False, 0.0
        
        str1_lower = str1.lower().strip()
        str2_lower = str2.lower().strip()
        
        # Direct match
        if str1_lower == str2_lower:
            return True, 1.0
        
        # Substring match
        if str1_lower in str2_lower or str2_lower in str1_lower:
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
        if tokens1 and tokens2:
            token_overlap = len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))
        else:
            token_overlap = 0
        
        # Take the best ratio
        best_ratio = max(original_ratio, normalized_ratio, token_overlap)
        
        return best_ratio >= threshold, best_ratio

    def normalize_country(self, country: str) -> str:
        """Normalize country name to standard form"""
        if not country:
            return ""
        
        country_clean = re.sub(r'[^\w\s]', '', country.lower().strip())
        return self.country_reverse_map.get(country_clean, country_clean)

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
        """Extract address components with improved fuzzy matching"""
        components = {
            "STREET": set(),
            "CITY": set(), 
            "ZIP_CODE": set(),
            "COUNTRY": set()
        }
        
        # Extract streets with better pattern matching
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
                
                # Normalize street suffixes
                for suffix_pattern, replacement in self.STREET_SUFFIXES.items():
                    street_name = re.sub(suffix_pattern, replacement, street_name, flags=re.IGNORECASE)
                
                if len(street_name) > 2:  # Filter out very short matches
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
        
        # Extract countries with normalization
        country_pattern = r'\b(' + '|'.join(self.country_reverse_map.keys()) + r')\b'
        matches = re.findall(country_pattern, text, flags=re.IGNORECASE)
        for match in matches:
            normalized_country = self.normalize_country(match)
            if normalized_country:
                components["COUNTRY"].add(normalized_country)
        
        return components

    def preprocess_sap_data(self, sap_data: List[Dict]) -> List[Dict]:
        """Preprocess SAP data for matching"""
        field_weights = {
            "Delivery Note Number": 6,
            "Delivery Note Date": 4,
            "Vendor - Name 1": 4,
            "Vendor - Name 2": 2,
            "Vendor - Address - Street": 3,
            "Vendor - Address - Number": 2,
            "Vendor - Address - ZIP Code": 3,
            "Vendor - Address - City": 3,
            "Vendor - Address - Country": 3,
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
                    
                # Special handling for different field types
                if field == "Vendor - Address - Street":
                    for pattern, replacement in self.STREET_SUFFIXES.items():
                        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
                elif field == "Vendor - Address - Country":
                    normalized = self.normalize_country(normalized)
                elif field == "Delivery Note Date":
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
        """Match a PDF page to SAP entries with enhanced fuzzy matching"""
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
                
                # Date matching
                if field == "Delivery Note Date":
                    date_str = normalized_value[:10] if len(normalized_value) >= 10 else normalized_value
                    if date_str in extracted_dates:
                        score += field_weight
                        match_details[field] = f"Exact match: {date_str}"
                    else:
                        # Fuzzy date matching
                        for extracted_date in extracted_dates:
                            is_match, ratio = self.fuzzy_match_enhanced(date_str, extracted_date, 0.8)
                            if is_match:
                                score += field_weight * ratio
                                match_details[field] = f"Fuzzy match: {extracted_date} (ratio: {ratio:.3f})"
                                break
                        else:
                            match_details[field] = "Not matched"
                    continue
                
                # Delivery Note Number matching
                if field == "Delivery Note Number":
                    matched = False
                    for extracted_note in extracted_delivery_notes:
                        is_match, ratio = self.fuzzy_match_enhanced(normalized_value, extracted_note, 0.7)
                        if is_match:
                            score += field_weight * ratio
                            match_details[field] = f"Fuzzy match: '{extracted_note}' (ratio: {ratio:.3f})"
                            matched = True
                            break
                    
                    if not matched:
                        # Fallback to simple text search
                        if normalized_value in pdf_text:
                            score += field_weight * 0.8
                            match_details[field] = f"Text found: {normalized_value}"
                        else:
                            match_details[field] = "Not matched"
                    continue
                
                # Street matching
                if field == "Vendor - Address - Street":
                    matched = False
                    for doc_street in extracted_address["STREET"]:
                        is_match, ratio = self.fuzzy_match_enhanced(normalized_value, doc_street, 0.6)
                        if is_match:
                            score += field_weight * ratio
                            match_details[field] = f"Fuzzy match: '{doc_street}' (ratio: {ratio:.3f})"
                            matched = True
                            break
                    
                    if not matched:
                        match_details[field] = "Not matched"
                    continue
                
                # City matching
                if field == "Vendor - Address - City":
                    matched = False
                    for city in extracted_address["CITY"]:
                        is_match, ratio = self.fuzzy_match_enhanced(normalized_value, city, 0.8)
                        if is_match:
                            score += field_weight * ratio
                            match_details[field] = f"Fuzzy match: '{city}' (ratio: {ratio:.3f})"
                            matched = True
                            break
                    
                    if not matched:
                        match_details[field] = "Not matched"
                    continue
                
                # Country matching
                if field == "Vendor - Address - Country":
                    matched = False
                    for country in extracted_address["COUNTRY"]:
                        if normalized_value == country:
                            score += field_weight
                            match_details[field] = f"Exact match: {country}"
                            matched = True
                            break
                    
                    if not matched:
                        match_details[field] = "Not matched"
                    continue
                
                # ZIP Code matching
                if field == "Vendor - Address - ZIP Code":
                    matched = False
                    for zip_code in extracted_address["ZIP_CODE"]:
                        if normalized_value == zip_code:
                            score += field_weight
                            match_details[field] = f"Exact match: {zip_code}"
                            matched = True
                            break
                    
                    if not matched:
                        match_details[field] = "Not matched"
                    continue
                
                # Generic field matching with fuzzy support
                if normalized_value in pdf_text:
                    score += field_weight
                    match_details[field] = f"Exact match: {normalized_value}"
                else:
                    # Try fuzzy matching for text fields
                    words = pdf_text.split()
                    best_word_match = 0
                    best_word = ""
                    
                    for word in words:
                        if len(word) > 3:  # Only check reasonably long words
                            is_match, ratio = self.fuzzy_match_enhanced(normalized_value, word, 0.7)
                            if is_match and ratio > best_word_match:
                                best_word_match = ratio
                                best_word = word
                    
                    if best_word_match > 0:
                        score += field_weight * best_word_match * 0.7  # Reduce score for fuzzy matches
                        match_details[field] = f"Fuzzy match: '{best_word}' (ratio: {best_word_match:.3f})"
                    else:
                        # Try token-based partial matching
                        tokens = normalized_value.split()
                        matched_tokens = sum(1 for token in tokens if token in pdf_text and len(token) > 2)
                        
                        if matched_tokens > 0:
                            partial_score = field_weight * (matched_tokens / len(tokens)) * 0.5
                            score += partial_score
                            match_details[field] = f"Partial match ({matched_tokens}/{len(tokens)} tokens)"
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

    def process_pdf(self, pdf_path: str, sap_file: str, output_path: str, threshold: float = 4.0):
        """Main processing function"""
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
                    "extracted_data": {
                        "dates": list(match_result['extracted_data']['dates']),
                        "delivery_notes": list(match_result['extracted_data']['delivery_notes']),
                        "streets": list(match_result['extracted_data']['address']['STREET']),
                        "cities": list(match_result['extracted_data']['address']['CITY']),
                        "zip_codes": list(match_result['extracted_data']['address']['ZIP_CODE']),
                        "countries": list(match_result['extracted_data']['address']['COUNTRY'])
                    }
                }
                
                results.append(result)
                print(f"✓ Matched page {page_num} with score {match_result['score']:.2f}")
            else:
                score = match_result['score'] if match_result else 0
                print(f"✗ No match for page {page_num} (best score: {score:.2f})")
        
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
    """Main execution function"""
    # Configuration
    config = {
        'pdf_path': r"C:\projects\hackathon_ScienceHack\dummy_invoices.pdf",
        'sap_file': r"C:\projects\hackathon_ScienceHack\DUMMY_SAP.json", 
        'output_path': r"C:\projects\hackathon_ScienceHack\dummy_out.json",
        'threshold': 4.0  # Minimum matching score threshold
    }
    
    print("="*80)
    print("ENHANCED PDF MATCHER")
    print("="*80)
    print(f"PDF file: {config['pdf_path']}")
    print(f"SAP file: {config['sap_file']}")
    print(f"Output file: {config['output_path']}")
    print(f"Threshold: {config['threshold']}")
    print("="*80)
    
    # Initialize matcher
    matcher = EnhancedPDFMatcher()
    
    # Process PDF
    try:
        results = matcher.process_pdf(
            config['pdf_path'],
            config['sap_file'], 
            config['output_path'],
            config['threshold']
        )
        
        # Display summary
        if results:
            print(f"\nTop matches:")
            for result in sorted(results, key=lambda x: x['match_score'], reverse=True)[:3]:
                print(f"  Page {result['page_number']}: {result['Delivery Note Number']} (score: {result['match_score']:.2f})")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()