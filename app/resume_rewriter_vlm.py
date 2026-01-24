"""
Resume Rewriter using GPT-5.2 VLM (Tier 2)
==========================================

Uses OpenAI Responses API with structured outputs to:
1. Parse resume content into profile JSON (upload flow)
2. Tailor resume to job description (refine flow)

Leverages vision capabilities for multi-column/complex layouts.
"""

import os
import logging
from typing import Optional, List
from dataclasses import dataclass

from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Structured Outputs
# =============================================================================

class PersonalInfo(BaseModel):
    """Personal/contact information extracted from resume."""
    name: str = Field(default="", description="Full name")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    location: str = Field(default="", description="City, State/Country")
    linkedin: str = Field(default="", description="LinkedIn URL")
    github: str = Field(default="", description="GitHub URL")
    website: str = Field(default="", description="Personal website URL")


class Experience(BaseModel):
    """A single work experience entry."""
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    location: str = Field(default="", description="Job location")
    start_date: str = Field(default="", description="Start date (e.g., Jan 2020)")
    end_date: str = Field(default="", description="End date or 'Present'")
    description: str = Field(default="", description="Role description/achievements")
    bullet_points: List[str] = Field(default_factory=list, description="Achievement bullets")


class Education(BaseModel):
    """A single education entry."""
    degree: str = Field(description="Degree and field of study")
    institution: str = Field(description="School/university name")
    location: str = Field(default="", description="Location")
    graduation_date: str = Field(default="", description="Graduation date")
    gpa: str = Field(default="", description="GPA if notable")
    honors: str = Field(default="", description="Honors/awards")


class ResumeData(BaseModel):
    """Resume content (summary, skills, experience, education)."""
    summary: str = Field(default="", description="Professional summary (2-3 sentences)")
    skills: List[str] = Field(default_factory=list, description="Prioritized list of skills")
    experience: List[Experience] = Field(default_factory=list, description="Work experience")
    education: List[Education] = Field(default_factory=list, description="Education")


class ParsedResume(BaseModel):
    """Complete parsed resume for profile storage."""
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    resume: ResumeData = Field(default_factory=ResumeData)
    story_bank: List[dict] = Field(
        default_factory=list, 
        description="STAR-format achievement stories extracted from experience"
    )


class TailoredExperience(BaseModel):
    """Experience entry tailored for a specific job."""
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    location: str = Field(default="", description="Location")
    start_date: str = Field(default="", description="Start date")
    end_date: str = Field(default="", description="End date or Present")
    bullet_points: List[str] = Field(
        description="3 achievement bullets max, tailored to target job"
    )


class TailoredEducation(BaseModel):
    """Compact education entry for tailored resume."""
    degree: str = Field(description="Degree and field")
    institution: str = Field(description="School name")
    graduation_date: str = Field(default="", description="Graduation date")


class TailoredResume(BaseModel):
    """Tailored resume optimized for a specific job (ephemeral, for PDF generation)."""
    summary: str = Field(description="2-3 sentence professional summary tailored to job")
    skills: List[str] = Field(description="Prioritized skills list (most relevant first)")
    experience: List[TailoredExperience] = Field(
        description="Max 4 roles, most relevant first, 3 bullets each"
    )
    education: List[TailoredEducation] = Field(description="Compact education entries")
    edit_log: List[str] = Field(
        default_factory=list,
        description="Brief notes on what was changed/prioritized for debugging"
    )


# =============================================================================
# VLM Rewriter Class
# =============================================================================

class ResumeRewriterVLM:
    """
    Tier 2: GPT-5.2 VLM-powered resume parsing and tailoring.
    
    Uses Responses API with structured outputs for reliable JSON.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5.2"):
        """
        Initialize the VLM rewriter.
        
        Args:
            api_key: OpenAI API key (defaults to env var)
            model: Model to use (default gpt-5.2)
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
    
    def parse_resume(
        self,
        fulltext: str,
        page_image_b64: Optional[str] = None,
        block_summary: Optional[str] = None,
    ) -> ParsedResume:
        """
        Parse resume content into structured profile JSON.
        
        Args:
            fulltext: Linear text extracted from resume
            page_image_b64: Base64 data URL of first page (optional, for VLM)
            block_summary: Summary of layout blocks (optional context)
            
        Returns:
            ParsedResume with personal_info, resume data, and story_bank
        """
        # Build input content
        input_content = []
        
        # Add image if available
        if page_image_b64:
            input_content.append({
                "type": "input_image",
                "image_url": page_image_b64,
            })
        
        # Build text prompt
        prompt_parts = [
            "You are an expert resume parser. Extract all information from this resume into structured JSON.",
            "",
            "RESUME TEXT:",
            fulltext[:8000],  # Limit to prevent token overflow
        ]
        
        if block_summary:
            prompt_parts.extend([
                "",
                "LAYOUT CONTEXT:",
                block_summary[:2000],
            ])
        
        prompt_parts.extend([
            "",
            "INSTRUCTIONS:",
            "1. Extract all contact information (name, email, phone, location, LinkedIn, GitHub, website)",
            "2. Generate a compelling 2-3 sentence professional summary if not present",
            "3. Extract skills as a flat prioritized list (most important first)",
            "4. Extract all work experience with titles, companies, dates, and achievements",
            "5. Extract education with degrees, institutions, and dates",
            "6. Create 3-5 STAR-format story entries from the most impressive achievements",
            "",
            "For story_bank entries, use format: {'title': 'Achievement Title', 'content': 'STAR story'}",
        ])
        
        input_content.append({
            "type": "input_text",
            "text": "\n".join(prompt_parts),
        })
        
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[{"role": "user", "content": input_content}],
                text_format=ParsedResume,
            )
            
            result = response.output_parsed
            logger.info(f"Parsed resume: {result.personal_info.name}, "
                       f"{len(result.resume.skills)} skills, "
                       f"{len(result.resume.experience)} experiences")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing resume with VLM: {str(e)}")
            # Return empty result on error
            return ParsedResume()
    
    def tailor_resume(
        self,
        candidate_data: dict,
        job_description: str,
        page_image_b64: Optional[str] = None,
    ) -> TailoredResume:
        """
        Tailor resume content to a specific job description.
        
        Args:
            candidate_data: Current profile data (personal_info, resume)
            job_description: Target job description
            page_image_b64: Original resume image for layout reference (optional)
            
        Returns:
            TailoredResume optimized for the target job
        """
        resume_data = candidate_data.get("resume", {})
        personal_info = candidate_data.get("personal_info", {})
        
        # Build input content
        input_content = []
        
        # Add image if available
        if page_image_b64:
            input_content.append({
                "type": "input_image",
                "image_url": page_image_b64,
            })
        
        # Format current resume data
        current_resume = self._format_resume_for_prompt(resume_data, personal_info)
        
        prompt = f"""You are an expert resume writer specializing in ATS-optimized, job-tailored resumes.

JOB DESCRIPTION:
{job_description[:4000]}

CANDIDATE'S CURRENT RESUME:
{current_resume}

INSTRUCTIONS:
1. Create a compelling 2-3 sentence professional summary that:
   - Includes the target job title naturally
   - Highlights 2-3 most relevant skills/achievements
   - Uses keywords from the job description
   - Is 40-60 words max

2. Prioritize skills list:
   - Put skills mentioned in job description first
   - Include 10-15 most relevant skills
   - Remove irrelevant skills

3. Optimize experience (max 4 roles, 3 bullets each):
   - Prioritize roles most relevant to target job
   - Rewrite bullets to emphasize matching achievements
   - Use action verbs and quantify results
   - Include keywords from job description naturally

4. Keep education compact (degree, school, date only)

5. In edit_log, briefly note what was changed/prioritized

CRITICAL CONSTRAINTS:
- Summary: 2-3 sentences, ~50 words
- Skills: 10-15 items
- Experience: Max 4 roles, 3 bullets each
- Bullets: 1-2 lines each, start with action verb
- Total resume must fit on ONE PAGE
"""
        
        input_content.append({
            "type": "input_text",
            "text": prompt,
        })
        
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[{"role": "user", "content": input_content}],
                text_format=TailoredResume,
            )
            
            result = response.output_parsed
            logger.info(f"Tailored resume: {len(result.skills)} skills, "
                       f"{len(result.experience)} experiences, "
                       f"{len(result.edit_log)} edits")
            return result
            
        except Exception as e:
            logger.error(f"Error tailoring resume with VLM: {str(e)}")
            # Return basic tailored resume from existing data
            return self._fallback_tailor(resume_data)
    
    def _format_resume_for_prompt(self, resume_data: dict, personal_info: dict) -> str:
        """Format resume data as readable text for the prompt."""
        parts = []
        
        # Name
        if personal_info.get("name"):
            parts.append(f"Name: {personal_info['name']}")
        
        # Summary
        if resume_data.get("summary"):
            parts.append(f"\nSummary:\n{resume_data['summary']}")
        
        # Skills
        skills = resume_data.get("skills", [])
        if skills:
            if isinstance(skills, list):
                parts.append(f"\nSkills: {', '.join(skills[:20])}")
            elif isinstance(skills, dict):
                all_skills = []
                for cat_skills in skills.values():
                    if isinstance(cat_skills, list):
                        all_skills.extend(cat_skills)
                parts.append(f"\nSkills: {', '.join(all_skills[:20])}")
        
        # Experience
        experience = resume_data.get("experience", [])
        if experience:
            parts.append("\nExperience:")
            for exp in experience[:5]:
                title = exp.get("title", "")
                company = exp.get("company", "")
                dates = f"{exp.get('start_date', '')} - {exp.get('end_date', '')}"
                parts.append(f"  - {title} at {company} ({dates})")
                
                # Include description or bullet points
                if exp.get("bullet_points"):
                    for bullet in exp["bullet_points"][:4]:
                        parts.append(f"    * {bullet}")
                elif exp.get("description"):
                    parts.append(f"    {exp['description'][:200]}")
        
        # Education
        education = resume_data.get("education", [])
        if education:
            parts.append("\nEducation:")
            for edu in education[:3]:
                degree = edu.get("degree", "")
                institution = edu.get("institution", "")
                date = edu.get("graduation_date", "")
                parts.append(f"  - {degree} from {institution} ({date})")
        
        return "\n".join(parts)
    
    def _fallback_tailor(self, resume_data: dict) -> TailoredResume:
        """Create a basic tailored resume from existing data when VLM fails."""
        experience = []
        for exp in resume_data.get("experience", [])[:4]:
            bullets = exp.get("bullet_points", [])
            if not bullets and exp.get("description"):
                # Split description into bullets
                desc = exp["description"]
                bullets = [s.strip() for s in desc.split(".") if len(s.strip()) > 10][:3]
            
            experience.append(TailoredExperience(
                title=exp.get("title", ""),
                company=exp.get("company", ""),
                location=exp.get("location", ""),
                start_date=exp.get("start_date", ""),
                end_date=exp.get("end_date", ""),
                bullet_points=bullets[:3],
            ))
        
        education = []
        for edu in resume_data.get("education", [])[:2]:
            education.append(TailoredEducation(
                degree=edu.get("degree", ""),
                institution=edu.get("institution", ""),
                graduation_date=edu.get("graduation_date", ""),
            ))
        
        skills = resume_data.get("skills", [])
        if isinstance(skills, dict):
            flat_skills = []
            for cat_skills in skills.values():
                if isinstance(cat_skills, list):
                    flat_skills.extend(cat_skills)
            skills = flat_skills
        
        return TailoredResume(
            summary=resume_data.get("summary", ""),
            skills=skills[:15] if isinstance(skills, list) else [],
            experience=experience,
            education=education,
            edit_log=["Fallback: Used existing data without optimization"],
        )


# Module-level instance for convenience
resume_rewriter = ResumeRewriterVLM()
