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
    
    # 最初に自動更新するかどうか確認
    autoYearRequest = False
    inputValue = input(f"全ての年代別のJsonを自動で作成して更新しますか？[y/n]:")
    if inputValue == "y": autoYearRequest = True
    autoWikiRequest = False
    inputValue = input(f"全ての年代別のコンテンツについてWikiページからデータを取得してコンテンツ情報を更新しますか？[y/n]:")
    if inputValue == "y": autoWikiRequest = True
    
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
        jsonFilePath = f"../WatchList/watchlist_{yearText}.json"
        #print(yearText)
        
        if not autoYearRequest:
            inputValue = input(f"{yearText}年のコンテンツリストからJsonを作成して更新しますか？[y/n]:")
            if inputValue != "y":
                print(f"{jsonFilePath}は更新せずに既存のものを再利用します。")
                
                jsonFileData = {}
                jsonFileData["title"] = yearText
                jsonFileData["url"] = jsonFilePath
                saveJsonFileList.append(jsonFileData)
                continue
        
        # 保存されているJsonデータを取得
        jsonList = []
        try:
            with open(jsonFilePath, "r", encoding="utf-8") as f:
                jsonList = json.load(f)
        except Exception as e:
            print(f"×get watchlist_{yearText}.json:{e}")
        
        # Jsonデータを最新に更新する
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
            
            if autoWikiRequest:
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
                            header2_tags = section_tag.find_all("h2")
                            for header_tag in header2_tags:
                                #print(header_tag)
                                header_id = header_tag.get("id")
                                print(f"●{header_id}●")
                                
                                if header_id == "概要":
                                    continue
                                elif header_id == "作品一覧":
                                    continue
                                elif header_id == "当時のテレビ欄での記載":
                                    continue
                                elif header_id == "「発見」の経緯":
                                    continue
                                elif header_id == "オープニング（演出）":
                                    continue
                                elif header_id == "エンディング（演出）":
                                    continue
                                elif header_id == "視聴率":
                                    continue
                                elif header_id == "各話リスト":
                                    continue
                                elif header_id == "商品化権の概念の確立":
                                    continue
                                elif header_id == "制作秘話":
                                    continue
                                elif header_id == "劇場版":
                                    continue
                                elif header_id == "評価":
                                    continue
                                elif header_id == "放送局":
                                    continue
                                elif header_id == "ネット配信":
                                    continue
                                elif header_id == "背景":
                                    continue
                                elif header_id == "出演者":
                                    li_tags = section_tag.find_all("li")
                                    for li_tag in li_tags:
                                        #print(li_tag)
                                        li_tag_text = li_tag.get_text()
                                        #print(f"text:{li_tag_text}")
                                        staffDataList = []
                                        if "：" in li_tag_text:
                                            staffDataList = li_tag_text.split("：")
                                        
                                        if len(staffDataList) == 0:
                                            print(f"text:{li_tag_text}")
                                        else:
                                            # 最初は担当役職なので削除
                                            position = staffDataList.pop(0)
                                            # お話
                                            for staffData in staffDataList:
                                                # 不要な文字列を削除
                                                staffData = re.sub(r"\[.*?\]", "", staffData)
                                                staffData = re.sub(r"\(.*?\)", "", staffData)
                                                staffData = re.sub(r"（.*?）", "", staffData)
                                                staffData = staffData.replace("　","")
                                                staffData = staffData.replace(" ","")
                                                staffList = []
                                                if "、" in staffData:
                                                    staffList = staffData.split("、")
                                                else:
                                                    staffList = [staffData]
                                                
                                                for staff in staffList:
                                                    # 担当者が追加されていなければ追加
                                                    if staff not in copyrightList:
                                                        copyrightList.append(staff)
                                                        print(f"{position} : {staff}")
                                elif header_id == "番組内容":
                                    continue
                                elif header_id == "備考":
                                    continue
                                elif header_id == "その後":
                                    continue
                                elif header_id == "スタッフ":
                                    li_tags = section_tag.find_all("li")
                                    for li_tag in li_tags:
                                        #print(li_tag)
                                        li_tag_text = li_tag.get_text()
                                        #print(f"text:{li_tag_text}")
                                        staffDataList = []
                                        if " - " in li_tag_text:
                                            staffDataList = li_tag_text.split(" - ")
                                        elif "：" in li_tag_text:
                                            staffDataList = li_tag_text.split("：")
                                        
                                        if len(staffDataList) == 0:
                                            print(f"text:{li_tag_text}")
                                        else:
                                            # 最初は担当役職なので削除
                                            position = staffDataList.pop(0)
                                            # 原案,作画,演出,音声,声の出演,製作
                                            # 演奏,原作,担当,構成と絵,音楽
                                            # 監督,助監督,演出・デザイン・作画,美術
                                            for staffData in staffDataList:
                                                # 不要な文字列を削除
                                                staffData = re.sub(r"\[.*?\]", "", staffData)
                                                staffData = re.sub(r"\(.*?\)", "", staffData)
                                                staffData = re.sub(r"（.*?）", "", staffData)
                                                staffData = staffData.replace("　","")
                                                staffData = staffData.replace(" ","")
                                                staffList = []
                                                if "、" in staffData:
                                                    staffList = staffData.split("、")
                                                else:
                                                    staffList = [staffData]
                                                
                                                for staff in staffList:
                                                    # 担当者が追加されていなければ追加
                                                    if staff not in copyrightList:
                                                        copyrightList.append(staff)
                                                        print(f"{position} : {staff}")
                                elif header_id == "補足":
                                    continue
                                elif header_id == "脚注":
                                    continue
                                elif header_id == "参考文献":
                                    continue
                                elif header_id == "関連項目":
                                    continue
                                elif header_id == "外部リンク":
                                    continue
                                else:
                                    print(section_tag)
                        
                        contentsData["copyright"] = copyrightList
                        #print(copyrightList)
                else:
                    print(f"Jsonから{yearData.text}のurlが取得できませんでした")
            else:
                print(f"作成済みのコンテンツ情報を参考にコンテンツ情報を作成しました。")
            
            newJsonList.append(contentsData)
            print(f"　{contentsData["start_date"]}～{contentsData["end_date"]}：{"★" if contentsData["favorite"] else "☆"}-{"●" if contentsData["watch"] else "○"} - {contentsData["title"]}")
            print(f"　{contentsData["copyright"]}")
            print(f"　{contentsData["tag"]}")
        
        # Jsonの保存
        try:
            with open(jsonFilePath, "w", encoding="utf-8") as f:
                json.dump(newJsonList, f, ensure_ascii=False, indent=2)
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
            json.dump(saveJsonFileList, f, ensure_ascii=False, indent=2)
            print(f"../watchlist.jsonへ保存しました。")
    except Exception as e:
        print(f"×save watchlist.json:{e}")

get_wiki_contents_list_from_year()