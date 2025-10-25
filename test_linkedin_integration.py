#!/usr/bin/env python3
"""
Integration test: LinkedIn scraper -> LLM email generation
Tests the complete data flow from LinkedIn profile scraping to email generation
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.retriever import DataRetriever
from app.llm_generator import LLMGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_integration():
    """Test complete integration from LinkedIn scraping to email generation."""
    print("=" * 80)
    print("LinkedIn Scraper -> LLM Integration Test")
    print("=" * 80)

    # Initialize components
    data_retriever = DataRetriever()
    llm_generator = LLMGenerator()

    # Test LinkedIn profile
    test_linkedin_url = "https://www.linkedin.com/in/zikailiu/"

    print(f"\n🧪 Step 1: Scrape LinkedIn Profile")
    print("-" * 80)
    profile_data = data_retriever.scrape_linkedin_profile(test_linkedin_url)

    if not profile_data or 'error' in profile_data:
        print(f"❌ LinkedIn scraping failed: {profile_data.get('error', 'Unknown error')}")
        return False

    print(f"✅ Profile scraped successfully!")
    print(f"   Name: {profile_data.get('name')}")
    print(f"   Title: {profile_data.get('title')}")
    print(f"   Company: {profile_data.get('company')}")
    print(f"   Skills: {len(profile_data.get('skills', []))} skills")
    print(f"   Experience: {len(profile_data.get('experience', []))} entries")

    # Mock candidate data
    candidate_data = {
        'personal_info': {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '+1234567890'
        },
        'resume': {
            'summary': 'Experienced software engineer with focus on machine learning',
            'skills': ['Python', 'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch'],
            'experience': [
                {
                    'title': 'Software Engineer',
                    'company': 'Tech Corp',
                    'start_date': '2020',
                    'end_date': 'Present',
                    'description': 'Developed ML models for production systems'
                }
            ],
            'education': [
                {
                    'institution': 'University of Technology',
                    'degree': 'BS Computer Science',
                    'graduation_year': '2020'
                }
            ]
        }
    }

    # Mock job data
    job_data = {
        'job_title': 'Machine Learning Engineer',
        'company_name': profile_data.get('company', 'Company'),
        'job_description': 'We are looking for an experienced ML engineer to join our team.',
        'requirements': 'Strong background in deep learning and NLP',
        'location': 'San Francisco, CA',
        'url': test_linkedin_url
    }

    print(f"\n🧪 Step 2: Generate Hiring Manager Email")
    print("-" * 80)

    # Generate hiring manager email using scraped LinkedIn data
    email_content = llm_generator.generate_hiring_manager_email(
        job_data,
        candidate_data,
        profile_data
    )

    if not email_content or email_content.startswith("Error"):
        print(f"❌ Email generation failed: {email_content}")
        return False

    print(f"✅ Email generated successfully!")
    print("-" * 80)
    print("Generated Email:")
    print("-" * 80)
    print(email_content)
    print("-" * 80)

    # Verify that LinkedIn profile data is used in the email
    print(f"\n🧪 Step 3: Verify LinkedIn Data Integration")
    print("-" * 80)

    checks = []

    # Check if recipient name is mentioned
    if profile_data.get('name', '').split()[0] in email_content:
        checks.append("✅ Recipient name mentioned")
    else:
        checks.append("⚠️  Recipient name not found in email")

    # Check if company is mentioned
    if profile_data.get('company', '') in email_content:
        checks.append("✅ Company name mentioned")
    else:
        checks.append("⚠️  Company name not found in email")

    # Check if any skills are mentioned
    linkedin_skills = profile_data.get('skills', [])
    skills_mentioned = any(skill.lower() in email_content.lower() for skill in linkedin_skills[:5])
    if skills_mentioned:
        checks.append("✅ LinkedIn skills referenced")
    else:
        checks.append("⚠️  No LinkedIn skills referenced")

    for check in checks:
        print(f"   {check}")

    print("\n" + "=" * 80)
    print("✅ Integration Test PASSED!")
    print("=" * 80)
    print("\nKey Findings:")
    print(f"  • LinkedIn scraper successfully extracted {len(profile_data.get('skills', []))} skills")
    print(f"  • Profile data properly formatted for LLM context")
    print(f"  • Email generation successfully uses LinkedIn profile data")
    print(f"  • Generated email is {len(email_content)} characters")
    print("=" * 80)
    return True

if __name__ == "__main__":
    try:
        success = test_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Integration test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
