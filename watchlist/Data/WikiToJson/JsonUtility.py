import requests
import urllib.parse
import os
import json

# Wikiページ情報のHTML取得
def get_wikipedia_html(title):
    if not title or title == None:
        Log(f"✖{'\033[31m'}PageTitle is None{'\033[0m'}")
        return None
    
    baseUrl = "https://ja.wikipedia.org/api/rest_v1/page/html/"
    url = None
    try:
        encoded_title = urllib.parse.quote(title)
        url = baseUrl+encoded_title
        
        if url == None or url == baseUrl:
            Log(f"✖{'\033[31m'}Url Failed - {url}:{e}{'\033[0m'}")
            return None
    except Exception as e:
        Log(f"✖{'\033[31m'}Url Encode - {title}:{e}{'\033[0m'}")
        return None
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/requests"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if response.text:
            return response.text
        else:
            Log(f"✖{'\033[31m'}{title} のHTML取得に失敗 [{response.status_code}]{'\033[0m'}")
            return None
    except requests.exceptions.ConnectTimeout:
        Log(f"⚠{'\033[31m'}接続タイムアウト: {url}{'\033[0m'}")
        return None
    except requests.exceptions.RequestException as e:
        Log(f"✖{'\033[31m'}リクエストエラー: {e}{'\033[0m'}")
        return None

# Jsonファイルの保存
def save_json_file(path, data):
    if not FolderExist(os.path.dirname(path)):
        return False
    
    # ファイル保存処理
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        Log(f"{path}へ保存しました。")
        return True
    except Exception as e:
        Log(f"✖{'\033[31m'}save json file:{path} - {e}{'\033[0m'}")
        return False

# Jsonファイルのロード
def load_json_file(path):
    # ファイルが存在するかどうか
    try:
        if not os.path.isfile(path):
            return False
    except Exception as e:
        Log(f"✖{'\033[31m'}file not found:{path} - {e}{'\033[0m'}")
        return False
    
    # Jsonデータの取得
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        Log(f"✖{'\033[31m'}get json {path}:{e}{'\033[0m'}")
        return None

# 保存先フォルダが存在しなければ新規作成
def FolderExist(dirpath):
    try:
        if not os.path.isdir(dirpath):
            os.makedirs(dirpath)
    except Exception as e:
        Log(f"✖{'\033[31m'}save folder:{dirpath} - {e}{'\033[0m'}")
        return False
    
    return True

# ログ出力
LogList = []
def Log(message):
    print(message)
    LogList.append(message)

# ログの保存
def SaveLogFile(path):
    if not FolderExist(os.path.dirname(path)):
        return False
    
    # ファイル保存処理
    try:
        with open(path, "w", encoding="utf-8") as f:
            for logMessage in LogList:
                print(logMessage, file=f)
        
        LogList.clear()
        print(f"{path}へ保存しました。")
        return True
    except Exception as e:
        print(f"✖{'\033[31m'}save log file:{path} - {e}{'\033[0m'}")
        LogList.clear()
        return False