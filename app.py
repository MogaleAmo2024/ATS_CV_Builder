import os
import io
import json
import smtplib
from email.message import EmailMessage
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from docx import Document
from xhtml2pdf import pisa
from twilio.rest import Client as TwilioClient

load_dotenv()

app = FastAPI()

# Mount static folder for script.js
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
MODEL = "openrouter/free"

ATS_SYSTEM_PROMPT = """
You are a ruthless ATS (Applicant Tracking System) Optimization Algorithm and an Expert Technical Recruiter.
Your goal is to rewrite the user's raw experience into a resume that scores a 90%+ match, AND write a compelling Motivational Letter (Cover Letter) for the same job.

Follow these strict rules:
1. Analyze the Job Description: Extract the top 10 most critical hard skills, tools, and keywords.
2. Match: Cross-reference these with the user's raw experience. If the user has done the task (even if they used different words), use the exact terminology from the Job Description.
3. Rewrite: Use strong action verbs (e.g., "Spearheaded," "Engineered," "Optimized") and quantify results where possible.
4. Formatting: Use standard HTML tags (<h1>, <h2>, <ul>, <li>, <p>). Do not include markdown formatting like ```html.

You must output a JSON object with exactly two keys: "cv_html" and "letter_html".

For "cv_html": Format the optimized resume. Include the Target Job Title, Professional Summary, Core Competencies, Professional Experience, and Education.
For "letter_html": Write a professional 3-paragraph motivational letter. Address it to "Hiring Manager". 
- Paragraph 1: Express enthusiasm for the role and highlight your biggest matching achievement.
- Paragraph 2: Explain how your skills directly solve their needs based on the JD.
- Paragraph 3: Reiterate your interest and request an interview.
"""

def generate_pdf_bytes(html_content: str) -> bytes:
    full_html = f"""
    <html>
    <head>
        <style>
            @page {{ size: A4; margin: 2cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; color: #000; line-height: 1.5; }}
            h1 {{ font-size: 18pt; text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; }}
            h2 {{ font-size: 13pt; margin-top: 15px; border-bottom: 1px solid #ccc; padding-bottom: 3px; text-transform: uppercase; }}
            ul {{ margin-top: 5px; padding-left: 20px; }}
            li {{ margin-bottom: 4px; }}
            p {{ margin-bottom: 10px; }}
        </style>
    </head>
    <body>{html_content}</body>
    </html>
    """
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(full_html), dest=pdf_buffer)
    if pisa_status.err:
        raise Exception("Failed to generate PDF")
    return pdf_buffer.getvalue()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/extract")
async def extract_cv_text(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = ""
        if file.filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(content))
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        elif file.filename.lower().endswith(".docx"):
            doc = Document(io.BytesIO(content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif file.filename.lower().endswith(".txt"):
            text = content.decode("utf-8")
        else:
            return {"error": "Unsupported file type."}
        return {"text": text.strip()}
    except Exception as e:
        return {"error": str(e)}

@app.post("/generate")
async def generate_cv(
    experience: str = Form(...),
    job_description: str = Form(...),
    job_title: str = Form(...)
):
    prompt = f"""
    TARGET JOB TITLE: {job_title}
    
    JOB DESCRIPTION:
    {job_description}
    
    MY RAW EXPERIENCE:
    {experience}
    
    Please generate the optimized ATS CV and the Motivational Letter in a valid JSON object.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ATS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/download")
async def download_pdf(html_content: str = Form(...)):
    try:
        pdf_bytes = generate_pdf_bytes(html_content)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Optimized_Document.pdf"}
        )
    except Exception as e:
        return {"error": str(e)}

@app.post("/send-email")
async def send_email(html_content: str = Form(...), recipient_email: str = Form(...)):
    try:
        pdf_bytes = generate_pdf_bytes(html_content)
        sender = os.environ.get("SENDER_EMAIL")
        password = os.environ.get("SENDER_PASSWORD")
        
        if not sender or not password:
            return {"error": "Email credentials not set in .env"}

        msg = EmailMessage()
        msg['Subject'] = 'Your Optimized Job Application Documents'
        msg['From'] = sender
        msg['To'] = recipient_email
        msg.set_content('Please find your optimized document attached.')
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename='Optimized_Document.pdf')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
            
        return {"status": "success", "message": f"Email sent to {recipient_email}!"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/send-whatsapp")
async def send_whatsapp(html_content: str = Form(...), phone_number: str = Form(...)):
    try:
        pdf_bytes = generate_pdf_bytes(html_content)
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_WHATSAPP_FROM")
        
        if not account_sid or not auth_token:
            return {"error": "Twilio credentials not set in .env"}
            
        client_wa = TwilioClient(account_sid, auth_token)
        
        message = client_wa.messages.create(
            from_=from_number,
            to=f"whatsapp:{phone_number}",
            body="Your optimized document has been generated successfully! (Note: Twilio sandbox requires a public URL to send the actual PDF file)."
        )
        
        return {"status": "success", "message": f"WhatsApp sent to {phone_number}!"}
    except Exception as e:
        return {"error": str(e)}