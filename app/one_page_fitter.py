"""
One-Page Fitter
===============

Deterministic compression loop to ensure tailored resumes fit on one page.
Applies progressive constraints until the resume fits.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FitterConstraints:
    """Constraints for one-page fitting."""
    max_experience_roles: int = 4
    max_bullets_per_role: int = 3
    max_skills: int = 15
    max_summary_words: int = 60
    max_bullet_words: int = 25
    max_education_entries: int = 2


@dataclass
class FitterResult:
    """Result of the fitting process."""
    fitted: bool  # Whether it fits on one page
    iterations: int  # How many compression iterations were run
    changes_made: list  # List of changes made to fit


class OnePageFitter:
    """
    Deterministic compression to ensure resume fits on one page.
    
    Applies progressive constraints in order:
    1. Limit experience roles to max
    2. Limit bullets per role to max
    3. Limit skills count
    4. Truncate long bullets
    5. Truncate summary if needed
    """
    
    def __init__(self, constraints: Optional[FitterConstraints] = None):
        """
        Initialize the fitter.
        
        Args:
            constraints: Fitting constraints (uses defaults if not provided)
        """
        self.constraints = constraints or FitterConstraints()
    
    def fit(self, tailored_resume: dict, page_counter=None) -> tuple[dict, FitterResult]:
        """
        Apply constraints to fit resume on one page.
        
        Args:
            tailored_resume: TailoredResume as dict
            page_counter: Optional callable(resume_dict) -> int that counts pages
            
        Returns:
            Tuple of (fitted resume dict, FitterResult)
        """
        result = FitterResult(fitted=True, iterations=0, changes_made=[])
        resume = self._deep_copy(tailored_resume)
        
        # Apply deterministic constraints
        resume, changes = self._apply_constraints(resume)
        result.changes_made.extend(changes)
        result.iterations = 1
        
        # If we have a page counter, verify and iterate if needed
        if page_counter:
            max_iterations = 5
            for i in range(max_iterations):
                page_count = page_counter(resume)
                if page_count <= 1:
                    result.fitted = True
                    break
                
                # Apply more aggressive constraints
                resume, changes = self._compress_further(resume, i + 1)
                result.changes_made.extend(changes)
                result.iterations = i + 2
            else:
                # Still doesn't fit after max iterations
                result.fitted = False
                logger.warning("Resume still exceeds one page after max iterations")
        
        return resume, result
    
    def _apply_constraints(self, resume: dict) -> tuple[dict, list]:
        """Apply initial constraints to the resume."""
        changes = []
        
        # 1. Limit experience roles
        experience = resume.get("experience", [])
        if len(experience) > self.constraints.max_experience_roles:
            resume["experience"] = experience[:self.constraints.max_experience_roles]
            changes.append(f"Limited experience to {self.constraints.max_experience_roles} roles")
        
        # 2. Limit bullets per role
        for i, exp in enumerate(resume.get("experience", [])):
            bullets = exp.get("bullet_points", [])
            if len(bullets) > self.constraints.max_bullets_per_role:
                resume["experience"][i]["bullet_points"] = bullets[:self.constraints.max_bullets_per_role]
                changes.append(f"Limited bullets for role {i+1} to {self.constraints.max_bullets_per_role}")
        
        # 3. Limit skills
        skills = resume.get("skills", [])
        if len(skills) > self.constraints.max_skills:
            resume["skills"] = skills[:self.constraints.max_skills]
            changes.append(f"Limited skills to {self.constraints.max_skills}")
        
        # 4. Truncate long bullets
        for i, exp in enumerate(resume.get("experience", [])):
            new_bullets = []
            for j, bullet in enumerate(exp.get("bullet_points", [])):
                words = bullet.split()
                if len(words) > self.constraints.max_bullet_words:
                    truncated = " ".join(words[:self.constraints.max_bullet_words])
                    new_bullets.append(truncated)
                    changes.append(f"Truncated bullet {j+1} in role {i+1}")
                else:
                    new_bullets.append(bullet)
            resume["experience"][i]["bullet_points"] = new_bullets
        
        # 5. Limit summary length
        summary = resume.get("summary", "")
        words = summary.split()
        if len(words) > self.constraints.max_summary_words:
            # Try to end at a sentence boundary
            truncated_words = words[:self.constraints.max_summary_words]
            truncated = " ".join(truncated_words)
            if not truncated.endswith("."):
                truncated += "."
            resume["summary"] = truncated
            changes.append(f"Truncated summary to {self.constraints.max_summary_words} words")
        
        # 6. Limit education entries
        education = resume.get("education", [])
        if len(education) > self.constraints.max_education_entries:
            resume["education"] = education[:self.constraints.max_education_entries]
            changes.append(f"Limited education to {self.constraints.max_education_entries} entries")
        
        return resume, changes
    
    def _compress_further(self, resume: dict, iteration: int) -> tuple[dict, list]:
        """
        Apply more aggressive compression for subsequent iterations.
        
        Order prioritizes reducing "width" (bullets, skills) before dropping
        entire roles to preserve as much content as possible.
        """
        changes = []
        
        # Progressive compression based on iteration
        if iteration == 1:
            # First: Reduce bullets to 2 per role (preserves all roles)
            for i, exp in enumerate(resume.get("experience", [])):
                bullets = exp.get("bullet_points", [])
                if len(bullets) > 2:
                    resume["experience"][i]["bullet_points"] = bullets[:2]
                    changes.append(f"Reduced role {i+1} to 2 bullets")
        
        elif iteration == 2:
            # Second: Reduce skills to 10 (preserves all roles)
            skills = resume.get("skills", [])
            if len(skills) > 10:
                resume["skills"] = skills[:10]
                changes.append("Limited to 10 skills")
        
        elif iteration == 3:
            # Third: Reduce experience to 3 roles (last resort for roles)
            experience = resume.get("experience", [])
            if len(experience) > 3:
                resume["experience"] = experience[:3]
                changes.append("Limited to 3 experience roles")
        
        elif iteration == 4:
            # Fourth: Truncate bullets further to 18 words
            for i, exp in enumerate(resume.get("experience", [])):
                new_bullets = []
                for bullet in exp.get("bullet_points", []):
                    words = bullet.split()
                    if len(words) > 18:
                        new_bullets.append(" ".join(words[:18]))
                    else:
                        new_bullets.append(bullet)
                resume["experience"][i]["bullet_points"] = new_bullets
            changes.append("Truncated bullets to 18 words")
        
        elif iteration >= 5:
            # Fifth+: Reduce summary and skills further
            summary = resume.get("summary", "")
            words = summary.split()
            if len(words) > 40:
                resume["summary"] = " ".join(words[:40]) + "."
                changes.append("Truncated summary to 40 words")
            
            skills = resume.get("skills", [])
            if len(skills) > 8:
                resume["skills"] = skills[:8]
                changes.append("Limited to 8 skills")
        
        return resume, changes
    
    def _deep_copy(self, obj):
        """Deep copy a dict/list structure."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj


# Module-level instance for convenience
one_page_fitter = OnePageFitter()
