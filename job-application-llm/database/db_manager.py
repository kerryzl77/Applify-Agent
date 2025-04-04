import json
import os
from pathlib import Path
import datetime
import hashlib
import uuid
import sqlite3

class DatabaseManager:
    def __init__(self, db_path='database/candidate_data.json', sqlite_path='database/users.db'):
        self.db_path = db_path
        self.sqlite_path = sqlite_path
        self._ensure_db_exists()
        self._ensure_sqlite_db_exists()
    
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
                    "connection_emails": {
                        "title": "",
                        "template": ""
                    },
                    "cover_letters": {
                        "title": "",
                        "template": ""
                    },
                    "hiring_manager_emails": {
                        "title": "",
                        "template": ""
                    },
                    "linkedin_messages": {
                        "title": "",
                        "template": ""
                    }
                },
                "generated_content": []
            }
            
            with open(self.db_path, 'w') as f:
                json.dump(default_data, f, indent=2)
    
    def _ensure_sqlite_db_exists(self):
        """Create the SQLite database if it doesn't exist."""
        db_dir = os.path.dirname(self.sqlite_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        if not os.path.exists(self.sqlite_path):
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            ''')
            
            # Create user_profiles table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            conn.commit()
            conn.close()
    
    def register_user(self, email, password):
        """Register a new user."""
        # Check if user already exists
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return False, "User with this email already exists"
        
        # Create new user
        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        created_at = str(datetime.datetime.now())
        
        cursor.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email, password_hash, created_at)
        )
        
        # Create default profile for the user
        default_profile = {
            "personal_info": {
                "name": "",
                "email": email,
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
                "linkedin_messages": {
                    "title": "",
                    "template": ""
                },
                "connection_emails": {
                    "title": "",
                    "template": ""
                },
                "hiring_manager_emails": {
                    "title": "",
                    "template": ""
                },
                "cover_letters": {
                    "title": "",
                    "template": ""
                }
            },
            "generated_content": []
        }
        
        cursor.execute(
            "INSERT INTO user_profiles (user_id, profile_data) VALUES (?, ?)",
            (user_id, json.dumps(default_profile))
        )
        
        conn.commit()
        conn.close()
        
        return True, user_id
    
    def verify_user(self, email, password):
        """Verify user credentials and return user ID if valid."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute(
            "SELECT id FROM users WHERE email = ? AND password_hash = ?",
            (email, password_hash)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return True, result[0]
        else:
            return False, "Invalid email or password"
    
    def get_user_by_id(self, user_id):
        """Get user information by ID."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, email, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return {
                "id": user[0],
                "email": user[1],
                "created_at": user[2]
            }
        else:
            return None
    
    def get_candidate_data(self, user_id=None):
        """Retrieve candidate data for a specific user or the default data."""
        if user_id:
            # Get user-specific profile
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT profile_data FROM user_profiles WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result:
                profile_data = json.loads(result[0])
                
                # Migrate old template structure to new format if needed
                if 'templates' in profile_data:
                    for template_type in ['linkedin_messages', 'connection_emails', 'hiring_manager_emails', 'cover_letters']:
                        if template_type in profile_data['templates'] and isinstance(profile_data['templates'][template_type], list):
                            # Convert array to object format
                            if len(profile_data['templates'][template_type]) > 0:
                                profile_data['templates'][template_type] = profile_data['templates'][template_type][0]
                            else:
                                profile_data['templates'][template_type] = {
                                    "title": "",
                                    "template": ""
                                }
                
                conn.close()
                return profile_data
            
            conn.close()
        
        # Return default data if no user-specific data exists
        with open(self.db_path, 'r') as f:
            return json.load(f)
    
    def update_candidate_data(self, data, user_id=None):
        """Update candidate data for a specific user or the default data."""
        if user_id:
            # Update user-specific profile
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE user_profiles SET profile_data = ? WHERE user_id = ?",
                (json.dumps(data), user_id)
            )
            
            conn.commit()
            conn.close()
        else:
            # Update default data
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
    
    def get_personal_info(self, user_id=None):
        """Get candidate's personal information."""
        data = self.get_candidate_data(user_id)
        return data.get("personal_info", {})
    
    def get_resume(self, user_id=None):
        """Get candidate's resume data."""
        data = self.get_candidate_data(user_id)
        return data.get("resume", {})
    
    def get_story_bank(self, user_id=None):
        """Get candidate's story bank entries."""
        data = self.get_candidate_data(user_id)
        return data.get("story_bank", [])
    
    def get_templates(self, template_type=None, user_id=None):
        """Get candidate's templates."""
        data = self.get_candidate_data(user_id)
        templates = data.get("templates", {})
        
        if template_type:
            return templates.get(template_type, {"title": "", "template": ""})
        return templates
    
    def save_generated_content(self, content_type, content, metadata, user_id=None):
        """Save generated content with metadata."""
        data = self.get_candidate_data(user_id)
        
        new_content = {
            "type": content_type,
            "content": content,
            "metadata": metadata,
            "created_at": str(datetime.datetime.now()),
            "status": "generated"
        }
        
        data["generated_content"].append(new_content)
        self.update_candidate_data(data, user_id)
        
        return len(data["generated_content"]) - 1  # Return the index of the new content 