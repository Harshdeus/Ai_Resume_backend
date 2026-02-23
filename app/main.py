from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from src.parse_resume import extract_resume
from langchain_ollama import OllamaLLM
from src.schema import json_structure
from prompt.structured_prompt import parse_resume_with_llm
from prompt.kpmg_prompt import wrap_kpmg_template_clean
from src.export_to_pdf import save_resume_as_pdf_reportlab
import os

app = FastAPI()

UPLOAD_FOLDER = "uploaded_resumes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
llm = OllamaLLM(model="llama3.2:3b", temperature=0.0)

@app.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".docx"]:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # Save the file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        text = extract_resume(file_path)
        json_schema = json_structure()
        structured = parse_resume_with_llm(text, llm, json_schema)
        formatted_resume = wrap_kpmg_template_clean(structured)
        save_resume_as_pdf_reportlab(formatted_resume)

        return JSONResponse(content={
            "filename": filename,
            "message": "Resume processed successfully!",
            "extracted_text": text
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resumes/")
async def list_resumes():
    files = os.listdir(UPLOAD_FOLDER)
    return {"uploaded_resumes": files}

@app.delete("/resumes/{filename}")
async def delete_resume(filename: str):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(file_path)
    return {"message": f"{filename} deleted successfully"}
