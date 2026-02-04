#!/usr/bin/env python3
"""
Islamic Portal Backend API Testing Suite
Tests all backend APIs for the Islamic Portal application
"""

import requests
import json
import uuid
from datetime import datetime, date
import time

# Backend URL from frontend environment
BACKEND_URL = "https://quran-mobile-app-1.preview.emergentagent.com/api"

class IslamicPortalTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = {}
        self.session_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        
    def log_result(self, test_name, success, details):
        """Log test results"""
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
    
    def test_prayer_times_api(self):
        """Test Prayer Times API with Istanbul coordinates"""
        print("\n🕌 Testing Prayer Times API...")
        
        # Test data - Istanbul coordinates as specified
        test_data = {
            "latitude": 41.0082,
            "longitude": 28.9784
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/prayer-times",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'isha', 'date', 'location']
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_result("Prayer Times API", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Validate time format (HH:MM)
                time_fields = ['fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'isha']
                for field in time_fields:
                    time_str = data[field]
                    try:
                        datetime.strptime(time_str, "%H:%M")
                    except ValueError:
                        self.log_result("Prayer Times API", False, f"Invalid time format for {field}: {time_str}")
                        return False
                
                self.log_result("Prayer Times API", True, f"All prayer times returned correctly for Istanbul: {data}")
                return True
            else:
                self.log_result("Prayer Times API", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Prayer Times API", False, f"Request failed: {str(e)}")
            return False
    
    def test_qibla_direction_api(self):
        """Test Qibla Direction API"""
        print("\n🧭 Testing Qibla Direction API...")
        
        # Test data - Istanbul coordinates
        test_data = {
            "latitude": 41.0082,
            "longitude": 28.9784
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/qibla",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['qibla_direction', 'distance_to_kaaba']
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_result("Qibla Direction API", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Validate qibla direction (0-360 degrees)
                qibla_dir = data['qibla_direction']
                if not (0 <= qibla_dir <= 360):
                    self.log_result("Qibla Direction API", False, f"Invalid qibla direction: {qibla_dir}")
                    return False
                
                # Validate distance (should be positive)
                distance = data['distance_to_kaaba']
                if distance <= 0:
                    self.log_result("Qibla Direction API", False, f"Invalid distance: {distance}")
                    return False
                
                self.log_result("Qibla Direction API", True, f"Qibla direction: {qibla_dir}°, Distance: {distance} km")
                return True
            else:
                self.log_result("Qibla Direction API", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Qibla Direction API", False, f"Request failed: {str(e)}")
            return False
    
    def test_ai_chat_api(self):
        """Test AI Chat API with Gemini integration"""
        print("\n🤖 Testing AI Chat API...")
        
        # Test data - Turkish query about patience (sabr) as specified
        test_data = {
            "session_id": self.session_id,
            "message": "Sabr hakkında ayet",
            "language": "tr"
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/chat",
                json=test_data,
                timeout=60  # AI responses may take longer
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['response', 'session_id']
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_result("AI Chat API", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Validate response content
                ai_response = data['response']
                if not ai_response or len(ai_response.strip()) == 0:
                    self.log_result("AI Chat API", False, "Empty AI response")
                    return False
                
                # Check if session_id matches
                if data['session_id'] != self.session_id:
                    self.log_result("AI Chat API", False, f"Session ID mismatch: expected {self.session_id}, got {data['session_id']}")
                    return False
                
                self.log_result("AI Chat API", True, f"AI responded with {len(ai_response)} characters. Response preview: {ai_response[:100]}...")
                return True
            else:
                self.log_result("AI Chat API", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("AI Chat API", False, f"Request failed: {str(e)}")
            return False
    
    def test_chat_history_get(self):
        """Test GET chat history API"""
        print("\n📜 Testing GET Chat History API...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/chat/history/{self.session_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Should be a list
                if not isinstance(data, list):
                    self.log_result("GET Chat History API", False, f"Expected list, got {type(data)}")
                    return False
                
                # If we had a successful chat, there should be messages
                if len(data) >= 2:  # user message + assistant response
                    # Validate message structure
                    for msg in data:
                        if 'role' not in msg or 'content' not in msg:
                            self.log_result("GET Chat History API", False, f"Invalid message structure: {msg}")
                            return False
                        if msg['role'] not in ['user', 'assistant']:
                            self.log_result("GET Chat History API", False, f"Invalid role: {msg['role']}")
                            return False
                
                self.log_result("GET Chat History API", True, f"Retrieved {len(data)} messages from history")
                return True
            else:
                self.log_result("GET Chat History API", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("GET Chat History API", False, f"Request failed: {str(e)}")
            return False
    
    def test_chat_history_delete(self):
        """Test DELETE chat history API"""
        print("\n🗑️ Testing DELETE Chat History API...")
        
        try:
            response = self.session.delete(
                f"{BACKEND_URL}/chat/history/{self.session_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Should return success message
                if 'message' not in data:
                    self.log_result("DELETE Chat History API", False, f"Missing success message: {data}")
                    return False
                
                # Verify history is actually cleared
                verify_response = self.session.get(f"{BACKEND_URL}/chat/history/{self.session_id}")
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    if len(verify_data) > 0:
                        self.log_result("DELETE Chat History API", False, f"History not cleared, still has {len(verify_data)} messages")
                        return False
                
                self.log_result("DELETE Chat History API", True, "Chat history successfully cleared")
                return True
            else:
                self.log_result("DELETE Chat History API", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("DELETE Chat History API", False, f"Request failed: {str(e)}")
            return False
    
    def test_user_progress_get(self):
        """Test GET user progress API"""
        print("\n📖 Testing GET User Progress API...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/user/progress/{self.user_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['user_id', 'last_read_page', 'last_read_surah', 'last_read_ayah', 'bookmarks', 'updated_at']
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_result("GET User Progress API", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Validate data types and values
                if data['user_id'] != self.user_id:
                    self.log_result("GET User Progress API", False, f"User ID mismatch: expected {self.user_id}, got {data['user_id']}")
                    return False
                
                if not isinstance(data['last_read_page'], int) or data['last_read_page'] < 1:
                    self.log_result("GET User Progress API", False, f"Invalid last_read_page: {data['last_read_page']}")
                    return False
                
                if not isinstance(data['bookmarks'], list):
                    self.log_result("GET User Progress API", False, f"Bookmarks should be a list, got {type(data['bookmarks'])}")
                    return False
                
                self.log_result("GET User Progress API", True, f"User progress retrieved: Page {data['last_read_page']}, Surah {data['last_read_surah']}")
                return True
            else:
                self.log_result("GET User Progress API", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("GET User Progress API", False, f"Request failed: {str(e)}")
            return False
    
    def test_user_progress_post(self):
        """Test POST user progress API"""
        print("\n📝 Testing POST User Progress API...")
        
        # Test data - update reading progress
        test_data = {
            "user_id": self.user_id,
            "last_read_page": 42,
            "last_read_surah": 2,
            "last_read_ayah": 255
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/user/progress",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Should return success message
                if 'message' not in data:
                    self.log_result("POST User Progress API", False, f"Missing success message: {data}")
                    return False
                
                # Verify the update by getting the progress again
                verify_response = self.session.get(f"{BACKEND_URL}/user/progress/{self.user_id}")
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    if (verify_data['last_read_page'] != 42 or 
                        verify_data['last_read_surah'] != 2 or 
                        verify_data['last_read_ayah'] != 255):
                        self.log_result("POST User Progress API", False, f"Progress not updated correctly: {verify_data}")
                        return False
                
                self.log_result("POST User Progress API", True, "User progress successfully updated and verified")
                return True
            else:
                self.log_result("POST User Progress API", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("POST User Progress API", False, f"Request failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting Islamic Portal Backend API Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Session ID: {self.session_id}")
        print(f"User ID: {self.user_id}")
        print("=" * 60)
        
        # Test all APIs in logical order
        tests = [
            ("Prayer Times API", self.test_prayer_times_api),
            ("Qibla Direction API", self.test_qibla_direction_api),
            ("AI Chat API", self.test_ai_chat_api),
            ("GET Chat History API", self.test_chat_history_get),
            ("DELETE Chat History API", self.test_chat_history_delete),
            ("GET User Progress API", self.test_user_progress_get),
            ("POST User Progress API", self.test_user_progress_post),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log_result(test_name, False, f"Test execution error: {str(e)}")
                failed += 1
            
            # Small delay between tests
            time.sleep(1)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"  - {test_name}: {result['details']}")
        
        return failed == 0

if __name__ == "__main__":
    tester = IslamicPortalTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)