import os
import PyPDF2
from docx import Document
import magic
from openai import OpenAI
import json
from dotenv import load_dotenv
import tempfile
import shutil
import time
from werkzeug.utils import secure_filename

load_dotenv()

class ResumeParser:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Use tempfile for Heroku compatibility
        self.temp_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.temp_dir, 'uploads')
        os.makedirs(self.upload_dir, exist_ok=True)

    def __del__(self):
        # Clean up temporary directory
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp directory: {e}")

    def extract_text(self, file_path, timeout=120):
        """Extract text from PDF or DOCX files with timeout handling."""
        start_time = time.time()
        
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)

        if time.time() - start_time > timeout:
            raise TimeoutError("Text extraction timed out")

        if file_type == 'application/pdf':
            return self._extract_text_from_pdf(file_path)
        elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return self._extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_text_from_pdf(self, file_path):
        """Extract text from PDF file."""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _extract_text_from_docx(self, file_path):
        """Extract text from DOCX file."""
        doc = Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])

    def parse_resume(self, text, timeout=120):
        """Parse resume text using GPT-4 with timeout handling."""
        start_time = time.time()
        
        prompt = """Extract the following information from this resume and return it as a JSON object:
        {
            "personal_info": {
                "name": "Full name",
                "email": "Email address",
                "phone": "Phone number",
                "linkedin": "LinkedIn URL if available",
                "github": "GitHub URL if available"
            },
            "resume": {
                "summary": "Professional summary or objective if not provided in the resume, generate one based on the resume content",
                "experience": [
                    {
                        "title": "Job title",
                        "company": "Company name",
                        "location": "Location",
                        "start_date": "Start date",
                        "end_date": "End date or 'Present'",
                        "description": "Job description"
                    }
                ],
                "education": [
                    {
                        "degree": "Degree name",
                        "institution": "Institution name",
                        "location": "Location",
                        "graduation_date": "Graduation date"
                    }
                ],
                "skills": ["List of skills"]
            },
            "story_bank": [
                {
                    "title": "Story title based on a significant achievement or project",
                    "content": "Detailed story about the achievement, including context, actions taken, and results achieved"
                }
            ]
        }"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a precise resume parser. Extract only the requested information and format it as a valid JSON object."},
                    {"role": "user", "content": f"{prompt}\n\nResume Text:\n{text}"}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            if time.time() - start_time > timeout:
                raise TimeoutError("Resume parsing timed out")

            parsed_data = json.loads(response.choices[0].message.content)
            return parsed_data

        except json.JSONDecodeError:
            raise ValueError("Failed to parse resume data")
        except Exception as e:
            raise Exception(f"Error parsing resume: {str(e)}")

    def save_uploaded_file(self, file):
        """Save uploaded file and return its path."""
        if not file:
            raise ValueError("No file uploaded")
        
        # Generate a unique filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(self.upload_dir, filename)
        
        # Save the file
        file.save(file_path)
        return file_path 