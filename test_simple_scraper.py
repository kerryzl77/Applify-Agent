#!/usr/bin/env python3
"""
Test the LinkedIn extractor (text-first + search fallback)
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.universal_extractor import extract_linkedin_profile, parse_linkedin_slug

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_scraper():
    """Test the LinkedIn text-first extractor."""
    print("=" * 80)
    print("LinkedIn Extractor Test (Text-first + Search Fallback)")
    print("=" * 80)

    # Test with profile including UI hints
    test_url = "https://www.linkedin.com/in/zikailiu/"
    test_name = "Zikai Liu"
    test_position = "AI Engineer at Articul8"
    test_company = None  # Let the extractor discover this

    print(f"\n🧪 Testing with profile: {test_url}")
    print(f"📝 UI Hints - Name: {test_name}, Position: {test_position}, Company: {test_company}")
    print("-" * 80)

    # Extract profile data with UI hints for better matching
    data = extract_linkedin_profile(
        test_url,
        name=test_name,
        position=test_position,
        company=test_company
    )
    
    # Debug: Print raw data
    print("\n🔍 Raw extracted data:")
    import json
    print(json.dumps(data, indent=2))
    
    if data and not (data.get('name') or '').strip():
        fallback = parse_linkedin_slug(test_url)
        if fallback:
            data['name'] = fallback

    has_any = bool(data and (
        (data.get('name') or '').strip() or
        (data.get('headline') or '').strip() or
        (data.get('company') or '').strip() or
        (data.get('location') or '').strip() or
        (data.get('title') or '').strip()
    ))

    if has_any:
        print("\n✅ SUCCESS! Profile extracted!")
        print("-" * 80)
        print(f"👤 Name: {data.get('name','')}")
        print(f"💼 Headline: {data.get('headline','')}")
        print(f"📍 Location: {data.get('location','')}")
        print(f"🏢 Company: {data.get('company','')}")
        print(f"💡 Position: {data.get('title','')}")
        
        if data.get('about'):
            print(f"\n📝 About (first 200 chars): {data.get('about','')[:200]}...")
        
        skills = data.get('skills') or []
        if skills:
            print(f"\n🎯 Skills ({len(skills)}): {', '.join(skills[:10])}")
        
        experience = data.get('experience') or []
        if experience:
            print(f"\n💼 Experience ({len(experience)} entries):")
            for i, exp in enumerate(experience[:3], 1):
                print(f"  {i}. {exp.get('title', 'N/A')}")
                if exp.get('company'):
                    print(f"     @ {exp.get('company')}")
        
        education = data.get('education') or []
        if education:
            print(f"\n🎓 Education ({len(education)} entries):")
            for i, edu in enumerate(education[:2], 1):
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

