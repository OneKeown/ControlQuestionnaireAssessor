
from csv import reader

import pymupdf as fitz
import easyocr as easyocr
from transformers import pipeline
from pdf2image import convert_from_bytes
from pdf2image.exceptions import PDFPageCountError

POPPLER_PATH = r"C:\Users\mattc\poppler-25.12.0\Library\bin"

def assess_files(uploaded_files):
    # Placeholder function to process uploaded files and generate assessment feedback
    # In a real implementation, this would involve parsing the files and applying assessment logic
    feedback = "Assessment feedback based on uploaded files:\n"
    for file in uploaded_files:
        feedback += f"- Processed {file.name}\n"
    return feedback

def get_cert_text(uploaded_files):
    # Placeholder function to extract text from certificate files
    # In a real implementation, this would involve parsing the certificate files and extracting relevant information
    cert_text = "Extracted certificate information:\n"
    for file in uploaded_files:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        
        if text == "":
            # If no text is found, try to extract text from images in the PDF
            reader = easyocr.Reader(['en'])
            images = page.get_images(full=True)
            if images:
                text = extract_text_from_image_pdf(images)
        return text
    return cert_text


def extract_text_from_image_pdf(images):
    results = []
    for img in images:
        results.append(" ".join(reader.readtext(img, detail=0)))
    return " ".join(results)


def read_pdf_bytes(uploaded_file) -> bytes:
    uploaded_file.seek(0)
    data = uploaded_file.read()

    if not data:
        raise ValueError("File is empty")

    if not data.startswith(b"%PDF"):
        raise ValueError("File does not appear to be a real PDF")

    return data

def LLM_assessment(uploaded_files):
    results = []
    qa_pipeline = pipeline(
    "document-question-answering",
    model="impira/layoutlm-document-qa")
    
    for uploaded_file in uploaded_files:
        try:
            pdf_bytes = read_pdf_bytes(uploaded_file)

            pages = convert_from_bytes(
                pdf_bytes,
                dpi=200,
                poppler_path=POPPLER_PATH,
            )

            results.append(f"{uploaded_file.name}: loaded {len(pages)} pages")

        except PDFPageCountError as e:
            results.append(
                f"{uploaded_file.name}: PDFPageCountError - "
                f"file may be corrupted or unreadable by Poppler: {e}"
            )
        except Exception as e:
            results.append(f"{uploaded_file.name}: {e}")

    
    
    image= pages[0] 
    
    questions = [
        "What kind of document is this?",
        "Is this an ISO 27001 certificate?",
        "What standard is this certificate issued against?",
        "What is the expiry date?",
        "What is the valid until date?",
        "What is the certificate number?",
        "What is the name of the certified company?",
        "Which assessing company issued this certificate?",
        "What is the certification body of this document?"
    ]

    results = {}
    for q in questions:
        try:
            answer = qa_pipeline(image=image, question=q)
            results[q] = answer
        except Exception as e:
            results[q] = {"error": str(e)}
    return str(results)




