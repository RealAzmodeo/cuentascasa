import sys
import os

# Try to use a common library if available, otherwise suggest it
try:
    import pypdf
except ImportError:
    # If not present, we will try to use another method or notify user
    pass

PDF_PATH = "d:/Proyectos/Antigravity Offline/Cuentas-Casa/Extractos bancarios/72ae3406-872f-452f-87f7-f8d7f475d3f6.pdf"

def analyze_pdf():
    if not os.path.exists(PDF_PATH):
        print(f"Error: {PDF_PATH} not found.")
        return

    try:
        from pypdf import PdfReader
        reader = PdfReader(PDF_PATH)
        print(f"Number of pages: {len(reader.pages)}")
        
        # Extract first page text
        text = reader.pages[0].extract_text()
        print("\n--- PDF CONTENT (PAGE 1) ---")
        print(text[:2000]) # First 2000 chars
    except Exception as e:
        print(f"Error analyzing PDF: {e}")

if __name__ == "__main__":
    analyze_pdf()
