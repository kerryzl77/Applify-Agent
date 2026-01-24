"""
Enhanced Resume Processor
=========================

Background processing for resume uploads using the 2-tier pipeline:
- Tier 1: PyMuPDF layout-aware extraction (fast, deterministic)
- Tier 2: GPT-5.2 VLM structured parsing (reliable JSON)

Handles progress tracking, caching, and profile merging.
"""

import threading
import time
import json
import hashlib
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from database.db_manager import DatabaseManager
from app.redis_manager import RedisManager
from app.resume_extractor_pymupdf import ResumeExtractorPyMuPDF, ExtractionResult
from app.resume_rewriter_vlm import ResumeRewriterVLM, ParsedResume

logger = logging.getLogger(__name__)


class EnhancedResumeProcessor:
    """
    Background processor for resume uploads using 2-tier extraction + VLM parsing.
    
    Flow:
    1. Extract layout + image with PyMuPDF (Tier 1)
    2. Parse to structured JSON with GPT-5.2 VLM (Tier 2)
    3. Merge into user profile
    4. Cache extraction artifacts for later refinement
    """
    
    def __init__(self):
        self.extractor = ResumeExtractorPyMuPDF()
        self.rewriter = ResumeRewriterVLM()
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
    
    def _cache_parsed_resume(self, file_hash: str, parsed_data: Dict, extraction_artifacts: Dict, user_id: str):
        """Cache parsed resume data and extraction artifacts."""
        cache_key = f"parsed_resume:{file_hash}"
        cache_data = {
            'parsed_data': parsed_data,
            'extraction_artifacts': extraction_artifacts,
            'processed_at': datetime.now().isoformat(),
            'user_id': user_id
        }
        # Cache for 7 days
        self.redis_manager.set(cache_key, cache_data, ttl=604800)
        logger.info(f"Cached parsed resume data for hash {file_hash}")
    
    def _cache_user_extraction(self, user_id: str, extraction_artifacts: Dict):
        """Cache extraction artifacts for user (used during refinement)."""
        cache_key = f"resume_extraction:{user_id}"
        self.redis_manager.set(cache_key, extraction_artifacts, ttl=86400)  # 24 hours
        logger.info(f"Cached extraction artifacts for user {user_id}")
    
    def get_user_extraction(self, user_id: str) -> Optional[Dict]:
        """Get cached extraction artifacts for user."""
        cache_key = f"resume_extraction:{user_id}"
        return self.redis_manager.get(cache_key)
    
    def process_resume_enhanced(self, file_path: str, user_id: str, original_filename: str):
        """
        Enhanced resume processing with 2-tier pipeline.
        
        Progress steps (compatible with frontend):
        - initializing (5%)
        - analyzing (10%)
        - extracting (20%) - Tier 1 PyMuPDF
        - text_extracted (40%)
        - ai_parsing (60%) - Tier 2 VLM
        - merging (80%)
        - saving (90%)
        - complete (100%)
        """
        try:
            self._update_progress(user_id, 'initializing', 5, 'Starting resume processing...')
            
            # Check file type
            file_ext = os.path.splitext(file_path)[1].lower()
            is_pdf = file_ext == '.pdf'
            
            # Generate file hash for caching
            file_hash = self._get_resume_hash(file_path)
            self._update_progress(user_id, 'analyzing', 10, 'Analyzing resume file...')
            
            # Check cache first
            cached_result = self._check_cached_resume(file_hash, user_id)
            if cached_result:
                self._update_progress(user_id, 'cache_hit', 50, 'Found cached resume data, applying to profile...')
                parsed_data = cached_result['parsed_data']
                extraction_artifacts = cached_result.get('extraction_artifacts', {})
                # Re-cache extraction for user
                if extraction_artifacts:
                    self._cache_user_extraction(user_id, extraction_artifacts)
            else:
                # ================================================================
                # TIER 1: PyMuPDF Layout-Aware Extraction
                # ================================================================
                self._update_progress(user_id, 'extracting', 20, 'Extracting layout from resume...')
                
                extraction_result: Optional[ExtractionResult] = None
                fulltext = ""
                page_image_b64 = None
                block_summary = ""
                
                if is_pdf:
                    try:
                        extraction_result = self.extractor.extract(file_path)
                        fulltext = extraction_result.fulltext_linear
                        
                        # Get first page image for VLM
                        if extraction_result.page_images:
                            page_image_b64 = extraction_result.page_images[0]
                        
                        # Build block summary for context
                        block_summary = self._build_block_summary(extraction_result)
                        
                        logger.info(f"Tier 1 extraction: {len(fulltext)} chars, "
                                   f"{extraction_result.metadata.get('page_count', 0)} pages")
                    except Exception as e:
                        logger.warning(f"PyMuPDF extraction failed, falling back: {str(e)}")
                        # Fall back to basic text extraction
                        fulltext = self._fallback_text_extraction(file_path)
                else:
                    # DOCX handling - basic text extraction
                    fulltext = self._extract_docx_text(file_path)
                
                if not fulltext or len(fulltext.strip()) < 50:
                    raise ValueError("Resume text is too short or empty. Please check your file.")
                
                self._update_progress(user_id, 'text_extracted', 40, f'Extracted {len(fulltext)} characters of text')
                
                # ================================================================
                # TIER 2: GPT-5.2 VLM Structured Parsing
                # ================================================================
                self._update_progress(user_id, 'ai_parsing', 60, 'AI is analyzing your resume...')
                
                parsed_resume: ParsedResume = self.rewriter.parse_resume(
                    fulltext=fulltext,
                    page_image_b64=page_image_b64,
                    block_summary=block_summary,
                )
                
                # Convert Pydantic model to dict
                parsed_data = self._parsed_resume_to_dict(parsed_resume)
                logger.info(f"Tier 2 parsing complete for user {user_id}")
                
                # Prepare extraction artifacts for caching
                extraction_artifacts = {
                    'fulltext': fulltext[:10000],  # Limit size for caching
                    'page_image': page_image_b64,  # First page image
                    'block_summary': block_summary[:2000],
                    'page_count': extraction_result.metadata.get('page_count', 1) if extraction_result else 1,
                }
                
                # Cache the result
                self._cache_parsed_resume(file_hash, parsed_data, extraction_artifacts, user_id)
                self._cache_user_extraction(user_id, extraction_artifacts)
            
            # ================================================================
            # Merge with existing profile
            # ================================================================
            self._update_progress(user_id, 'merging', 80, 'Updating your profile...')
            merged_data = self._intelligent_profile_merge(user_id, parsed_data)
            
            # Update database
            self._update_progress(user_id, 'saving', 90, 'Saving to database...')
            save_success = self.db_manager.update_candidate_data(merged_data, user_id)
            logger.info(f"Database update success: {save_success} for user {user_id}")
            
            # Invalidate user cache to force fresh data
            self.redis_manager.invalidate_user_cache(user_id)
            logger.info(f"Cache invalidated for user {user_id}")
            
            # Complete
            completion_data = {
                'parsed_data': merged_data,
                'original_filename': original_filename,
                'processed_at': datetime.now().isoformat(),
                'cached': cached_result is not None,
                'pipeline': '2-tier-vlm'
            }
            
            self._update_progress(user_id, 'complete', 100, 'Resume processed successfully!', completion_data)
            logger.info(f"Resume processing completed for user {user_id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing resume for user {user_id}: {error_msg}")
            self._update_progress(user_id, 'error', 0, f'Error: {error_msg}')
    
    def _build_block_summary(self, extraction_result: ExtractionResult) -> str:
        """Build a summary of layout blocks for VLM context."""
        parts = []
        for page in extraction_result.pages[:2]:  # First 2 pages
            parts.append(f"Page {page.page_number + 1}:")
            for block in page.blocks[:20]:  # First 20 blocks
                if block.is_heading_candidate:
                    parts.append(f"  [HEADING] {block.text[:80]}")
                elif block.block_type == "image":
                    parts.append(f"  [IMAGE]")
                else:
                    parts.append(f"  {block.text[:60]}...")
        return "\n".join(parts)
    
    def _fallback_text_extraction(self, file_path: str) -> str:
        """Fallback text extraction using PyPDF2."""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Fallback PDF extraction failed: {str(e)}")
            return ""
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX extraction failed: {str(e)}")
            return ""
    
    def _parsed_resume_to_dict(self, parsed: ParsedResume) -> Dict:
        """Convert ParsedResume Pydantic model to dict for storage."""
        # Convert experience list
        experience = []
        for exp in parsed.resume.experience:
            experience.append({
                'title': exp.title,
                'company': exp.company,
                'location': exp.location,
                'start_date': exp.start_date,
                'end_date': exp.end_date,
                'description': exp.description,
                'bullet_points': exp.bullet_points,
            })
        
        # Convert education list
        education = []
        for edu in parsed.resume.education:
            education.append({
                'degree': edu.degree,
                'institution': edu.institution,
                'location': edu.location,
                'graduation_date': edu.graduation_date,
                'gpa': edu.gpa,
                'honors': edu.honors,
            })
        
        # Convert story_bank (already list of dicts from Pydantic)
        story_bank = parsed.story_bank if parsed.story_bank else []
        
        return {
            'personal_info': {
                'name': parsed.personal_info.name,
                'email': parsed.personal_info.email,
                'phone': parsed.personal_info.phone,
                'location': parsed.personal_info.location,
                'linkedin': parsed.personal_info.linkedin,
                'github': parsed.personal_info.github,
                'website': parsed.personal_info.website,
            },
            'resume': {
                'summary': parsed.resume.summary,
                'skills': parsed.resume.skills,  # Flat list
                'experience': experience,
                'education': education,
            },
            'story_bank': story_bank,
        }
    
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
        
        # Merge personal info (update non-empty fields)
        incoming_personal_info = new_data.get('personal_info', {})
        for key, value in incoming_personal_info.items():
            if value and value != merged['personal_info'].get(key):
                merged['personal_info'][key] = value
                logger.info(f"Updated personal_info.{key} for user {user_id}")
        
        # Update resume data (replace with new data for core fields)
        resume_fragment = new_data.get('resume', {})
        if resume_fragment:
            for key in ['summary', 'skills', 'experience', 'education']:
                if key in resume_fragment and resume_fragment[key]:
                    merged['resume'][key] = resume_fragment[key]
        
        # Replace story bank with new resume-generated stories
        if new_data.get('story_bank'):
            merged['story_bank'] = new_data['story_bank']
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
