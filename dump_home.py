import asyncio
import httpx
import json

async def dump_home_item():
    url = "https://dramabite.dramabos.my.id/home"
    params = {"lang": "id"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        
        module_list = data.get("module_list", [])
        if module_list:
            module = module_list[0]
            items = module.get("module_item_list", [])
            if items:
                print(f"SAMPLE ITEM JSON:\n{json.dumps(items[0], indent=2)}")

if __name__ == "__main__":
    asyncio.run(dump_home_item())
