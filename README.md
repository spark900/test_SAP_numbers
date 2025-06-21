In this code edit the path to the pdf batch accordingly to your file system.

batch_finding is for a single pdf file.

finding_numbers is for seperate files in a folder.


The  _improved_pdf_matcher.py is very slow but more fuzzy/broad. May be less accurate because of very broad search and matches that aren't real matches in real life. 
The problem being: There is no AI function implemented, only very simple regex and fuzzy comparing. An AI could recognize where the street number is and what the country is for more useful and precise but at the same time fuzzy matches. Fuzzy because it will still recogize something like "Mun ic h" as Munich and accurate because a random number in the text would not be recogized as an address number if it is not next to a street name.
