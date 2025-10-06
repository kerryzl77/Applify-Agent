import json
import os
from pathlib import Path
import datetime
import hashlib
import uuid
import psycopg2
from psycopg2.extras import Json
from psycopg2 import pool

class DatabaseManager:
    _instance = None
    _connection_pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self._connection_pool = pool.SimpleConnectionPool(
                1,  # min connections
                10,  # max connections
                os.environ.get('DATABASE_URL')
            )
            self._ensure_tables_exist()
        except Exception as e:
            print(f"Error initializing connection pool: {str(e)}")
            raise

    def _get_connection(self):
        """Get a connection from the pool."""
        try:
            return self._connection_pool.getconn()
        except Exception as e:
            print(f"Error getting connection from pool: {str(e)}")
            raise

    def _return_connection(self, conn):
        """Return a connection to the pool."""
        try:
            self._connection_pool.putconn(conn)
        except Exception as e:
            print(f"Error returning connection to pool: {str(e)}")

    def _ensure_tables_exist(self):
        """Create necessary tables if they don't exist."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Create users table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create user_profiles table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id TEXT PRIMARY KEY REFERENCES users(id),
                        profile_data JSONB NOT NULL
                    )
                ''')
                
                # Create generated_content table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS generated_content (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT REFERENCES users(id),
                        content_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                ''')

                # Create gmail_auth table for storing Gmail MCP credentials
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS gmail_auth (
                        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        token_expiry TIMESTAMP NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error creating tables: {str(e)}")
            raise
        finally:
            if conn:
                self._return_connection(conn)

    def register_user(self, email, password):
        """Register a new user."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Check if user already exists
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    return False, "User with this email already exists"
                
                # Create new user
                user_id = str(uuid.uuid4())
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                created_at = datetime.datetime.now()
                
                cur.execute(
                    "INSERT INTO users (id, email, password_hash, created_at) VALUES (%s, %s, %s, %s)",
                    (user_id, email, password_hash, created_at)
                )
                
                # Create default profile
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
                        "linkedin_messages": {"title": "", "template": ""},
                        "connection_emails": {"title": "", "template": ""},
                        "hiring_manager_emails": {"title": "", "template": ""},
                        "cover_letters": {"title": "", "template": ""}
                    }
                }
                
                cur.execute(
                    "INSERT INTO user_profiles (user_id, profile_data) VALUES (%s, %s)",
                    (user_id, Json(default_profile))
                )
                
                conn.commit()
                return True, user_id
                
        except Exception as e:
            if conn:
                conn.rollback()
            return False, str(e)
        finally:
            if conn:
                self._return_connection(conn)

    def verify_user(self, email, password):
        """Verify user credentials."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                cur.execute(
                    "SELECT id FROM users WHERE email = %s AND password_hash = %s",
                    (email, password_hash)
                )
                result = cur.fetchone()
                if result:
                    return True, result[0]
                return False, "Invalid email or password"
        except Exception as e:
            return False, str(e)
        finally:
            if conn:
                self._return_connection(conn)

    def get_candidate_data(self, user_id):
        """Get candidate data for a specific user."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT profile_data FROM user_profiles WHERE user_id = %s",
                    (user_id,)
                )
                result = cur.fetchone()
                if result:
                    return result[0]
                return None
        except Exception as e:
            print(f"Error getting candidate data: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def update_candidate_data(self, data, user_id):
        """Update candidate data for a specific user."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE user_profiles SET profile_data = %s WHERE user_id = %s",
                    (Json(data), user_id)
                )
                conn.commit()
                return True
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error updating candidate data: {str(e)}")
            return False
        finally:
            if conn:
                self._return_connection(conn)

    def save_generated_content(self, content_type, content, metadata, user_id):
        """Save generated content."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO generated_content 
                    (user_id, content_type, content, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, content_type, content, Json(metadata), datetime.datetime.now())
                )
                content_id = cur.fetchone()[0]
                conn.commit()
                return content_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error saving generated content: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    # ------------------------------------------------------------------
    # Gmail MCP credential helpers
    # ------------------------------------------------------------------
    def save_gmail_auth(self, user_id, access_token, refresh_token, expiry):
        conn = None
        now = datetime.datetime.utcnow()
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO gmail_auth (user_id, access_token, refresh_token, token_expiry, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token,
                        token_expiry = EXCLUDED.token_expiry,
                        updated_at = EXCLUDED.updated_at
                    ''',
                    (user_id, access_token, refresh_token, expiry, now, now)
                )
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error saving gmail auth: {str(e)}")
            raise
        finally:
            if conn:
                self._return_connection(conn)

    def get_gmail_auth(self, user_id):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT access_token, refresh_token, token_expiry FROM gmail_auth WHERE user_id = %s",
                    (user_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                access_token, refresh_token, token_expiry = row
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_expiry": token_expiry.isoformat() if hasattr(token_expiry, 'isoformat') else token_expiry,
                }
        except Exception as e:
            print(f"Error retrieving gmail auth: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def delete_gmail_auth(self, user_id):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM gmail_auth WHERE user_id = %s", (user_id,))
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error deleting gmail auth: {str(e)}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_user_by_id(self, user_id):
        """Get user information by ID."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT id, email, created_at FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()
                
                if user:
                    return {
                        "id": user[0],
                        "email": user[1],
                        "created_at": user[2]
                    }
                else:
                    return None
        except Exception as e:
            print(f"Error getting user by ID: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)
    
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

    def get_generated_content_history(self, user_id, limit=5):
        """Get the user's generated content history."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, content_type, content, metadata, created_at 
                    FROM generated_content 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (user_id, limit))
                
                results = cur.fetchall()
                return [{
                    'id': row[0],
                    'type': row[1],
                    'content': row[2],
                    'metadata': row[3],
                    'created_at': row[4].isoformat()
                } for row in results]
        except Exception as e:
            print(f"Error getting generated content history: {str(e)}")
            return []
        finally:
            if conn:
                self._return_connection(conn) 