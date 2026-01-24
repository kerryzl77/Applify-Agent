"""
DEPRECATED: Legacy Background Processor
========================================

This module is deprecated and replaced by enhanced_resume_processor.py
which uses the new 2-tier VLM pipeline.

This file is kept for backwards compatibility but is not used.
Use enhanced_resume_processor instead.
"""

import threading
import warnings
from app.enhanced_resume_processor import enhanced_resume_processor
from database.db_manager import DatabaseManager


def _deprecation_warning():
    warnings.warn(
        "BackgroundProcessor is deprecated. Use enhanced_resume_processor instead.",
        DeprecationWarning,
        stacklevel=3
    )


class BackgroundProcessor:
    """
    DEPRECATED: Use enhanced_resume_processor instead.
    
    This class is kept for backwards compatibility only.
    """
    
    def __init__(self):
        _deprecation_warning()
        self.db_manager = DatabaseManager()
        self.processing_queue = {}
        
    def process_resume(self, file_path, user_id):
        """DEPRECATED: Use enhanced_resume_processor.process_resume_enhanced instead."""
        _deprecation_warning()
        # Delegate to new processor
        enhanced_resume_processor.process_resume_enhanced(file_path, user_id, "resume.pdf")
        
    def start_processing(self, file_path, user_id):
        """DEPRECATED: Use enhanced_resume_processor.start_processing instead."""
        _deprecation_warning()
        # Delegate to new processor
        enhanced_resume_processor.start_processing(file_path, user_id, "resume.pdf")
        
    def get_status(self, user_id):
        """DEPRECATED: Use enhanced_resume_processor.get_status instead."""
        return enhanced_resume_processor.get_status(user_id)


# Create a global instance (deprecated)
background_processor = BackgroundProcessor()
