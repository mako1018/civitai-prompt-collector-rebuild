import requests
from config import settings

def fetch_prompts(limit=50):
    url = f"{settings['API_URL']}?limit={limit}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data.get("items", [])
