import requests
import urllib.parse

def get_wikipedia_html(title):
    encoded_title = urllib.parse.quote(title)
    url = f"https://ja.wikipedia.org/api/rest_v1/page/html/{encoded_title}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/requests"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"{title} のHTML取得に失敗 [{response.status_code}]")
        return None