# ocr_utils.py
import pytesseract
from PIL import Image
import cv2
import numpy as np
import spacy
import re  # For regex-based extraction
from pymongo import MongoClient

# Configure Tesseract path (update this path based on your system)
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\kusha\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Load spaCy's English language model
nlp = spacy.load("en_core_web_sm")

# MongoDB client setup
client = MongoClient('mongodb://localhost:27017/')  # Connect to MongoDB server
db = client['ocr_database']  # Database name
collection = db['entities']  # Collection name

def preprocess_image(image):
    """
    Preprocess the image for better OCR accuracy.
    Converts the image to grayscale and applies thresholding.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    # Apply thresholding
    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return Image.fromarray(binary)

def extract_text_from_image(image_file):
    """
    Extract text from an image using OCR.
    """
    try:
        # Open the image using PIL
        image = Image.open(image_file)
        # Preprocess the image (optional)
        processed_image = preprocess_image(image)
        # Use pytesseract to extract text
        extracted_text = pytesseract.image_to_string(processed_image)
        return extracted_text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

def extract_entities(text):
    """
    Extract specific entities (patient name, doctor name, drug name, quantity) using spaCy NER and regex.
    """
    doc = nlp(text)
    entities = {
        "patient_name": [],
        "doctor_name": [],
        "drug_name": [],
        "quantity": []
    }

    # Extract Patient Name (Look for "PATIENT" keyword)
    patient_match = re.search(r"PATIENT\s*\([MF]\)\s*/\s*(\d+Y)\s*(.*)", text)
    if patient_match:
        entities["patient_name"].append(patient_match.group(2).strip())

    # Extract Doctor Name (Look for "Dr." or "Doctor")
    doctor_match = re.search(r"Dr\.\s*([A-Za-z]+)", text)
    if doctor_match:
        entities["doctor_name"].append(doctor_match.group(1).strip())

    # List of common drug names to look for
    common_drugs = [
        "Paracetamol", "Ibuprofen", "Amoxicillin", "Lisinopril", "Metformin", 
        "Atorvastatin", "Omeprazole", "Levothyroxine", "Amlodipine", "Simvastatin", 
        "Losartan", "Metoprolol", "Albuterol", "Gabapentin", "Hydrochlorothiazide", 
        "Sertraline", "Prednisone", "Tramadol", "Citalopram", "Warfarin", "Methamphetamine", "Dolo 650"]

    # Extract Drug Names (Look for common drug names in the text)
    for drug in common_drugs:
        if re.search(rf"\b{drug}\b", text, re.IGNORECASE):
            entities["drug_name"].append(drug)

    # Extract Quantities (Look for numbers after "Tot:" or similar keywords)
    quantity_matches = re.findall(r"Tot:\s*(\d+)", text)
    for qty in quantity_matches:
        entities["quantity"].append(qty.strip())

    return entities

def store_entities_in_mongo(entities):
    """
    Store extracted entities into MongoDB.
    """
    try:
        collection.insert_one(entities)  # Insert the extracted entities into MongoDB
        print("Entities successfully stored in MongoDB.")
    except Exception as e:
        print(f"Error storing entities in MongoDB: {e}")
