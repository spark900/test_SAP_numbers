'''# check_logo.py
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
    '''

'''
# check_logo.py
import os
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
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        images.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    return images

def detect_logo_in_pdf(logo_path, pdf_path, threshold=0.8):
    """
    Prüft das PDF auf das Logo und öffnet EIN Fenster mit
    roter Markierung an der Fundstelle des stärksten Matches.
    """
    # Logo laden und in Graustufen
    logo = cv2.imread(logo_path)
    if logo is None:
        raise FileNotFoundError(f"Logo '{logo_path}' nicht gefunden.")
    logo_gray = cv2.cvtColor(logo, cv2.COLOR_BGR2GRAY)
    h_logo, w_logo = logo_gray.shape

    # PDF in Bilder umwandeln
    pages = pdf_to_images(pdf_path)

    best_val = -1
    best_page, best_loc = None, None

    # Suche über alle Seiten nur das stärkste Match
    for page_num, page_img in enumerate(pages, start=1):
        target_gray = cv2.cvtColor(page_img, cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(target_gray, logo_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val > best_val and max_val >= threshold:
            best_val = max_val
            best_page = page_img
            best_loc = (max_loc, page_num)

    # Wenn ein Match gefunden wurde, zeige es einmal an:
    if best_page is not None:
        top_left = best_loc[0]
        bottom_right = (top_left[0] + w_logo, top_left[1] + h_logo)
        annotated = best_page.copy()
        cv2.rectangle(annotated, top_left, bottom_right, (0, 0, 255), 2)

        window_name = os.path.basename(pdf_path)
        cv2.imshow(window_name, annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return True

    return False

def detect_logo_across_pdfs(logo_path, pdf_paths, threshold=0.8):
    """
    Geht alle PDFs durch und gibt diejenigen zurück, in denen das Logo gefunden wurde.
    Pro PDF wird nur ein Fenster geöffnet.
    """
    matches = []
    for pdf in pdf_paths:
        if detect_logo_in_pdf(logo_path, pdf, threshold):
            matches.append(pdf)
    return matches
'''

# check_logo.py
import os
import fitz  # PyMuPDF
import cv2
import numpy as np

def pdf_to_images(pdf_path, dpi=300):
    """
    Konvertiert ein PDF in eine Liste von OpenCV-Bildern (numpy arrays) bei 300 dpi.
    """
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        images.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    return images


def show_full_image_window(window_name, img):
    """
    Zeigt das Bild img komplett in einem skalierbaren Fenster,
    sodass eine Hochkant DIN A4 (300 dpi) vollständig sichtbar ist.
    """
    # Bildschirmauflösung (hier Beispielwerte, ggf. dynamisch ermitteln)
    screen_w, screen_h = 1920, 1080
    # Maximal 90% des Bildschirms nutzen
    max_w = int(screen_w * 0.9)
    max_h = int(screen_h * 0.9)

    # Originalmaße
    h, w = img.shape[:2]

    # Skalierungsfaktor (niemals >1)
    scale = min(max_w / w, max_h / h, 1.0)

    # Bild bei Bedarf verkleinern
    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Fenster anlegen und anzeigen
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(window_name, img.shape[1], img.shape[0])
    cv2.imshow(window_name, img)


def detect_logo_in_pdf(logo_path, pdf_path, threshold=0.8, top_k=3):
    """
    Prüft das PDF auf das Logo und öffnet bis zu top_k Fenster
    mit roten Markierungen an den stärksten Matches (A4 komplett sichtbar).
    """
    logo = cv2.imread(logo_path)
    if logo is None:
        raise FileNotFoundError(f"Logo '{logo_path}' nicht gefunden.")
    logo_gray = cv2.cvtColor(logo, cv2.COLOR_BGR2GRAY)
    h_logo, w_logo = logo_gray.shape

    pages = pdf_to_images(pdf_path)
    candidates = []
    for page_num, page_img in enumerate(pages, start=1):
        tgt_gray = cv2.cvtColor(page_img, cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(tgt_gray, logo_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            candidates.append((max_val, page_num, max_loc, page_img))

    if not candidates:
        return False

    top_matches = sorted(candidates, key=lambda x: x[0], reverse=True)[:top_k]

    for idx, (score, page_num, top_left, page_img) in enumerate(top_matches, start=1):
        annotated = page_img.copy()
        bottom_right = (top_left[0] + w_logo, top_left[1] + h_logo)
        cv2.rectangle(annotated, top_left, bottom_right, (0, 0, 255), 2)

        window_name = f"{os.path.basename(pdf_path)}_Top{idx}_Seite{page_num}"
        show_full_image_window(window_name, annotated)

    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return True


def detect_logo_across_pdfs(logo_path, pdf_paths, threshold=0.8, top_k=3):
    """
    Durchläuft eine Liste von PDF-Dateien und gibt diejenigen zurück,
    in denen das Logo gefunden wurde. Pro PDF bis zu top_k Fenster.
    """
    matches = []
    for pdf in pdf_paths:
        if detect_logo_in_pdf(logo_path, pdf, threshold, top_k):
            matches.append(pdf)
    return matches
