import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMGenerator:
    def __init__(self):
        # Initialize OpenAI client with API key from environment variable
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def generate_linkedin_message(self, job_data, candidate_data):
        """Generate a LinkedIn connection message (200 characters max)."""
        prompt = self._build_linkedin_message_prompt(job_data, candidate_data)
        return self._generate_text(prompt, max_tokens=100)  # ~200 characters
    
    def generate_connection_email(self, job_data, candidate_data):
        """Generate a connection email (200 words max)."""
        prompt = self._build_connection_email_prompt(job_data, candidate_data)
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
                model="gpt-4",  # or another appropriate model
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
    
    def _build_linkedin_message_prompt(self, job_data, candidate_data):
        """Build prompt for LinkedIn connection message."""
        # Get values with defaults for missing keys
        company_name = job_data.get('company_name', 'the company')
        job_title = job_data.get('job_title', 'the position')
        current_role = candidate_data['personal_info'].get('current_role', 
            f"{candidate_data['resume']['experience'][0]['title']} at {candidate_data['resume']['experience'][0]['company']}" 
            if candidate_data['resume']['experience'] else "Current Student")
        
        return f"""
        Create a LinkedIn connection message from {candidate_data['personal_info']['name']} to someone at {company_name}.
        
        About the job:
        - Title: {job_title}
        - Company: {company_name}
        
        About the candidate:
        - Current role: {current_role}
        - Key skills: {', '.join(candidate_data['resume']['skills'][:5])}
        
        The message should:
        - Be personalized and specific to the job/company
        - Show genuine interest
        - Be concise and professional
        - Be MAXIMUM 200 CHARACTERS (this is critical)
        - Not include salutations or signatures
        
        Write only the message content.
        """
    
    def _build_connection_email_prompt(self, job_data, candidate_data):
        """Build prompt for connection email."""
        # Get values with defaults for missing keys
        company_name = job_data.get('company_name', 'the company')
        job_title = job_data.get('job_title', 'the position')
        job_description = job_data.get('job_description', 'The job involves working with data and technology.')
        current_role = candidate_data['personal_info'].get('current_role',
            f"{candidate_data['resume']['experience'][0]['title']} at {candidate_data['resume']['experience'][0]['company']}"
            if candidate_data['resume']['experience'] else "Current Student")
        
        return f"""
        Create a connection email from {candidate_data['personal_info']['name']} to someone at {company_name}.
        
        About the job:
        - Title: {job_title}
        - Company: {company_name}
        - Description: {job_description[:300]}...
        
        About the candidate:
        - Current role: {current_role}
        - Experience: {candidate_data['resume']['summary']}
        - Key skills: {', '.join(candidate_data['resume']['skills'][:5])}
        
        The email should:
        - Be personalized and specific to the job/company
        - Briefly highlight relevant skills/experience
        - Express interest in learning more about opportunities
        - Be professional and concise
        - Be MAXIMUM 200 WORDS (this is critical)
        - Include appropriate salutation and signature
        
        Write the complete email.
        """
    
    def _build_hiring_manager_email_prompt(self, job_data, candidate_data):
        """Build prompt for hiring manager email."""
        # Get values with defaults for missing keys
        company_name = job_data.get('company_name', 'the company')
        job_title = job_data.get('job_title', 'the position')
        job_description = job_data.get('job_description', 'The job involves working with data and technology.')
        requirements = job_data.get('requirements', 'Skills in data analysis, programming, and communication.')
        current_role = candidate_data['personal_info'].get('current_role',
            f"{candidate_data['resume']['experience'][0]['title']} at {candidate_data['resume']['experience'][0]['company']}"
            if candidate_data['resume']['experience'] else "Current Student")
        
        return f"""
        Create an email from {candidate_data['personal_info']['name']} to the hiring manager for the {job_title} position at {company_name}.
        
        About the job:
        - Title: {job_title}
        - Company: {company_name}
        - Description: {job_description[:300]}...
        - Requirements: {requirements[:300]}...
        
        About the candidate:
        - Current role: {current_role}
        - Experience: {candidate_data['resume']['summary']}
        - Key skills: {', '.join(candidate_data['resume']['skills'])}
        - Relevant story: {candidate_data['story_bank'][0]['content'] if candidate_data['story_bank'] else 'Experienced in delivering results.'}
        
        The email should:
        - Be addressed to the hiring manager
        - Express interest in the specific position
        - Highlight 2-3 most relevant qualifications/experiences
        - Connect candidate's background to job requirements
        - Include a call to action
        - Be MAXIMUM 200 WORDS (this is critical)
        - Include appropriate salutation and signature
        
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
        current_role = candidate_data['personal_info'].get('current_role',
            f"{candidate_data['resume']['experience'][0]['title']} at {candidate_data['resume']['experience'][0]['company']}"
            if candidate_data['resume']['experience'] else "Current Student")
        
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
        - Current role: {current_role}
        - Previous role: {candidate_data['resume']['experience'][1]['title'] if len(candidate_data['resume']['experience']) > 1 else 'Previous role'} at {candidate_data['resume']['experience'][1]['company'] if len(candidate_data['resume']['experience']) > 1 else 'Previous company'}
        - Education: {candidate_data['resume']['education'][0]['degree']} from {candidate_data['resume']['education'][0]['institution']}
        - Summary: {candidate_data['resume']['summary']}
        - Key skills: {', '.join(candidate_data['resume']['skills'])}
        - Stories: 
          1. {candidate_data['story_bank'][0]['content'] if candidate_data['story_bank'] else 'Experienced in delivering results.'}
          2. {candidate_data['story_bank'][1]['content'] if len(candidate_data['story_bank']) > 1 else ''}
        
        The cover letter should:
        - Follow standard cover letter format
        - Be addressed to the hiring manager
        - Have a compelling introduction that mentions the specific position
        - Highlight 3-4 most relevant qualifications/experiences that match job requirements
        - Include specific achievements with measurable results
        - Explain why the candidate is interested in this specific company
        - Have a strong closing paragraph with a call to action
        - Be MAXIMUM 350 WORDS (this is critical)
        - Be professional but show personality
        
        Write the complete cover letter.
        """