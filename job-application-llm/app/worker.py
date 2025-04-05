import os
import redis
from rq import Worker, Queue, Connection
from app.resume_parser import ResumeParser
from app.database.db_manager import DatabaseManager

# Initialize components
resume_parser = ResumeParser()
db_manager = DatabaseManager()

def process_resume(file_path, user_id):
    """Process resume in background job."""
    try:
        # Extract text from the file
        text = resume_parser.extract_text(file_path)
        
        # Parse the resume
        parsed_data = resume_parser.parse_resume(text)
        
        # Update candidate data in database
        db_manager.update_candidate_data(user_id, parsed_data)
        
        return {
            'status': 'success',
            'data': parsed_data
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def start_worker():
    """Start the RQ worker."""
    listen = ['default']
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    conn = redis.from_url(redis_url)
    
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work() 