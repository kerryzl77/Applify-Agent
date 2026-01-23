import os
import re
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
        return self.parse_resume_enhanced(text, timeout)
    
    def parse_resume_enhanced(self, text, timeout=120):
        """Enhanced resume parsing with better prompts and error handling."""
        start_time = time.time()
        
        # Clean and preprocess text
        cleaned_text = self._preprocess_text(text)
        
        system_prompt = """You are an expert resume parser with deep understanding of professional documents. 
        Extract information accurately and generate compelling professional summaries when needed.
        Always return valid JSON with all required fields, using empty strings or arrays if information is not available."""
        
        user_prompt = f"""Parse this resume and extract the following information in JSON format:

        {{
            "personal_info": {{
                "name": "Full name (required)",
                "email": "Email address",
                "phone": "Phone number with proper formatting",
                "linkedin": "Full LinkedIn URL if available",
                "github": "Full GitHub URL if available",
                "location": "City, State/Country if available"
            }},
            "resume": {{
                "summary": "Generate a compelling 2-3 sentence professional summary based on the resume content if not explicitly provided",
                "experience": [
                    {{
                        "title": "Job title",
                        "company": "Company name",
                        "location": "City, State/Country",
                        "start_date": "Start date (MM/YYYY format)",
                        "end_date": "End date (MM/YYYY format) or 'Present'",
                        "description": "Concise description highlighting key achievements and responsibilities"
                    }}
                ],
                "education": [
                    {{
                        "degree": "Degree type and field of study",
                        "institution": "Institution name",
                        "location": "City, State/Country",
                        "graduation_date": "Graduation date (MM/YYYY format) or expected date"
                    }}
                ],
                "skills": ["Technical skills, tools, programming languages, etc."]
            }},
            "story_bank": [
                {{
                    "title": "Achievement or project title",
                    "content": "STAR format story: Situation, Task, Action, Result. Focus on quantifiable achievements and impact."
                }}
            ]
        }}

        Resume Content:
        {cleaned_text}

        Important:
        - Extract ALL contact information available
        - Generate professional summary if none exists
        - Include quantifiable achievements in experience descriptions
        - Create 3-5 compelling STAR format stories from work experience for the story bank
        - Each story should highlight a specific achievement with measurable results
        - Stories should cover different aspects (leadership, problem-solving, technical skills, teamwork)
        - Ensure all dates are properly formatted
        - Return valid JSON only"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5.2",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_completion_tokens=4000
            )

            if time.time() - start_time > timeout:
                raise TimeoutError("Resume parsing timed out")

            response_content = response.choices[0].message.content.strip()
            
            # Clean JSON response
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_content = response_content[json_start:json_end]
            parsed_data = json.loads(json_content)
            
            # Validate and clean the parsed data
            return self._validate_and_clean_parsed_data(parsed_data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse resume data: Invalid JSON - {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing resume: {str(e)}")
    
    def _preprocess_text(self, text):
        """Clean and preprocess resume text for better parsing."""
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize
        cleaned = ' '.join(text.split())
        
        # Remove common OCR artifacts
        cleaned = cleaned.replace('•', '-').replace('◦', '-')
        
        return cleaned[:8000]  # Limit to prevent token overflow
    
    def _validate_and_clean_parsed_data(self, data):
        """Validate and clean the parsed resume data."""
        # Ensure required structure
        cleaned_data = {
            "personal_info": {
                "name": data.get("personal_info", {}).get("name", ""),
                "email": data.get("personal_info", {}).get("email", ""),
                "phone": data.get("personal_info", {}).get("phone", ""),
                "linkedin": data.get("personal_info", {}).get("linkedin", ""),
                "github": data.get("personal_info", {}).get("github", "")
            },
            "resume": {
                "summary": data.get("resume", {}).get("summary", ""),
                "experience": data.get("resume", {}).get("experience", []),
                "education": data.get("resume", {}).get("education", []),
                "skills": data.get("resume", {}).get("skills", [])
            },
            "story_bank": data.get("story_bank", [])
        }

        # Normalize skills to a flat technical skills list
        skills = cleaned_data["resume"].get("skills", [])
        skills_list = []

        if isinstance(skills, dict):
            for category in skills.values():
                if isinstance(category, list):
                    skills_list.extend(category)
                elif isinstance(category, str):
                    skills_list.append(category)
        elif isinstance(skills, list):
            skills_list = skills
        elif isinstance(skills, str):
            skills_list = [skills]

        cleaned_data["resume"]["skills"] = [skill.strip() for skill in skills_list if skill and skill.strip()]
        
        # Preserve nested bullet points/details if provided in original text
        experiences = cleaned_data["resume"].get("experience", [])
        for experience in experiences:
            if not isinstance(experience, dict):
                continue

            # Promote list descriptions to bullet_points while preserving full text
            description = experience.get("description")
            if isinstance(description, list):
                experience["bullet_points"] = description
                experience["description"] = " ".join(description)
                continue

            if description:
                # Split bullet-like sentences (•, -, or numbered) to retain detail
                raw_lines = re.split(r"(?:\n|\s*•\s+|\s*-\s+|\s*\d+[\.)]\s+)", description)
                bullet_lines = [line.strip() for line in raw_lines if len(line.strip()) > 0]
                if bullet_lines:
                    experience.setdefault("bullet_points", bullet_lines)

        # Clean URLs
        if cleaned_data["personal_info"]["linkedin"] and not cleaned_data["personal_info"]["linkedin"].startswith("http"):
            cleaned_data["personal_info"]["linkedin"] = "https://linkedin.com/in/" + cleaned_data["personal_info"]["linkedin"]
        
        if cleaned_data["personal_info"]["github"] and not cleaned_data["personal_info"]["github"].startswith("http"):
            cleaned_data["personal_info"]["github"] = "https://github.com/" + cleaned_data["personal_info"]["github"]
        
        return cleaned_data

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