import JsonUtility
from bs4 import BeautifulSoup

def get_wiki_year_list():
    # 年代リストデータの取得
    htmlText = JsonUtility.get_wikipedia_html("日本のテレビアニメ作品一覧")
    if not htmlText: return
    
    # 年代リストデータの成型
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
            #JsonUtility.Log(header_id)
            break
        if not findHeader: continue
        
        # Sectionタグからaタグを検索
        a_tags = section_tag.find_all("a")
        for a_tag in a_tags:
            text = a_tag.get_text()
            if "年代" not in text: continue
            href = a_tag.get("href", "")
            if not href: continue
            
            yearText = text
            try:
                yearText = yearText.replace("(","")
                yearText = yearText.replace(")","")
                yearText = yearText.replace(" ","")
                yearText = yearText.replace("の","")
                yearText = yearText.replace("日本","")
                yearText = yearText.replace("テレビアニメ","")
                yearText = yearText.replace("作品一覧","")
            except Exception as e:
                JsonUtility.Log(f"×get yearText({yearText}):{e}")
                continue
            
            linkdata = {}
            linkdata["text"] = yearText
            linkdata["url"] = href
            yearList.append(linkdata)
            JsonUtility.Log(text)
    
    # 年代リストデータの保存
    JsonUtility.save_json_file("./Data/YearList.json",yearList)
    
    # ログファイル出力
    JsonUtility.SaveLogFile("./Data/Log/YearList_Log.txt")

get_wiki_year_list()