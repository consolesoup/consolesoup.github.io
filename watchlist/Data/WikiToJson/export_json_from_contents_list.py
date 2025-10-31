import wiki_to_json_common
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime

def get_wiki_contents_list_from_year():
    # 年代リストデータの取得
    yearList = []
    try:
        with open("./Data/YearList.json", "r", encoding="utf-8") as f:
            yearList = json.load(f)
    except Exception as e:
        print(f"×get YearList.json:{e}")
        return
    #print(yearList)
    
    saveJsonFileList = []
    for yearData in yearList:
        # コンテンツリスト取得
        if "text" not in yearData: continue
        contentsList = []
        try:
            with open(f"./Data/{yearData["text"]}.json", "r", encoding="utf-8") as f:
                contentsList = json.load(f)
        except Exception as e:
            print(f"×get {yearData["text"]}.json:{e}")
            continue
        #print(contentsList)
        
        # 作成済みJson取得
        yearText = yearData["text"]
        try:
            yearText = yearText.replace("(","")
            yearText = yearText.replace(")","")
            yearText = yearText.replace(" ","")
            yearText = yearText.replace("の","")
            yearText = yearText.replace("日本","")
            yearText = yearText.replace("テレビアニメ","")
            yearText = yearText.replace("作品一覧","")
        except Exception as e:
            print(f"×get yearText:{e}\nyearText[{yearText}]\nfrom[{yearData["text"]}]")
        #print(yearText)
        
        inputValue = input(f"{yearText}年のコンテンツリストからJsonを作成して更新しますか？[y/n]:")
        if inputValue != "y": continue
        
        jsonList = []
        jsonFilePath = f"../WatchList/watchlist_{yearText}.json"
        try:
            with open(jsonFilePath, "r", encoding="utf-8") as f:
                jsonList = json.load(f)
        except Exception as e:
            print(f"×get watchlist_{yearText}.json:{e}")
        
        # コンテンツリストを詳細にしてJsonデータにする
        newJsonList = []
        for contents in contentsList:
            # コンテンツタイトル取得
            if "title" not in contents: continue
            contentsData = {}
            contentsData["title"] = contents["title"]
            
            # 放送期間
            if "start_date" not in contents: continue
            contentsData["start_date"] = contents["start_date"]
            if "end_date" not in contents: continue
            contentsData["end_date"] = contents["end_date"]
            
            # コメント/コピーライト/タグを初期化
            contentsData["comment"] = ""
            contentsData["copyright"] = []
            contentsData["tag"] = []
            contentsData["watch"] = False
            contentsData["favorite"] = False
            
            # 作成済みの同じコンテンツデータ取得
            jsonData = next((data for data in jsonList if contentsData["title"] in data["title"]), None)
            if jsonData:
                # print(jsonData)
                # 設定をコピー
                if "comment" in jsonData:
                    contentsData["comment"] = jsonData["comment"]
                if "copyright" in jsonData:
                    contentsData["copyright"] = jsonData["copyright"]
                if "tag" in jsonData:
                    contentsData["tag"] = jsonData["tag"]
                if "watch" in jsonData:
                    contentsData["watch"] = jsonData["watch"]
                if "favorite" in jsonData:
                    contentsData["favorite"] = jsonData["favorite"]
            
            if "url" in contents:
                htmlText = wiki_to_json_common.get_wikipedia_html(contents["url"])
                if htmlText:
                    #print(htmlText)
                    
                    copyrightList = []
                    
                    # HTMLからSectionタグを検索
                    html = BeautifulSoup(htmlText, "html.parser")
                    section_tags = html.find_all("section")
                    for section_tag in section_tags:
                        #print(section_tag)
                        # SectionタグからHeaderタグを検索
                        header_tags = section_tag.find_all(["h2", "h3"])
                        for header_tag in header_tags:
                            #print(header_tag)
                            header_id = header_tag.get("id")
                            print(f"●{header_id}●")
                            
                            # スタッフ情報から制作陣を取得
                            if header_id == "スタッフ":
                                li_tags = section_tag.find_all("li")
                                for li_tag in li_tags:
                                    #print(li_tag)
                                    li_tag_text = li_tag.get_text()
                                    #print(f"text:{li_tag_text}")
                                    staffData = li_tag_text.split(" - ")
                                    index = 0
                                    for staff in staffData:
                                        if index == 0:
                                            # 最初は担当役職なので無視
                                            index = 1
                                        else:
                                            # 2つ目以降は担当者なので追加されていなければ追加
                                            index = index+1
                                            if staff not in copyrightList:
                                                copyrightList.append(staff)
                            else:
                                print(section_tag)
                    
                    contentsData["copyright"] = copyrightList
                    #print(copyrightList)
            else:
                print(f"Jsonから{yearData.text}のurlが取得できませんでした")
            
            newJsonList.append(contentsData)
            print(f"　{contentsData["start_date"]}～{contentsData["end_date"]}：{"★" if contentsData["favorite"] else "☆"}-{"●" if contentsData["watch"] else "○"} - {contentsData["title"]}")
            print(f"　{contentsData["copyright"]}")
            print(f"　{contentsData["tag"]}")
        
        # Jsonの保存
        try:
            with open(jsonFilePath, "w", encoding="utf-8") as f:
                #json.dump(newJsonList, f, ensure_ascii=False, indent=2)
                print(f"{jsonFilePath}へ保存しました。")
                
                jsonFileData = {}
                jsonFileData["title"] = yearText
                jsonFileData["url"] = jsonFilePath
                saveJsonFileList.append(jsonFileData)
        except Exception as e:
            print(f"×save watchlist_{yearText}.json:{e}")
    
    # 保存したJsonのパスリストを保存
    try:
        with open("../watchlist.json", "w", encoding="utf-8") as f:
            #json.dump(saveJsonFileList, f, ensure_ascii=False, indent=2)
            print(f"../watchlist.jsonへ保存しました。")
    except Exception as e:
        print(f"×save watchlist.json:{e}")

get_wiki_contents_list_from_year()