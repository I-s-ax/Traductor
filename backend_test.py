import requests
import sys
import json
from datetime import datetime

class TranslationAPITester:
    def __init__(self, base_url="https://doc-translate-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {}
        if data and not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response_preview": response.text[:200] if not success else "OK"
            })

            return success, response.json() if success and response.content else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "response_preview": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        if success and "message" in response:
            print(f"   Message: {response['message']}")
            return "running" in response["message"].lower()
        return False

    def test_languages_endpoint(self):
        """Test the languages endpoint"""
        success, response = self.run_test(
            "Languages Endpoint",
            "GET",
            "languages",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} languages")
            if len(response) >= 50:
                print("✅ Has 50+ languages as required")
                return True
            else:
                print(f"❌ Only {len(response)} languages, expected 50+")
                return False
        return False

    def test_providers_endpoint(self):
        """Test the providers endpoint"""
        success, response = self.run_test(
            "Providers Endpoint",
            "GET",
            "providers",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} providers")
            provider_ids = [p.get('id') for p in response]
            print(f"   Provider IDs: {provider_ids}")
            
            expected_providers = ['openai', 'gemini', 'claude']
            has_all_providers = all(provider in provider_ids for provider in expected_providers)
            
            if has_all_providers and len(response) == 3:
                print("✅ Has all 3 required providers (openai, gemini, claude)")
                return True
            else:
                print(f"❌ Missing providers. Expected: {expected_providers}, Got: {provider_ids}")
                return False
        return False

    def test_history_endpoint(self):
        """Test the history endpoint"""
        success, response = self.run_test(
            "History Endpoint",
            "GET",
            "history",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} history items")
            if len(response) == 0:
                print("✅ History is empty as expected for initial state")
                return True
            else:
                print(f"ℹ️  History has {len(response)} items (not empty)")
                return True  # This is still valid, just not empty
        return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print(f"📊 BACKEND API TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print(f"\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['name']}: {result['actual_status']}")
            if not result["success"]:
                print(f"   Error: {result['response_preview']}")
        
        return self.tests_passed == self.tests_run

def main():
    print("🚀 Starting Translation API Backend Tests...")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = TranslationAPITester()
    
    # Run all tests
    root_ok = tester.test_root_endpoint()
    languages_ok = tester.test_languages_endpoint()
    providers_ok = tester.test_providers_endpoint()
    history_ok = tester.test_history_endpoint()
    
    # Print summary
    all_passed = tester.print_summary()
    
    # Specific validations
    print(f"\n🎯 REQUIREMENT VALIDATIONS:")
    print(f"✅ Root endpoint returns 'running' message: {root_ok}")
    print(f"✅ Languages endpoint returns 50+ languages: {languages_ok}")
    print(f"✅ Providers endpoint returns 3 providers: {providers_ok}")
    print(f"✅ History endpoint returns array: {history_ok}")
    
    if all_passed:
        print(f"\n🎉 ALL BACKEND TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  SOME BACKEND TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())