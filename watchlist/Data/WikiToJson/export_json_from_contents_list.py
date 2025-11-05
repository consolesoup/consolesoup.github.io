import wiki_to_json_common
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime

def get_wiki_contents_list_from_year():
    # 年代リストデータの取得
    yearList = wiki_to_json_common.load_json_file("./Data/YearList.json")
    if not isinstance(yearList,list):
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
        contentsList = wiki_to_json_common.load_json_file(f"./Data/{yearData["text"]}.json")
        if not isinstance(contentsList,list):
            return
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
        
        # 保存されているJsonデータをキャッシュデータとして取得
        cacheDataList = wiki_to_json_common.load_json_file(jsonFilePath)
        if not isinstance(cacheDataList,list):
            cacheDataList = []
        
        # Jsonデータを最新に更新する
        contentsDataList = []
        for contents in contentsList:
            # コンテンツのバリデーションチェック
            if "title" not in contents: continue
            if "start_date" not in contents: continue
            if "end_date" not in contents: continue
            
            # コンテンツ情報の初期化
            contentsData = initialize_contents_data(contents)
            
            # 作成済みの同じコンテンツデータ取得
            contentsData = override_cache_contents_data(contentsData,cacheDataList)
            
            # Wikiから最新の情報を取得するかどうか
            wikiRequest = False
            if autoWikiRequest: wikiRequest = True
            else:
                print("===============================")
                inputValue = input(f"{contentsData["title"]}についてWikiページからデータを取得してコンテンツ情報を更新しますか？[y/n]:")
                if inputValue == "y": wikiRequest = True
            
            if wikiRequest:
                if "url" in contents:
                    # Wikiからコンテンツ情報を最新に更新する
                    contentsData = update_wiki_contents_data(contentsData,contents["url"])
                else:
                    print(f"Jsonから{contentsData["title"]}のurlが取得できませんでした")
            else:
                print(f"作成済みのコンテンツ情報を参考にコンテンツ情報を作成しました。")
            
            contentsDataList.append(contentsData)
            print("------Export ContentsData------")
            print(f"{contentsData["start_date"]}～{contentsData["end_date"]}：{"★" if contentsData["favorite"] else "☆"}-{"●" if contentsData["watch"] else "○"} - {contentsData["title"]}")
            print(f"{contentsData["copyright"]}")
            print(f"{contentsData["tag"]}")
        
        # Jsonの保存
        if wiki_to_json_common.save_json_file(jsonFilePath,contentsDataList):
            jsonFileData = {}
            jsonFileData["title"] = yearText
            jsonFileData["url"] = jsonFilePath
            saveJsonFileList.append(jsonFileData)
    
    # 保存したJsonのパスリストを保存
    wiki_to_json_common.save_json_file("../watchlist.json",saveJsonFileList)

# コンテンツ情報の初期化
def initialize_contents_data(contents:dict):
    contentsData = {}
    if "title" in contents:
        contentsData["title"] = contents["title"]
    
    # 放送期間
    if "start_date" in contents:
        contentsData["start_date"] = contents["start_date"]
    if "end_date" in contents:
        contentsData["end_date"] = contents["end_date"]
    
    # コメント/コピーライト/タグを初期化
    contentsData["comment"] = ""
    contentsData["copyright"] = []
    contentsData["tag"] = []
    contentsData["watch"] = False
    contentsData["favorite"] = False
    return contentsData

# コンテンツ情報へキャッシュデータから必要な情報を引き継ぎ
def override_cache_contents_data(contentsData:dict, cacheDataList:list):
    # キャッシュデータがlist型で中身がある場合のみ引き継ぎできる
    if len(cacheDataList) == 0:
        return contentsData
    
    # キャッシュデータから一致するコンテンツ情報を取得
    jsonData = next((cacheData for cacheData in cacheDataList if contentsData["title"] == cacheData["title"]), None)
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
    return contentsData

# Wikiからコンテンツ情報を最新に更新する
def update_wiki_contents_data(contentsData:dict, url:str):
    # HTMLのテキストを取得
    htmlText = wiki_to_json_common.get_wikipedia_html(url)
    if not isinstance(htmlText,str):
        return contentsData
    #print(htmlText)
    html = BeautifulSoup(htmlText, "html.parser")
    
    contentsData["copyright"] = get_copyright_from_wiki(html)
    
    return contentsData

# WikiページからCopyrightを作成
def get_copyright_from_wiki(html:BeautifulSoup):
    print("------Copyright from Wiki------")
    copyrightList = []
    
    # infoboxのテーブルタグから作品情報を取得
    tableTag = html.find("table", class_="infobox")
    if tableTag:
        tbodyTag = tableTag.find("tbody")
        if tbodyTag:
            trTags = tbodyTag.find_all("tr")
            animeTrFlag = False
            for trTag in trTags:
                thTag = trTag.find("th")
                if not thTag: continue
                
                thText = thTag.get_text()
                if "アニメ" in thText:
                    print(f"〇{thText}")
                    animeTrFlag = True
                elif animeTrFlag:
                    tdTag = trTag.find("td")
                    if tdTag:
                        if "原作" in thText:
                            print(f"＋{thText}：{tdTag.get_text()}")
                        elif "監督" in thText:
                            print(f"＋{thText}：{tdTag.get_text()}")
                        elif "製作" in thText:
                            print(f"＋{thText}：{tdTag.get_text()}")
                        elif "制作" in thText:
                            print(f"＋{thText}：{tdTag.get_text()}")
                        else: print(f"　{thText}：{tdTag.get_text()}")
                else: print(f"　{thText}")
        else: print(f"table(infobox) find not tbody: {tableTag}")
    else: print("html find not table(infobox)")
    
    return copyrightList

get_wiki_contents_list_from_year()