#!/usr/bin/env python3
"""
Comprehensive test runner for Glucose-GPT with notification support.
Runs API tests and unit tests before app launch.
"""
import os
import sys
import subprocess
import traceback
from typing import Dict, List, Tuple

# Conditional streamlit import to avoid import errors
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    # Create a mock st object for when streamlit is not available
    class MockStreamlit:
        def success(self, msg): print(f"✅ {msg}")
        def error(self, msg): print(f"❌ {msg}")
        def warning(self, msg): print(f"⚠️ {msg}")
        def write(self, msg): print(msg)
        def expander(self, title, expanded=False): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass
    st = MockStreamlit()

class TestRunner:
    """Comprehensive test runner for Glucose-GPT."""
    
    def __init__(self, project_root: str = None):
        """Initialize the test runner."""
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.project_root = project_root
        self.test_results = {}
    
    def run_api_tests(self) -> Tuple[bool, str]:
        """Run comprehensive API tests."""
        try:
            print("🧪 Running API Tests...")
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_api_clients.py", 
                "-v", "--tb=short"
            ], 
            cwd=self.project_root,
            capture_output=True, 
            text=True,
            timeout=60
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                passed_count = sum(1 for line in lines if " PASSED " in line)
                return True, f"✅ API Tests: {passed_count} tests passed"
            else:
                error_lines = [line for line in result.stdout.split('\n') if "FAILED" in line]
                return False, f"❌ API Tests Failed:\n" + "\n".join(error_lines[:3])
                
        except subprocess.TimeoutExpired:
            return False, "❌ API Tests: Timeout after 60 seconds"
        except Exception as e:
            return False, f"❌ API Tests: Error - {str(e)}"
    
    def run_unit_tests(self) -> Tuple[bool, str]:
        """Run unit tests."""
        try:
            print("🧪 Running Unit Tests...")
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_libre_chat_simple.py", 
                "-v", "--tb=short"
            ], 
            cwd=self.project_root,
            capture_output=True, 
            text=True,
            timeout=60
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                passed_count = sum(1 for line in lines if " PASSED " in line)
                return True, f"✅ Unit Tests: {passed_count} tests passed"
            else:
                error_lines = [line for line in result.stdout.split('\n') if "FAILED" in line]
                return False, f"❌ Unit Tests Failed:\n" + "\n".join(error_lines[:3])
                
        except subprocess.TimeoutExpired:
            return False, "❌ Unit Tests: Timeout after 60 seconds"
        except Exception as e:
            return False, f"❌ Unit Tests: Error - {str(e)}"
    
    def run_integration_tests(self) -> Tuple[bool, str]:
        """Run integration tests."""
        try:
            print("🧪 Running Integration Tests...")
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_libre_chat_integration.py", 
                "-v", "--tb=short"
            ], 
            cwd=self.project_root,
            capture_output=True, 
            text=True,
            timeout=120
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                passed_count = sum(1 for line in lines if " PASSED " in line)
                return True, f"✅ Integration Tests: {passed_count} tests passed"
            else:
                error_lines = [line for line in result.stdout.split('\n') if "FAILED" in line]
                return False, f"❌ Integration Tests Failed:\n" + "\n".join(error_lines[:3])
                
        except subprocess.TimeoutExpired:
            return False, "❌ Integration Tests: Timeout after 120 seconds"
        except Exception as e:
            return False, f"❌ Integration Tests: Error - {str(e)}"
    
    def run_comprehensive_tests(self) -> Tuple[bool, List[str]]:
        """Run all tests comprehensively."""
        print("🚀 Starting Comprehensive Test Suite for Glucose-GPT")
        print("=" * 60)
        
        results = []
        all_passed = True
        
        # Run API tests
        api_passed, api_msg = self.run_api_tests()
        results.append(api_msg)
        if not api_passed:
            all_passed = False
        
        # Run unit tests
        unit_passed, unit_msg = self.run_unit_tests()
        results.append(unit_msg)
        if not unit_passed:
            all_passed = False
        
        # Run integration tests
        integration_passed, integration_msg = self.run_integration_tests()
        results.append(integration_msg)
        if not integration_passed:
            all_passed = False
        
        if all_passed:
            results.append("🎉 All test suites passed! Glucose-GPT is ready to launch.")
        else:
            results.append("⚠️ Some tests failed. Please check the errors above.")
        
        print("=" * 60)
        for result in results:
            print(result)
        print("=" * 60)
        
        return all_passed, results
    
    def show_streamlit_notification(self, success: bool, messages: List[str]):
        """Show test results as Streamlit notifications."""
        if not STREAMLIT_AVAILABLE:
            return True
            
        if success:
            st.success("🎉 All tests passed! Glucose-GPT is ready.")
            with st.expander("📊 Test Results Details"):
                for msg in messages:
                    st.write(msg)
        else:
            st.error("⚠️ Some tests failed!")
            with st.expander("❌ Test Failure Details", expanded=True):
                for msg in messages:
                    if "❌" in msg:
                        st.error(msg)
                    elif "✅" in msg:
                        st.success(msg)
                    else:
                        st.write(msg)
            
            st.warning("🔧 Please fix the failing tests before using Glucose-GPT.")
            return False
        return True
    
    def run_pre_launch_tests(self) -> bool:
        """Run tests before app launch with Streamlit integration."""
        try:
            success, messages = self.run_comprehensive_tests()
            
            # If running in Streamlit context, show notifications
            if STREAMLIT_AVAILABLE and 'streamlit' in sys.modules:
                return self.show_streamlit_notification(success, messages)
            
            return success
            
        except Exception as e:
            error_msg = f"❌ Test execution failed: {str(e)}"
            print(error_msg)
            
            # Show error in Streamlit if available
            if STREAMLIT_AVAILABLE and 'streamlit' in sys.modules:
                st.error(error_msg)
                st.error("🔧 Please check your test configuration and try again.")
            
            return False

def run_tests_from_cli():
    """Run tests from command line."""
    runner = TestRunner()
    success, messages = runner.run_comprehensive_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    run_tests_from_cli()
