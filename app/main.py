from fastapi import FastAPI, File, UploadFile, HTTPException, Form,Depends
from fastapi.responses import JSONResponse,FileResponse
from datetime import datetime
from sqlalchemy.orm import Session
from database.models.db import init_db,get_db
from database.resume_models import ResumeUpload
from src.parse_resume import extract_resume
from langchain_ollama import OllamaLLM
from src.schema import json_structure
from prompt.structured_prompt import parse_resume_with_llm
from prompt.kpmg_prompt import wrap_kpmg_template_from_json
from src.export_to_pdf import create_kpmg_template_pdf
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils.email_utils import send_email_notification
import os

app = FastAPI()
init_db()

UPLOAD_FOLDER = "uploaded_resumes"
JD_FOLDER = "JD"
OUTPUT_FOLDER = "output/KPMG_Template.pdf"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(JD_FOLDER, exist_ok=True)

llm = OllamaLLM(model="llama3.2:3b", temperature=0.0)
embeddings = SentenceTransformer('all-MiniLM-L6-V2')

# @app.post("/upload_resume/")
# async def upload_resume(file: UploadFile = File(...)):
#     try:
#         filename = file.filename
#         ext = os.path.splitext(filename)[1].lower()
#         if ext not in [".pdf", ".docx"]:
#             raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")
#
#         file_path = os.path.join(UPLOAD_FOLDER, filename)
#
#         # Save the file
#         with open(file_path, "wb") as f:
#             content = await file.read()
#             f.write(content)
#
#         print("Extracting the resume .pdf / .docx file...")
#         text = extract_resume(file_path)
#         json_schema = json_structure()
#         print("Converting structured Resume......")
#         structured = parse_resume_with_llm(text, llm, json_schema)
#         formatted_resume = wrap_kpmg_template_from_json(structured)
#         print("Structured Output")
#         print("="*60)
#         print(structured)
#         print("=" * 60)
#         print("Converting structured Resume to PDF Format......")
#         create_kpmg_template_pdf(structured)
#
#         return JSONResponse(content={
#             "filename": filename,
#             "message": "Resume processed successfully!",
#             "Resume Upload Time is":f"you uploaded resume time is {datetime.now()}",
#             "text":text
#         })
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post('/compare_input_resume_with_jd')
async def compare_output_resume_with_jd(file: UploadFile = File(...),jd_text: str = Form(...)):
    try:
        input_filename = file.filename
        ext = os.path.splitext(input_filename)[1].lower()
        if ext not in [".pdf", ".docx"]:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

        input_file_path = os.path.join(UPLOAD_FOLDER, input_filename)
        output_filepath = "output/KPMG_Template.pdf"
        if not os.path.exists(output_filepath):
            raise HTTPException(status_code=404, detail="File not found")


        with open(input_file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        print("Extracting the resume .pdf / .docx file...")
        text = extract_resume(input_file_path)
        resume_embedding = embeddings.encode([text])
        jd_embedding = embeddings.encode([jd_text])
        score = cosine_similarity(resume_embedding, jd_embedding)[0][0]
        similarity = round(float(score) * 100, 2)
        if similarity>=50:
            print(f"Resume matches JD Successfully by {similarity}%",)
            json_schema = json_structure()
            print("Converting structured Resume......")
            structured = parse_resume_with_llm(text, llm, json_schema)
            formatted_resume = wrap_kpmg_template_from_json(structured)
            print("Structured Output")
            print("=" * 60)
            print(structured)
            print("=" * 60)
            print("Converting structured Resume to PDF Format......")
            create_kpmg_template_pdf(structured)
            print("Output Resume is extracted to text...")
            output_test = extract_resume(output_filepath)
            input_embedding = embeddings.encode([text])
            output_embedding = embeddings.encode([output_test])
            score2 = round(float(cosine_similarity(input_embedding, output_embedding)[0][0]) * 100, 2)
            send_email_notification()
            return JSONResponse(content={
                "filename": input_filename,
                "message": "Resume processed successfully!",
                "Resume Upload Time is": f"you uploaded resume time is {datetime.now()}",
                "Score1": f"Resume matches JD by {similarity}%",
                "Compare_input_output_score": f"{score2}%",
                "Email": "email sent successfully"
            })
        else:
            print(f"Resume not matched JD by {similarity}%", )
            return {
                "Similarity_score_percent":f"Resume not matches JD by {similarity}%",
                "message":  "Resume not processed successfully",
                "Resume Upload Time is": f"you uploaded resume time is {datetime.now()}",
            }
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

@app.post("/send_notification")
def send_notification(score: float):
    if score>=50:
        send_email_notification()
        return "Email sent successfully"
    else:
        return f"Score is below {score}%, so email is not sent"

@app.post("/store_the_resume_in_DB")
def store_the_resume_in_DB(
    score: float = Form(...),
    compare_inputandoutput_resume_score: float = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    notification_status = "Email Sent" if score >= 50 else "Email Not Sent"

    output_resume_path = "output/KPMG_Template.pdf"

    new_resume = ResumeUpload(
        filename=file.filename,
        output_resume=output_resume_path,
        score=score,
        email=notification_status,
        Time=datetime.now(),
        score2=compare_inputandoutput_resume_score
    )

    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    return {
        "message": "Resume stored successfully",
        "score": score,
        "input_vs_output_score": compare_inputandoutput_resume_score,
        "email_status": notification_status
    }

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

@app.delete("/delete_resume/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(ResumeUpload).filter(ResumeUpload.id == resume_id).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
    return {"message": f"Resume with id {resume_id} deleted successfully"}


