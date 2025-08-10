import threading
import time
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from app.resume_parser import ResumeParser
from database.db_manager import DatabaseManager
from app.redis_manager import RedisManager

logger = logging.getLogger(__name__)

class EnhancedResumeProcessor:
    def __init__(self):
        self.resume_parser = ResumeParser()
        self.db_manager = DatabaseManager()
        self.redis_manager = RedisManager()
        self.processing_queue = {}
        self.lock = threading.Lock()
        
    def _update_progress(self, user_id: str, step: str, progress: int, message: str, data: Optional[Dict] = None):
        """Update processing progress with Redis caching."""
        progress_data = {
            'user_id': user_id,
            'step': step,
            'progress': progress,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': data or {}
        }
        
        with self.lock:
            self.processing_queue[user_id] = progress_data
            
        # Cache progress in Redis for persistence
        cache_key = f"resume_progress:{user_id}"
        self.redis_manager.set(cache_key, progress_data, ttl=1800)  # 30 minutes
        
        logger.info(f"Progress update for user {user_id}: {step} - {progress}% - {message}")
        
    def _get_resume_hash(self, file_path: str) -> str:
        """Generate hash for resume file to enable caching."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error generating file hash: {str(e)}")
            return f"hash_error_{int(time.time())}"
    
    def _check_cached_resume(self, file_hash: str, user_id: str) -> Optional[Dict]:
        """Check if resume has been processed before."""
        cache_key = f"parsed_resume:{file_hash}"
        cached_data = self.redis_manager.get(cache_key)
        
        if cached_data:
            logger.info(f"Found cached resume data for hash {file_hash}")
            return cached_data
        return None
    
    def _cache_parsed_resume(self, file_hash: str, parsed_data: Dict, user_id: str):
        """Cache parsed resume data."""
        cache_key = f"parsed_resume:{file_hash}"
        cache_data = {
            'parsed_data': parsed_data,
            'processed_at': datetime.now().isoformat(),
            'user_id': user_id
        }
        # Cache for 7 days
        self.redis_manager.set(cache_key, cache_data, ttl=604800)
        logger.info(f"Cached parsed resume data for hash {file_hash}")
    
    def process_resume_enhanced(self, file_path: str, user_id: str, original_filename: str):
        """Enhanced resume processing with progress tracking and caching."""
        try:
            self._update_progress(user_id, 'initializing', 5, 'Starting resume processing...')
            
            # Generate file hash for caching
            file_hash = self._get_resume_hash(file_path)
            self._update_progress(user_id, 'analyzing', 10, 'Analyzing resume file...')
            
            # Check cache first
            cached_result = self._check_cached_resume(file_hash, user_id)
            if cached_result:
                self._update_progress(user_id, 'cache_hit', 50, 'Found cached resume data, applying to profile...')
                parsed_data = cached_result['parsed_data']
            else:
                # Extract text
                self._update_progress(user_id, 'extracting', 20, 'Extracting text from resume...')
                text = self.resume_parser.extract_text(file_path, timeout=120)
                
                if not text or len(text.strip()) < 50:
                    raise ValueError("Resume text is too short or empty. Please check your file.")
                
                self._update_progress(user_id, 'text_extracted', 40, f'Extracted {len(text)} characters of text')
                
                # Parse with AI
                self._update_progress(user_id, 'ai_parsing', 60, 'AI is analyzing your resume...')
                parsed_data = self.resume_parser.parse_resume_enhanced(text, timeout=120)
                logger.info(f"Parsed resume data for user {user_id}: {json.dumps(parsed_data, indent=2, default=str)}")
                
                # Cache the result
                self._cache_parsed_resume(file_hash, parsed_data, user_id)
            
            # Merge with existing profile data intelligently
            self._update_progress(user_id, 'merging', 80, 'Updating your profile...')
            merged_data = self._intelligent_profile_merge(user_id, parsed_data)
            
            # Update database
            self._update_progress(user_id, 'saving', 90, 'Saving to database...')
            save_success = self.db_manager.update_candidate_data(merged_data, user_id)
            logger.info(f"Database update success: {save_success} for user {user_id}")
            
            # Invalidate user cache to force fresh data
            self.redis_manager.invalidate_user_cache(user_id)
            logger.info(f"Cache invalidated for user {user_id}")
            
            # Log the merged data for debugging
            logger.info(f"Merged data for user {user_id}: {json.dumps(merged_data, indent=2, default=str)}")
            
            # Complete
            completion_data = {
                'parsed_data': merged_data,
                'original_filename': original_filename,
                'processed_at': datetime.now().isoformat(),
                'cached': cached_result is not None
            }
            
            self._update_progress(user_id, 'complete', 100, 'Resume processed successfully!', completion_data)
            logger.info(f"Resume processing completed for user {user_id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing resume for user {user_id}: {error_msg}")
            self._update_progress(user_id, 'error', 0, f'Error: {error_msg}')
    
    def _intelligent_profile_merge(self, user_id: str, new_data: Dict) -> Dict:
        """Intelligently merge new resume data with existing profile."""
        # Get current profile
        current_data = self.db_manager.get_candidate_data(user_id) or {}
        
        # Initialize structure if needed
        merged = {
            'personal_info': current_data.get('personal_info', {}),
            'resume': current_data.get('resume', {}),
            'story_bank': current_data.get('story_bank', []),
            'templates': current_data.get('templates', {
                'linkedin_messages': {'title': '', 'template': ''},
                'connection_emails': {'title': '', 'template': ''},
                'hiring_manager_emails': {'title': '', 'template': ''},
                'cover_letters': {'title': '', 'template': ''}
            }),
            'generated_content': current_data.get('generated_content', [])
        }
        
        # Merge personal info (only update empty fields)
        for key, value in new_data.get('personal_info', {}).items():
            if value and (not merged['personal_info'].get(key) or merged['personal_info'].get(key) == '' or merged['personal_info'].get(key) is None):
                merged['personal_info'][key] = value
                logger.info(f"Updated personal_info.{key} = {value} for user {user_id}")
        
        # Update resume data (replace with new data)
        merged['resume'] = new_data.get('resume', {})
        
        # Replace story bank completely with new resume-generated stories
        merged['story_bank'] = new_data.get('story_bank', [])
        logger.info(f"Replaced story bank with {len(merged['story_bank'])} new stories for user {user_id}")
        
        return merged
    
    def start_processing(self, file_path: str, user_id: str, original_filename: str):
        """Start enhanced background processing."""
        self._update_progress(user_id, 'queued', 0, 'Resume queued for processing...')
        
        thread = threading.Thread(
            target=self.process_resume_enhanced,
            args=(file_path, user_id, original_filename)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started enhanced resume processing for user {user_id}")
    
    def get_status(self, user_id: str) -> Dict:
        """Get detailed processing status."""
        # Try memory first
        with self.lock:
            if user_id in self.processing_queue:
                return self.processing_queue[user_id]
        
        # Fall back to Redis
        cache_key = f"resume_progress:{user_id}"
        cached_status = self.redis_manager.get(cache_key)
        if cached_status:
            return cached_status
        
        return {'status': 'not_found', 'message': 'No processing found for this user'}
    
    def clear_status(self, user_id: str):
        """Clear processing status."""
        with self.lock:
            self.processing_queue.pop(user_id, None)
        
        cache_key = f"resume_progress:{user_id}"
        self.redis_manager.delete(cache_key)

# Create enhanced global instance
enhanced_resume_processor = EnhancedResumeProcessor()