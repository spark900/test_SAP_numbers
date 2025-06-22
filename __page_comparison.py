import json


def find_document_starts(pages_data: list) -> list:
   """
   Identifies the first page of each document based on a change in UID.
   """
   if not pages_data:
       return []


   document_start_pages = []
   for i, current_page in enumerate(pages_data):
       if i == 0:
           document_start_pages.append(current_page)
       elif current_page.get('UID') != pages_data[i - 1].get('UID'):
           document_start_pages.append(current_page)
  
   return document_start_pages


def transform_to_final_format(start_pages: list) -> list:
   """
   Transforms the start pages into a list of dictionaries with descriptive
   keys and integer values.
   """
   final_json_output = []
   for page in start_pages:
       page_number_int = page.get('page_number')
       uid = page.get('UID')
      
       mblnr_int = None  # Default to None (will become 'null' in JSON)
       mjahr_int = None
      
       if uid and uid != "NONE FOUND IN SAP JSON":
           parts = uid.split('_')
           if len(parts) == 2:
               try:
                   mblnr_int = int(parts[0])
                   mjahr_int = int(parts[1])
               except (ValueError, TypeError):
                   # In case of conversion error, values remain None
                   mblnr_int = None
                   mjahr_int = None


       # --- THE FIX IS HERE ---
       # Create a dictionary using your specified descriptive keys.
       transformed_doc = {
           "Page of batch where document starts": page_number_int,
           "MBLNR (Goods entry receipt Nr.)": mblnr_int,
           "MJAHR (Year)": mjahr_int
       }
       final_json_output.append(transformed_doc)
      
   return final_json_output


def main():
   """
   Main execution function.
   """
   input_filename = 'output_2017.json'


   try:
       with open(input_filename, 'r', encoding='utf-8') as f:
           all_pages_data = json.load(f)
   except FileNotFoundError:
       print(f"Error: The input file '{input_filename}' was not found.")
       return
   except json.JSONDecodeError:
       print(f"Error: The input file '{input_filename}' contains invalid JSON.")
       return


   document_starts = find_document_starts(all_pages_data)
   final_output = transform_to_final_format(document_starts)


   print("--- Final Output JSON ---")
   print(json.dumps(final_output, indent=4))
   print("--- End of Final Output JSON ---")


if __name__ == "__main__":
   main()


