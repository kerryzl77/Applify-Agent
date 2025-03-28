import json
import os
from pathlib import Path
import datetime

class DatabaseManager:
    def __init__(self, db_path='database/candidate_data.json'):
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create the database file if it doesn't exist."""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        if not os.path.exists(self.db_path):
            # Create default structure
            default_data = {
                "personal_info": {
                    "name": "",
                    "email": "",
                    "phone": "",
                    "linkedin": "",
                    "github": ""
                },
                "resume": {
                    "summary": "",
                    "experience": [],
                    "education": [],
                    "skills": []
                },
                "story_bank": [],
                "templates": {
                    "linkedin_messages": [],
                    "connection_emails": [],
                    "hiring_manager_emails": [],
                    "cover_letters": []
                },
                "generated_content": []
            }
            
            with open(self.db_path, 'w') as f:
                json.dump(default_data, f, indent=2)
    
    def get_candidate_data(self):
        """Retrieve all candidate data."""
        with open(self.db_path, 'r') as f:
            return json.load(f)
    
    def update_candidate_data(self, data):
        """Update candidate data."""
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_personal_info(self):
        """Get candidate's personal information."""
        data = self.get_candidate_data()
        return data.get("personal_info", {})
    
    def get_resume(self):
        """Get candidate's resume data."""
        data = self.get_candidate_data()
        return data.get("resume", {})
    
    def get_story_bank(self):
        """Get candidate's story bank entries."""
        data = self.get_candidate_data()
        return data.get("story_bank", [])
    
    def get_templates(self, template_type=None):
        """Get candidate's templates."""
        data = self.get_candidate_data()
        templates = data.get("templates", {})
        
        if template_type:
            return templates.get(template_type, [])
        return templates
    
    def save_generated_content(self, content_type, content, metadata):
        """Save generated content with metadata."""
        data = self.get_candidate_data()
        
        new_content = {
            "type": content_type,
            "content": content,
            "metadata": metadata,
            "created_at": str(datetime.datetime.now()),
            "status": "generated"
        }
        
        data["generated_content"].append(new_content)
        self.update_candidate_data(data)
        
        return len(data["generated_content"]) - 1  # Return the index of the new content 