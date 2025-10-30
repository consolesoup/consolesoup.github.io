from os import link
import requests
import urllib.parse
import json
from bs4 import BeautifulSoup

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

def get_year_list():
    #----------------------------------
    # YearListデータの取得
    #----------------------------------
    title = "日本のテレビアニメ作品一覧"
    htmlText = get_wikipedia_html(title)
    if not htmlText: return
    
    #----------------------------------
    # YearListデータの成型
    #----------------------------------
    yearList = []
    # HTMLからSectionタグを検索
    html = BeautifulSoup(htmlText, "html.parser")
    sections = html.find_all("section")
    for section in sections:
        # Sectionタグから特定のHeaderタグを探す
        findHeader = False
        headers = section.find_all(["h2", "h3"])
        for header in headers:
            if "年代別" not in header.get("id"): continue
            findHeader = True
            #print(header.get("id"))
            break
        if not findHeader: continue
        
        # SectionタグからLinkタグを検索
        links = section.find_all("a")
        for link in links:
            text = link.get_text()
            if "年代" not in text: continue
            href = link.get("href", "")
            linkdata = {}
            linkdata["text"] = text
            linkdata["url"] = href.replace('./', '')
            yearList.append(linkdata)
    
    return yearList

def main():
    # YearListの取得
    yearList = get_year_list()
    
    # YearListの保存
    yearListFileName = "YearList"
    with open(f"./Data/{yearListFileName}.json", "w", encoding="utf-8") as f:
        json.dump(yearList, f, ensure_ascii=False, indent=2)
    print(f"{yearListFileName}を保存しました。")

if __name__ == "__main__":
    main()