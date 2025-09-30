import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMGenerator:
    def __init__(self):
        # Initialize OpenAI client with API key from environment variable
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def generate_linkedin_message(self, job_data, candidate_data, profile_data=None):
        """Generate a LinkedIn connection message (200 characters max)."""
        prompt = self._build_linkedin_message_prompt(job_data, candidate_data, profile_data)
        return self._generate_text(prompt, max_tokens=100)  # ~200 characters
    
    def generate_connection_email(self, job_data, candidate_data, profile_data=None):
        """Generate a connection email (200 words max)."""
        prompt = self._build_connection_email_prompt(job_data, candidate_data, profile_data)
        return self._generate_text(prompt, max_tokens=300)  # ~200 words
    
    def generate_hiring_manager_email(self, job_data, candidate_data):
        """Generate an email to a hiring manager (200 words max)."""
        prompt = self._build_hiring_manager_email_prompt(job_data, candidate_data)
        return self._generate_text(prompt, max_tokens=300)  # ~200 words
    
    def generate_cover_letter(self, job_data, candidate_data):
        """Generate a cover letter (350 words max)."""
        prompt = self._build_cover_letter_prompt(job_data, candidate_data)
        return self._generate_text(prompt, max_tokens=500)  # ~350 words
    
    def _generate_text(self, prompt, max_tokens=300):
        """Call the OpenAI API to generate text."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4o (latest stable model)
                messages=[
                    {"role": "system", "content": "You are an expert professional writer and career advisor with deep understanding of modern job markets, hiring practices, and effective communication strategies. You create highly personalized, impactful application materials that resonate with hiring managers and decision makers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.6  # Slightly lower for more consistency while maintaining creativity
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating text: {str(e)}"
    
    def _build_linkedin_message_prompt(self, job_data, candidate_data, profile_data=None):
        """Build prompt for LinkedIn connection message."""
        # Extract relevant data
        job_title = job_data.get('job_title', 'the position')
        job_description = job_data.get('job_description', '')
        company_name = job_data.get('company_name', 'the company')
        
        recipient_name = profile_data.get('name', 'there') if profile_data else 'there'
        recipient_title = profile_data.get('title', '') if profile_data else ''
        recipient_company = profile_data.get('company', '') if profile_data else ''
        recipient_about = profile_data.get('about', '') if profile_data else ''
        recipient_experience = profile_data.get('experience', []) if profile_data else []
        
        candidate_name = candidate_data['personal_info']['name']
        candidate_summary = candidate_data['resume'].get('summary', 'Professional seeking new opportunities')
        candidate_skills = candidate_data['resume']['skills'][:5]
        candidate_experience = candidate_data['resume']['experience'][:2]
        
        # Find connection points
        connection_points = []
        if profile_data:
            # Common skills
            recipient_skills = set(profile_data.get('skills', []))
            common_skills = set(candidate_skills) & recipient_skills
            if common_skills:
                connection_points.append(f"shared expertise in {list(common_skills)[0]}")
            
            # Industry/role relevance
            if any(skill.lower() in recipient_title.lower() for skill in candidate_skills):
                connection_points.append(f"relevant {job_title} background")
        
        return f"""
        CONTEXT: Write a LinkedIn connection message for {candidate_name} reaching out to {recipient_name} about the {job_title} role at {company_name}.

        RECIPIENT PROFILE:
        - Name: {recipient_name}
        - Current Role: {recipient_title} at {recipient_company}
        - Background: {recipient_about[:200] if recipient_about else 'Industry professional'}
        
        CANDIDATE PROFILE:
        - Name: {candidate_name}
        - Current Summary: {candidate_summary}
        - Relevant Skills: {', '.join(candidate_skills)}
        - Recent Experience: {candidate_experience[0]['title'] + ' at ' + candidate_experience[0]['company'] if candidate_experience else 'Professional experience'}
        
        JOB CONTEXT:
        - Position: {job_title} at {company_name}
        - Key Requirements: {job_description[:300]}...
        
        CONNECTION POINTS: {', '.join(connection_points) if connection_points else 'Professional interest in the role'}
        
        REQUIREMENTS:
        1. Maximum 200 characters (LinkedIn limit)
        2. Start with "Hi {recipient_name}," 
        3. Mention specific interest in the {job_title} role
        4. Reference one relevant skill/experience that matches the job
        5. Professional but warm tone
        6. No closing signature (just the message)
        7. Focus on value proposition for both the role and the recipient
        
        Write ONLY the connection message content:
        """
    
    def _build_connection_email_prompt(self, job_data, candidate_data, profile_data=None):
        """Build prompt for connection email."""
        # Extract relevant data
        job_title = job_data.get('job_title', 'the position')
        job_description = job_data.get('job_description', '')
        job_requirements = job_data.get('requirements', '')
        company_name = job_data.get('company_name', 'the company')
        
        recipient_name = profile_data.get('name', '') if profile_data else ''
        recipient_title = profile_data.get('title', '') if profile_data else ''
        recipient_company = profile_data.get('company', '') if profile_data else ''
        recipient_about = profile_data.get('about', '') if profile_data else ''
        recipient_experience = profile_data.get('experience', []) if profile_data else []
        recipient_skills = profile_data.get('skills', []) if profile_data else []
        
        candidate_name = candidate_data['personal_info']['name']
        candidate_email = candidate_data['personal_info']['email']
        candidate_summary = candidate_data['resume'].get('summary', 'Professional seeking new opportunities')
        candidate_skills = candidate_data['resume']['skills']
        candidate_experience = candidate_data['resume']['experience'][:3]
        
        # Advanced connection analysis
        connection_insights = []
        if profile_data:
            # Skills overlap analysis
            common_skills = set(candidate_skills) & set(recipient_skills)
            if common_skills:
                connection_insights.append(f"shared expertise in {', '.join(list(common_skills)[:2])}")
            
            # Role relevance
            relevant_experience = [exp for exp in candidate_experience if any(skill.lower() in exp.get('description', '').lower() for skill in recipient_skills[:3])]
            if relevant_experience:
                connection_insights.append(f"relevant experience in {relevant_experience[0]['title']}")
            
            # Company insights
            if recipient_company and any(exp['company'] == recipient_company for exp in candidate_experience):
                connection_insights.append(f"previous experience at {recipient_company}")
        
        # Job-candidate fit analysis
        job_fit_points = []
        for skill in candidate_skills[:5]:
            if skill.lower() in job_requirements.lower() or skill.lower() in job_description.lower():
                job_fit_points.append(skill)
        
        return f"""
        CONTEXT: Write a professional connection email for {candidate_name} reaching out to {recipient_name} regarding the {job_title} position at {company_name}. This person likely works at the company or has relevant industry insights.

        RECIPIENT ANALYSIS:
        - Name: {recipient_name}
        - Current Role: {recipient_title} at {recipient_company}
        - Professional Background: {recipient_about[:250] if recipient_about else 'Industry professional'}
        - Key Skills: {', '.join(recipient_skills[:5]) if recipient_skills else 'Professional expertise'}
        - Current Experience: {recipient_experience[0]['title'] if recipient_experience else 'Industry professional'}
        
        CANDIDATE PROFILE:
        - Name: {candidate_name}
        - Professional Summary: {candidate_summary}
        - Relevant Skills for this Role: {', '.join(job_fit_points[:3]) if job_fit_points else ', '.join(candidate_skills[:3])}
        - Key Experience: {candidate_experience[0]['title'] + ' at ' + candidate_experience[0]['company'] if candidate_experience else 'Professional experience'}
        - Notable Achievement: {candidate_experience[0].get('description', 'Professional achievements')[:100] if candidate_experience else 'Professional achievements'}
        
        JOB CONTEXT:
        - Position: {job_title} at {company_name}
        - Key Requirements: {job_requirements[:400]}
        - Role Description: {job_description[:400]}
        
        CONNECTION INSIGHTS: {', '.join(connection_insights) if connection_insights else 'Professional interest and relevant background'}
        
        EMAIL REQUIREMENTS:
        1. Subject line: "Re: {job_title} opportunity - {candidate_name}"
        2. Start with "Hi {recipient_name},"
        3. Professional introduction with current role/background
        4. Specific mention of the {job_title} role and why you're reaching out to them specifically
        5. Highlight 2-3 relevant qualifications that match the job requirements
        6. Reference any connection insights to create rapport
        7. Ask for specific advice/insights about the role, team, or company culture
        8. Professional closing with contact information
        9. Maximum 200 words
        10. Tone: Professional, respectful, genuinely interested (not pushy)
        
        Write the complete email including subject line:
        """
    
    def _build_hiring_manager_email_prompt(self, job_data, candidate_data):
        """Build prompt for hiring manager email."""
        # Extract job details
        job_title = job_data.get('job_title', 'the position')
        company_name = job_data.get('company_name', 'the company')
        job_description = job_data.get('job_description', '')
        job_requirements = job_data.get('requirements', '')
        job_location = job_data.get('location', '')
        
        # Extract candidate details
        candidate_name = candidate_data['personal_info']['name']
        candidate_email = candidate_data['personal_info']['email']
        candidate_phone = candidate_data['personal_info'].get('phone', '')
        candidate_summary = candidate_data['resume'].get('summary', 'Professional seeking new opportunities')
        candidate_skills = candidate_data['resume']['skills']
        candidate_experience = candidate_data['resume']['experience'][:3]
        candidate_education = candidate_data['resume']['education'][0] if candidate_data['resume']['education'] else {}
        
        # Analyze job-candidate fit
        matching_skills = []
        for skill in candidate_skills:
            if skill.lower() in job_requirements.lower() or skill.lower() in job_description.lower():
                matching_skills.append(skill)
        
        # Find most relevant experience
        relevant_experience = []
        for exp in candidate_experience:
            relevance_score = 0
            exp_description = exp.get('description', '').lower()
            for skill in matching_skills[:5]:
                if skill.lower() in exp_description:
                    relevance_score += 1
            if relevance_score > 0:
                relevant_experience.append((exp, relevance_score))
        relevant_experience.sort(key=lambda x: x[1], reverse=True)
        
        # Get quantifiable achievements
        achievements = []
        for exp in candidate_experience[:2]:
            desc = exp.get('description', '')
            # Look for numbers/percentages in descriptions
            import re
            numbers = re.findall(r'\d+%|\$\d+|\d+[KMB]|\d+ years?|\d+ projects?|\d+ teams?', desc)
            if numbers:
                achievements.append(f"{exp['title']}: {desc[:100]}...")
        
        return f"""
        CONTEXT: Write a direct email from {candidate_name} to the hiring manager for the {job_title} position at {company_name}. This should demonstrate strong interest and clear value proposition.

        JOB ANALYSIS:
        - Position: {job_title} at {company_name}
        - Location: {job_location}
        - Key Requirements: {job_requirements[:500]}
        - Role Description: {job_description[:500]}
        
        CANDIDATE PROFILE:
        - Name: {candidate_name}
        - Contact: {candidate_email}{', ' + candidate_phone if candidate_phone else ''}
        - Professional Summary: {candidate_summary}
        - Education: {candidate_education.get('degree', '') + ' from ' + candidate_education.get('institution', '') if candidate_education else 'Relevant education'}
        
        RELEVANT QUALIFICATIONS:
        - Matching Skills: {', '.join(matching_skills[:5]) if matching_skills else ', '.join(candidate_skills[:5])}
        - Most Relevant Experience: {relevant_experience[0][0]['title'] + ' at ' + relevant_experience[0][0]['company'] if relevant_experience else candidate_experience[0]['title'] + ' at ' + candidate_experience[0]['company'] if candidate_experience else 'Professional experience'}
        - Key Achievements: {achievements[0] if achievements else 'Professional achievements in relevant areas'}
        
        EMAIL REQUIREMENTS:
        1. Subject line: "Application for {job_title} Position - {candidate_name}"
        2. Professional greeting: "Dear Hiring Manager," or "Dear {company_name} Hiring Team,"
        3. Strong opening paragraph expressing specific interest in the role
        4. Body highlighting 2-3 most relevant qualifications that directly match job requirements
        5. Include specific achievements with quantifiable results where possible
        6. Demonstrate knowledge of the company/role
        7. Clear call to action requesting interview/next steps
        8. Professional closing with full contact information
        9. Maximum 200 words
        10. Tone: Confident, professional, results-oriented
        
        Write the complete email including subject line:
        """
    
    def _build_cover_letter_prompt(self, job_data, candidate_data):
        """Build prompt for cover letter."""
        # Extract comprehensive job details
        job_title = job_data.get('job_title', 'the position')
        company_name = job_data.get('company_name', 'the company')
        job_description = job_data.get('job_description', '')
        job_requirements = job_data.get('requirements', '')
        job_location = job_data.get('location', '')
        
        # Extract comprehensive candidate details
        candidate_name = candidate_data['personal_info']['name']
        candidate_email = candidate_data['personal_info']['email']
        candidate_phone = candidate_data['personal_info'].get('phone', '')
        candidate_summary = candidate_data['resume'].get('summary', 'Professional seeking new opportunities')
        candidate_skills = candidate_data['resume']['skills']
        candidate_experience = candidate_data['resume']['experience'][:4]
        candidate_education = candidate_data['resume']['education'][0] if candidate_data['resume']['education'] else {}
        
        # Advanced job-candidate matching analysis
        matching_skills = []
        priority_skills = []
        for skill in candidate_skills:
            if skill.lower() in job_requirements.lower():
                priority_skills.append(skill)
            elif skill.lower() in job_description.lower():
                matching_skills.append(skill)
        
        # Analyze experience relevance with scoring
        experience_analysis = []
        for exp in candidate_experience:
            relevance_score = 0
            exp_description = exp.get('description', '').lower()
            
            # Score based on skill matches
            for skill in priority_skills + matching_skills:
                if skill.lower() in exp_description:
                    relevance_score += 2 if skill in priority_skills else 1
            
            # Score based on job title/company relevance
            if job_title.lower() in exp['title'].lower():
                relevance_score += 3
            
            experience_analysis.append((exp, relevance_score))
        
        experience_analysis.sort(key=lambda x: x[1], reverse=True)
        top_experiences = [exp[0] for exp in experience_analysis[:3]]
        
        # Extract quantifiable achievements
        achievements = []
        for exp in top_experiences:
            desc = exp.get('description', '')
            # Enhanced pattern matching for achievements
            import re
            achievement_patterns = [
                r'\d+%', r'\$\d+[\dKMB]*', r'\d+[KMB]', r'\d+ years?', 
                r'\d+ projects?', r'\d+ teams?', r'\d+ clients?', r'\d+ users?',
                r'increased.*\d+', r'reduced.*\d+', r'improved.*\d+', r'led.*\d+'
            ]
            
            for pattern in achievement_patterns:
                matches = re.findall(pattern, desc, re.IGNORECASE)
                if matches:
                    # Extract sentence containing the achievement
                    sentences = desc.split('.')
                    for sentence in sentences:
                        if any(match in sentence for match in matches):
                            achievements.append(sentence.strip())
                            break
                    break
        
        # Company research insights (mock - in real implementation, could use web search)
        company_insights = f"Leading company in the {job_title.split()[0] if job_title else 'industry'} space"
        
        return f"""
        CONTEXT: Write a compelling, ATS-optimized cover letter for {candidate_name} applying for the {job_title} position at {company_name}. This should be highly tailored and demonstrate clear value proposition.

        JOB ANALYSIS:
        - Position: {job_title} at {company_name}
        - Location: {job_location}
        - Core Requirements: {job_requirements[:600]}
        - Role Description: {job_description[:600]}
        - Company Context: {company_insights}
        
        CANDIDATE PROFILE:
        - Name: {candidate_name}
        - Contact: {candidate_email}{', ' + candidate_phone if candidate_phone else ''}
        - Professional Summary: {candidate_summary}
        - Education: {candidate_education.get('degree', '') + ', ' + candidate_education.get('institution', '') if candidate_education else 'Relevant educational background'}
        
        STRATEGIC MATCHING:
        - Priority Skills (match job requirements): {', '.join(priority_skills[:4]) if priority_skills else 'Core professional skills'}
        - Additional Relevant Skills: {', '.join(matching_skills[:4]) if matching_skills else ', '.join(candidate_skills[:4])}
        - Most Relevant Experience: {top_experiences[0]['title'] + ' at ' + top_experiences[0]['company'] if top_experiences else 'Professional experience'}
        - Key Achievements: {achievements[:2] if achievements else ['Professional accomplishments with measurable impact']}
        
        COVER LETTER REQUIREMENTS:
        1. Professional header: Date, then "Dear Hiring Manager," or "Dear {company_name} Hiring Team,"
        2. Opening paragraph (2-3 sentences):
           - Express specific interest in the {job_title} role
           - Brief mention of most relevant background/qualification
           - Hook that connects to company/role
        3. Body paragraph 1 (3-4 sentences):
           - Highlight most relevant experience with specific examples
           - Include quantifiable achievement from top experience
           - Connect directly to job requirements
        4. Body paragraph 2 (3-4 sentences):
           - Showcase additional relevant skills/experiences
           - Demonstrate knowledge of company/industry
           - Show cultural fit and enthusiasm
        5. Closing paragraph (2-3 sentences):
           - Reiterate interest and value proposition
           - Professional call to action for next steps
           - Thank them for consideration
        6. Professional closing: "Sincerely," (no name after)
        
        FORMATTING & STYLE:
        - Maximum 350 words
        - Professional, confident tone
        - Use keywords from job description naturally
        - No generic statements - everything should be specific
        - Include specific metrics/achievements where possible
        - Show genuine enthusiasm for the role and company
        
        Write the complete cover letter content (no header with addresses):
        """