import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_CC = os.getenv("EMAIL_CC")

def send_email_notification():
    subject = "Resume Shortlisted "
    body = """
    Hello,
    Your resume has been shortlisted for a job opportunity at DeUS Tech Services.
    You will be contacted soon regarding the next steps.
    Regards,
    Recruitment Team
    DeUS Tech Services
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Cc"] = EMAIL_CC
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    recipients =  EMAIL_TO.split(",") + EMAIL_CC.split(",")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())

    print("Email sent successfully")