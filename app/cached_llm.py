from app.redis_manager import RedisManager, cache_result
from app.llm_generator import LLMGenerator
import logging

logger = logging.getLogger(__name__)

class CachedLLMGenerator(LLMGenerator):
    """LLM Generator with Redis caching for better performance."""
    
    def __init__(self):
        super().__init__()
        self.redis_manager = RedisManager()
    
    @cache_result("linkedin_msg", ttl=3600)
    def generate_linkedin_message(self, job_data, candidate_data, profile_data):
        """Generate LinkedIn message with caching."""
        return super().generate_linkedin_message(job_data, candidate_data, profile_data)
    
    @cache_result("connection_email", ttl=3600)  
    def generate_connection_email(self, job_data, candidate_data, profile_data):
        """Generate connection email with caching."""
        return super().generate_connection_email(job_data, candidate_data, profile_data)
    
    @cache_result("connection_email_bundle", ttl=3600)
    def generate_connection_email_bundle(self, job_data, candidate_data, profile_data):
        """Generate connection email bundle with caching."""
        return super().generate_connection_email_bundle(job_data, candidate_data, profile_data)

    @cache_result("hiring_email", ttl=3600)
    def generate_hiring_manager_email(self, job_data, candidate_data, profile_data=None):
        """Generate hiring manager email with caching."""
        return super().generate_hiring_manager_email(job_data, candidate_data, profile_data)
    
    @cache_result("hiring_email_bundle", ttl=3600)
    def generate_hiring_manager_email_bundle(self, job_data, candidate_data, profile_data=None):
        """Generate hiring manager email bundle with caching."""
        return super().generate_hiring_manager_email_bundle(job_data, candidate_data, profile_data)

    @cache_result("cover_letter", ttl=3600)
    def generate_cover_letter(self, job_data, candidate_data):
        """Generate cover letter with caching."""
        return super().generate_cover_letter(job_data, candidate_data)