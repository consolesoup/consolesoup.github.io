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
                    print(f"✖{'\033[31m'}Jsonから{contentsData["title"]}のurlが取得できませんでした{'\033[0m'}")
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
    
    # infoboxのテーブルタグから作品情報を取得
    print("--------------------------------------------------")
    print("〇Get InfoboxData from Wiki")
    infoDataDict = {}
    tableTag = html.find("table", class_="infobox")
    if tableTag:
        tbodyTag = tableTag.find("tbody")
        if tbodyTag:
            # テーブルの中身をセル結合されたブロックごとに分別
            infoDataDict = {}
            mergedHeader = "None"
            trTags = tbodyTag.find_all("tr")
            for trTag in trTags:
                #print(trTag)
                # テーブルを行ごとに取得
                thTag = trTag.find("th")
                if not thTag:
                    # テンプレートにはthタグがないのが正常なので無視
                    if "./Template" not in str(trTag):
                        print(f"✖{'\033[31m'}{mergedHeader}のtrタグからthタグが取得できませんでした\n{trTag}{'\033[0m'}")
                    continue
                
                th_colspan = thTag.get("colspan")
                if th_colspan != None:
                   mergedHeader = thTag.get_text()
                else:
                    # ブロックごとのリスト作成
                    if mergedHeader not in infoDataDict or not isinstance(infoDataDict[mergedHeader],list):
                       infoDataDict[mergedHeader] = []
                    
                    # 各列のデータ作成
                    infoData = {}
                    
                    # tdタグの取得
                    tdTag = trTag.find("td")
                    if not tdTag:
                        print(f"✖{'\033[31m'}{mergedHeader}のtrタグからtdタグが取得できませんでした\n{trTag}{'\033[0m'}")
                        continue
                    
                    infoData["header"] = get_headers_from_table_th_tag(thTag)
                    infoData["data"] = get_datas_from_table_td_tag(tdTag)
                    infoDataDict[mergedHeader].append(infoData)
        else: print(f"　✖table(infobox) find not tbody: {tableTag}")
    else: print("　✖html find not table(infobox)")
    
    # infoboxのテーブルタグの作品情報からデータ取得
    if len(infoDataDict.keys()) > 0:
        print("--------------------------------------------------")
        print("〇Get ContentsData from InfoboxData")
        for mergedHeader in infoDataDict.keys():
            infoDataList = infoDataDict[mergedHeader]
            if not isinstance(infoDataList,list):
                print(f"◇{mergedHeader}：not list")
                continue
            
            # 結合セルのヘッダーから何の情報か判別
            copyrightHeaders = []
            if "アニメ" in mergedHeader:
                copyrightHeaders = ["製作","制作","アニメーション制作"]
                if "原作" in str(infoDataList): copyrightHeaders.append("原作")
                else: copyrightHeaders.append("監督")
                
                # アニメの場合は放送時期が違うデータの可能性があるので開始日で比較
                if "start_date" in contentsData:
                    startDateYear = datetime.strptime(contentsData["start_date"], "%Y/%m/%d").year
                    # 放送期間が書いてあるのに放送開始年が書いてない場合は期間外とする
                    if "放送期間" in str(infoDataList):
                        if str(startDateYear) not in str(infoDataList):
                            copyrightHeaders = []
                
                print(f"◇{mergedHeader}：アニメ")
            elif "漫画" in mergedHeader:
                copyrightHeaders = ["作者","原作","原案","作画","出版社","掲載誌"]
                
                print(f"◇{mergedHeader}：漫画")
            else:
                # ヘッダーにコンテンツ名が含まれている場合は一応追加する
                if "title" in contentsData:
                    if  contentsData["title"] in mergedHeader:
                        copyrightHeaders = ["制作","製作"]
                        if "原作" in str(infoDataList): copyrightHeaders.append("原作")
                        else: copyrightHeaders.append("監督")
                
                # ただし劇場版の作品は除外する
                if "映画" in mergedHeader: copyrightHeaders = []
                if "劇場版" in mergedHeader: copyrightHeaders = []
                
                print(f"◇{mergedHeader}：不明")
            
            # 追加項目が無い場合はスキップ
            if len(copyrightHeaders) == 0: continue
            print(f"Copyright：{copyrightHeaders}")
            
            for infoData in infoDataList:
                if "header" not in infoData or "data" not in infoData:
                    continue
                
                # コピーライトに追加する情報かどうか
                addCopyright = False
                for copyrightHeader in copyrightHeaders:
                    if copyrightHeader in infoData["header"]:
                        addCopyright = True
                        break
                
                if addCopyright:
                    # 重複しないようにリストに追加
                    for header in infoData["header"]:
                        for data in infoData["data"]:
                            contentsData["copyright"] = add_copyright_list(contentsData["copyright"],data,header)
    
    return contentsData

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

# infoboxのtable-thタグの文字列からヘッダー情報を取得
def get_headers_from_table_th_tag(tag:BeautifulSoup):
    # タグから文字列取得
    tagText = tag.get_text(separator="<br>", strip=True)
    headerText = remove_parentheses_text(tagText,["（）","[]"])
    
    # 区切り文字で配列化
    headerTexts = re.split(r"<br>|・", headerText)
    if len(headerTexts) == 0: headerTexts = [headerText]
    
    # 配列からヘッダーリストを作成
    headers = []
    for header in headerTexts:
        header = header.replace(" ","").replace("　","")
        if header.endswith("など"): header = header[:-2]
        if not header: continue
        headers.append(header)
    
    message = f"ヘッダー：{headers}"
    if headers != headerTexts:
        message += f" ← {headerTexts}"
    if headerTexts != [headerText]:
        message += f" ← {headerText}"
    if headerText != tagText:
        message += f" ← {tagText}"
    print(message)
    
    return headers

# infoboxのtable-tdタグの文字列からデータ情報を取得
def get_datas_from_table_td_tag(tag:BeautifulSoup):
    # タグから文字列取得
    tagText = tag.get_text(separator="<br>", strip=True)
    dataText = remove_parentheses_text(tagText,["（）","()","[]","「」","『』"])
    dataText = dataText.replace("<br>と<br>","<br>")
    dataText = dataText.replace("<br>・","<br>")
    dataText = dataText.replace("年<br>","年")
    dataText = dataText.replace("<br>-","、")
    
    # 区切り文字で配列化
    dataTexts = re.split(r"<br>|、", dataText)
    if len(dataTexts) == 0: dataTexts = [dataText]
    
    # 配列からデータリストを作成
    datas = []
    for data in dataTexts:
        data = data.replace(" ","").replace("　","")
        if data.startswith("→"): data = data[1:]
        if data.endswith("→"): data = data[:-1]
        if data.endswith("など"): data = data[:-2]
        if data.endswith("ほか"): data = data[:-2]
        if not data: continue
        elif data == "企画室": continue
        elif data == "第一部-第三部：": continue
        elif data == "第四部-第六部：": continue
        
        if data == "ムロタニ・ツネ象":
            data = "ムロタニツネ象"
        elif data == "武内つなよし/スタジオBell":
            data = "武内つなよし"
        elif data == "東京テレビ動画":
            data = "日本テレビ動画"
        elif data == "日本テレビ放送網":
            data = "日本テレビ"
        elif data == "テレビ東京メディアネット":
            data = "テレビ東京"
        elif data == "NET" or data == "NET日本教育テレビ":
            data = "テレビ朝日"
        elif data == "日本文華社":
            data = "ぶんか社"
        elif data == "円谷映像":
            data = "円谷プロ"
        elif data == "和光プロダクション":
            data = "ワコープロ"
        elif data == "創映社" or data == "サンライズスタジオ":
            data = "サンライズ"
        elif data == "竜の子プロダクション":
            data = "タツノコプロ"
        elif data == "虫プロダクション" or data == "虫プロ商事":
            data = "手塚プロダクション"
        elif data == "東映動画":
            data = "東映"
        elif data == "国際放映":
            data = "東宝"
        elif data == "ズイヨー映像":
            data = "瑞鷹"
        elif data == "TMS" or data == "東京ムービー新社":
            data = "トムス"
        elif data == "TCJ" or data == "TCJ動画センター":
            data = "エイケン"
        elif data == "旭通信社" or data == "第一動画" or data == "アサツーディ・ケイ" or data == "ADKエモーションズ":
            data = "ADKHD"
        elif data == "スタジオ・ゼロ":
            data = "スタジオゼロ"
        elif data == "Aプロダクション" or data == "Aプロ":
            data = "シンエイ動画"
        elif data == "フジテレビ・エンタプライズ" or data == "テレビ動画":
            data = "フジテレビ"
        elif "小学一年生" in data or "小学二年生" in data or "小学三年生" in data or "小学四年生" in data or "小学五年生" in data or "小学六年生" in data:
            data = "小学館の学年別学習雑誌"
        
        datas.append(data)
    
    message = f"データ　：{datas}"
    if datas != dataTexts:
        message += f" ← {dataTexts}"
    if dataTexts != [dataText]:
        message += f" ← {dataText}"
    if dataText != tagText:
        message += f" ← {tagText}"
    print(message)
    
    return datas

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

get_wiki_contents_data_from_title()