import fitz  # PyMuPDF
import cv2
import numpy as np

def pdf_to_images(pdf_path, dpi=200):
    """
    Konvertiert ein PDF in eine Liste von OpenCV-Bildern (numpy arrays).
    """
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        # Pixmap in numpy array umwandeln (RGB → BGR für cv2)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            # RGBA → RGB
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        images.append(bgr)
    return images

def detect_logo_in_image(logo_img, target_img, method=cv2.TM_CCOEFF_NORMED, threshold=0.8):
    """
    Sucht das Logo (logo_img) im Zielbild (target_img) mittels Template Matching.
    Gibt True zurück, wenn ein Treffer >= threshold gefunden wurde.
    """
    # in Graustufen umwandeln
    logo_gray = cv2.cvtColor(logo_img, cv2.COLOR_BGR2GRAY)
    target_gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
    # Template Matching
    res = cv2.matchTemplate(target_gray, logo_gray, method)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= threshold

def detect_logo_in_pdf(logo_path, pdf_path, threshold=0.8):
    """
    Prüft, ob das in logo_path gespeicherte Logo in einer der Seiten des PDFs vorkommt.
    Liefert True, sobald das Logo auf einer Seite erkannt wurde.
    """
    # Logo laden
    logo = cv2.imread(logo_path)
    if logo is None:
        raise FileNotFoundError(f"Logo-Bild '{logo_path}' nicht gefunden.")
    # PDF in Bilder konvertieren
    pages = pdf_to_images(pdf_path)
    # Prüfen jeder Seite
    for page_img in pages:
        if detect_logo_in_image(logo, page_img, threshold=threshold):
            return True
    return False

def detect_logo_across_pdfs(logo_path, pdf_paths, threshold=0.8):
    """
    Durchläuft eine Liste von PDF-Dateien und gibt diejenigen zurück,
    auf denen das Logo gefunden wurde.
    """
    matches = []
    for pdf in pdf_paths:
        if detect_logo_in_pdf(logo_path, pdf, threshold):
            matches.append(pdf)
    return matches