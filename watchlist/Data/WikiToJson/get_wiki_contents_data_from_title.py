from turtle import position
import wiki_to_json_common
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime

def get_wiki_contents_data_from_title():
    # 年代リストデータの取得
    yearList = wiki_to_json_common.load_json_file("./Data/YearList.json")
    if not isinstance(yearList,list):
        return
    #print(yearList)
    
    # 最初に自動更新するかどうか確認
    autoRequest = False
    inputValue = input(f"全ての年代別のコンテンツ詳細データを全件自動で最新情報に更新しますか？[y/n]:")
    if inputValue == "y": autoRequest = True
    
    for yearData in yearList:
        if "text" not in yearData: continue
        
        # 自動更新が無効の場合は更新するか確認する
        if not autoRequest:
            inputValue = input(f"{yearData["text"]}のコンテンツ詳細データを最新情報に更新しますか？[y/n]:")
            if inputValue != "y": continue
        
        yearAutoRequest = False
        if autoRequest: yearAutoRequest = True
        else:
            inputValue = input(f"{yearData["text"]}のコンテンツ詳細データを全件自動で最新情報に更新しますか？[y/n]:")
            if inputValue == "y": yearAutoRequest = True
        
        # コンテンツタイトルリスト取得
        contentsTitleListPath = f"./Data/ContentsTitleList/{yearData["text"]}.json"
        contentsTitleList = wiki_to_json_common.load_json_file(contentsTitleListPath)
        if not isinstance(contentsTitleList,list): continue
        #print(contentsList)
        
        # コンテンツ詳細データを最新に更新する
        contentsDataList = []
        for contentsTitleData in contentsTitleList:
            # コンテンツのバリデーションチェック
            if "title" not in contentsTitleData: continue
            if "start_date" not in contentsTitleData: continue
            if "end_date" not in contentsTitleData: continue
            print("==================================================")
            
            # コンテンツ情報の初期化
            contentsData = initialize_contents_data(contentsTitleData)
            
            # 自動更新が無効の場合は更新するか確認する
            contentsAutoRequest = False
            if yearAutoRequest: contentsAutoRequest = True
            else:
                inputValue = input(f"{contentsData["title"]}についてWikiページからデータを取得してコンテンツ詳細情報を更新しますか？[y/n]:")
                if inputValue == "y": contentsAutoRequest = True
            
            if contentsAutoRequest:
                if "url" in contentsTitleData:
                    # Wikiからコンテンツ情報を最新に更新する
                    contentsData = update_wiki_contents_data(contentsData,contentsTitleData["url"])
                else:
                    print(f"{'\033[31m'}Jsonから{contentsData["title"]}のurlが取得できませんでした{'\033[0m'}")
            else:
                print(f"コンテンツタイトルから仮のコンテンツ詳細情報を作成しました。")
            
            contentsDataList.append(contentsData)
            print("--------------------------------------------------")
            print("〇Export ContentsData")
            print(f"　{contentsData["start_date"]}～{contentsData["end_date"]}：{contentsData["title"]}")
            print(f"　{contentsData["copyright"]}")
            print(f"　{contentsData["tag"]}")
        
        # コンテンツ詳細データリストの保存
        wiki_to_json_common.save_json_file(f"./Data/ContentsDataList/{yearData["text"]}.json",contentsDataList)

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
    contentsData["copyright"] = []
    contentsData["tag"] = []
    return contentsData

# Wikiからコンテンツ情報を最新に更新する
def update_wiki_contents_data(contentsData:dict, url:str):
    # HTMLのテキストを取得
    htmlText = wiki_to_json_common.get_wikipedia_html(url)
    if not isinstance(htmlText,str):
        return contentsData
    #print(htmlText)
    html = BeautifulSoup(htmlText, "html.parser")
    
    contentsData["copyright"] = get_copyright_from_wiki(html,contentsData)
    
    return contentsData

# WikiページからCopyrightを作成
def get_copyright_from_wiki(html:BeautifulSoup,contentsData:dict):
    copyrightList = []
    
    # infoboxのテーブルタグから作品情報を取得
    print("--------------------------------------------------")
    print("〇Copyright from infobox in Wiki")
    tableTag = html.find("table", class_="infobox")
    if tableTag:
        tbodyTag = tableTag.find("tbody")
        if tbodyTag:
            # テーブルの中身をセル結合されたブロックごとに分別
            infoDataDict = {}
            infoTitle = "None"
            inOrigin = False
            trTags = tbodyTag.find_all("tr")
            for trTag in trTags:
                #print(trTag)
                # テーブルを行ごとに取得
                thTag = trTag.find("th")
                if not thTag: continue
                
                th_colspan = thTag.get("colspan")
                if th_colspan != None: infoTitle = thTag.get_text()
                else:
                    if infoTitle not in infoDataDict or not isinstance(infoDataDict[infoTitle],list):
                       infoDataDict[infoTitle] = []
                    
                    infoDataDict[infoTitle].append(trTag)
                    if "原作" in trTag.get_text(): inOrigin = True
            
            # InfoDatasから情報取得
            for key in infoDataDict.keys():
                print(f"◇{key}")
                addPositions = []
                inBroadcastTime = True
                
                infoDataList = infoDataDict[key]
                if not isinstance(infoDataList,list): continue
                
                if "アニメ" in key:
                    addPositions = ["製作","制作","アニメーション制作"]
                    if inOrigin: addPositions.append("原作")
                    else: addPositions.append("監督")
                    
                    # アニメの場合は放送時期が違うデータの可能性があるので開始日で比較
                    if "start_date" in contentsData:
                        startDateYear = datetime.strptime(contentsData["start_date"], "%Y/%m/%d").year
                        inBroadcastTime = False
                        for trTag in infoDataList:
                            if "放送期間" not in trTag.get_text(): continue
                            if str(startDateYear) not in trTag.get_text(): continue
                            inBroadcastTime = True
                elif "漫画" in key:
                    addPositions = ["作者","原作","原案","作画","出版社","掲載誌"]
                elif "title" in contentsData and contentsData["title"] in key and "映画" not in key:
                    addPositions = ["制作","製作"]
                    if inOrigin: addPositions.append("原作")
                    else: addPositions.append("監督")
                else: continue
                print(f"追加対象：{addPositions}")
                
                for trTag in infoDataList:
                    # thタグの取得
                    thTag = trTag.find("th")
                    if not thTag:
                        print(f"{'\033[31m'}{key}のtrタグからthタグが取得できませんでした\n{trTag}{'\033[0m'}")
                        continue
                    
                    # tdタグの取得
                    tdTag = trTag.find("td")
                    if not tdTag:
                        print(f"{'\033[31m'}{key}のtrタグからtdタグが取得できませんでした\n{trTag}{'\033[0m'}")
                        continue
                    
                    # thタグから役職リストを取得
                    positions = get_positions_from_tag(thTag)
                    # tdタグから名前リストを取得
                    names = get_names_from_tag(tdTag)
                    
                    # コピーライトに追加する情報かどうか
                    addCopyright = False
                    for addPosition in addPositions:
                        if addPosition in positions:
                            addCopyright = True
                            break
                    
                    if addCopyright and inBroadcastTime:
                        # 重複しないようにリストに追加
                        for name in names:
                            for position in positions:
                                copyrightList = add_copyright_list(copyrightList,name,position)
                        print(f"＋{positions}：{names}")
                    else:
                        print(f"　{positions}：{names}")
        else: print(f"　table(infobox) find not tbody: {tableTag}")
    else: print("　html find not table(infobox)")
    
    return copyrightList

# コピーライト情報リストにデータ追加
def add_copyright_list(copyrightList:list,name:str,position:str):
    # リストから一致するデータを取得
    index = -1
    copyrightData = {}
    copyrightData["name"] = name
    for i, copyright in enumerate(copyrightList):
        if "name" not in copyright:
            continue
        if copyright["name"] == name:
            copyrightData = copyright
            index = i
            break
    
    # データの役職リストの型チェック
    if "positions" not in copyrightData:
        copyrightData["positions"] = []
    if not isinstance(copyrightData["positions"],list):
        copyrightData["positions"] = []
    
    # データの役職リストに役職を追加
    if position not in copyrightData["positions"]:
        copyrightData["positions"].append(position)
    
    if 0 <= index and index < len(copyrightList):
        copyrightList[index] = copyrightData
    else: copyrightList.append(copyrightData)
    
    return copyrightList

# 文字列から括弧とその中の文字を消す
def remove_parentheses_text(text:str,parentheses:list):
    removeText = ""
    parenthesesCount = {}
    for keyText in parentheses:
        if len(keyText) < 2:
            continue
        parenthesesCount[keyText] = 0
    
    # 括弧とその中の文字以外を取得
    for char in text:
        # 括弧が始まるか
        for keyText in parenthesesCount.keys():
            if char == keyText[0]:
                parenthesesCount[keyText] = parenthesesCount[keyText]+1
                        
        # 括弧の中にいるか
        inParentheses = False
        for keyText in parenthesesCount.keys():
            if parenthesesCount[keyText] > 0:
                inParentheses = True
                break
                        
        # 括弧の外の文字なら追加
        if not inParentheses:
            removeText = removeText+char
                        
        # 括弧が終わるか
        for keyText in parenthesesCount.keys():
            if char == keyText[1]:
                parenthesesCount[keyText] = parenthesesCount[keyText]-1
    
    return removeText

# infoboxのtable-thタグの文字列から役職情報を取得
def get_positions_from_tag(tag:BeautifulSoup):
    # タグから文字列取得
    tagText = tag.get_text(separator="<br>", strip=True)
    positionText = remove_parentheses_text(tagText,["（）","[]"])
    
    # 区切り文字で配列化
    positionTexts = re.split(r"<br>|・", positionText)
    if len(positionTexts) == 0: positionTexts = [positionText]
    
    # 配列から役職リストを作成
    positions = []
    for position in positionTexts:
        position = position.replace(" ","").replace("　","")
        if position.endswith("など"): position = position[:-2]
        if not position: continue
        positions.append(position)
    
    message = f"　役職：{positions}"
    if positions != positionTexts:
        message += f" ← {positionTexts}"
    if positionTexts != [positionText]:
        message += f" ← {positionText}"
    if positionText != tagText:
        message += f" ← {tagText}"
    print(message)
    
    return positions

# infoboxのtable-tdタグの文字列から名前情報を取得
def get_names_from_tag(tag:BeautifulSoup):
    # タグから文字列取得
    tagText = tag.get_text(separator="<br>", strip=True)
    nameText = remove_parentheses_text(tagText,["（）","()","[]","「」","『』"])
    nameText = nameText.replace("<br>と<br>","<br>")
    nameText = nameText.replace("<br>・","<br>")
    
    # 区切り文字で配列化
    nameTexts = re.split(r"<br>|、", nameText)
    if len(nameTexts) == 0: nameTexts = [nameText]
    
    # 配列から名前リストを作成
    names = []
    for name in nameTexts:
        name = name.replace(" ","").replace("　","")
        if name.startswith("→"): name = name[1:]
        if name.endswith("→"): name = name[:-1]
        if name.endswith("など"): name = name[:-2]
        if name.endswith("ほか"): name = name[:-2]
        if not name: continue
        
        if name == "虫プロダクション" or name == "虫プロ商事" or name == "手塚プロダクション":
            name = "手塚プロ"
        if name == "竜の子プロダクション":
            nema = "タツノコプロ"
        if name == "日本テレビ放送網":
            name = "日本テレビ"
        if name == "フジテレビ・エンタプライズ":
            name = "フジテレビ"
        if name == "東映動画":
            name = "東映"
        if name == "東京ムービー新社" or name == "TMS":
            name = "トムス"
        if name == "スタジオ・ゼロ":
            name = "スタジオゼロ"
        
        names.append(name)
    
    message = f"　名前：{names}"
    if names != nameTexts:
        message += f" ← {nameTexts}"
    if nameTexts != [nameText]:
        message += f" ← {nameText}"
    if nameText != tagText:
        message += f" ← {tagText}"
    print(message)
    
    return names

get_wiki_contents_data_from_title()