import httpx
import logging
import os

logger = logging.getLogger(__name__)

BASE_URL = "https://dramabite.dramabos.online"
AUTH_CODE = os.getenv("DRAMABITE_TOKEN", "A8D6AB170F7B89F2182561D3B32F390D")

_client = None

def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        # Browser-like headers to bypass Cloudflare and rate limits
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        _client = httpx.AsyncClient(timeout=60, headers=headers, follow_redirects=True)
    return _client

async def get_drama_detail(book_id: str):
    url = f"{BASE_URL}/drama/{book_id}"
    params = {"lang": "id"}
    client = get_client()
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            logger.error(f"API returned error for drama detail of {book_id}: {data['error']}")
            return None
        return data
    except Exception as e:
        logger.error(f"Error fetching drama detail for {book_id}: {e}")
        return None

async def get_all_episodes(book_id: str):
    url = f"{BASE_URL}/episodes/{book_id}"
    params = {"lang": "id", "code": AUTH_CODE}
    client = get_client()
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            logger.error(f"API returned error for episodes of {book_id}: {data['error']}")
            return []
        if not isinstance(data, list):
            logger.error(f"API returned unexpected data type for episodes of {book_id}: {type(data)}")
            return []
        return data
    except Exception as e:
        logger.error(f"Error fetching episodes for {book_id}: {e}")
        return []

async def get_latest_dramas(pages=1, types=None):
    """Fetches latest dramas from DramaBite /module recursive."""
    all_dramas = []
    client = get_client()
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
    client = get_client()
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
    client = get_client()
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
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
