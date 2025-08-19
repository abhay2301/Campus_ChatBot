# ChatBot/generate_knowledge_base.py

import os
import json
import docx
from PyPDF2 import PdfReader

DATA_DIR = "ChatBot/data_files"
KB_PATH = "ChatBot/knowledge_base.json"

def extract_text_from_file(file_path):
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    else:
        return None  # Unsupported file

def build_knowledge_base():
    knowledge_data = []

    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        content = extract_text_from_file(file_path)
        if content:
            knowledge_data.append({
                "title": filename,
                "content": content.strip()
            })

    # Save to JSON
    with open(KB_PATH, "w", encoding="utf-8") as f:
        json.dump(knowledge_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Extracted data from {len(knowledge_data)} files and saved to {KB_PATH}")

if __name__ == "__main__":
    build_knowledge_base()
