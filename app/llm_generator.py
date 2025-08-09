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
                model="gpt-4o-mini",  # or another appropriate model
                messages=[
                    {"role": "system", "content": "You are a professional writer helping a job applicant create tailored application materials."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating text: {str(e)}"
    
    def _build_linkedin_message_prompt(self, job_data, candidate_data, profile_data=None):
        """Build prompt for LinkedIn connection message."""
        # Get values with defaults for missing keys
        company_name = job_data.get('company_name', 'the company')
        job_title = job_data.get('job_title', 'the position')
        recipient_name = profile_data.get('name', '') if profile_data else ''
        recipient_title = profile_data.get('title', '') if profile_data else ''
        recipient_company = profile_data.get('company', '') if profile_data else ''
        
        # Get candidate's professional summary
        current_role = candidate_data['resume'].get('summary', 'Professional seeking new opportunities')
        
        # Get user's template if available
        template_example = ""
        if candidate_data.get('templates', {}).get('linkedin_messages', {}).get('template'):
            template = candidate_data['templates']['linkedin_messages']
            template_example = f"\nHere is an example template to follow:\nTitle: {template['title']}\nContent:\n{template['template']}\n"
        
        return f"""
        Create a LinkedIn connection message from {candidate_data['personal_info']['name']} to {recipient_name} at {recipient_company}.
        
        About the recipient:
        - Name: {recipient_name}
        - Title: {recipient_title}
        - Company: {recipient_company}
        
        About the candidate:
        - Professional Summary: {current_role}
        - Key skills: {', '.join(candidate_data['resume']['skills'][:5])}
        
        The message should:
        - Start with "Hi [Name]"
        - Introduce yourself as {candidate_data['personal_info']['name']}, {current_role}
        - Express interest in their specific role/work at their company
        - Be concise and friendly
        - Be MAXIMUM 200 CHARACTERS (this is critical)
        - Not include salutations or signatures
        {template_example}
        
        Write only the message content.
        """
    
    def _build_connection_email_prompt(self, job_data, candidate_data, profile_data=None):
        """Build prompt for connection email."""
        # Get values with defaults for missing keys
        company_name = job_data.get('company_name', 'the company')
        job_title = job_data.get('job_title', 'the position')
        recipient_name = profile_data.get('name', '') if profile_data else ''
        recipient_title = profile_data.get('title', '') if profile_data else ''
        recipient_company = profile_data.get('company', '') if profile_data else ''
        recipient_about = profile_data.get('about', '') if profile_data else ''
        
        # Get candidate's experience summary
        experience_summary = candidate_data['resume'].get('summary', 'Professional seeking new opportunities')
        key_skills = ', '.join(candidate_data['resume']['skills'])
        
        # Get most relevant experience
        relevant_experience = []
        for exp in candidate_data['resume']['experience'][:2]:  # Get top 2 experiences
            relevant_experience.append(f"{exp['title']} at {exp['company']}")
        
        # Find commonalities between candidate and recipient
        commonalities = []
        if profile_data:
            # Check for common skills
            recipient_skills = set(profile_data.get('skills', []))
            candidate_skills = set(candidate_data['resume']['skills'])
            common_skills = recipient_skills.intersection(candidate_skills)
            if common_skills:
                commonalities.append(f"shared skills in {', '.join(list(common_skills)[:3])}")
            
            # Check for common education
            recipient_education = profile_data.get('education', [])
            candidate_education = candidate_data['resume']['education']
            for rec_edu in recipient_education:
                for cand_edu in candidate_education:
                    if rec_edu.get('school') == cand_edu.get('institution'):
                        commonalities.append(f"alumni of {rec_edu['school']}")
                        break
            
            # Check for common interests
            recipient_interests = set(profile_data.get('interests', []))
            candidate_interests = set(candidate_data.get('interests', []))
            common_interests = recipient_interests.intersection(candidate_interests)
            if common_interests:
                commonalities.append(f"shared interests in {', '.join(list(common_interests)[:2])}")
        
        # Build connection points
        connection_points = []
        if commonalities:
            connection_points.append(f"I noticed we have {', '.join(commonalities)}")
        
        # Add relevant experience points
        if profile_data and profile_data.get('experience'):
            recipient_experience = profile_data['experience'][0]  # Get current role
            if recipient_experience.get('company') in [exp['company'] for exp in candidate_data['resume']['experience']]:
                connection_points.append(f"I see you're currently at {recipient_experience['company']}")
        
        # Get user's template if available
        template_example = ""
        if candidate_data.get('templates', {}).get('connection_emails', {}).get('template'):
            template = candidate_data['templates']['connection_emails']
            template_example = f"\nHere is an example template to follow:\nTitle: {template['title']}\nContent:\n{template['template']}\n"
        
        return f"""
        Create a connection email from {candidate_data['personal_info']['name']} to {recipient_name} at {recipient_company}.
        
        About the recipient:
        - Name: {recipient_name}
        - Title: {recipient_title}
        - Company: {recipient_company}
        - About: {recipient_about}
        - Current role: {profile_data['experience'][0]['title'] if profile_data and profile_data.get('experience') else 'Unknown'}
        
        About the candidate:
        - Professional Summary: {experience_summary}
        - Key experiences: {', '.join(relevant_experience)}
        - Key skills: {key_skills}
        
        Connection points to highlight:
        {chr(10).join(connection_points) if connection_points else 'No specific connection points found'}
        
        The email should:
        - Start with "Hi [Name]"
        - Introduce yourself as {candidate_data['personal_info']['name']}, {experience_summary}
        - Highlight relevant experience and skills that align with the recipient's role/company
        - Use the connection points above to create a personal touch
        - Express genuine interest in their work and company
        - Ask for insights or advice about the role/team
        - Be professional but friendly
        - Include "Best, [Your Name] LinkedIn" as signature
        - Be MAXIMUM 200 WORDS (this is critical)
        {template_example}
        
        Write the complete email.
        """
    
    def _build_hiring_manager_email_prompt(self, job_data, candidate_data):
        """Build prompt for hiring manager email."""
        # Get values with defaults for missing keys
        company_name = job_data.get('company_name', 'the company')
        job_title = job_data.get('job_title', 'the position')
        job_description = job_data.get('job_description', 'The job involves working with data and technology.')
        requirements = job_data.get('requirements', 'Skills in data analysis, programming, and communication.')
        
        # Get candidate's professional summary and experience
        current_role = candidate_data['resume'].get('summary', 'Professional seeking new opportunities')
        
        # Format past experience for the prompt
        past_experience = []
        for exp in candidate_data['resume'].get('experience', []):
            exp_str = f"- {exp['title']} at {exp['company']} ({exp['start_date']} - {exp['end_date']}): {exp['description']}"
            past_experience.append(exp_str)
        
        # Get user's template if available
        template_example = ""
        if candidate_data.get('templates', {}).get('hiring_manager_emails', {}).get('template'):
            template = candidate_data['templates']['hiring_manager_emails']
            template_example = f"\nHere is an example template to follow:\nTitle: {template['title']}\nContent:\n{template['template']}\n"
        
        return f"""
        Create an email from {candidate_data['personal_info']['name']} to the hiring manager for the {job_title} position at {company_name}.
        
        About the job:
        - Title: {job_title}
        - Company: {company_name}
        - Description: {job_description[:300]}...
        - Requirements: {requirements[:300]}...
        
        About the candidate:
        - Professional Summary: {current_role}
        - Experience: {candidate_data['resume']['summary']}
        - Key skills: {', '.join(candidate_data['resume']['skills'])}
        - Past Experience:
        {chr(10).join(past_experience)}
        - Relevant story: {candidate_data['story_bank'][0]['content'] if candidate_data['story_bank'] else 'Experienced in delivering results.'}
        
        The email should:
        - Be addressed to the hiring manager
        - Express interest in the specific position
        - Highlight 2-3 most relevant qualifications/experiences from past roles
        - Connect candidate's background to job requirements
        - Include a call to action
        - Be MAXIMUM 200 WORDS (this is critical)
        - Include appropriate salutation and signature
        {template_example}
        
        Write the complete email.
        """
    
    def _build_cover_letter_prompt(self, job_data, candidate_data):
        """Build prompt for cover letter."""
        # Get values with defaults for missing keys
        company_name = job_data.get('company_name', 'the company')
        job_title = job_data.get('job_title', 'the position')
        job_description = job_data.get('job_description', 'The job involves working with data and technology.')
        requirements = job_data.get('requirements', 'Skills in data analysis, programming, and communication.')
        location = job_data.get('location', 'the location')
        
        # Get candidate's professional summary and experience
        current_role = candidate_data['resume'].get('summary', 'Professional seeking new opportunities')
        
        # Format past experience for the prompt
        past_experience = []
        for exp in candidate_data['resume'].get('experience', []):
            exp_str = f"- {exp['title']} at {exp['company']} ({exp['start_date']} - {exp['end_date']}): {exp['description']}"
            past_experience.append(exp_str)
        
        # Get user's template if available
        template_example = ""
        if candidate_data.get('templates', {}).get('cover_letters', {}).get('template'):
            template = candidate_data['templates']['cover_letters']
            template_example = f"\nHere is an example template to follow:\nTitle: {template['title']}\nContent:\n{template['template']}\n"
        
        return f"""
        Create a cover letter from {candidate_data['personal_info']['name']} for the {job_title} position at {company_name}.
        
        About the job:
        - Title: {job_title}
        - Company: {company_name}
        - Description: {job_description}
        - Requirements: {requirements}
        - Location: {location}
        
        About the candidate:
        - Contact: {candidate_data['personal_info']['email']} | {candidate_data['personal_info']['phone']}
        - Professional Summary: {current_role}
        - Education: {candidate_data['resume']['education'][0]['degree']} from {candidate_data['resume']['education'][0]['institution']}
        - Key skills: {', '.join(candidate_data['resume']['skills'])}
        - Past Experience:
        {chr(10).join(past_experience)}
        - Stories: 
          1. {candidate_data['story_bank'][0]['content'] if candidate_data['story_bank'] else 'Experienced in delivering results.'}
          2. {candidate_data['story_bank'][1]['content'] if len(candidate_data['story_bank']) > 1 else ''}
        
        The cover letter should:
        - Follow standard cover letter format
        - Be addressed to the hiring manager
        - Have a compelling introduction that mentions the specific position
        - Highlight 3-4 most relevant qualifications/experiences that match job requirements
        - Include specific achievements with measurable results from past roles
        - Explain why the candidate is interested in this specific company
        - Have a strong closing paragraph with a call to action
        - Do not include Title, Exclude any header or closing that explicitly includes the candidate's name
        - Be MAXIMUM 350 WORDS (this is critical)
        - Be professional but show personality
        {template_example}
        
        Write the complete cover letter.
        """