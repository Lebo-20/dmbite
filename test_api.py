import asyncio
from api import get_drama_detail, get_all_episodes
import json

async def test():
    book_id = "14799"
    detail = await get_drama_detail(book_id)
    episodes = await get_all_episodes(book_id)
    
    output = {
        "detail": detail,
        "episodes_count": len(episodes),
        "first_episode": episodes[0] if episodes else None
    }
    
    with open("test_output.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Done. Saved to test_output.json")

if __name__ == "__main__":
    asyncio.run(test())
