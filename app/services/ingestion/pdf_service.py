import pdfplumber
from typing import List, Tuple

def extract_pdf(file_path: str) -> List[Tuple[str, int]]:
    results = []
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                results.append((text, page_num))
    return results
