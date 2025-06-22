# find_similarities.py
import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
from skimage.metrics import structural_similarity as ssim

# optional (pyzbar)
try:
    from pyzbar.pyzbar import decode as decode_barcodes
except ImportError:
    decode_barcodes = None


def load_images_from_folder(folder_path):
    """Lädt alle Bilddateien (png/jpg/tiff) aus einem Verzeichnis."""
    imgs = []
    for fname in sorted(os.listdir(folder_path)):
        if fname.lower().endswith(('.png','.jpg','.jpeg','.tif','.tiff')):
            path = os.path.join(folder_path, fname)
            img = cv2.imread(path)
            if img is not None:
                imgs.append((fname, img))
    return imgs


def avg_hash(img, hash_size=8):
    """Berechnet einfachen average hash (aHash) eines Bildes."""
    # Konvertiere zu PIL Image und in Graustufen
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    # Verwende LANCZOS Resampling statt ANTIALIAS (deprecated)
    gray = pil.convert('L')
    resized = gray.resize((hash_size, hash_size), resample=Image.LANCZOS)
    arr = np.array(resized)
    mean = arr.mean()
    bits = arr > mean
    h = 0
    for idx, v in enumerate(bits.flatten()):
        if v:
            h |= 1 << idx
    return h


def hamming_dist(h1, h2):
    """Hamming-Distanz zwischen zwei Hash-Ints."""
    return bin(h1 ^ h2).count('1')


def compute_header_footer_hash(img, region='header', pct=0.1):
    """Berechnet aHash für die Header- oder Footer-Region."""
    h, w = img.shape[:2]
    if region == 'header':
        crop = img[0:int(h*pct), :]
    else:
        crop = img[int(h*(1-pct)):h, :]
    return avg_hash(crop)


def detect_barcodes(img):
    """Liests Barcodes/QR-Codes aus (optional)."""
    if not decode_barcodes:
        return []
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    codes = decode_barcodes(pil)
    return [c.data.decode('utf-8') for c in codes]


def compute_histogram_signature(img, bins=(8,8,8)):
    """Erstellt einen 3D-Farbhistogramm-Vektor und normalisiert ihn."""
    hist = cv2.calcHist([img], [0,1,2], None, bins, [0,256,0,256,0,256])
    cv2.normalize(hist, hist)
    return hist.flatten()


#def ocr_text(img):
#    """Extrahiert reinen Text via Tesseract OCR."""
#    return pytesseract.image_to_string(img)


def pairwise_similarity(p1, p2, threshold_hash=2, threshold_corr=0.9, threshold_ssim=0.8):
    """Berechnet Score basierend auf visuellen & inhaltlichen Merkmalen."""
    score = 0
    # Barcode match
    if p1['barcodes'] and p2['barcodes'] and set(p1['barcodes']) & set(p2['barcodes']):
        score += 5
    # Header similarity
    if hamming_dist(p1['header_hash'], p2['header_hash']) <= threshold_hash:
        score += 2
    # Footer similarity
    if hamming_dist(p1['footer_hash'], p2['footer_hash']) <= threshold_hash:
        score += 2
    # Histogram correlation
    corr = np.corrcoef(p1['hist'], p2['hist'])[0,1]
    if corr > threshold_corr:
        score += 1
    # Structural similarity
    g1 = cv2.cvtColor(p1['img'], cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(p2['img'], cv2.COLOR_BGR2GRAY)
    h_min, w_min = min(g1.shape[0], g2.shape[0]), min(g1.shape[1], g2.shape[1])
    sim, _ = ssim(g1[:h_min, :w_min], g2[:h_min, :w_min], full=True)
    if sim > threshold_ssim:
        score += 1
    return score


def cluster_pages(pages, threshold=5):
    """Clustert Seiten zu Dokumenten basierend auf paarweisen Scores."""
    n = len(pages)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(i+1, n):
            if pairwise_similarity(pages[i], pages[j]) >= threshold:
                union(i, j)

    clusters = {}
    for i in range(n):
        r = find(i)
        clusters.setdefault(r, []).append(pages[i]['index'])
    return list(clusters.values())


def analyze_folder(folder_path, threshold=5):
    """Hauptfunktion: Lädt Bilder, extrahiert Merkmale, clustert und liefert JSON."""
    imgs = load_images_from_folder(folder_path)
    pages = []
    for idx, (fname, img) in enumerate(imgs, 1):
        pages.append({
            'index': idx,
            'filename': fname,
            'img': img,
            'header_hash': compute_header_footer_hash(img, 'header'),
            'footer_hash': compute_header_footer_hash(img, 'footer'),
            'barcodes': detect_barcodes(img),
            'hist': compute_histogram_signature(img),
            #'text': ocr_text(img)
        })
    groups = cluster_pages(pages, threshold)
    return {'groups': [{'pages': grp} for grp in groups]}