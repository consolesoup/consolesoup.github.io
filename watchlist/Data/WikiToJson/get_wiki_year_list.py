import wiki_to_json_common
import json
from bs4 import BeautifulSoup

def get_wiki_year_list():
    #----------------------------------
    # YearListデータの取得
    #----------------------------------
    title = "日本のテレビアニメ作品一覧"
    htmlText = wiki_to_json_common.get_wikipedia_html(title)
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
            linkdata["url"] = href
            yearList.append(linkdata)
    
    #----------------------------------
    # YearListデータの保存
    #----------------------------------
    yearListFileName = "YearList"
    with open(f"./Data/{yearListFileName}.json", "w", encoding="utf-8") as f:
        json.dump(yearList, f, ensure_ascii=False, indent=2)
    print(f"{yearListFileName} にリンクを保存しました。")

get_wiki_year_list()