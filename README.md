Initial idea:

Probabilistic PDF Pairing Approach:
This is a probability‑based method that builds on our existing text extraction and first-page-detection pipeline. For each entry in our JSON metadata, we will compare its fields against every candidate PDF and assign a likelihood score indicating how probable it is that the two belong together. We base these scores on a hierarchy of matching criteria (stronger matches yield higher probability):
Company name + Order/PO/Delivery Note number + "Page 1 of X"
Company name + Order/PO/Delivery Note number
Address + Order/PO/Delivery Note number
Order/PO/Delivery Note number + Date
Delivery number + Date
Delivery number (alone)
Order/PO/Delivery Note number (alone)
Terms & Conditions (AGB) reference + Company name
Ranking is not final

Algorithm Overview
Initialization
 Load all JSON entries and their associated first page PDF (from the other approach).
Pairwise Scoring
 For each JSON entry J (representing one page or document):
Compare J against every (or at least every non-first-page) candidate PDF page P.
Evaluate which of the above criteria apply.
Assign a probability score based on the highest-matching criterion.
Example: If both company and delivery note match exactly, assign a very high probability (e.g. 0.9).
If only the company matches, assign a lower probability (e.g. 0.3).
Probability Matrix
 Build a matrix M where M[J][P] = probability(J matches P).
Symmetric Confirmation
 Later, when processing JSON entry K, compare it to all pages again, filling out row M[K][*]. This ensures that both directions are considered.
Pair Selection
 For each page P, find the JSON entry J* that maximizes M[J*][P]. (We also have already the first page matched to the JSON from the other approach [No two pages marked as “first-pages” will be matched, even if they have a big matching score [Example: Two first pages from Alternate have matching addresses and matching company name so the probability would be moderate])
If the highest probability for P is above a chosen threshold, consider P and J* a match.
Otherwise, leave P unpaired or flag for manual review.
Assembly
 Merge PDFs that have been paired (i.e., those with mutually highest probability matches).
Example: If PDF_A has a 90% match to PDF_B and lower scores to others, group A with B.

Illustrative Example
We have two multi-page documents A (pages A1, A2) and B (pages B1, B2).
In the first pass, comparing JSON entry for A1:
A2 scores 0.9 (identical delivery note, company, page sequence)
B1 and B2 each score 0.3 (same company but no matching delivery note)
In the second pass, comparing JSON entry for B1:
A1 and A2 each score 0.3 (company match only)
B2 scores 0.9 (delivery note + company + page sequence)
At the end, we pair A1 ↔ A2 and B1 ↔ B2 (90% matches), and ignore the weaker 30% associations.


----

First match non first page approach:
python find_matches.py --pdf-file Path/to/PDF/batch.pdf

Example output: (not working realiably / not out final approach)
Tested with: batch_2_2019_2020.pdf
1 --> 2 mit 27.0%
1 --> 3 mit 1.7%
1 --> 4 mit 2.3%
1 --> 5 mit 1.7%
1 --> 6 mit 2.2%
1 --> 7 mit 0.8%
1 --> 8 mit 2.5%
1 --> 9 mit 3.4%
1 --> 10 mit 1.4%
1 --> 11 mit 1.9%
1 --> 12 mit 2.0%
1 --> 13 mit 1.4%
1 --> 14 mit 2.4%
1 --> 15 mit 3.0%
1 --> 16 mit 2.3%
2 --> 3 mit 3.8%
2 --> 4 mit 2.7%
2 --> 5 mit 1.1%
2 --> 6 mit 3.5%
2 --> 7 mit 1.6%
2 --> 8 mit 1.5%
2 --> 9 mit 2.9%
2 --> 10 mit 3.3%
2 --> 11 mit 1.9%
2 --> 12 mit 2.1%
2 --> 13 mit 2.9%
2 --> 14 mit 2.4%
2 --> 15 mit 3.3%
2 --> 16 mit 2.1%
3 --> 4 mit 37.9%
3 --> 5 mit 5.5%
3 --> 6 mit 1.7%
3 --> 7 mit 0.8%
3 --> 8 mit 2.5%
3 --> 9 mit 3.3%
3 --> 10 mit 1.1%
3 --> 11 mit 4.6%
3 --> 12 mit 0.9%
3 --> 13 mit 6.0%
3 --> 14 mit 1.9%
3 --> 15 mit 1.4%
3 --> 16 mit 2.9%
4 --> 5 mit 1.2%
4 --> 6 mit 1.3%
4 --> 7 mit 0.3%
4 --> 8 mit 1.9%
4 --> 9 mit 1.3%
4 --> 10 mit 1.2%
4 --> 11 mit 1.2%
4 --> 12 mit 1.3%
4 --> 13 mit 1.4%
4 --> 14 mit 1.3%
4 --> 15 mit 1.5%
4 --> 16 mit 1.9%
5 --> 6 mit 3.2%
5 --> 7 mit 1.0%
5 --> 8 mit 6.5%
5 --> 9 mit 8.3%
5 --> 10 mit 1.5%
5 --> 11 mit 5.6%
5 --> 12 mit 2.5%
5 --> 13 mit 7.8%
5 --> 14 mit 3.1%
5 --> 15 mit 1.5%
5 --> 16 mit 1.7%
6 --> 7 mit 8.5%
6 --> 8 mit 8.1%
6 --> 9 mit 8.0%
6 --> 10 mit 3.8%
6 --> 11 mit 1.7%
6 --> 12 mit 3.2%
6 --> 13 mit 7.7%
6 --> 14 mit 2.4%
6 --> 15 mit 2.6%
6 --> 16 mit 3.2%
7 --> 8 mit 6.2%
7 --> 9 mit 6.3%
7 --> 10 mit 3.3%
7 --> 11 mit 5.7%
7 --> 12 mit 2.4%
7 --> 13 mit 7.9%
7 --> 14 mit 8.6%
7 --> 15 mit 6.1%
7 --> 16 mit 12.2%
8 --> 9 mit 7.2%
8 --> 10 mit 1.2%
8 --> 11 mit 1.6%
8 --> 12 mit 2.6%
8 --> 13 mit 4.7%
8 --> 14 mit 2.3%
8 --> 15 mit 1.9%
8 --> 16 mit 2.4%
9 --> 10 mit 1.7%
9 --> 11 mit 1.2%
9 --> 12 mit 2.5%
9 --> 13 mit 5.0%
9 --> 14 mit 3.0%
9 --> 15 mit 2.6%
9 --> 16 mit 1.6%
10 --> 11 mit 1.5%
10 --> 12 mit 1.8%
10 --> 13 mit 4.7%
10 --> 14 mit 3.0%
10 --> 15 mit 1.5%
10 --> 16 mit 3.9%
11 --> 12 mit 1.6%
11 --> 13 mit 4.8%
11 --> 14 mit 3.5%
11 --> 15 mit 4.1%
11 --> 16 mit 1.9%
12 --> 13 mit 8.5%
12 --> 14 mit 3.3%
12 --> 15 mit 3.7%
12 --> 16 mit 2.3%
13 --> 14 mit 3.1%
13 --> 15 mit 2.9%
13 --> 16 mit 1.7%
14 --> 15 mit 3.2%
14 --> 16 mit 1.8%
15 --> 16 mit 2.7%


Second approach (not final approach / not working reliably)

python find_matches_2.py --pdf-file Path/To/PDF/batch/file.pdf --json-path Path/To/JSON.pdf

Example output:
PDF 'batch_2_2019_2020.pdf' mit 16 Seiten analysiert.

Seiten-Mapping zu JSON-Einträgen:
Seite 1 → Eintrag 'LS19037829' mit 90.0%
Seite 2 → Eintrag 'LS19037829' mit 90.0%
Seite 3 → Eintrag '709 024 7953' mit 90.0%
Seite 4 → Eintrag '708 985 9234' mit 90.0%
Seite 5 → Eintrag '40433-001' mit 90.0%
Seite 6 → Eintrag '354382935' mit 10.0%
Seite 7 → Eintrag '1315749502' mit 8.5%
Seite 8 → Eintrag 'hd_53799691' mit 12.8%
Seite 9 → Eintrag 'LS-19-1007067' mit 90.0%
Seite 10 → Eintrag '6060857244' mit 90.0%
Seite 11 → Eintrag '201900501866' mit 90.0%
Seite 12 → Eintrag '22078787' mit 90.0%
Seite 13 → Eintrag '70588' mit 50.0%
Seite 14 → Eintrag '1315749502' mit 8.5%
Seite 15 → Eintrag 'hd_53799691' mit 90.0%
Seite 16 → Eintrag '120961772' mit 90.0%

Inter-Seiten Wahrscheinlichkeiten:
1 --> 2 mit 90.0%
1 --> 3 mit 4.3%
1 --> 4 mit 4.3%
1 --> 5 mit 8.5%
1 --> 6 mit 8.5%
1 --> 7 mit 8.5%
1 --> 8 mit 12.8%
1 --> 9 mit 8.5%
1 --> 10 mit 4.3%
1 --> 11 mit 8.5%
1 --> 12 mit 4.3%
1 --> 13 mit 8.5%
1 --> 14 mit 8.5%
1 --> 15 mit 8.5%
1 --> 16 mit 8.5%
2 --> 3 mit 4.3%
2 --> 4 mit 4.3%
2 --> 5 mit 8.5%
2 --> 6 mit 8.5%
2 --> 7 mit 8.5%
2 --> 8 mit 12.8%
2 --> 9 mit 8.5%
2 --> 10 mit 4.3%
2 --> 11 mit 8.5%
2 --> 12 mit 4.3%
2 --> 13 mit 8.5%
2 --> 14 mit 8.5%
2 --> 15 mit 8.5%
2 --> 16 mit 8.5%
3 --> 4 mit 10.0%
3 --> 5 mit 12.8%
3 --> 6 mit 4.3%
3 --> 7 mit 0.0%
3 --> 8 mit 4.3%
3 --> 9 mit 0.0%
3 --> 10 mit 4.3%
3 --> 11 mit 4.3%
3 --> 12 mit 8.5%
3 --> 13 mit 0.0%
3 --> 14 mit 0.0%
3 --> 15 mit 0.0%
3 --> 16 mit 12.8%
4 --> 5 mit 12.8%
4 --> 6 mit 4.3%
4 --> 7 mit 0.0%
4 --> 8 mit 4.3%
4 --> 9 mit 0.0%
4 --> 10 mit 4.3%
4 --> 11 mit 4.3%
4 --> 12 mit 8.5%
4 --> 13 mit 0.0%
4 --> 14 mit 0.0%
4 --> 15 mit 0.0%
4 --> 16 mit 12.8%
5 --> 6 mit 4.3%
5 --> 7 mit 4.3%
5 --> 8 mit 8.5%
5 --> 9 mit 4.3%
5 --> 10 mit 8.5%
5 --> 11 mit 4.3%
5 --> 12 mit 8.5%
5 --> 13 mit 4.3%
5 --> 14 mit 4.3%
5 --> 15 mit 4.3%
5 --> 16 mit 12.8%
6 --> 7 mit 0.0%
6 --> 8 mit 4.3%
6 --> 9 mit 0.0%
6 --> 10 mit 0.0%
6 --> 11 mit 0.0%
6 --> 12 mit 0.0%
6 --> 13 mit 0.0%
6 --> 14 mit 0.0%
6 --> 15 mit 0.0%
6 --> 16 mit 4.3%
7 --> 8 mit 8.5%
7 --> 9 mit 8.5%
7 --> 10 mit 4.3%
7 --> 11 mit 8.5%
7 --> 12 mit 0.0%
7 --> 13 mit 8.5%
7 --> 14 mit 8.5%
7 --> 15 mit 4.3%
7 --> 16 mit 8.5%
8 --> 9 mit 8.5%
8 --> 10 mit 4.3%
8 --> 11 mit 8.5%
8 --> 12 mit 4.3%
8 --> 13 mit 8.5%
8 --> 14 mit 8.5%
8 --> 15 mit 12.8%
8 --> 16 mit 8.5%
9 --> 10 mit 4.3%
9 --> 11 mit 8.5%
9 --> 12 mit 4.3%
9 --> 13 mit 8.5%
9 --> 14 mit 8.5%
9 --> 15 mit 8.5%
9 --> 16 mit 8.5%
10 --> 11 mit 4.3%
10 --> 12 mit 8.5%
10 --> 13 mit 4.3%
10 --> 14 mit 4.3%
10 --> 15 mit 4.3%
10 --> 16 mit 12.8%
11 --> 12 mit 4.3%
11 --> 13 mit 8.5%
11 --> 14 mit 8.5%
11 --> 15 mit 8.5%
11 --> 16 mit 8.5%
12 --> 13 mit 0.0%
12 --> 14 mit 0.0%
12 --> 15 mit 0.0%
12 --> 16 mit 8.5%
13 --> 14 mit 8.5%
13 --> 15 mit 8.5%
13 --> 16 mit 8.5%
14 --> 15 mit 4.3%
14 --> 16 mit 8.5%
15 --> 16 mit 8.5%

Third Appoach: Only consider the pages that could not previously be matched to a JSON entry and try to assign them to a first page.(Not our final approach / not working 100% reliable)

IMPORTANT: Replace the paths in Code:
pdf_path = 
sap_file_path = 

Example output:
Seiten-zu-Seiten-Übereinstimmungswahrscheinlichkeiten:
1 -> 2 mit 90.00% Wahrscheinlichkeit
2 -> 1 mit 90.00% Wahrscheinlichkeit
3 -> 4 mit 10.00% Wahrscheinlichkeit
4 -> 3 mit 10.00% Wahrscheinlichkeit