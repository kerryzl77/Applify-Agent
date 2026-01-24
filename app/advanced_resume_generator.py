"""
DEPRECATED: Advanced Resume Generation System
==============================================

This module is deprecated and replaced by the 2-tier VLM pipeline:
- resume_extractor_pymupdf.py (Tier 1: layout extraction)
- resume_rewriter_vlm.py (Tier 2: GPT-5.2 VLM structured outputs)
- one_page_fitter.py (deterministic one-page fitting)
- fast_pdf_generator.py (PDF generation)

The new pipeline is simpler (1-2 LLM calls vs 5), more reliable
(structured outputs instead of regex JSON parsing), and faster.

This file is kept for backwards compatibility but should not be used
for new development. It will be removed in a future release.

Original description:
Multi-Agent LLM-Powered Resume Optimization (2025)
Implements Google-level engineering standards for ATS-optimized, 
job-specific resume generation using 5 specialized AI agents.
"""

import os
import json
import time
import warnings


def _deprecation_warning():
    warnings.warn(
        "AdvancedResumeGenerator is deprecated. Use resume_rewriter_vlm.py with one_page_fitter.py instead.",
        DeprecationWarning,
        stacklevel=3
    )
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from openai import OpenAI
import re
from datetime import datetime

from app.utils.text import normalize_text

@dataclass
class ResumeMetrics:
    """Advanced metrics for resume optimization."""
    ats_score: int = 0
    keyword_match_score: int = 0
    content_quality_score: int = 0
    format_compliance_score: int = 0
    job_relevance_score: int = 0
    estimated_word_count: int = 0
    one_page_compliance: bool = False
    improvement_areas: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)

@dataclass
class JobAnalysis:
    """Comprehensive job analysis results."""
    job_title: str = ""
    industry: str = ""
    company_size: str = ""
    seniority_level: str = ""
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    technical_keywords: List[str] = field(default_factory=list)
    qualifications: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    company_values: List[str] = field(default_factory=list)
    salary_range: str = ""
    location_type: str = ""
    urgency_indicators: List[str] = field(default_factory=list)
    growth_opportunities: List[str] = field(default_factory=list)


class AdvancedResumeGenerator:
    """
    Enterprise-grade resume generation system using 5 specialized AI agents.
    
    Agent Architecture:
    1. Job Intelligence Agent - Deep job description analysis
    2. Resume Analysis Agent - Comprehensive resume evaluation
    3. Content Optimization Agent - Generate tailored content
    4. ATS Compliance Agent - Ensure ATS compatibility
    5. Quality Assurance Agent - Final review and optimization
    """
    
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-5.2"
        self.temperature = 0.3
        
        # Performance tracking
        self.generation_start_time = None
        self.agent_timings = {}
        
        # ATS 2025 Standards
        self.ats_standards = {
            'max_word_count': 600,
            'required_sections': ['summary', 'experience', 'skills', 'education'],
            'optimal_keyword_density': {'min': 65, 'max': 85},
            'font_standards': ['Arial', 'Calibri', 'Times New Roman'],
            'max_bullets_per_job': 3,
            'max_experience_entries': 4,
            'summary_word_range': (40, 80),
            'skills_categories': ['Technical Skills', 'Tools & Technologies', 'Soft Skills']
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def generate_optimized_resume(self, candidate_data: Dict, job_description: str, 
                                 progress_callback=None) -> Tuple[Dict, ResumeMetrics]:
        """
        Generate ATS-optimized, job-tailored resume using 5 AI agents.
        
        Returns:
            Tuple[optimized_resume_data, performance_metrics]
        """
        self.generation_start_time = time.time()
        job_description = normalize_text(job_description)
        
        try:
            # Agent 1: Job Intelligence Analysis
            if progress_callback:
                progress_callback("job_analysis", 15, "🧠 AI Agent 1: Analyzing job requirements...")
            
            job_analysis = self._job_intelligence_agent(job_description)
            
            # Agent 2: Resume Analysis
            if progress_callback:
                progress_callback("resume_analysis", 30, "📊 AI Agent 2: Evaluating current resume...")
            
            resume_analysis = self._resume_analysis_agent(candidate_data, job_analysis)
            
            # Agent 3: Content Optimization
            if progress_callback:
                progress_callback("content_optimization", 50, "✨ AI Agent 3: Generating optimized content...")
            
            optimized_content = self._content_optimization_agent(
                candidate_data, job_analysis, resume_analysis
            )
            
            # Agent 4: ATS Compliance Check
            if progress_callback:
                progress_callback("ats_optimization", 75, "🎯 AI Agent 4: Ensuring ATS compatibility...")
            
            ats_optimized_content = self._ats_compliance_agent(
                optimized_content, job_analysis
            )
            
            # Agent 5: Quality Assurance
            if progress_callback:
                progress_callback("quality_assurance", 90, "🔍 AI Agent 5: Final quality review...")
            
            final_resume, metrics = self._quality_assurance_agent(
                ats_optimized_content, job_analysis, candidate_data
            )
            
            # Calculate final metrics
            total_time = time.time() - self.generation_start_time
            self.logger.info(f"✅ Resume generation completed in {total_time:.2f}s")
            
            metrics.ats_score = self._calculate_final_ats_score(final_resume, job_analysis)
            
            return final_resume, metrics
            
        except Exception as e:
            self.logger.error(f"Resume generation failed: {str(e)}")
            raise
    
    def _job_intelligence_agent(self, job_description: str) -> JobAnalysis:
        """Agent 1: Deep job description analysis with industry intelligence."""
        start_time = time.time()
        
        prompt = f"""
        You are a Senior Job Market Intelligence Analyst with expertise in ATS systems and hiring trends.
        
        Analyze this job description with Google-level precision and extract comprehensive intelligence:
        
        Job Description:
        {job_description}
        
        Provide a detailed JSON analysis with these fields:
        {{
            "job_title": "Exact job title",
            "industry": "Specific industry/sector",
            "company_size": "startup/small/medium/large/enterprise",
            "seniority_level": "entry/mid/senior/executive",
            "required_skills": ["skill1", "skill2", ...],
            "preferred_skills": ["skill1", "skill2", ...],
            "technical_keywords": ["keyword1", "keyword2", ...],
            "qualifications": ["qualification1", "qualification2", ...],
            "responsibilities": ["responsibility1", "responsibility2", ...],
            "company_values": ["value1", "value2", ...],
            "salary_range": "estimated range if mentioned",
            "location_type": "remote/hybrid/onsite",
            "urgency_indicators": ["urgent", "immediate", "asap", ...],
            "growth_opportunities": ["opportunity1", "opportunity2", ...]
        }}
        
        Focus on:
        - Exact keyword extraction for ATS optimization
        - Hidden requirements between the lines
        - Company culture signals
        - Growth trajectory indicators
        - Technical depth requirements
        
        Return ONLY valid JSON.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an elite job market intelligence analyst. Extract precise, ATS-optimized job insights. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                timeout=45
            )
            
            analysis_data = self._parse_json_response(response.choices[0].message.content)
            
            # Convert to JobAnalysis dataclass
            job_analysis = JobAnalysis(**analysis_data)
            
            self.agent_timings['job_intelligence'] = time.time() - start_time
            self.logger.info(f"🧠 Job Intelligence Analysis: {job_analysis.job_title} ({job_analysis.seniority_level} level)")
            
            return job_analysis
            
        except Exception as e:
            self.logger.error(f"Job Intelligence Agent failed: {str(e)}")
            # Return fallback analysis
            return JobAnalysis(
                job_title="Professional Role",
                industry="Technology",
                seniority_level="mid",
                required_skills=["Professional Skills"],
                technical_keywords=["Technology", "Leadership"]
            )
    
    def _resume_analysis_agent(self, candidate_data: Dict, job_analysis: JobAnalysis) -> Dict:
        """Agent 2: Comprehensive resume analysis with gap identification."""
        start_time = time.time()
        
        resume_data = candidate_data.get('resume', {})
        
        prompt = f"""
        You are a Senior Resume Analyst specializing in ATS optimization and job matching.
        
        Analyze this resume against the target job with forensic precision:
        
        Target Job Analysis:
        {json.dumps(job_analysis.__dict__, indent=2)}
        
        Current Resume Data:
        {json.dumps(resume_data, indent=2)}
        
        Provide comprehensive analysis in JSON format:
        {{
            "current_strengths": ["strength1", "strength2", ...],
            "critical_gaps": ["gap1", "gap2", ...],
            "keyword_gaps": ["missing_keyword1", "missing_keyword2", ...],
            "experience_relevance": "high/medium/low",
            "skills_alignment": "excellent/good/poor",
            "achievements_quality": "quantified/descriptive/weak",
            "content_optimization_needs": {{
                "summary": "needs_rewrite/needs_improvement/good",
                "experience": "major_revision/minor_revision/good",
                "skills": "complete_overhaul/reorganization/good",
                "education": "enhancement/good/irrelevant"
            }},
            "ats_risk_factors": ["factor1", "factor2", ...],
            "competitive_advantages": ["advantage1", "advantage2", ...],
            "improvement_priority": ["highest_priority", "medium_priority", "low_priority"],
            "estimated_job_match_score": 85,
            "content_gaps": {{
                "missing_technical_skills": ["skill1", "skill2"],
                "missing_achievements": ["type1", "type2"],
                "missing_keywords": ["keyword1", "keyword2"]
            }}
        }}
        
        Analysis Focus:
        - ATS keyword matching precision
        - Content quality and quantification
        - Competitive positioning
        - Gap analysis for job requirements
        - Achievement impact assessment
        
        Return ONLY valid JSON.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an elite resume analyst. Provide precise, actionable insights for ATS optimization. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                timeout=45
            )
            
            analysis = self._parse_json_response(response.choices[0].message.content)
            
            self.agent_timings['resume_analysis'] = time.time() - start_time
            self.logger.info(f"📊 Resume Analysis: {analysis.get('estimated_job_match_score', 0)}/100 match score")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Resume Analysis Agent failed: {str(e)}")
            return {
                "current_strengths": [],
                "critical_gaps": [],
                "estimated_job_match_score": 70,
                "experience_relevance": "medium"
            }
    
    def _content_optimization_agent(self, candidate_data: Dict, job_analysis: JobAnalysis, 
                                   resume_analysis: Dict) -> Dict:
        """Agent 3: Generate optimized content for each resume section."""
        start_time = time.time()
        
        # Generate each section with specialized prompts
        sections = {}
        
        # Professional Summary
        sections['professional_summary'] = self._generate_optimized_summary(
            candidate_data, job_analysis, resume_analysis
        )
        
        # Skills Section
        sections['skills'] = self._generate_optimized_skills(
            candidate_data, job_analysis, resume_analysis
        )
        
        # Experience Section
        sections['experience'] = self._generate_optimized_experience(
            candidate_data, job_analysis, resume_analysis
        )
        
        # Education Section
        sections['education'] = self._generate_optimized_education(
            candidate_data, job_analysis
        )
        
        self.agent_timings['content_optimization'] = time.time() - start_time
        self.logger.info("✨ Content Optimization: All sections generated")
        
        return {
            'sections': sections,
            'optimization_metadata': {
                'job_title': job_analysis.job_title,
                'target_keywords': job_analysis.technical_keywords[:10],
                'optimization_focus': resume_analysis.get('improvement_priority', []),
                'job_summary': self._build_job_summary(job_analysis),
                'generation_timestamp': datetime.now().isoformat()
            }
        }
    
    def _build_job_summary(self, job_analysis: JobAnalysis) -> str:
        """Create concise job summary text for downstream prompts."""
        parts = []
        if job_analysis.job_title:
            title = job_analysis.job_title
            if job_analysis.seniority_level:
                title += f" ({job_analysis.seniority_level} level)"
            parts.append(f"Role: {title}")
        if job_analysis.industry:
            parts.append(f"Industry: {job_analysis.industry}")
        if job_analysis.location_type:
            parts.append(f"Location: {job_analysis.location_type}")
        if job_analysis.required_skills:
            parts.append("Must-have skills: " + ", ".join(job_analysis.required_skills[:5]))
        if job_analysis.responsibilities:
            parts.append("Top responsibilities: " + ", ".join(job_analysis.responsibilities[:3]))
        if job_analysis.company_values:
            parts.append("Company values: " + ", ".join(job_analysis.company_values[:2]))
        return " | ".join(parts)

    def _generate_optimized_summary(self, candidate_data: Dict, job_analysis: JobAnalysis, 
                                  resume_analysis: Dict) -> str:
        """Generate ATS-optimized professional summary."""
        resume_data = candidate_data.get('resume', {})
        
        prompt = f"""
        You are a Senior Resume Writer specializing in ATS-optimized professional summaries.
        
        Create a compelling 2 sentence (maximum 25 words) professional summary that:
        
        Target Job: {job_analysis.job_title} ({job_analysis.seniority_level} level)
        Industry: {job_analysis.industry}
        Required Skills: {', '.join(job_analysis.required_skills[:5])}
        Key Keywords: {', '.join(job_analysis.technical_keywords[:8])}
        
        Current Experience: {json.dumps(resume_data.get('experience', [])[:2], indent=2)}
        Current Skills: {', '.join(resume_data.get('skills', [])[:10])}
        
        Requirements:
        - Include exact job title "{job_analysis.job_title}" naturally
        - Integrate 4-5 top keywords: {', '.join(job_analysis.technical_keywords[:5])}
        - Mention years of experience if relevant
        - Highlight 2-3 key achievements/value propositions
        - 40-60 words total (ATS optimal length)
        - Professional, confident tone
        - Quantify impact where possible
        
        Return ONLY the professional summary text, no additional formatting or explanation.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a world-class resume writer. Create ATS-optimized professional summaries that get results."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                timeout=30
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Summary generation failed: {str(e)}")
            return f"Experienced {job_analysis.job_title} with expertise in {', '.join(job_analysis.required_skills[:3])}. Proven track record of delivering results and driving organizational success."
    
    def _generate_optimized_skills(self, candidate_data: Dict, job_analysis: JobAnalysis, 
                                 resume_analysis: Dict) -> Dict:
        """Generate ATS-optimized skills section."""
        current_skills = candidate_data.get('resume', {}).get('skills', [])
        
        prompt = f"""
        You are a Skills Optimization Specialist for ATS systems.
        
        Optimize the skills section for maximum ATS impact:
        
        Target Job Requirements:
        - Required Skills: {', '.join(job_analysis.required_skills)}
        - Preferred Skills: {', '.join(job_analysis.preferred_skills)}
        - Technical Keywords: {', '.join(job_analysis.technical_keywords)}
        
        Current Skills: {', '.join(current_skills)}
        
        Create optimized skills categories in JSON format:
        {{
            "technical_skills": ["skill1", "skill2", ...],
            "tools_technologies": ["tool1", "tool2", ...],
            "certifications": ["cert1", "cert2", ...]
        }}
        
        Rules:
        - Prioritize exact keyword matches from job requirements
        - Include variations of key skills (e.g., "Python", "Python Programming")
        - Maximum 8 skills per category
        - Use exact terminology from job description
        - Include industry-standard tools/technologies
        
        Return ONLY valid JSON.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert in ATS skills optimization. Create perfectly categorized, keyword-rich skills sections."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                timeout=30
            )
            
            return self._parse_json_response(response.choices[0].message.content)
            
        except Exception as e:
            self.logger.error(f"Skills generation failed: {str(e)}")
            return {
                "technical_skills": current_skills[:8],
                "tools_technologies": [],
                "certifications": []
            }
    
    def _generate_optimized_experience(self, candidate_data: Dict, job_analysis: JobAnalysis, 
                                     resume_analysis: Dict) -> List[Dict]:
        """Generate ATS-optimized experience section."""
        current_experience = candidate_data.get('resume', {}).get('experience', [])
        
        optimized_experience = []
        
        job_summary = self._build_job_summary(job_analysis)

        for i, exp in enumerate(current_experience[:4]):  # Max 4 experiences for one page
            required_bullets = 3 if i < 2 else 2 if i == 2 else 1
            prompt = f"""
            You are a Senior Career Strategist specializing in achievement-focused job descriptions.
            
            Optimize this work experience for the target role:
            
            Job Summary: {job_summary}
            
            Target Job: {job_analysis.job_title}
            Key Keywords: {', '.join(job_analysis.technical_keywords[:10])}
            Required Skills: {', '.join(job_analysis.required_skills[:8])}
            Responsibilities: {', '.join(job_analysis.responsibilities[:5])}
            
            Current Experience Entry:
            {json.dumps(exp, indent=2)}
            
            Create optimized experience entry in JSON format:
            {{
                "company": "{exp.get('company', 'Company')}",
                "title": "{exp.get('title', 'Position')}",
                "start_date": "{exp.get('start_date', '')}",
                "end_date": "{exp.get('end_date', 'Present')}",
                "location": "{exp.get('location', '')}",
                "bullet_points": [
                    "• Achievement 1 with quantified results",
                    "• Achievement 2 with impact metrics",
                    "• Achievement 3 with keyword integration"
                ]
            }}
            
            Rules for bullet points:
            - Start with strong action verbs (Led, Developed, Implemented, Achieved)
            - Include quantified results (percentages, numbers, metrics)
            - Integrate 2-3 keywords from target job naturally
            - Maximum 3 bullet points per position
            - Focus on achievements, not just responsibilities
            - Use past tense for previous roles, present for current
            - Each bullet: 1-2 lines maximum
            - EXACTLY {required_bullets} bullet points are required for this entry
            
            Return ONLY valid JSON.
            """
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert in writing achievement-focused job descriptions. Create compelling experience entries with quantified results."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    timeout=30
                )
                
                optimized_exp = self._parse_json_response(response.choices[0].message.content)
                optimized_experience.append(optimized_exp)
                
            except Exception as e:
                self.logger.error(f"Experience optimization failed for entry {i}: {str(e)}")
                # Keep original if optimization fails
                optimized_experience.append(exp)
        
        return optimized_experience
    
    def _generate_optimized_education(self, candidate_data: Dict, job_analysis: JobAnalysis) -> List[Dict]:
        """Generate optimized education section."""
        education_data = candidate_data.get('resume', {}).get('education', [])
        
        # For education, minimal optimization needed - just clean formatting
        optimized_education = []
        for edu in education_data[:2]:  # Max 2 education entries
            optimized_edu = {
                'institution': edu.get('institution', ''),
                'degree': edu.get('degree', ''),
                'field': edu.get('field', ''),
                'graduation_year': edu.get('graduation_year', ''),
                'gpa': edu.get('gpa', '') if float(edu.get('gpa', 0)) >= 3.5 else '',
                'relevant_coursework': edu.get('relevant_coursework', [])
            }
            optimized_education.append(optimized_edu)
        
        return optimized_education
    
    def _ats_compliance_agent(self, optimized_content: Dict, job_analysis: JobAnalysis) -> Dict:
        """Agent 4: Ensure ATS compliance and keyword optimization."""
        start_time = time.time()
        
        # Analyze keyword density
        content_text = self._extract_text_from_content(optimized_content)
        keyword_analysis = self._analyze_keyword_density(content_text, job_analysis)
        
        # Apply ATS compliance rules
        ats_compliant_content = self._apply_ats_standards(optimized_content, keyword_analysis)
        
        self.agent_timings['ats_compliance'] = time.time() - start_time
        self.logger.info(f"🎯 ATS Compliance: {keyword_analysis['match_score']}/100 keyword match")
        
        return {
            'content': ats_compliant_content,
            'ats_analysis': keyword_analysis,
            'compliance_score': self._calculate_compliance_score(ats_compliant_content)
        }
    
    def _quality_assurance_agent(self, ats_content: Dict, job_analysis: JobAnalysis, 
                               candidate_data: Dict) -> Tuple[Dict, ResumeMetrics]:
        """Agent 5: Final quality review and metrics calculation."""
        start_time = time.time()
        
        final_content = ats_content['content']
        
        # Calculate comprehensive metrics
        metrics = ResumeMetrics()
        metrics.ats_score = ats_content['compliance_score']
        metrics.keyword_match_score = ats_content['ats_analysis']['match_score']
        
        # Word count analysis
        total_text = self._extract_text_from_content(final_content)
        word_count = len(total_text.split())
        metrics.estimated_word_count = word_count
        metrics.one_page_compliance = word_count <= self.ats_standards['max_word_count']
        
        # Content quality analysis
        metrics.content_quality_score = self._analyze_content_quality(final_content)
        metrics.format_compliance_score = self._analyze_format_compliance(final_content)
        
        # Job relevance analysis
        metrics.job_relevance_score = self._calculate_job_relevance(
            final_content, job_analysis
        )
        
        # Generate improvement recommendations
        metrics.improvement_areas = self._generate_improvement_areas(
            final_content, ats_content['ats_analysis']
        )
        
        metrics.strengths = self._identify_strengths(final_content, job_analysis)
        
        self.agent_timings['quality_assurance'] = time.time() - start_time
        self.logger.info(f"🔍 Quality Assurance: {metrics.content_quality_score}/100 quality score")
        
        # Prepare final resume structure
        final_resume = {
            'sections': final_content['sections'],
            'metadata': {
                'generation_time': time.time() - self.generation_start_time,
                'agent_timings': self.agent_timings,
                'target_job': job_analysis.job_title,
                'optimization_level': 'advanced',
                'ats_version': '2025'
            },
            'formatting_rules': self.ats_standards
        }
        
        return final_resume, metrics
    
    def _extract_text_from_content(self, content: Dict) -> str:
        """Extract all text content for analysis."""
        text_parts = []
        
        sections = content.get('sections', {})
        
        # Professional summary
        if sections.get('professional_summary'):
            text_parts.append(sections['professional_summary'])
        
        # Skills
        skills = sections.get('skills', {})
        for category, skill_list in skills.items():
            if isinstance(skill_list, list):
                text_parts.extend(skill_list)
        
        # Experience
        experiences = sections.get('experience', [])
        for exp in experiences:
            if exp.get('title'):
                text_parts.append(exp['title'])
            if exp.get('company'):
                text_parts.append(exp['company'])
            for bullet in exp.get('bullet_points', []):
                text_parts.append(bullet)
        
        # Education
        educations = sections.get('education', [])
        for edu in educations:
            for field in ['degree', 'institution', 'field']:
                if edu.get(field):
                    text_parts.append(edu[field])
        
        return ' '.join(text_parts)
    
    def _analyze_keyword_density(self, content_text: str, job_analysis: JobAnalysis) -> Dict:
        """Analyze keyword density for ATS optimization."""
        content_lower = content_text.lower()
        
        # Check required keywords
        required_keywords = job_analysis.required_skills + job_analysis.technical_keywords
        keyword_matches = []
        
        for keyword in required_keywords:
            if keyword.lower() in content_lower:
                keyword_matches.append(keyword)
        
        match_score = min(100, int((len(keyword_matches) / max(len(required_keywords), 1)) * 100))
        
        return {
            'total_keywords': len(required_keywords),
            'matched_keywords': keyword_matches,
            'match_count': len(keyword_matches),
            'match_score': match_score,
            'missing_keywords': [k for k in required_keywords if k.lower() not in content_lower],
            'keyword_density': len(keyword_matches) / max(len(content_text.split()), 1) * 100
        }
    
    def _apply_ats_standards(self, content: Dict, keyword_analysis: Dict) -> Dict:
        """Apply 2025 ATS standards to content."""
        # Ensure one-page compliance
        sections = content.get('sections', {})
        
        # Limit experience entries
        if 'experience' in sections:
            sections['experience'] = sections['experience'][:4]
            
            # Limit bullet points per job
            for exp in sections['experience']:
                if 'bullet_points' in exp:
                    exp['bullet_points'] = exp['bullet_points'][:3]
        
        # Optimize skills categories
        if 'skills' in sections:
            skills = sections['skills']
            for category in skills:
                if isinstance(skills[category], list):
                    skills[category] = skills[category][:8]
        
        return {'sections': sections}
    
    def _calculate_compliance_score(self, content: Dict) -> int:
        """Calculate ATS compliance score."""
        score = 100
        sections = content.get('sections', {})
        
        # Check required sections
        required_sections = ['professional_summary', 'experience', 'skills', 'education']
        missing_sections = [s for s in required_sections if s not in sections]
        score -= len(missing_sections) * 20
        
        # Check content quality
        if sections.get('professional_summary'):
            summary_words = len(sections['professional_summary'].split())
            if not (40 <= summary_words <= 80):
                score -= 10
        
        # Check experience formatting
        experiences = sections.get('experience', [])
        if len(experiences) > 4:
            score -= 5
        
        for exp in experiences:
            bullets = exp.get('bullet_points', [])
            if len(bullets) > 3:
                score -= 5
        
        return max(0, score)
    
    def _analyze_content_quality(self, content: Dict) -> int:
        """Analyze content quality score."""
        score = 80  # Base score
        
        sections = content.get('sections', {})
        
        # Check for quantified achievements
        experiences = sections.get('experience', [])
        quantified_count = 0
        
        for exp in experiences:
            for bullet in exp.get('bullet_points', []):
                if re.search(r'\d+[%$]?|\b\d+\b', bullet):
                    quantified_count += 1
        
        score += min(20, quantified_count * 5)
        
        return min(100, score)
    
    def _analyze_format_compliance(self, content: Dict) -> int:
        """Analyze format compliance with 2025 standards."""
        score = 100
        
        # Check structure compliance
        sections = content.get('sections', {})
        
        # Verify all required sections exist
        required = ['professional_summary', 'skills', 'experience', 'education']
        for section in required:
            if section not in sections:
                score -= 25
        
        return max(0, score)
    
    def _calculate_job_relevance(self, content: Dict, job_analysis: JobAnalysis) -> int:
        """Calculate job relevance score."""
        content_text = self._extract_text_from_content(content)
        
        # Count relevant keywords
        relevant_keywords = (
            job_analysis.required_skills + 
            job_analysis.technical_keywords + 
            job_analysis.responsibilities
        )
        
        relevance_count = 0
        for keyword in relevant_keywords:
            if keyword.lower() in content_text.lower():
                relevance_count += 1
        
        return min(100, int((relevance_count / max(len(relevant_keywords), 1)) * 100))
    
    def _generate_improvement_areas(self, content: Dict, ats_analysis: Dict) -> List[str]:
        """Generate specific improvement recommendations."""
        improvements = []
        
        if ats_analysis['match_score'] < 75:
            improvements.append(f"Add missing keywords: {', '.join(ats_analysis['missing_keywords'][:3])}")
        
        if len(ats_analysis['missing_keywords']) > 5:
            improvements.append("Increase keyword density for better ATS matching")
        
        # Check word count
        total_text = self._extract_text_from_content(content)
        word_count = len(total_text.split())
        
        if word_count > 600:
            improvements.append("Reduce content length for one-page compliance")
        
        return improvements[:5]  # Top 5 improvements
    
    def _identify_strengths(self, content: Dict, job_analysis: JobAnalysis) -> List[str]:
        """Identify resume strengths."""
        strengths = []
        
        sections = content.get('sections', {})
        
        # Check for quantified achievements
        experiences = sections.get('experience', [])
        for exp in experiences:
            for bullet in exp.get('bullet_points', []):
                if re.search(r'\d+[%$]?', bullet):
                    strengths.append("Contains quantified achievements")
                    break
        
        # Check keyword integration
        content_text = self._extract_text_from_content(content)
        matched_skills = 0
        for skill in job_analysis.required_skills:
            if skill.lower() in content_text.lower():
                matched_skills += 1
        
        if matched_skills >= 5:
            strengths.append("Strong keyword alignment with job requirements")
        
        return list(set(strengths))  # Remove duplicates
    
    def _calculate_final_ats_score(self, resume: Dict, job_analysis: JobAnalysis) -> int:
        """Calculate final comprehensive ATS score."""
        content_text = self._extract_text_from_content(resume)
        
        # Keyword matching (40% weight)
        keyword_score = self._analyze_keyword_density(content_text, job_analysis)['match_score']
        
        # Format compliance (20% weight)
        format_score = self._analyze_format_compliance(resume)
        
        # Content quality (20% weight)
        content_score = self._analyze_content_quality(resume)
        
        # Job relevance (20% weight)
        relevance_score = self._calculate_job_relevance(resume, job_analysis)
        
        final_score = int(
            keyword_score * 0.4 + 
            format_score * 0.2 + 
            content_score * 0.2 + 
            relevance_score * 0.2
        )
        
        return min(100, final_score)
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """Safely parse JSON response from LLM."""
        try:
            # Clean markdown code blocks
            cleaned = response_text.strip()
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {str(e)}")
            return {}

