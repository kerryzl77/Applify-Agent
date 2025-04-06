import os
from rq import get_current_job
from app.resume_parser import parse_resume
from app.llm_generator import generate_cover_letter
from app.output_formatter import format_output
import json

def process_resume_task(resume_path, job_description):
    """
    Background task to process resume and generate cover letter
    """
    try:
        # Get current job ID
        job = get_current_job()
        
        # Parse resume
        resume_data = parse_resume(resume_path)
        
        # Generate cover letter
        cover_letter = generate_cover_letter(resume_data, job_description)
        
        # Format output
        formatted_output = format_output(resume_data, cover_letter)
        
        # Clean up uploaded file
        if os.path.exists(resume_path):
            os.remove(resume_path)
            
        return {
            'status': 'completed',
            'result': formatted_output
        }
        
    except Exception as e:
        # Clean up uploaded file in case of error
        if os.path.exists(resume_path):
            os.remove(resume_path)
            
        return {
            'status': 'failed',
            'error': str(e)
        } 