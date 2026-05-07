import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        try:
            print("Trying msedge...")
            await p.chromium.launch_persistent_context('test_data', channel='msedge')
            print("msedge OK")
            return
        except Exception as e:
            print(f"msedge failed: {e}")
            
        try:
            print("Trying chrome...")
            await p.chromium.launch_persistent_context('test_data', channel='chrome')
            print("chrome OK")
            return
        except Exception as e:
            print(f"chrome failed: {e}")
            
        try:
            print("Trying default chromium...")
            await p.chromium.launch_persistent_context('test_data')
            print("chromium OK")
            return
        except Exception as e:
            print(f"chromium failed: {e}")

asyncio.run(test())
