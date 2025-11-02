"""Test script to verify Google CSE and DuckDuckGo integration"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.universal_extractor import duckduckgo_signals, _google_cse_search
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_google_cse():
    """Test Google Custom Search Engine"""
    print("\n" + "="*60)
    print("Testing Google CSE")
    print("="*60)
    
    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    
    if not api_key:
        print("❌ GOOGLE_CSE_API_KEY not set")
        return False
    if not cx:
        print("❌ GOOGLE_CSE_CX not set")
        return False
    
    print(f"✅ GOOGLE_CSE_API_KEY: {api_key[:10]}...")
    print(f"✅ GOOGLE_CSE_CX: {cx}")
    
    # Test search
    try:
        results = _google_cse_search("rodrigo charaba site:linkedin.com/in", num=3)
        print(f"\n✅ Google CSE returned {len(results)} results")
        for i, r in enumerate(results[:3], 1):
            print(f"\n  Result {i}:")
            print(f"    Title: {r.get('title', 'N/A')[:60]}")
            print(f"    URL: {r.get('href', 'N/A')}")
        return len(results) > 0
    except Exception as e:
        print(f"\n❌ Google CSE failed: {e}")
        return False

def test_duckduckgo():
    """Test DuckDuckGo search"""
    print("\n" + "="*60)
    print("Testing DuckDuckGo")
    print("="*60)
    
    try:
        from ddgs import DDGS
        print("✅ DDGS module imported successfully")
    except Exception as e:
        print(f"❌ DDGS import failed: {e}")
        return False
    
    # Test search
    try:
        results = duckduckgo_signals("rodrigo charaba linkedin", max_n=3)
        print(f"\n✅ DuckDuckGo returned {len(results)} results")
        for i, r in enumerate(results[:3], 1):
            print(f"\n  Result {i}:")
            print(f"    Title: {r.get('title', 'N/A')[:60]}")
            print(f"    URL: {r.get('href', 'N/A')}")
        return len(results) > 0
    except Exception as e:
        print(f"\n❌ DuckDuckGo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_linkedin_extraction():
    """Test LinkedIn profile extraction"""
    print("\n" + "="*60)
    print("Testing LinkedIn Profile Extraction")
    print("="*60)
    
    from app.universal_extractor import extract_linkedin_profile
    
    url = "https://www.linkedin.com/in/rodrigo-charaba/"
    name = "rodrigo charaba"
    position = "SDE"
    company = "Articul8"
    
    try:
        profile = extract_linkedin_profile(url, name=name, position=position, company=company)
        print(f"\n✅ Profile extracted successfully")
        print(f"  Name: {profile.get('name', 'N/A')}")
        print(f"  Title: {profile.get('title', 'N/A')}")
        print(f"  Company: {profile.get('company', 'N/A')}")
        print(f"  Location: {profile.get('location', 'N/A')}")
        print(f"  Scraping method: {profile.get('scraping_method', 'N/A')}")
        print(f"  Skills: {len(profile.get('skills', []))} skills found")
        print(f"  Experience: {len(profile.get('experience', []))} experiences found")
        return profile.get('name') is not None
    except Exception as e:
        print(f"\n❌ LinkedIn extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SEARCH & EXTRACTION INTEGRATION TEST")
    print("="*70)
    
    results = {}
    results['Google CSE'] = test_google_cse()
    results['DuckDuckGo'] = test_duckduckgo()
    results['LinkedIn Extraction'] = test_linkedin_extraction()
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL TESTS PASSED")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("="*70)
    
    sys.exit(0 if all_passed else 1)

