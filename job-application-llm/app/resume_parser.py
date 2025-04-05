import os
import PyPDF2
from docx import Document
import magic
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

class ResumeParser:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(self.upload_dir, exist_ok=True)

    def extract_text(self, file_path):
        """Extract text from PDF or DOCX files."""
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)

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

    def parse_resume(self, text):
        """Parse resume text using GPT-4 to extract structured information."""
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
                "summary": "Professional summary or objective",
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
                },
                {
                    "title": "Story title based on a significant achievement or project",
                    "content": "Detailed story about the achievement, including context, actions taken, and results achieved"
                },
                {
                    "title": "Story title based on a significant achievement or project",
                    "content": "Detailed story about the achievement, including context, actions taken, and results achieved"
                }
            ]
        }

        For the story bank, extract 3 compelling stories from the resume that highlight:
        1. A significant achievement or project
        2. A challenge overcome
        3. A leadership or teamwork experience

        Each story should be detailed and include:
        - The context/situation
        - Specific actions taken
        - Measurable results or outcomes
        - Skills demonstrated
        """

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a precise resume parser. Extract only the requested information and format it as a valid JSON object. For stories, focus on concrete achievements with measurable results."},
                {"role": "user", "content": f"{prompt}\n\nResume Text:\n{text}"}
            ],
            temperature=0.1
        )

        try:
            parsed_data = json.loads(response.choices[0].message.content)
            return parsed_data
        except json.JSONDecodeError:
            raise ValueError("Failed to parse resume data")

    def save_uploaded_file(self, file):
        """Save uploaded file and return its path."""
        if not file:
            raise ValueError("No file uploaded")
        
        filename = os.path.join(self.upload_dir, file.filename)
        file.save(filename)
        return filename 