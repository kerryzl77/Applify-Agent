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
    def generate_linkedin_message(self, job_data, candidate_data, profile_data, evidence_pack=None):
        """Generate LinkedIn message with caching."""
        return super().generate_linkedin_message(job_data, candidate_data, profile_data, evidence_pack=evidence_pack)
    
    def generate_connection_email_artifact(self, job_data, candidate_data, profile_data, evidence_pack=None):
        """Generate connection email with caching."""
        return super().generate_connection_email_artifact(job_data, candidate_data, profile_data, evidence_pack=evidence_pack)
    
    def generate_hiring_manager_email_artifact(self, job_data, candidate_data, profile_data=None, evidence_pack=None):
        """Generate hiring manager email with caching."""
        return super().generate_hiring_manager_email_artifact(job_data, candidate_data, profile_data, evidence_pack=evidence_pack)
    
    def generate_cover_letter_artifact(self, job_data, candidate_data, evidence_pack=None):
        """Generate cover letter with caching."""
        return super().generate_cover_letter_artifact(job_data, candidate_data, evidence_pack=evidence_pack)
