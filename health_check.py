#!/usr/bin/env python3
"""
Quick health check to see if the server is running and test basic functionality.
"""

import asyncio
import aiohttp
import sys

BASE_URL = "http://localhost:8000"

async def health_check():
    """Check if the server is running and responsive."""
    
    print("🏥 Checking Server Health...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test chat health endpoint
            async with session.get(f"{BASE_URL}/chat/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Chat service is healthy")
                    print(f"   Status: {data.get('status', 'unknown')}")
                    
                    services = data.get('services', {})
                    for service, status in services.items():
                        icon = "✅" if status == "healthy" else "❌"
                        print(f"   {icon} {service}: {status}")
                        
                    return True
                else:
                    print(f"❌ Chat health check failed: {response.status}")
                    return False
                    
    except aiohttp.ClientConnectorError:
        print("❌ Cannot connect to server. Is it running on http://localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

def main():
    """Run health check."""
    print("🔍 Server Health Check")
    print("=" * 30)
    
    result = asyncio.run(health_check())
    
    if result:
        print(f"\n✅ Server is running and ready for testing!")
        print(f"\nNext steps:")
        print(f"1. Re-upload your blood test PDF to: {BASE_URL}/upload/pdf")
        print(f"2. The updated service will extract patient ID automatically")
        print(f"3. Test patient-specific queries with the patient ID: 68c3f4df1ce4403df50e1930")
        print(f"4. Run: python test_workflow.py")
    else:
        print(f"\n❌ Server is not available. Please:")
        print(f"1. Start the server: python -m uvicorn app.main:app --reload")
        print(f"2. Wait for it to fully initialize")
        print(f"3. Run this health check again")

if __name__ == "__main__":
    main()