#!/usr/bin/env python3
"""
Test the LinkedIn Vision Scraper (Playwright + GPT-4 Vision)
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.linkedin_vision_scraper import LinkedInVisionScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_scraper():
    """Test the LinkedIn Vision scraper."""
    print("=" * 80)
    print("LinkedIn Vision Scraper Test (Playwright + GPT-4 Vision)")
    print("=" * 80)

    # Initialize scraper
    scraper = LinkedInVisionScraper()

    # Test with Satya Nadella's profile
    test_url = "https://www.linkedin.com/in/zikailiu/"

    print(f"\n🧪 Testing with profile: {test_url}")
    print("-" * 80)

    # Extract profile data
    profile = scraper.extract_profile_data(test_url)

    if profile and profile.name:
        print("\n✅ SUCCESS! Profile extracted!")
        print("-" * 80)
        print(f"👤 Name: {profile.name}")
        print(f"💼 Headline: {profile.headline}")
        print(f"📍 Location: {profile.location}")
        print(f"🏢 Company: {profile.current_company}")
        print(f"💡 Position: {profile.current_position}")
        
        if profile.about:
            print(f"\n📝 About (first 200 chars): {profile.about[:200]}...")
        
        if profile.skills:
            print(f"\n🎯 Skills ({len(profile.skills)}): {', '.join(profile.skills[:10])}")
        
        if profile.experience:
            print(f"\n💼 Experience ({len(profile.experience)} entries):")
            for i, exp in enumerate(profile.experience[:3], 1):
                print(f"  {i}. {exp.get('title', 'N/A')}")
                if exp.get('company'):
                    print(f"     @ {exp.get('company')}")
        
        if profile.education:
            print(f"\n🎓 Education ({len(profile.education)} entries):")
            for i, edu in enumerate(profile.education[:2], 1):
                print(f"  {i}. {edu.get('institution', 'N/A')}")
                if edu.get('degree'):
                    print(f"     {edu.get('degree')}")
        
        print("\n" + "=" * 80)
        print("✅ Test PASSED!")
        print("=" * 80)
        return True
    else:
        print("\n❌ FAILED! Could not extract profile")
        print("=" * 80)
        return False

if __name__ == "__main__":
    try:
        success = test_scraper()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

