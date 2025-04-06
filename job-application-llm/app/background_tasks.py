import threading
import time
import json
from app.resume_parser import ResumeParser
from database.db_manager import DatabaseManager

class BackgroundProcessor:
    def __init__(self):
        self.resume_parser = ResumeParser()
        self.db_manager = DatabaseManager()
        self.processing_queue = {}
        
    def process_resume(self, file_path, user_id):
        """Process resume in background and update database when complete."""
        try:
            print(f"Starting resume processing for user {user_id}")
            
            # Extract text from the file with longer timeout
            text = self.resume_parser.extract_text(file_path, timeout=120)
            print(f"Text extracted successfully for user {user_id}")
            
            # Parse the resume with longer timeout
            parsed_data = self.resume_parser.parse_resume(text, timeout=120)
            print(f"Resume parsed successfully for user {user_id}")
            print(f"Parsed data: {json.dumps(parsed_data, indent=2)}")
            
            # Update candidate data in database
            print(f"Attempting to update database for user {user_id}")
            self.db_manager.update_candidate_data(parsed_data, user_id)
            print(f"Database update completed for user {user_id}")
            
            # Mark processing as complete
            self.processing_queue[user_id] = {
                'status': 'complete',
                'data': parsed_data
            }
            print(f"Processing marked as complete for user {user_id}")
            
        except Exception as e:
            print(f"Error processing resume for user {user_id}: {str(e)}")
            self.processing_queue[user_id] = {
                'status': 'error',
                'error': str(e)
            }
            
    def start_processing(self, file_path, user_id):
        """Start background processing of resume."""
        self.processing_queue[user_id] = {'status': 'processing'}
        thread = threading.Thread(
            target=self.process_resume,
            args=(file_path, user_id)
        )
        thread.daemon = True
        thread.start()
        
    def get_status(self, user_id):
        """Get processing status for a user."""
        return self.processing_queue.get(user_id, {'status': 'not_found'})

# Create a global instance
background_processor = BackgroundProcessor() 