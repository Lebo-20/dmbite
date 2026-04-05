import asyncio
from api import get_latest_dramas, get_home_dramas
import json

async def test():
    rec_dramas = await get_latest_dramas(pages=1)
    home_dramas = await get_home_dramas()
    
    ids_in_rec = [str(d.get("cid") or d.get("id")) for d in rec_dramas]
    ids_in_home = [str(d.get("cid") or d.get("id")) for d in home_dramas]
    
    with open("processed.json", "r") as f:
        processed = json.load(f)
        
    print(f"IDs in Recent: {ids_in_rec[:5]}...")
    print(f"IDs in Home: {ids_in_home[:5]}...")
    print(f"IDs in Processed: {processed[:5]}...")
    
    # Are any recent dramas NOT in processed?
    new_in_rec = [i for i in ids_in_rec if i not in processed]
    new_in_home = [i for i in ids_in_home if i not in processed]
    
    print(f"New in Recent: {new_in_rec}")
    print(f"New in Home: {new_in_home}")

if __name__ == "__main__":
    asyncio.run(test())
