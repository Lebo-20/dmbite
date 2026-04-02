import httpx
import logging
import os

logger = logging.getLogger(__name__)

BASE_URL = "https://dramabite.dramabos.my.id"
AUTH_CODE = os.getenv("DRAMABITE_TOKEN", "A8D6AB170F7B89F2182561D3B32F390D")

async def get_drama_detail(book_id: str):
    url = f"{BASE_URL}/drama/{book_id}"
    params = {"lang": "id"}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching drama detail for {book_id}: {e}")
            return None

async def get_all_episodes(book_id: str):
    url = f"{BASE_URL}/episodes/{book_id}"
    params = {"lang": "id", "code": AUTH_CODE}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            # DramaBite returns a list of episodes directly
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching episodes for {book_id}: {e}")
            return []

async def get_latest_dramas(pages=1, types=None):
    """Fetches latest dramas from DramaBite /module recursive."""
    all_dramas = []
    async with httpx.AsyncClient(timeout=30) as client:
        for page in range(1, pages + 1):
            url = f"{BASE_URL}/module"
            params = {"page": page, "lang": "id"}
            try:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    videos = data.get("videos", [])
                    if not videos:
                        break
                    all_dramas.extend(videos)
                else:
                    break
            except Exception as e:
                logger.error(f"Error fetching module page {page}: {e}")
                break
    return all_dramas

async def get_home_dramas():
    """Fetches dramas from DramaBite home page modules."""
    url = f"{BASE_URL}/home"
    params = {"lang": "id"}
    all_items = []
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                module_list = data.get("module_list", [])
                for module in module_list:
                    items = module.get("module_item_list", [])
                    for item_wrapper in items:
                        item = item_wrapper.get("Item", {})
                        video_info = item.get("VideoInfo")
                        if video_info:
                            all_items.append(video_info)
        except Exception as e:
            logger.error(f"Error fetching home: {e}")
    return all_items

async def search_dramas(query: str):
    url = f"{BASE_URL}/search"
    params = {"q": query, "lang": "id"}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # DramaBite search returns a list directly
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error searching for {query}: {e}")
            return []

async def get_token():
    """Returns the auth token/code."""
    return AUTH_CODE

# Backwards compatibility names for main.py
get_latest_idramas = get_home_dramas
get_idrama_detail = get_drama_detail
get_idrama_all_episodes = get_all_episodes
