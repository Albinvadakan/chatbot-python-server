#!/usr/bin/env python3
"""
Test script to verify OpenAI integration is working.
"""
import requests
import json

def test_chat_endpoint():
    """Test the chat endpoint with a simple query."""
    url = "http://localhost:8000/api/v1/chat/ai-response"
    
    payload = {
        "query": "Hello, how are you?",
        "patient_id": "test-patient-123"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("Testing chat endpoint...")
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            
            # Check if it's a real OpenAI response (not mock)
            if "Mock AI Response" in result.get("response", ""):
                print("❌ Still getting mock responses!")
            else:
                print("✅ Real OpenAI response received!")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Test failed: {str(e)}")

def test_health_endpoint():
    """Test the health endpoint."""
    url = "http://localhost:8000/health"
    
    try:
        print("Testing health endpoint...")
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Health Status: {json.dumps(result, indent=2)}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Health check failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Testing OpenAI Integration...")
    print("=" * 50)
    
    # Test health first
    test_health_endpoint()
    print()
    
    # Test chat endpoint
    test_chat_endpoint()
    
    print("=" * 50)
    print("Test completed!")