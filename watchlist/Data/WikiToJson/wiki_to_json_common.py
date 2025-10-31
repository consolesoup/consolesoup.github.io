import requests
import urllib.parse

def get_wikipedia_html(title):
    if not title or title == None:
        print(f"×PageTitle is None")
        return None
    
    baseUrl = "https://ja.wikipedia.org/api/rest_v1/page/html/"
    url = None
    try:
        encoded_title = urllib.parse.quote(title)
        url = baseUrl+encoded_title
    except Exception as e:
        print(f"×Url Encode - {title}:{e}")
        return None
    
    if url == None or url == baseUrl:
        print(f"×Url Failed - {url}:{e}")
        return None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/requests"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"{title} のHTML取得に失敗 [{response.status_code}]")
        return None