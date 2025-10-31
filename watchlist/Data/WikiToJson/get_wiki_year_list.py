import wiki_to_json_common
import json
from bs4 import BeautifulSoup

def get_wiki_year_list():
    #----------------------------------
    # 年代リストデータの取得
    #----------------------------------
    htmlText = wiki_to_json_common.get_wikipedia_html("日本のテレビアニメ作品一覧")
    if not htmlText: return
    
    #----------------------------------
    # 年代リストデータの成型
    #----------------------------------
    yearList = []
    # HTMLからSectionタグを検索
    html = BeautifulSoup(htmlText, "html.parser")
    section_tags = html.find_all("section")
    for section_tag in section_tags:
        # Sectionタグから特定のHeaderタグを探す
        findHeader = False
        header_tags = section_tag.find_all(["h2", "h3"])
        for header_tag in header_tags:
            header_id = header_tag.get("id")
            if "年代別" not in header_id: continue
            findHeader = True
            #print(header_id)
            break
        if not findHeader: continue
        
        # Sectionタグからaタグを検索
        a_tags = section_tag.find_all("a")
        for a_tag in a_tags:
            text = a_tag.get_text()
            if "年代" not in text: continue
            href = a_tag.get("href", "")
            linkdata = {}
            linkdata["text"] = text
            linkdata["url"] = href
            yearList.append(linkdata)
            print(text)
    
    #----------------------------------
    # 年代リストデータの保存
    #----------------------------------
    yearListFileName = "YearList"
    with open(f"./Data/{yearListFileName}.json", "w", encoding="utf-8") as f:
        json.dump(yearList, f, ensure_ascii=False, indent=2)
    print(f"{yearListFileName} にリンクを保存しました。")

get_wiki_year_list()