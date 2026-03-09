# import json
# from database.candidate import Candidate
# from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
# from pydantic import BaseModel
# from fastapi.responses import JSONResponse, FileResponse
# from fastapi.middleware.cors import CORSMiddleware
# from datetime import datetime
# from sqlalchemy.orm import Session
# from typing import Optional
# import os
# from database.job_description import JobDescription
# from database.models.db import SessionLocal, init_db, get_db
# from database.resume_models import ResumeUpload

# from src.parse_resume import extract_resume
# from langchain_ollama import OllamaLLM
# from src.schema import json_structure
# from prompt.structured_prompt import parse_resume_with_llm
# from prompt.kpmg_prompt import wrap_kpmg_template_from_json
# from src.export_to_pdf import create_kpmg_template_pdf
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
# from utils.email_utils import send_email_notification

# # If you want to use the separate file:
# # from src.templet import templet

# def templet(company: str = "KPMG"):
#     return company.strip().upper()


# app = FastAPI()
# init_db()

# # Global selected template
# selected_company = "KPMG"

# UPLOAD_FOLDER = "uploaded_resumes"
# JD_FOLDER = "JD"
# OUTPUT_FILEPATH = "output/KPMG_Template.pdf"  # generated pdf path
# OUTPUT_FOLDER = "output"

# os.makedirs(OUTPUT_FOLDER, exist_ok=True)
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(JD_FOLDER, exist_ok=True)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# llm = OllamaLLM(model="llama3.2:3b", temperature=0.0)
# embeddings = SentenceTransformer("all-MiniLM-L6-V2")


# class TemplateRequest(BaseModel):
#     company: str



# @app.post("/Generate_different_templets")
# def templets_generator(req: TemplateRequest):
#     global selected_company
#     selected_company = templet(req.company)
#     return {"status": "success", "company": selected_company}


# def save_candidateto_db(db: Session, resume_text: str, score2: float):
#     candidate_prompt = f"""
# You are an AI that extracts structured information from a resume.

# Return ONLY JSON with these fields:
# - name
# - position
# - experience

# If a field is missing, return "Not Found".
# Do not return any extra keys.

# Example output:
# {{
#   "name": "John Doe",
#   "position": "Data Scientist",
#   "experience": "5 years"
# }}

# Resume:
# {resume_text}
# """

#     response_text = llm.invoke(candidate_prompt)

#     try:
#         response = json.loads(response_text)
#         if not isinstance(response, dict):
#             raise ValueError("LLM did not return a JSON object")
#     except Exception:
#         print("Invalid JSON from LLM:", response_text)
#         response = {"name": "Not Found", "position": "Not Found", "experience": "Not Found"}

#     candidate = Candidate(
#         candidate_name=response.get("name", "Not Found"),
#         position=response.get("position", "Not Found"),
#         experience=response.get("experience", "Not Found"),
#         score=score2,
#         extracted_on=datetime.now(),   # ✅ because DB says NOT NULL
#     )

#     db.add(candidate)
#     db.commit()
#     db.refresh(candidate)
#     return candidate
 

# def extract_field_jd(jd_text: str,status,active_till_date):
#     jd_prompt = f"""
# You are an AI that extracts structured information from Job Descriptions.
# Return ONLY JSON with the fields: company_name, position, years_of_experience.
# If a field is missing, return "Not Found".
# Do NOT add extra text or explanations.

# Example output:
# {{
#   "company_name": "ABC Corp",
#   "position": "Data Scientist",
#   "years_of_experience": "3-5 years"
# }}

# Job Description:
# {jd_text}
# """
#     response_text = llm.invoke(jd_prompt)
#     try:
#         response = json.loads(response_text)
#     except Exception as e:
#         print("LLM returned invalid JSON:", response_text)
#         response = {"company_name": "Not Found", "position": "Not Found", "years_of_experience": "Not Found"}
#     db = SessionLocal()
#     job = JobDescription(
#         company_name=response.get("company_name", "Not Found"),
#         position=response.get("position", "Not Found"),
#         years_of_experience=response.get("years_of_experience", "Not Found"),
#         active_till_date=active_till_date,
#         status=status,
#         created_time=datetime.now(),
#         updated_time=datetime.now(),
#     )
#     db.add(job)
#     db.commit()
#     db.refresh(job)
#     db.close()
#     return response


# @app.post("/compare_input_resume_with_jd")
# async def compare_output_resume_with_jd(file: UploadFile = File(...), jd_text: str = Form(...),
#     status: str = Form("Activate"),  active_till_date: Optional[str] = Form(None),db: Session = Depends(get_db)):
#     try:
#         # Validate resume
#         input_filename = file.filename
#         ext = os.path.splitext(input_filename)[1].lower()
#         if ext not in [".pdf", ".docx"]:
#             raise HTTPException(status_code=400, detail="Only PDF and DOCX resume files are allowed")

#         # JD: either uploaded file or pasted text
#         final_jd_text = None
#         jd_data = extract_field_jd(jd_text,status,active_till_date)
#         print("Extracted JD:", jd_data)

#         if (final_jd_text is None or not final_jd_text.strip()) and jd_text:
#             final_jd_text = jd_text

#         if final_jd_text is None or not final_jd_text.strip():
#             raise HTTPException(status_code=400, detail="Please paste JD text or upload a JD file")

#         # Template: allow frontend to send template directly
#         global selected_company

#         company_selected = selected_company

#         # Save resume to disk
#         input_file_path = os.path.join(UPLOAD_FOLDER, input_filename)
#         with open(input_file_path, "wb") as f:
#             content = await file.read()
#             f.write(content)

#         # Extract resume text
#         print("Extracting the resume .pdf / .docx file...")
#         resume_text = extract_resume(input_file_path)
  
#         # Similarity
#         resume_embedding = embeddings.encode([resume_text])
#         jd_embedding = embeddings.encode([final_jd_text])
#         score = cosine_similarity(resume_embedding, jd_embedding)[0][0]
#         similarity = round(float(score) * 100, 2)

#         if similarity >= 50:
#             print(f"Resume matches JD Successfully by {similarity}%")

#             json_schema = json_structure()
#             print("Converting structured Resume......")
#             structured = parse_resume_with_llm(resume_text, llm, json_schema)
#             candidate = structured.get("name")
#             # Generate output PDF
#             print("Converting structured Resume to PDF Format......")
#             create_kpmg_template_pdf(structured, company_selected)  # writes to OUTPUT_FILEPATH by default

#             # Ensure output exists now
#             if not os.path.exists(OUTPUT_FILEPATH):
#                 raise HTTPException(status_code=500, detail="Output PDF was not generated")

#             # Compare input vs output (optional)
#             output_text = extract_resume(OUTPUT_FILEPATH)
#             input_embedding = embeddings.encode([resume_text])
#             output_embedding = embeddings.encode([output_text])
#             score2 = round(float(cosine_similarity(input_embedding, output_embedding)[0][0]) * 100, 2)
#             print("saving the candidate details")
            
#             send_email_notification()
#             notification_status = "Email Sent" if score >= 50 else "Email Not Sent"
#             output_resume_path = OUTPUT_FILEPATH
#             new_resume = ResumeUpload(
#                 filename=input_filename,                  # resume file name
#                 output_resume=OUTPUT_FILEPATH,            # generated output pdf path
#                 score=similarity,                         # JD similarity score
#                 email=notification_status,                # "Email Sent" or "Email Not Sent"
#                 Time=datetime.now(),                      # upload time
#                 score2=score2,                            # input vs output similarity
#                 candidate=candidate,                      # extracted from resume
#                 company=company_selected,                 # template/company used
#             )
#             db.add(new_resume)
#             db.commit()
#             db.refresh(new_resume)
#             save_candidateto_db(db, resume_text, score2)
#             return JSONResponse(
#                 content={
#                     "filename": input_filename,
#                     "message": "Resume processed successfully!",
#                     "Resume Upload Time is": f"you uploaded resume time is {datetime.now()}",
#                     "Score1": f"Resume matches JD by {similarity}%",
#                     "Compare_input_output_score": f"{score2}%",
#                     "Email": "email sent successfully",
#                     "template_used": company_selected,
#                 }
#             )
#         print(f"Resume not matched JD by {similarity}% so Template is not created")
#         return {
#             "Similarity_score_percent": f"Resume not matches JD by {similarity}%",
#             "message": "Resume not processed successfully",
#             "Resume Upload Time is": f"you uploaded resume time is {datetime.now()}",
#             "template_used": company_selected,
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
# @app.post("/create_jd")
# def create_jd(
#     company_name: str = Form(...),
#     position: str = Form(...),
#     years_of_experience: str = Form(...),
#     status: str = Form("Activate"),
#     active_till_date: Optional[str] = Form(None),
#     db: Session = Depends(get_db),
# ):

#     job = JobDescription(
#         company_name=company_name,
#         position=position,
#         years_of_experience=years_of_experience,
#         status=status,
#         active_till_date=active_till_date,
#         created_time=datetime.now(),
#         updated_time=datetime.now(),
#     )
#     db.add(job)
#     db.commit()
#     db.refresh(job)
#     return {"message": "JD stored successfully", "id": job.id}

# @app.get("/get_all_jd")
# def get_all_jd(db: Session = Depends(get_db)):
#     jd_list = db.query(JobDescription).all()
#     result = []
#     for jd in jd_list:
#         result.append({
#             "id": jd.id,
#             "company_name": jd.company_name,
#             "position": jd.position,
#             "years_of_experience": jd.years_of_experience,
#             "status": jd.status,
#             "active_till_date": jd.active_till_date.strftime("%Y-%m-%d %H:%M:%S") if jd.active_till_date else None,
#             "created_time": jd.created_time.strftime("%Y-%m-%d %H:%M:%S") if jd.created_time else None,
#             "updated_time": jd.updated_time.strftime("%Y-%m-%d %H:%M:%S") if jd.updated_time else None
#         })
#     return {"job_descriptions": result}
 

# @app.post("/send_notification")
# def send_notification(score: float):
#     if score >= 50:
#         send_email_notification()
#         return "Email sent successfully"
#     else:
#         return f"Score is below {score}%, so email is not sent"


# @app.post("/store_the_resume_in_DB")
# def store_the_resume_in_DB(
#     score: float = Form(...),
#     compare_inputandoutput_resume_score: float = Form(...),
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db),
# ):
#     notification_status = "Email Sent" if score >= 50 else "Email Not Sent"
#     output_resume_path = OUTPUT_FILEPATH

#     new_resume = ResumeUpload(
#         filename=file.filename,
#         output_resume=output_resume_path,
#         score=score,
#         email=notification_status,
#         Time=datetime.now(),
#         score2=compare_inputandoutput_resume_score,
#     )

#     db.add(new_resume)
#     db.commit()
#     db.refresh(new_resume)

#     return {
#         "message": "Resume stored successfully",
#         "score": score,
#         "input_vs_output_score": compare_inputandoutput_resume_score,
#         "email_status": notification_status,
#     }

# @app.get("/candidate_data")
# def candidate_data_get(db: Session = Depends(get_db)):
#     rows = db.query(Candidate).order_by(Candidate.extracted_on.asc()).all()

#     return [
#         {
#             "Id": r.id,
#             "candidate_name": r.candidate_name,
#             "Position": r.position,
#             "Experience": r.experience,
#             "OutputCompareScore": r.score,
#             "Extracted_on": r.extracted_on.isoformat() if r.extracted_on else None,
#         }
#         for r in rows
#     ]

# @app.get("/dashboard")
# def get_database(db: Session = Depends(get_db)):
#     rows = db.query(ResumeUpload).order_by(ResumeUpload.Time.asc()).all()

#     return [
#         {
#            "Id":r.id,
#            "InputResume":r.filename,
#            "OutputResume":r.output_resume,
#            "JDScore":r.score,
#            "OutputScore":r.score2,
#            "Email":r.email,
#            "Time":r.Time
#         }
#         for r in rows
#     ]

# @app.get("/download_resume")
# async def download_resume():
#     output_file = os.path.join(OUTPUT_FOLDER, f"KPMG_Template.pdf")
#     if not os.path.exists(output_file):
#         raise HTTPException(status_code=404, detail="File not found")
#     return FileResponse(path=output_file, media_type="application/pdf", filename=f"{selected_company}_Template.pdf")
 

# @app.get("/view_resume")
# async def view_resume():
#     output_file = os.path.join(OUTPUT_FOLDER, "KPMG_Template.pdf")
#     extract = extract_resume(output_file)

#     if not os.path.exists(output_file):
#         raise HTTPException(status_code=404, detail="File not found")
#     return FileResponse(path=output_file, media_type="application/pdf")


# @app.delete("/delete_resume/{resume_id}")
# def delete_resume(resume_id: int, db: Session = Depends(get_db)):
#     resume = db.query(ResumeUpload).filter(ResumeUpload.id == resume_id).first()

#     if not resume:
#         raise HTTPException(status_code=404, detail="Resume not found")
#     db.delete(resume)
#     db.commit()
#     return {"message": f"Resume with id {resume_id} deleted successfully"}

import json
from database.candidate import Candidate
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from pydantic import BaseModel
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional
import os
from database.job_description import JobDescription
from database.models.db import SessionLocal, init_db, get_db, Base
from database.resume_models import ResumeUpload
from database.user import User
from app.auth.JWT import encrypt_password,decrypt_password
from src.parse_resume import extract_resume
from langchain_ollama import OllamaLLM
from src.schema import json_structure
from prompt.structured_prompt import parse_resume_with_llm
from prompt.kpmg_prompt import wrap_kpmg_template_from_json
from src.export_to_pdf import create_kpmg_template_pdf
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils.email_utils import send_email_notification

# If you want to use the separate file:
# from src.templet import templet

import json
from database.candidate import Candidate
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from pydantic import BaseModel
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional
import os
from database.job_description import JobDescription
from database.models.db import SessionLocal, init_db, get_db, Base
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

# ✅ NEW import for CompanyTemplate
from sqlalchemy import Column, Integer, String, DateTime, func


# If you want to use the separate file:
# from src.templet import templet

def templet(company: str = "KPMG"):
    return company.strip().upper()


app = FastAPI()
init_db()

# ✅ FIX: ensure all tables are created after ALL models are loaded
@app.on_event("startup")
def _ensure_tables():
    try:
        engine = SessionLocal().get_bind()
        Base.metadata.create_all(bind=engine)
        print("✅ All tables ensured (including company_templates).")
    except Exception as e:
        print("⚠️ Table ensure failed:", e)


# Global selected template
selected_company = "KPMG"

UPLOAD_FOLDER = "uploaded_resumes"
JD_FOLDER = "JD"
OUTPUT_FILEPATH = "output/KPMG_Template.pdf"  # generated pdf path
OUTPUT_FOLDER = "output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(JD_FOLDER, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = OllamaLLM(model="llama3.2:3b", temperature=0.0)
embeddings = SentenceTransformer("all-MiniLM-L6-V2")


class TemplateRequest(BaseModel):
    company: str

def resume_quality_check(jd_score, capture_score, missing_info_percent, structured_resume):
    missing_fields = []

    required_fields = [
        "name",
        "primary_skill_set",
        "education",
        "work_experience",
        "project_experience"
    ]

    for field in required_fields:
        if not structured_resume.get(field):
            missing_fields.append(field)

    completeness = round((len(required_fields) - len(missing_fields)) / len(required_fields) * 100, 2)

    # Quality status rules
    if jd_score >= 70 and capture_score >= 80 and completeness >= 80:
        quality_status = "Excellent"
    elif jd_score >= 50 and capture_score >= 70:
        quality_status = "Good"
    elif jd_score >= 30:
        quality_status = "Average"
    else:
        quality_status = "Poor"

    return {
        "jd_match_score": jd_score,
        "capture_accuracy": capture_score,
        "missing_information_percent": missing_info_percent,
        "completeness_percent": completeness,
        "missing_fields": missing_fields,
        "quality_status": quality_status
    }

@app.post("/Generate_different_templets")
def templets_generator(req: TemplateRequest):
    global selected_company
    selected_company = templet(req.company)
    return {"status": "success", "company": selected_company}


def save_candidateto_db(db: Session, resume_text: str, score2: float):
    candidate_prompt = f"""
You are an AI that extracts structured information from a resume.

Return ONLY JSON with these fields:
- name
- position
- experience

If a field is missing, return "Not Found".
Do not return any extra keys.

Example output:
{{
  "name": "John Doe",
  "position": "Data Scientist",
  "experience": "5 years"
}}

Resume:
{resume_text}
"""

    response_text = llm.invoke(candidate_prompt)

    try:
        response = json.loads(response_text)
        if not isinstance(response, dict):
            raise ValueError("LLM did not return a JSON object")
    except Exception:
        print("Invalid JSON from LLM:", response_text)
        response = {"name": "Not Found", "position": "Not Found", "experience": "Not Found"}

    candidate = Candidate(
        candidate_name=response.get("name", "Not Found"),
        position=response.get("position", "Not Found"),
        experience=response.get("experience", "Not Found"),
        score=score2,
        extracted_on=datetime.now(),  
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def extract_field_jd(jd_text: str, status, active_till_date):
    jd_prompt = f"""
You are an AI that extracts structured information from Job Descriptions.
Return ONLY JSON with the fields: company_name, position, years_of_experience.
If a field is missing, return "Not Found".
Do NOT add extra text or explanations.

Example output:
{{
  "company_name": "ABC Corp",
  "position": "Data Scientist",
  "years_of_experience": "3-5 years"
}}

Job Description:
{jd_text}
"""
    response_text = llm.invoke(jd_prompt)
    try:
        response = json.loads(response_text)
        structured_folder = os.path.join(OUTPUT_FOLDER, "JD_structure")
        os.makedirs(structured_folder, exist_ok=True)
        file_name = f"jd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        structured_json_store = os.path.join(structured_folder, file_name)
        with open(structured_json_store, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=4)
    except Exception:
        print("LLM returned invalid JSON:", response_text)
        response = {"company_name": "Not Found", "position": "Not Found", "years_of_experience": "Not Found"}

    db = SessionLocal()
    job = JobDescription(
        company_name=response.get("company_name", "Not Found"),
        position=response.get("position", "Not Found"),
        years_of_experience=response.get("years_of_experience", "Not Found"),
        active_till_date=active_till_date,
        status=status,
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    db.close()
    return response


@app.post("/compare_input_resume_with_jd")
async def compare_output_resume_with_jd(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    jd_file: Optional[UploadFile] = File(None),
    status: str = Form("Activate"),
    active_till_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    try:
        final_jd_text = None
        
        # Validate resume
        input_filename = file.filename
        ext = os.path.splitext(input_filename)[1].lower()
        if ext not in [".pdf", ".docx"]:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX resume files are allowed")

        # JD: either uploaded file or pasted text
        final_jd_text = None
        if jd_file is not None:
            jd_filename = jd_file.filename or "jd"
            jd_ext = os.path.splitext(jd_filename)[1].lower()

            if jd_ext not in [".pdf", ".docx"]:
                raise HTTPException(status_code=400, detail="JD file must be PDF or DOCX")

            jd_path = os.path.join(JD_FOLDER, jd_filename)
            with open(jd_path, "wb") as f:
                f.write(await jd_file.read())

            print("Converting pdf to text....")
            jd_text = extract_resume(jd_path)
        print(jd_text)
        jd_data = extract_field_jd(jd_text, status, active_till_date)
        print("Extracted JD:", jd_data)

        if (final_jd_text is None or not final_jd_text.strip()) and jd_text:
            final_jd_text = jd_text

        if final_jd_text is None or not final_jd_text.strip():
            raise HTTPException(status_code=400, detail="Please paste JD text or upload a JD file")

        global selected_company
        company_selected = selected_company

        # Save resume to disk
        input_file_path = os.path.join(UPLOAD_FOLDER, input_filename)
        with open(input_file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        print("Extracting the resume .pdf / .docx file...")
        resume_text = extract_resume(input_file_path)

        # Similarity
        resume_embedding = embeddings.encode([resume_text])
        jd_embedding = embeddings.encode([final_jd_text])
        score = cosine_similarity(resume_embedding, jd_embedding)[0][0]
        similarity = round(float(score) * 100, 2)

        if similarity >= 50 or similarity <=50 or similarity ==50:
            print(f"Resume matches JD Successfully by {similarity}%")

            json_schema = json_structure()
            print("Converting structured Resume......")
            structured = parse_resume_with_llm(resume_text, llm, json_schema)
            structured_json_path = os.path.join(OUTPUT_FOLDER,"structured_resume.json")
            with open(structured_json_path,"w") as f:
                json.dump(structured,f,indent=4)
            candidate = structured.get("name")
            
            print("Converting structured Resume to PDF Format......")
            create_kpmg_template_pdf(structured, company_selected)

            if not os.path.exists(OUTPUT_FILEPATH):
                raise HTTPException(status_code=500, detail="Output PDF was not generated")

            output_text = extract_resume(OUTPUT_FILEPATH)
            input_embedding = embeddings.encode([resume_text])
            output_embedding = embeddings.encode([output_text])
            score2 = round(float(cosine_similarity(input_embedding, output_embedding)[0][0]) * 100, 2)
            missing_info_percent = round(100 - score2, 2)
            save_candidateto_db(db, resume_text, score2)
            send_email_notification()
            notification_status = "Email Sent" if score >= 50 else "Email Not Sent"

            new_resume = ResumeUpload(
                filename=input_filename,
                output_resume=OUTPUT_FILEPATH,
                score=similarity,
                email=notification_status,
                Time=datetime.now(),
                score2=score2,
                missing_info_= missing_info_percent
            )
            db.add(new_resume)
            db.commit()
            db.refresh(new_resume)
            print('='*60)
            print("quality check ...")
            print(f"Resume matches JD by {similarity}%")
            print("Compare_input_output_score",f"{score2}%")
            print( "Missing_info_percent", f"{missing_info_percent}%")
            print('='*60)
            return JSONResponse(
                content={
                    "filename": input_filename,
                    "message": "Resume processed successfully!",
                    "Resume Upload Time is": f"you uploaded resume time is {datetime.now()}",
                    "Score1": f"Resume matches JD by {similarity}%",
                    "Compare_input_output_score": f"{score2}%",
                    "Missing_info_percent": f"{missing_info_percent}%",
                    "Email": "email sent successfully",
                    "template_used": company_selected,
                }
            )

        print(f"Resume not matched JD by {similarity}% so Template is not created")
        return {
            "Similarity_score_percent": f"Resume not matches JD by {similarity}%",
            "message": "Resume not processed successfully",
            "Resume Upload Time is": f"you uploaded resume time is {datetime.now()}",
            "template_used": company_selected,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_jd")
def create_jd(
        company_name: str = Form(...),
        position: str = Form(...),
        years_of_experience: str = Form(...),
        status: str = Form("Activate"),
        active_till_date: Optional[str] = Form(None),
        db: Session = Depends(get_db),
        jd_text: Optional[str] = Form(None),
        jd_file: Optional[UploadFile] = File(None),
):
    job = JobDescription(
        company_name=company_name,
        position=position,
        years_of_experience=years_of_experience,
        status=status,
        jd=jd_text,
        active_till_date=active_till_date,
        created_time=datetime.now(),
        updated_time=datetime.now(),

    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"message": "JD stored successfully", "id": job.id,"jd": job.jd}
 

@app.get("/get_all_jd")
def get_all_jd(db: Session = Depends(get_db)):
    jd_list = db.query(JobDescription).order_by(JobDescription.id.desc()).all()
    result = []

    for jd in jd_list:
        jd_text = jd.jd or "" 

        result.append({
            "id": jd.id,
            "company_name": jd.company_name,
            "position": jd.position,
            "years_of_experience": jd.years_of_experience,

            # ✅ keep existing key
            "jd": jd_text,

            # ✅ ADD THIS: ResumeCompare reads jd.description
            "description": jd_text,

            # (optional but helpful for future)
            "jd_description": jd_text,
            "jd_text": jd_text,

            "status": jd.status,
            "active_till_date": jd.active_till_date.strftime("%Y-%m-%d %H:%M:%S") if jd.active_till_date else None,
            "created_time": jd.created_time.strftime("%Y-%m-%d %H:%M:%S") if jd.created_time else None,
            "updated_time": jd.updated_time.strftime("%Y-%m-%d %H:%M:%S") if jd.updated_time else None
        })

    return {"job_descriptions": result}


@app.post("/send_notification")
def send_notification(score: float):
    if score >= 50:
        send_email_notification()
        return "Email sent successfully"
    else:
        return f"Score is below {score}%, so email is not sent"


@app.post("/store_the_resume_in_DB")
def store_the_resume_in_DB(
    score: float = Form(...),
    compare_inputandoutput_resume_score: float = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    notification_status = "Email Sent" if score >= 50 else "Email Not Sent"
    output_resume_path = OUTPUT_FILEPATH

    new_resume = ResumeUpload(
        filename=file.filename,
        output_resume=output_resume_path,
        score=score,
        email=notification_status,
        Time=datetime.now(),
        score2=compare_inputandoutput_resume_score,
    )

    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    return {
        "message": "Resume stored successfully",
        "score": score,
        "input_vs_output_score": compare_inputandoutput_resume_score,
        "email_status": notification_status,
    }


@app.get("/candidate_data")
def candidate_data_get(db: Session = Depends(get_db)):
    rows = db.query(Candidate).order_by(Candidate.extracted_on.desc()).all()

    return [
        {
            "Id": r.id,
            "candidate_name": r.candidate_name,
            "Position": r.position,
            "Experience": r.experience,
            "OutputCompareScore": r.score,
            "Extracted_on": r.extracted_on.isoformat() if r.extracted_on else None,
        }
        for r in rows
    ]


@app.get("/dashboard")
def get_database(db: Session = Depends(get_db)):
    rows = db.query(ResumeUpload).order_by(ResumeUpload.Time.desc()).all()

    return [
        {
           "Id": r.id,
           "InputResume": r.filename,
           "OutputResume": r.output_resume,
           "JDScore": r.score,
           "OutputScore": r.score2,
           "Email": r.email,
           "Time": r.Time
        }
        for r in rows
    ]


@app.get("/download_resume")
async def download_resume():
    output_file = os.path.join(OUTPUT_FOLDER, f"KPMG_Template.pdf")
    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=output_file, media_type="application/pdf", filename=f"{selected_company}_Template.pdf")


@app.get("/view_resume")
async def view_resume():
    output_file = os.path.join(OUTPUT_FOLDER, "KPMG_Template.pdf")
    extract = extract_resume(output_file)

    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=output_file, media_type="application/pdf")


@app.delete("/delete_resume/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(ResumeUpload).filter(ResumeUpload.id == resume_id).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
    return {"message": f"Resume with id {resume_id} deleted successfully"}


# ===============================
# Company Templates Persistence
# ===============================
class CompanyTemplate(Base):
    __tablename__ = "company_templates"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CompanyCreate(BaseModel):
    company_name: str


@app.get("/company_templates")
def get_company_templates(db: Session = Depends(get_db)):
    rows = db.query(CompanyTemplate).order_by(CompanyTemplate.id.desc()).all()
    return [{"id": r.id, "company_name": r.company_name} for r in rows]


@app.post("/company_templates")
def create_company_template(payload: CompanyCreate, db: Session = Depends(get_db)):
    name = (payload.company_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="company_name is required")

    existing = (
        db.query(CompanyTemplate)
        .filter(func.lower(CompanyTemplate.company_name) == name.lower())
        .first()
    )
    if existing:
        return {"id": existing.id, "company_name": existing.company_name}

    row = CompanyTemplate(company_name=name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "company_name": row.company_name}

class ConvertTemplateRequest(BaseModel):
    company:str

@app.post('/convert_template')
def convert_template(req:ConvertTemplateRequest):
    company_selected =  req.company.upper()
    json_path = "output/structured_resume.json"
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Structured JSON not found")
    with open(json_path, "r") as f:
        structured = json.load(f)
        create_kpmg_template_pdf(structured, company_selected)
        return {"message": "Template converted successfully"}

@app.put("/job_descriptions/{jd_id}")
def update_jd(
    jd_id: int,
    company_name: str = Form(...),
    position: str = Form(...),
    years_of_experience: str = Form(...),
    jd_description: str = Form(None),  
    status: str = Form(...),
    active_till_date: str = Form(None),
    db: Session = Depends(get_db),
):
    job = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="JobDescription not found")

    job.company_name = company_name
    job.position = position
    job.years_of_experience = years_of_experience
    job.jd =  jd_description
    job.status = status

    if jd_description is not None:
        job.jd_description = jd_description

    if active_till_date:
        job.active_till_date = datetime.fromisoformat(active_till_date.replace(" ", "T"))
    else:
        job.active_till_date = None

    job.updated_time = datetime.now()
    db.commit()
    db.refresh(job)

    return {"message": "JD updated successfully", "id": job.id}

@app.delete("/delete_jd/{delete_id}")
def delete_jd(delete_id: int, db: Session = Depends(get_db)):
    print("DELETE DB URL:", str(db.bind.url))
    job = db.query(JobDescription).filter(JobDescription.id == delete_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="JobDescription not found")
    db.delete(job)
    db.commit()
    return {"message": "JD deleted successfully", "deleted_id": delete_id}


@app.post("/signup")
def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("candidate"),
    db: Session = Depends(get_db)
):
    print(password)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    encrypted_password = encrypt_password(password)

    new_user = User(
        username=username,
        email=email,
        password_hash=encrypted_password,
        is_logged_in=False,
        last_login=None,
        role=role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": f"Account created for {username} with role {role}"}

# ------------------ LOGIN ------------------ #
@app.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email or password not provided")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email")

    try:
        stored_password = decrypt_password(user.password_hash)
    except Exception:
        raise HTTPException(status_code=500, detail="Error decrypting password")

    if password != stored_password:
        raise HTTPException(status_code=400, detail="Invalid password")

    # Update login status
    user.is_logged_in = True
    user.last_login = datetime.now()

    db.commit()
    db.refresh(user)

    return {
        "message": f"Login successful! Welcome, {user.username}",
        "username": user.username,
        "is_logged_in": user.is_logged_in,
        "email": user.email
    }
@app.post("/logout")
def logout(email: str = Form(...), db: Session = Depends(get_db)):
    from datetime import datetime
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.last_login = datetime.utcnow()  # fix here
    db.commit()
    db.refresh(user)  # optional but ensures latest state

    return {
        "message": f"{user.username} has been logged out",
        "is_logged_in": user.is_logged_in
    }
# ------------------ FORGET PASSWORD ------------------ #
@app.post("/forget-password")
def forget_password(
     username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    print(new_password)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email not registered")

    # Encrypt new password
    encrypted_password = encrypt_password(new_password)

    # Update the instance's password
    user.password_hash = encrypted_password
    User.username = username
    User.role = role
    db.commit()
    db.refresh(user)

    return {"message": "Password has been successfully updated"}

def get_current_user(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(required_role: str):
    def role_checker(user: User = Depends(get_current_user)):
        if user.role != required_role:
            raise HTTPException(status_code=403, detail="Forbidden: Insufficient role")
        return user
    return role_checker

@app.get("/admin/dashboard")
def admin_dashboard(current_user: User = Depends(require_role("admin"))):
    return {"message": f"Welcome Admin {current_user.username}"}
@app.post("/admin/update-role")
def update_role(user_id: int = Form(...), role: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    db.commit()
    db.refresh(user)
    return {"message": f"Role updated to {role} for {user.username}"}

@app.delete("/admin/delete-user/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"{user.username} deleted successfully"}

@app.get("/admin/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "email": u.email, "role": u.role, "is_logged_in": u.is_logged_in} for u in users]
@app.post("/admin/logout-user")
def admin_logout_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return {
        "message": f"{user.username} has been logged out",
        "is_logged_in": user.is_logged_in
    }
@app.get("/active-users")
def active_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_logged_in == True).all()
    return [{"username": u.username, "role": u.role, "last_login": u.last_login} for u in users]