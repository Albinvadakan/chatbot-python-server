"""
Example script demonstrating how to use the Chatbot API endpoints.
"""

import requests
import json
from pathlib import Path

# API Base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_chat_endpoint():
    """Test the chat endpoint."""
    print("Testing chat endpoint...")
    
    data = {
        "query": "What are the symptoms of diabetes?"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/chat/ai-response", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_pdf_upload():
    """Test the PDF upload endpoint."""
    print("Testing PDF upload...")
    
    # Create a sample PDF file path (you need to provide an actual PDF)
    pdf_path = "sample.pdf"  # Replace with actual PDF path
    
    if not Path(pdf_path).exists():
        print(f"PDF file not found: {pdf_path}")
        print("Please provide a valid PDF file path to test upload.")
        return
    
    with open(pdf_path, "rb") as pdf_file:
        files = {"file": (pdf_path, pdf_file, "application/pdf")}
        data = {"patient_id": "patient_123"}
        
        response = requests.post(f"{BASE_URL}/api/v1/upload/pdf", files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_upload_stats():
    """Test the upload stats endpoint."""
    print("Testing upload stats...")
    
    response = requests.get(f"{BASE_URL}/api/v1/upload/stats")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def main():
    """Run all test functions."""
    print("Chatbot API Test Script")
    print("=" * 50)
    
    try:
        test_health_check()
        test_chat_endpoint()
        test_upload_stats()
        # test_pdf_upload()  # Uncomment when you have a PDF file
        
        print("All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()