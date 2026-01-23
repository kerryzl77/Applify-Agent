import json
import os
from pathlib import Path
import datetime
import hashlib
import uuid
import psycopg2
from psycopg2.extras import Json
from psycopg2 import pool
import logging

logger = logging.getLogger(__name__)

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
            self._run_migrations()
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

                # Create gmail_auth table for storing Gmail OAuth credentials
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS gmail_auth (
                        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        token_expiry TIMESTAMP NOT NULL,
                        scope TEXT DEFAULT '' NOT NULL,
                        email TEXT DEFAULT '' NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                cur.execute("""
                    ALTER TABLE gmail_auth
                    ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT ''
                """)
                cur.execute("""
                    ALTER TABLE gmail_auth
                    ADD COLUMN IF NOT EXISTS email TEXT DEFAULT ''
                """)
                
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error creating tables: {str(e)}")
            raise
        finally:
            if conn:
                self._return_connection(conn)

    def _run_migrations(self):
        """Run SQL migrations from database/migrations/ directory."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Create schema_migrations table if not exists
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ DEFAULT NOW()
                    )
                ''')
                conn.commit()

                # Get already applied migrations
                cur.execute("SELECT version FROM schema_migrations ORDER BY version")
                applied = set(row[0] for row in cur.fetchall())

                # Find migrations directory
                migrations_dir = Path(__file__).parent / "migrations"
                if not migrations_dir.exists():
                    logger.info("No migrations directory found, skipping migrations")
                    return

                # Get and sort migration files
                migration_files = sorted(migrations_dir.glob("*.sql"))

                for migration_file in migration_files:
                    version = migration_file.stem  # e.g., "001_jobs_tables"
                    if version in applied:
                        continue

                    logger.info(f"Applying migration: {version}")
                    sql_content = migration_file.read_text()

                    try:
                        cur.execute(sql_content)
                        cur.execute(
                            "INSERT INTO schema_migrations (version) VALUES (%s)",
                            (version,)
                        )
                        conn.commit()
                        logger.info(f"Successfully applied migration: {version}")
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Failed to apply migration {version}: {str(e)}")
                        raise

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error running migrations: {str(e)}")
            # Don't raise - allow app to start even if migrations fail
            # This prevents blocking existing functionality
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
    # Gmail OAuth credential helpers
    # ------------------------------------------------------------------
    def save_gmail_token(self, user_id, access_token, refresh_token, expiry, scope, email):
        conn = None
        now = datetime.datetime.utcnow()
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO gmail_auth (user_id, access_token, refresh_token, token_expiry, scope, email, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token,
                        token_expiry = EXCLUDED.token_expiry,
                        scope = EXCLUDED.scope,
                        email = EXCLUDED.email,
                        updated_at = EXCLUDED.updated_at
                    ''',
                    (user_id, access_token, refresh_token, expiry, scope, email, now, now)
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

    def get_gmail_token(self, user_id):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT access_token, refresh_token, token_expiry, scope, email FROM gmail_auth WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                access_token, refresh_token, token_expiry, scope, email = row
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_expiry": token_expiry.isoformat() if hasattr(token_expiry, 'isoformat') else token_expiry,
                    "scope": scope,
                    "email": email,
                }
        except Exception as e:
            print(f"Error retrieving gmail auth: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def delete_gmail_token(self, user_id):
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

    # ------------------------------------------------------------------
    # ATS Company Sources CRUD
    # ------------------------------------------------------------------
    def upsert_ats_company_source(self, company_name, ats_type, board_root_url, tags=None):
        """Upsert an ATS company source."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ats_company_sources (company_name, ats_type, board_root_url, tags)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (board_root_url)
                    DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        ats_type = EXCLUDED.ats_type,
                        tags = EXCLUDED.tags,
                        updated_at = NOW()
                    RETURNING id
                """, (company_name, ats_type, board_root_url, tags or []))
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error upserting ATS company source: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def get_ats_company_sources(self, ats_type=None, is_active=True):
        """Get ATS company sources with optional filtering."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = "SELECT id, company_name, ats_type, board_root_url, is_active, tags, last_success_at FROM ats_company_sources WHERE 1=1"
                params = []
                if ats_type:
                    query += " AND ats_type = %s"
                    params.append(ats_type)
                if is_active is not None:
                    query += " AND is_active = %s"
                    params.append(is_active)
                query += " ORDER BY company_name"
                cur.execute(query, params)
                results = cur.fetchall()
                return [{
                    'id': row[0],
                    'company_name': row[1],
                    'ats_type': row[2],
                    'board_root_url': row[3],
                    'is_active': row[4],
                    'tags': row[5],
                    'last_success_at': row[6].isoformat() if row[6] else None
                } for row in results]
        except Exception as e:
            logger.error(f"Error getting ATS company sources: {str(e)}")
            return []
        finally:
            if conn:
                self._return_connection(conn)

    def update_ats_source_last_success(self, source_id):
        """Update last_success_at for an ATS source."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE ats_company_sources SET last_success_at = NOW(), updated_at = NOW() WHERE id = %s",
                    (source_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating ATS source last success: {str(e)}")
            return False
        finally:
            if conn:
                self._return_connection(conn)

    # ------------------------------------------------------------------
    # Job Posts CRUD
    # ------------------------------------------------------------------
    def upsert_job_post(self, source_type, company_name, ats_type, title, url,
                        company_source_id=None, created_by_user_id=None,
                        external_job_id=None, location=None, team=None,
                        employment_type=None, hash_value=None, raw_json=None):
        """Upsert a job post by URL."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO job_posts (
                        source_type, company_source_id, created_by_user_id,
                        external_job_id, company_name, ats_type, title,
                        location, team, employment_type, url, hash, raw_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        location = EXCLUDED.location,
                        team = EXCLUDED.team,
                        employment_type = EXCLUDED.employment_type,
                        hash = EXCLUDED.hash,
                        raw_json = EXCLUDED.raw_json,
                        last_seen_at = NOW(),
                        updated_at = NOW()
                    RETURNING id
                """, (
                    source_type, company_source_id, created_by_user_id,
                    external_job_id, company_name, ats_type, title,
                    location, team, employment_type, url, hash_value,
                    Json(raw_json) if raw_json else None
                ))
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error upserting job post: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def get_job_posts_feed(self, user_id, ats_type=None, company=None, location=None,
                           query=None, page=1, page_size=20):
        """Get paginated job posts feed with optional filters."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Build query - show ATS jobs + user's own external jobs
                base_query = """
                    SELECT jp.id, jp.source_type, jp.company_name, jp.ats_type, jp.title,
                           jp.location, jp.team, jp.employment_type, jp.url, jp.last_seen_at,
                           usj.status as saved_status
                    FROM job_posts jp
                    LEFT JOIN user_saved_jobs usj ON jp.id = usj.job_post_id AND usj.user_id = %s
                    WHERE (jp.source_type = 'ats' OR jp.created_by_user_id = %s)
                """
                params = [user_id, user_id]

                if ats_type and ats_type != 'all':
                    base_query += " AND jp.ats_type = %s"
                    params.append(ats_type)
                if company:
                    base_query += " AND jp.company_name ILIKE %s"
                    params.append(f"%{company}%")
                if location:
                    base_query += " AND jp.location ILIKE %s"
                    params.append(f"%{location}%")
                if query:
                    base_query += " AND (jp.title ILIKE %s OR jp.company_name ILIKE %s)"
                    params.extend([f"%{query}%", f"%{query}%"])

                # Count total
                count_query = f"SELECT COUNT(*) FROM ({base_query}) as subq"
                cur.execute(count_query, params)
                total = cur.fetchone()[0]

                # Paginate
                base_query += " ORDER BY jp.last_seen_at DESC LIMIT %s OFFSET %s"
                params.extend([page_size, (page - 1) * page_size])
                cur.execute(base_query, params)
                results = cur.fetchall()

                jobs = [{
                    'id': row[0],
                    'source_type': row[1],
                    'company_name': row[2],
                    'ats_type': row[3],
                    'title': row[4],
                    'location': row[5],
                    'team': row[6],
                    'employment_type': row[7],
                    'url': row[8],
                    'last_seen_at': row[9].isoformat() if row[9] else None,
                    'saved_status': row[10]
                } for row in results]

                return {
                    'jobs': jobs,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size
                }
        except Exception as e:
            logger.error(f"Error getting job posts feed: {str(e)}")
            return {'jobs': [], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}
        finally:
            if conn:
                self._return_connection(conn)

    def get_job_post_by_id(self, job_id, user_id=None):
        """Get a single job post by ID."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT jp.id, jp.source_type, jp.company_source_id, jp.created_by_user_id,
                           jp.external_job_id, jp.company_name, jp.ats_type, jp.title,
                           jp.location, jp.team, jp.employment_type, jp.url,
                           jp.last_seen_at, jp.hash, jp.raw_json, jp.created_at,
                           usj.status as saved_status
                    FROM job_posts jp
                    LEFT JOIN user_saved_jobs usj ON jp.id = usj.job_post_id AND usj.user_id = %s
                    WHERE jp.id = %s
                """, (user_id, job_id))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    'id': row[0],
                    'source_type': row[1],
                    'company_source_id': row[2],
                    'created_by_user_id': row[3],
                    'external_job_id': row[4],
                    'company_name': row[5],
                    'ats_type': row[6],
                    'title': row[7],
                    'location': row[8],
                    'team': row[9],
                    'employment_type': row[10],
                    'url': row[11],
                    'last_seen_at': row[12].isoformat() if row[12] else None,
                    'hash': row[13],
                    'raw_json': row[14],
                    'created_at': row[15].isoformat() if row[15] else None,
                    'saved_status': row[16]
                }
        except Exception as e:
            logger.error(f"Error getting job post by ID: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def get_job_post_by_url(self, url):
        """Get a job post by URL."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM job_posts WHERE url = %s", (url,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting job post by URL: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    # ------------------------------------------------------------------
    # User Saved Jobs CRUD
    # ------------------------------------------------------------------
    def save_job(self, user_id, job_post_id, status='saved'):
        """Save or update a job for a user."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_saved_jobs (user_id, job_post_id, status)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, job_post_id)
                    DO UPDATE SET status = EXCLUDED.status, updated_at = NOW()
                    RETURNING id, status
                """, (user_id, job_post_id, status))
                result = cur.fetchone()
                conn.commit()
                return {'id': result[0], 'status': result[1]} if result else None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error saving job: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def get_user_saved_jobs(self, user_id, status=None):
        """Get saved jobs for a user."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = """
                    SELECT usj.id, usj.job_post_id, usj.status, usj.created_at,
                           jp.title, jp.company_name, jp.location, jp.url
                    FROM user_saved_jobs usj
                    JOIN job_posts jp ON usj.job_post_id = jp.id
                    WHERE usj.user_id = %s
                """
                params = [user_id]
                if status:
                    query += " AND usj.status = %s"
                    params.append(status)
                query += " ORDER BY usj.updated_at DESC"
                cur.execute(query, params)
                results = cur.fetchall()
                return [{
                    'id': row[0],
                    'job_post_id': row[1],
                    'status': row[2],
                    'saved_at': row[3].isoformat() if row[3] else None,
                    'title': row[4],
                    'company_name': row[5],
                    'location': row[6],
                    'url': row[7]
                } for row in results]
        except Exception as e:
            logger.error(f"Error getting user saved jobs: {str(e)}")
            return []
        finally:
            if conn:
                self._return_connection(conn)

    # ------------------------------------------------------------------
    # Job Campaigns CRUD
    # ------------------------------------------------------------------
    def create_job_campaign(self, user_id, job_post_id, initial_state=None):
        """Create a job campaign."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO job_campaigns (user_id, job_post_id, state)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (user_id, job_post_id, Json(initial_state or {})))
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error creating job campaign: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def get_job_campaign(self, campaign_id, user_id=None):
        """Get a job campaign by ID."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = "SELECT id, user_id, job_post_id, state, created_at FROM job_campaigns WHERE id = %s"
                params = [campaign_id]
                if user_id:
                    query += " AND user_id = %s"
                    params.append(user_id)
                cur.execute(query, params)
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'job_post_id': row[2],
                    'state': row[3],
                    'created_at': row[4].isoformat() if row[4] else None
                }
        except Exception as e:
            logger.error(f"Error getting job campaign: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def get_job_campaign_with_job(self, campaign_id, user_id=None):
        """Get a job campaign with associated job post data."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = """
                    SELECT jc.id, jc.user_id, jc.job_post_id, jc.state, jc.created_at, jc.updated_at,
                           jp.title, jp.company_name, jp.location, jp.team, jp.employment_type, jp.url, jp.ats_type
                    FROM job_campaigns jc
                    JOIN job_posts jp ON jc.job_post_id = jp.id
                    WHERE jc.id = %s
                """
                params = [campaign_id]
                if user_id:
                    query += " AND jc.user_id = %s"
                    params.append(user_id)
                cur.execute(query, params)
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'job_post_id': row[2],
                    'state': row[3] or {},
                    'created_at': row[4].isoformat() if row[4] else None,
                    'updated_at': row[5].isoformat() if row[5] else None,
                    'job': {
                        'title': row[6],
                        'company_name': row[7],
                        'location': row[8],
                        'team': row[9],
                        'employment_type': row[10],
                        'url': row[11],
                        'ats_type': row[12],
                    }
                }
        except Exception as e:
            logger.error(f"Error getting job campaign with job: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def update_job_campaign_state(self, campaign_id, user_id, patch, merge=True):
        """Update campaign state with optional merge. Uses row-level locking for safety."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Lock the row for update
                cur.execute(
                    "SELECT state FROM job_campaigns WHERE id = %s AND user_id = %s FOR UPDATE",
                    (campaign_id, user_id)
                )
                row = cur.fetchone()
                if not row:
                    return False
                
                current_state = row[0] or {}
                
                if merge:
                    # Deep merge patch into current state
                    new_state = self._deep_merge(current_state, patch)
                else:
                    new_state = patch
                
                cur.execute(
                    "UPDATE job_campaigns SET state = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
                    (Json(new_state), campaign_id, user_id)
                )
                conn.commit()
                return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating job campaign state: {str(e)}")
            return False
        finally:
            if conn:
                self._return_connection(conn)

    def _deep_merge(self, base, patch):
        """Deep merge patch dict into base dict."""
        result = base.copy()
        for key, value in patch.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def append_job_campaign_trace(self, campaign_id, user_id, event):
        """Append an event to the campaign trace array. Thread-safe via row lock."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Lock and get current state
                cur.execute(
                    "SELECT state FROM job_campaigns WHERE id = %s AND user_id = %s FOR UPDATE",
                    (campaign_id, user_id)
                )
                row = cur.fetchone()
                if not row:
                    return False
                
                current_state = row[0] or {}
                trace = current_state.get('trace', [])
                trace.append(event)
                current_state['trace'] = trace
                
                cur.execute(
                    "UPDATE job_campaigns SET state = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
                    (Json(current_state), campaign_id, user_id)
                )
                conn.commit()
                return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error appending campaign trace: {str(e)}")
            return False
        finally:
            if conn:
                self._return_connection(conn)

    def set_job_campaign_selected_contacts(self, campaign_id, user_id, selected_contacts):
        """Set selected contacts for a campaign."""
        return self.update_job_campaign_state(
            campaign_id, user_id,
            {'selected_contacts': selected_contacts}
        )

    def add_job_campaign_feedback(self, campaign_id, user_id, scope, text, must=False):
        """Add feedback to a campaign. Feedback is stored with timestamp for ordering."""
        import datetime
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT state FROM job_campaigns WHERE id = %s AND user_id = %s FOR UPDATE",
                    (campaign_id, user_id)
                )
                row = cur.fetchone()
                if not row:
                    return False
                
                current_state = row[0] or {}
                feedback = current_state.get('feedback', {'global': [], 'draft_specific': {}})
                
                feedback_entry = {
                    'text': text,
                    'must': must,
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }
                
                if scope == 'global':
                    if 'global' not in feedback:
                        feedback['global'] = []
                    feedback['global'].append(feedback_entry)
                else:
                    if 'draft_specific' not in feedback:
                        feedback['draft_specific'] = {}
                    if scope not in feedback['draft_specific']:
                        feedback['draft_specific'][scope] = []
                    feedback['draft_specific'][scope].append(feedback_entry)
                
                current_state['feedback'] = feedback
                
                cur.execute(
                    "UPDATE job_campaigns SET state = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
                    (Json(current_state), campaign_id, user_id)
                )
                conn.commit()
                return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error adding campaign feedback: {str(e)}")
            return False
        finally:
            if conn:
                self._return_connection(conn)

    def get_job_post_with_jd(self, job_post_id):
        """Get job post with raw JD data if available."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, source_type, company_name, ats_type, title, location, team,
                           employment_type, url, raw_json
                    FROM job_posts WHERE id = %s
                """, (job_post_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    'id': row[0],
                    'source_type': row[1],
                    'company_name': row[2],
                    'ats_type': row[3],
                    'title': row[4],
                    'location': row[5],
                    'team': row[6],
                    'employment_type': row[7],
                    'url': row[8],
                    'raw_json': row[9] or {}
                }
        except Exception as e:
            logger.error(f"Error getting job post with JD: {str(e)}")
            return None
        finally:
            if conn:
                self._return_connection(conn)

    def get_campaign_trace_from_index(self, campaign_id, user_id, from_index=0):
        """Get trace events starting from a specific index (for SSE streaming)."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT state FROM job_campaigns WHERE id = %s AND user_id = %s",
                    (campaign_id, user_id)
                )
                row = cur.fetchone()
                if not row:
                    return None, None
                
                state = row[0] or {}
                trace = state.get('trace', [])
                phase = state.get('phase', 'idle')
                
                return trace[from_index:], phase
        except Exception as e:
            logger.error(f"Error getting campaign trace: {str(e)}")
            return None, None
        finally:
            if conn:
                self._return_connection(conn)