import os
import logging
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import datetime
import platform
import tempfile
import shutil
import time
from app.fast_pdf_generator import FastPDFGenerator

class OutputFormatter:
    def __init__(self):
        # Use a shared temp directory so downloads work across worker processes
        base_temp_dir = os.path.join(tempfile.gettempdir(), 'applify_output')
        self.output_dir = os.path.join(base_temp_dir, 'files')
        os.makedirs(self.output_dir, exist_ok=True)
            
        # Check if running in Docker or Heroku
        self.in_docker = os.path.exists('/.dockerenv')
        self.in_heroku = bool(os.environ.get('DYNO'))
        
        # Initialize fast PDF generator
        self.pdf_generator = FastPDFGenerator(output_dir=self.output_dir)
        
        # Clean up old files periodically
        self._cleanup_old_files()
    
    def _cleanup_old_files(self):
        """Clean up files older than 1 hour."""
        try:
            current_time = datetime.datetime.now()
            for filename in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (current_time - file_time).total_seconds() > 900:  # 15 minutes
                        os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning up old files: {str(e)}")
    
    def format_text(self, content, content_type):
        """Return formatted plain text."""
        if content_type == 'linkedin_message':
            # Ensure LinkedIn message is under 200 characters
            if len(content) > 200:
                content = content[:197] + '...'
        
        elif content_type in ['connection_email', 'hiring_manager_email']:
            # Ensure emails are reasonable length (roughly 200 words)
            words = content.split()
            if len(words) > 220:  # Give a little buffer
                content = ' '.join(words[:200]) + '...'
        
        elif content_type == 'cover_letter':
            # Ensure cover letter is reasonable length (roughly 350 words)
            words = content.split()
            if len(words) > 370:  # Give a little buffer
                content = ' '.join(words[:350]) + '...'
        
        return content
    
    def create_docx(self, content, job_data, candidate_data, content_type):
        """Create a DOCX file with the formatted content."""
        try:
            doc = Document()
            
            # Set margins
            sections = doc.sections
            for section in sections:
                section.top_margin = Inches(1)
                section.bottom_margin = Inches(1)
                section.left_margin = Inches(1)
                section.right_margin = Inches(1)
            
            if content_type == 'cover_letter':
                self._format_cover_letter_docx(doc, content, job_data, candidate_data)
            else:
                # For emails, use a simpler format
                self._format_email_docx(doc, content, job_data, candidate_data, content_type)
            
            # Generate filename with user ID to prevent conflicts
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            company_name = job_data['company_name'].replace(' ', '_')
            filename = f"{content_type}_{company_name}_{timestamp}.docx"
            filepath = os.path.join(self.output_dir, filename)
            
            # Save the document
            doc.save(filepath)
            
            # Ensure file is written to disk and verify it exists
            max_retries = 3
            for i in range(max_retries):
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    logging.info(f"Document verified on disk: {filename} ({os.path.getsize(filepath)} bytes)")
                    break
                time.sleep(0.1)  # Wait 100ms between checks
            else:
                logging.error(f"Document not found after saving: {filepath}")
                return None
            
            # Return both the filename and the full path
            return {
                'filename': filename,
                'filepath': filepath
            }
            
        except Exception as e:
            logging.error(f"Error creating document: {str(e)}", exc_info=True)
            return None
    
    def convert_to_pdf(self, docx_info):
        """
        FAST PDF generation - bypasses slow LibreOffice conversion.
        
        Performance: ~50-100ms (vs 30-60s LibreOffice)
        """
        print("⚡ Using fast PDF generation (bypassing LibreOffice)")
        
        try:
            from docx import Document
            import os
            
            # Read the DOCX file to extract content
            if not os.path.exists(docx_info['filepath']):
                print(f"❌ DOCX file not found: {docx_info['filepath']}")
                return None
            
            doc = Document(docx_info['filepath'])
            
            # Extract text content from DOCX
            content_paragraphs = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content_paragraphs.append(paragraph.text.strip())
            
            full_content = '\n\n'.join(content_paragraphs)
            
            # Determine content type from filename
            filename = docx_info['filename'].lower()
            if 'cover_letter' in filename:
                content_type = 'cover_letter'
            elif 'email' in filename:
                content_type = 'hiring_manager_email'
            else:
                content_type = 'cover_letter'  # Default
            
            # Create fake job_data and candidate_data from filename
            job_data = {
                'company_name': 'Company',
                'job_title': 'Position',
                'location': 'Location'
            }
            
            candidate_data = {
                'personal_info': {
                    'name': 'Candidate Name',
                    'email': 'candidate@email.com',
                    'phone': '(555) 123-4567',
                    'location': 'City, State'
                }
            }
            
            # Generate PDF directly using fast generator
            pdf_result = self.pdf_generator.generate_cover_letter_pdf(
                full_content, job_data, candidate_data
            )
            
            if pdf_result:
                print(f"✅ Successfully converted DOCX to PDF: {pdf_result['filename']}")
                return pdf_result
            else:
                print("❌ PDF generation failed")
                return None
                
        except Exception as e:
            print(f"❌ Error converting DOCX to PDF: {str(e)}")
            return None
    
    def create_pdf_direct(self, content, job_data, candidate_data, content_type):
        """
        Create PDF directly without DOCX intermediate step.
        
        ULTRA-FAST: ~30-100ms generation time.
        """
        try:
            if content_type == 'cover_letter':
                return self.pdf_generator.generate_cover_letter_pdf(
                    content, job_data, candidate_data
                )
            elif content_type in ['connection_email', 'hiring_manager_email', 'linkedin_message']:
                # For emails, use cover letter format but with email-specific styling
                return self.pdf_generator.generate_cover_letter_pdf(
                    content, job_data, candidate_data
                )
            else:
                print(f"PDF generation not supported for content type: {content_type}")
                return None
                
        except Exception as e:
            print(f"Error creating PDF directly: {str(e)}")
            return None
    
    def create_resume_pdf_direct(self, resume_data, candidate_data, job_title="Position"):
        """
        Create optimized resume PDF directly - ULTRA-FAST.
        
        Performance: ~50-100ms for complete resume PDF.
        """
        try:
            return self.pdf_generator.generate_resume_pdf(
                resume_data, candidate_data, job_title
            )
        except Exception as e:
            print(f"Error creating resume PDF: {str(e)}")
            return None
    
    def _format_cover_letter_docx(self, doc, content, job_data, candidate_data):
        """Format a cover letter in DOCX."""
        try:
            personal_info = candidate_data.get('personal_info', {})
            header_parts = []
            name = personal_info.get('name')
            email = personal_info.get('email')
            phone = personal_info.get('phone')
            location = personal_info.get('location')

            # Add name line (bold)
            if name:
                name_para = doc.add_paragraph()
                name_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                name_run = name_para.add_run(name)
                name_run.bold = True

            if email:
                header_parts.append(email)
            if phone:
                header_parts.append(phone)
            if location:
                header_parts.append(location)

            if header_parts:
                contact_para = doc.add_paragraph()
                contact_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                contact_para.add_run(' - '.join(header_parts))

            # Add space before LLM content
            doc.add_paragraph()
            
            # Split content into paragraphs and add them
            paragraphs = content.split('\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p.add_run(paragraph.strip())
            
            # # Add signature space
            # doc.add_paragraph()  # Add space
            # signature = doc.add_paragraph()
            # signature.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
        except Exception as e:
            print(f"Error formatting cover letter: {str(e)}")
            raise
    
    def _format_email_docx(self, doc, content, job_data, candidate_data, content_type):
        """Format an email in DOCX."""
        # Add subject line for emails
        if content_type == 'connection_email':
            subject = f"Connection Request - {candidate_data['personal_info']['name']}"
        elif content_type == 'hiring_manager_email':
            subject = f"Application for {job_data['job_title']} Position - {candidate_data['personal_info']['name']}"
        
        subject_line = doc.add_paragraph()
        subject_line.alignment = WD_ALIGN_PARAGRAPH.LEFT
        subject_line.add_run('Subject: ').bold = True
        subject_line.add_run(subject)
        
        # Add content
        doc.add_paragraph()  # Add space
        for paragraph in content.split('\n'):
            if paragraph.strip():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.add_run(paragraph) 