from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse,FileResponse
from multipart import file_path

from src.parse_resume import extract_resume
from langchain_ollama import OllamaLLM
from src.schema import json_structure
from prompt.structured_prompt import parse_resume_with_llm
from prompt.kpmg_prompt import wrap_kpmg_template_from_json
from src.export_to_pdf import create_kpmg_template_pdf
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

app = FastAPI()

UPLOAD_FOLDER = "uploaded_resumes"
JD_FOLDER = "JD"
OUTPUT_FOLDER = "output/KPMG_Template.pdf"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(JD_FOLDER, exist_ok=True)

llm = OllamaLLM(model="llama3.2:3b", temperature=0.0)
embeddings = SentenceTransformer('all-MiniLM-L6-V2')

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
        print("Extracting the resume .pdf / .docx file...")
        text = extract_resume(file_path)
        json_schema = json_structure()
        print("Converting structured Resume......")
        structured = parse_resume_with_llm(text, llm, json_schema)
        formatted_resume = wrap_kpmg_template_from_json(structured)
        print("Structured Output")
        print("="*60)
        print(structured)
        print("=" * 60)
        print("Converting structured Resume to PDF Format......")
        create_kpmg_template_pdf(structured)

        return JSONResponse(content={
            "filename": filename,
            "message": "Resume processed successfully!",
            "extracted_text": text
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/compare_resume_with_jd')
async def compare_output_resume_with_jd(jd_text: str = Form(...)):
    try:
        filepath = "output/KPMG_Template.pdf"
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")
        text = extract_resume(filepath)
        resume_embedding = embeddings.encode([text])
        jd_embedding = embeddings.encode([jd_text])
        score = cosine_similarity(resume_embedding, jd_embedding)[0][0]
        similarity = round(float(score) * 100, 2)
        return {
            "Similarity_score_percent": similarity,
            "message": f"Resume matches JD by {similarity}%"
        }
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))


@app.get("/download_resume/{filename}")
async def download_resume():
    filepath = "output/KPMG_Template.pdf"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404,detail="File not found")
    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename="KPMG_Template.pdf"
    )
@app.get("/list-of-resumes-uploaded/")
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
