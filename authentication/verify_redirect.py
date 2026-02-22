import httpx
import asyncio

async def verify_redirect():
    url = "http://localhost:8000/auth/dashboard"
    
    print(f"Checking {url} for unauthenticated redirect...")
    
    async with httpx.AsyncClient() as client:
        try:
            # We use follow_redirects=False to see the 302 response itself
            response = await client.get(url, follow_redirects=False)
            
            print(f"Status Code: {response.status_code}")
            print(f"Location Header: {response.headers.get('location')}")
            
            if response.status_code == 302 and "/auth/login" in response.headers.get("location", ""):
                print("SUCCESS: Correctly redirected to /auth/login")
            elif response.status_code == 401:
                print("FAILURE: Received 401 Unauthorized (Redirect failed)")
            else:
                print(f"UNEXPECTED: {response.status_code} {response.text}")
                
        except Exception as e:
            print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    asyncio.run(verify_redirect())
