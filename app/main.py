import json
import os
import traceback
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import Session

from database.candidate import Candidate
from database.job_description import JobDescription
from database.models.db import SessionLocal, init_db, get_db, Base
from database.resume_models import ResumeUpload
from database.user import User

from app.auth.JWT import (
    encrypt_password,
    decrypt_password,
    create_access_token,
    verify_access_token,
)
from src.parse_resume import extract_resume
from langchain_ollama import OllamaLLM
from src.schema import json_structure
from prompt.structured_prompt import parse_resume_with_llm
from src.export_to_pdf import create_kpmg_template_pdf
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils.email_utils import send_email_notification


def templet(company: str = "KPMG"):
    return company.strip().upper()


app = FastAPI()
init_db()


@app.on_event("startup")
def _ensure_tables():
    try:
        engine = SessionLocal().get_bind()
        Base.metadata.create_all(bind=engine)
        print("✅ All tables ensured.")
    except Exception as e:
        print("⚠️ Table ensure failed:", e)


selected_company = "KPMG"

UPLOAD_FOLDER = "uploaded_resumes"
JD_FOLDER = "JD"
OUTPUT_FOLDER = "output"
OUTPUT_FILEPATH = os.path.join(OUTPUT_FOLDER, "KPMG_Template.pdf")

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


class CompanyCreate(BaseModel):
    company_name: str


class ConvertTemplateRequest(BaseModel):
    company: str


class CompanyTemplate(Base):
    __tablename__ = "company_templates"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def get_user_by_email(email: str, db: Session) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.split(" ", 1)[1]

    try:
        payload = verify_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Forbidden: Insufficient role")
        return current_user
    return role_checker


def resume_quality_check(jd_score, capture_score, missing_info_percent, structured_resume):
    missing_fields = []

    required_fields = [
        "name",
        "primary_skill_set",
        "education",
        "work_experience",
        "project_experience",
    ]

    for field in required_fields:
        if not structured_resume.get(field):
            missing_fields.append(field)

    completeness = round((len(required_fields) - len(missing_fields)) / len(required_fields) * 100, 2)

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
        "quality_status": quality_status,
    }


@app.post("/Generate_different_templets")
def templets_generator(
    req: TemplateRequest,
    current_user: User = Depends(get_current_user),
):
    global selected_company
    selected_company = templet(req.company)
    return {"status": "success", "company": selected_company}


def save_candidateto_db(db: Session, resume_text: str, score2: float, current_user: User):
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
        user_id=current_user.id,
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
        response = {
            "company_name": "Not Found",
            "position": "Not Found",
            "years_of_experience": "Not Found",
        }

    return response


@app.post("/compare_input_resume_with_jd")
async def compare_output_resume_with_jd(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    jd_file: Optional[UploadFile] = File(None),
    status: str = Form("Activate"),
    active_till_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        final_jd_text = None

        input_filename = file.filename
        ext = os.path.splitext(input_filename)[1].lower()
        if ext not in [".pdf", ".docx"]:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX resume files are allowed")

        if jd_file is not None:
            jd_filename = jd_file.filename or "jd"
            jd_ext = os.path.splitext(jd_filename)[1].lower()

            if jd_ext not in [".pdf", ".docx"]:
                raise HTTPException(status_code=400, detail="JD file must be PDF or DOCX")

            jd_path = os.path.join(JD_FOLDER, jd_filename)
            with open(jd_path, "wb") as f:
                f.write(await jd_file.read())

            jd_text = extract_resume(jd_path)

        jd_data = extract_field_jd(jd_text, status, active_till_date)
        print("Extracted JD:", jd_data)

        if jd_text:
            final_jd_text = jd_text

        if final_jd_text is None or not final_jd_text.strip():
            raise HTTPException(status_code=400, detail="Please paste JD text or upload a JD file")

        global selected_company
        company_selected = selected_company

        input_file_path = os.path.join(UPLOAD_FOLDER, input_filename)
        with open(input_file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        print("Extracting the resume .pdf / .docx file...")
        resume_text = extract_resume(input_file_path)

        resume_embedding = embeddings.encode([resume_text])
        jd_embedding = embeddings.encode([final_jd_text])
        score = cosine_similarity(resume_embedding, jd_embedding)[0][0]
        similarity = round(float(score) * 100, 2)

        if similarity >= 50 or similarity <= 50:
            print(f"Resume matches JD successfully by {similarity}%")

            json_schema = json_structure()
            print("Converting structured Resume...")
            structured = parse_resume_with_llm(resume_text, llm, json_schema)

            print("TYPE OF structured:", type(structured))
            print("VALUE OF structured:", structured)
            if isinstance(structured, list):
                if structured and isinstance(structured[0], dict):
                    structured = structured[0]
                else:
                    raise HTTPException(status_code=500, detail="Structured resume format is invalid")
            structured_json_path = os.path.join(OUTPUT_FOLDER, "structured_resume.json")
            with open(structured_json_path, "w", encoding="utf-8") as f:
                 json.dump(structured, f, indent=4)

            create_kpmg_template_pdf(structured, company_selected)

            if not os.path.exists(OUTPUT_FILEPATH):
                raise HTTPException(status_code=500, detail="Output PDF was not generated")

            output_text = extract_resume(OUTPUT_FILEPATH)
            input_embedding = embeddings.encode([resume_text])
            output_embedding = embeddings.encode([output_text])

            score2 = round(float(cosine_similarity(input_embedding, output_embedding)[0][0]) * 100, 2)
            missing_info_percent = round(100 - score2, 2)

            save_candidateto_db(db, resume_text, similarity, current_user)
            notification_status = "Email Not Sent"

            new_resume = ResumeUpload(
                filename=input_filename,
                output_resume=OUTPUT_FILEPATH,
                score=similarity,
                email=notification_status,
                Time=datetime.now(),
                score2=score2,
                missing_info=str(missing_info_percent),
                user_id=current_user.id,
            )
            db.add(new_resume)
            db.commit()
            db.refresh(new_resume)

            print("=" * 60)
            print("quality check ...")
            print(f"Resume matches JD by {similarity}%")
            print("Compare_input_output_score", f"{score2}%")
            print("Missing_info_percent", f"{missing_info_percent}%")
            print("=" * 60)

            return JSONResponse(
                content={
                    "filename": input_filename,
                    "message": "Resume processed successfully!",
                    "Resume Upload Time is": f"you uploaded resume time is {datetime.now()}",
                    "Score1": f"Resume matches JD by {similarity}%",
                    "Compare_input_output_score": f"{score2}%",
                    "Missing_info_percent": f"{missing_info_percent}%",
                    "Email": "email not sent yet",
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
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_jd")
def create_jd(
    company_name: str = Form(...),
    position: str = Form(...),
    years_of_experience: str = Form(...),
    status: str = Form("Activate"),
    active_till_date: Optional[str] = Form(None),

    work_mode: Optional[str] = Form(None),
    employment_type: Optional[str] = Form(None),
    min_budget_lpa: Optional[str] = Form(None),
    max_budget_lpa: Optional[str] = Form(None),

    db: Session = Depends(get_db),
    jd_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
):

    parsed_date = None
    if active_till_date:
        try:
            parsed_date = datetime.fromisoformat(active_till_date)
        except:
            parsed_date = None

    if jd_file is not None:
        filename = jd_file.filename
        filepath = os.path.join("jd_files", filename)

        with open(filepath, "wb") as f:
            f.write(jd_file.file.read())

        jd_text = extract_resume(filepath)

    job = JobDescription(
        company_name=company_name,
        position=position,
        years_of_experience=years_of_experience,
        jd=jd_text,
        active_till_date=parsed_date,
        status=status,
        created_time=datetime.now(),
        updated_time=datetime.now(),

        user_id=current_user.id,

        work_mode=work_mode,
        employment_type=employment_type,
        min_budget_lpa=min_budget_lpa,
        max_budget_lpa=max_budget_lpa
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "message": "JD stored successfully",
        "id": job.id
    }


@app.get("/get_all_jd")
def get_all_jd(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    print("CURRENT USER ID:", current_user.id)
    print("CURRENT USER ROLE:", current_user.role)

    if current_user.role == "admin":
        jd_list = db.query(JobDescription).order_by(JobDescription.id.desc()).all()
        print("ADMIN MODE - TOTAL JDS:", len(jd_list))
    else:
        jd_list = (
            db.query(JobDescription)
            .filter(JobDescription.user_id == current_user.id)
            .order_by(JobDescription.id.desc())
            .all()
        )
        print("USER MODE - TOTAL JDS:", len(jd_list))

    result = []
    for jd in jd_list:
        jd_text = jd.jd or ""
        result.append({
            "id": jd.id,
            "company_name": jd.company_name,
            "position": jd.position,
            "years_of_experience": jd.years_of_experience,
            "jd": jd_text,
            "description": jd_text,
            "jd_description": jd_text,
            "jd_text": jd_text,
            "status": jd.status,
            "active_till_date": jd.active_till_date.strftime("%Y-%m-%d %H:%M:%S") if jd.active_till_date else None,
            "created_time": jd.created_time.strftime("%Y-%m-%d %H:%M:%S") if jd.created_time else None,
            "updated_time": jd.updated_time.strftime("%Y-%m-%d %H:%M:%S") if jd.updated_time else None,
            "work_mode": jd.work_mode,
            "employment_type": jd.employment_type,
            "min_budget_lpa": jd.min_budget_lpa,
            "max_budget_lpa": jd.max_budget_lpa,
        })

    print("RETURNING JDS:", len(result))
    return {"job_descriptions": result}


@app.post("/send_notification")
def send_notification(
    score: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if score < 50:
        return {"message": f"Score is below {score}%, so email is not sent"}

    try:
        send_email_notification()

        latest_resume = (
            db.query(ResumeUpload)
            .filter(ResumeUpload.user_id == current_user.id)
            .order_by(ResumeUpload.Time.desc())
            .first()
        )

        if latest_resume:
            latest_resume.email = "Email Sent"
            db.commit()
            db.refresh(latest_resume)

        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@app.post("/store_the_resume_in_DB")
def store_the_resume_in_DB(
    score: float = Form(...),
    compare_inputandoutput_resume_score: float = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        user_id=current_user.id,
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


@app.get("/api/candidates")
def get_candidates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "admin":
        rows = db.query(Candidate).order_by(Candidate.extracted_on.desc()).all()
    else:
        rows = (
            db.query(Candidate)
            .filter(Candidate.user_id == current_user.id)
            .order_by(Candidate.extracted_on.desc())
            .all()
        )

    return [
        {
            "id": r.id,
            "candidate_name": r.candidate_name,
            "experience": r.experience,
            "score": r.score,
            "extracted_on": r.extracted_on,
            "position": r.position,
            "user_id": r.user_id,
        }
        for r in rows
    ]


@app.get("/dashboard")
def get_database(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "admin":
        rows = db.query(ResumeUpload).order_by(ResumeUpload.Time.desc()).all()
    else:
        rows = (
            db.query(ResumeUpload)
            .filter(ResumeUpload.user_id == current_user.id)
            .order_by(ResumeUpload.Time.desc())
            .all()
        )

    return [
        {
            "Id": r.id,
            "InputResume": r.filename,
            "OutputResume": r.output_resume,
            "JDScore": r.score,
            "OutputScore": r.score2,
            "Email": r.email,
            "Time": r.Time,
        }
        for r in rows
    ]


@app.get("/download_resume")
async def download_resume(current_user: User = Depends(get_current_user)):
    output_file = os.path.join(OUTPUT_FOLDER, "KPMG_Template.pdf")
    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=output_file,
        media_type="application/pdf",
        filename=f"{selected_company}_Template.pdf",
    )


@app.get("/view_resume")
async def view_resume(current_user: User = Depends(get_current_user)):
    output_file = os.path.join(OUTPUT_FOLDER, "KPMG_Template.pdf")
    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=output_file, media_type="application/pdf")


@app.delete("/delete_resume/{resume_id}")
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ResumeUpload).filter(ResumeUpload.id == resume_id)

    if current_user.role != "admin":
        query = query.filter(ResumeUpload.user_id == current_user.id)

    resume = query.first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    db.delete(resume)
    db.commit()
    return {"message": f"Resume with id {resume_id} deleted successfully"}


@app.get("/company_templates")
def get_company_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(CompanyTemplate).order_by(CompanyTemplate.id.desc()).all()
    return [{"id": r.id, "company_name": r.company_name} for r in rows]


@app.post("/company_templates")
def create_company_template(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@app.delete("/company_templates/{template_id}")
def delete_company_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(CompanyTemplate).filter(CompanyTemplate.id == template_id).first()

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(row)
    db.commit()

    return {"message": "Template deleted successfully"}


@app.post("/convert_template")
def convert_template(
    req: ConvertTemplateRequest,
    current_user: User = Depends(get_current_user),
):
    company_selected = req.company.upper()
    json_path = "output/structured_resume.json"
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Structured JSON not found")

    with open(json_path, "r", encoding="utf-8") as f:
        structured = json.load(f)

    create_kpmg_template_pdf(structured, company_selected)
    return {"message": "Template converted successfully"}


@app.put("/job_descriptions/{jd_id}")
def update_jd(
    jd_id: int,
    company_name: str = Form(...),
    position: str = Form(...),
    years_of_experience: str = Form(...),
    jd_description: Optional[str] = Form(None),
    status: str = Form(...),
    active_till_date: Optional[str] = Form(None),

    work_mode: Optional[str] = Form(None),
    employment_type: Optional[str] = Form(None),
    min_budget_lpa: Optional[str] = Form(None),
    max_budget_lpa: Optional[str] = Form(None),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(JobDescription).filter(JobDescription.id == jd_id)

    if current_user.role != "admin":
        query = query.filter(JobDescription.user_id == current_user.id)

    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="JobDescription not found")

    job.company_name = company_name
    job.position = position
    job.years_of_experience = years_of_experience
    job.jd = jd_description
    job.status = status

    job.work_mode = work_mode
    job.employment_type = employment_type
    job.min_budget_lpa = min_budget_lpa
    job.max_budget_lpa = max_budget_lpa

    if active_till_date:
        job.active_till_date = datetime.fromisoformat(active_till_date.replace(" ", "T"))
    else:
        job.active_till_date = None

    job.updated_time = datetime.now()
    db.commit()
    db.refresh(job)

    return {"message": "JD updated successfully", "id": job.id}


@app.delete("/delete_jd/{delete_id}")
def delete_jd(
    delete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(JobDescription).filter(JobDescription.id == delete_id)

    if current_user.role != "admin":
        query = query.filter(JobDescription.user_id == current_user.id)

    job = query.first()
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
    db: Session = Depends(get_db),
):
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
        role="hr",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": f"Account created for {username} with role hr"}


@app.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
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

    user.is_logged_in = True
    user.last_login = datetime.now()

    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )

    return {
        "message": f"Login successful! Welcome, {user.username}",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_logged_in": user.is_logged_in,
        }
    }


@app.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.is_logged_in = False
    db.commit()
    db.refresh(current_user)

    return {
        "message": f"{current_user.username} has been logged out",
        "is_logged_in": current_user.is_logged_in,
    }


@app.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_logged_in": current_user.is_logged_in,
    }


@app.post("/forget-password")
def forget_password(
    email: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    if not new_password:
        raise HTTPException(status_code=400, detail="New password is required")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email not registered")

    encrypted_password = encrypt_password(new_password)
    user.password_hash = encrypted_password

    db.commit()
    db.refresh(user)

    return {"message": "Password has been successfully updated"}


@app.get("/admin/dashboard")
def admin_dashboard(current_user: User = Depends(require_role("admin"))):
    return {"message": f"Welcome Admin {current_user.username}"}


@app.post("/admin/update-role")
def update_role(
    user_id: int = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    db.commit()
    db.refresh(user)
    return {"message": f"Role updated to {role} for {user.username}"}


@app.delete("/admin/delete-user/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"{user.username} deleted successfully"}


@app.get("/admin/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "is_logged_in": u.is_logged_in,
        }
        for u in users
    ]


@app.post("/admin/logout-user")
def admin_logout_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_logged_in = False
    db.commit()
    db.refresh(user)

    return {
        "message": f"{user.username} has been logged out",
        "is_logged_in": user.is_logged_in,
    }


@app.get("/active-users")
def active_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    users = db.query(User).filter(User.is_logged_in == True).all()
    return [
        {
            "username": u.username,
            "role": u.role,
            "last_login": u.last_login,
        }
        for u in users
    ]