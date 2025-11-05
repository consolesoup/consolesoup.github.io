import requests
import urllib.parse
import json

# Wikiページ情報のHTML取得
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

# Jsonファイルの保存
def save_json_file(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"{path}へ保存しました。")
            return True
    except Exception as e:
        print(f"×save json file:{path} - {e}")
        return False

# Jsonファイルのロード
def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"×get YearList.json:{e}")
        return None