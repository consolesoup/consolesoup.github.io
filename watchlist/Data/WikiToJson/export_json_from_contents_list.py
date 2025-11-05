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
            print(f"　{contentsData["start_date"]}～{contentsData["end_date"]}：{"★" if contentsData["favorite"] else "☆"}-{"●" if contentsData["watch"] else "○"} - {contentsData["title"]}")
            print(f"　{contentsData["copyright"]}")
            print(f"　{contentsData["tag"]}")
        
        # Jsonの保存
        if wiki_to_json_common.save_json_file(jsonFilePath,contentsDataList):
            jsonFileData = {}
            jsonFileData["title"] = yearText
            jsonFileData["url"] = jsonFilePath
            saveJsonFileList.append(jsonFileData)
    
    # 保存したJsonのパスリストを保存
    wiki_to_json_common.save_json_file("../watchlist.json",saveJsonFileList)

# コンテンツ情報の初期化
def initialize_contents_data(contents):
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
def override_cache_contents_data(contentsData, cacheDataList):
    # キャッシュデータがlist型で中身がある場合のみ引き継ぎできる
    if isinstance(cacheDataList,list) or len(cacheDataList) == 0:
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
def update_wiki_contents_data(contentsData,url):
    # urlが指定されていない場合はそのまま返す
    if not isinstance(url,str):
        return contentsData
    
    # HTMLのテキストを取得
    htmlText = wiki_to_json_common.get_wikipedia_html(url)
    if not isinstance(htmlText,str):
        return contentsData
    #print(htmlText)
    
    staffDataList = []
    
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
            
            # 必要のない情報のヘッダーは処理スキップ
            skipHeaderList = [
                "概要","解説","作品解説","あらすじ","登場人物","ストーリー",
                "作品一覧","各話リスト","当時のテレビ欄での記載","オープニング（演出）","エンディング（演出）",
                "視聴率","商品化権の概念の確立","制作秘話","モノクロ版とカラー版",
                "漫画","単行本","コミカライズ","アニメ版","テレビアニメ","リメイク、派生作品","劇場版","映画",
                "評価","放送局","ネット配信","背景","番組内容","備考","その後",
                "声の出演","キャスト","メインキャスト",
                "現存する映像","放送時間","主題歌","主題歌・挿入歌","補足","豆知識","その他",
                "オリジナルビデオ","映像ソフト","ビデオソフト化","関連事項","脚注","参考文献","関連項目","外部リンク","前後番組"
            ]
            skipFlag = False
            for skipHeader in skipHeaderList:
                if skipHeader == header_id:
                    skipFlag = True
                    break
            if "の経緯" in header_id:
                skipFlag = True
            if skipFlag: continue
            
            # スタッフ・出演者から情報を取得
            if header_id == "スタッフ" or header_id == "出演者":
                li_tags = section_tag.find_all("li")
                for li_tag in li_tags:
                    li_tag_text = li_tag.get_text()
                    # listタグから区切り文字でスタッフ情報配列を作成
                    staff_data_list = []
                    if " - " in li_tag_text:
                        li_tag_text = li_tag_text.replace("ほか - "," - ")
                        staff_data_list = li_tag_text.split(" - ")
                    elif "：" in li_tag_text:
                        li_tag_text = li_tag_text.replace("ほか：","：")
                        staff_data_list = li_tag_text.split("：")
                    
                    # スタッフ情報配列が取得できなかった場合はスキップ
                    if len(staff_data_list) == 0:
                        print(f"staff_data_list is 0:{li_tag_text}")
                        continue
                    print(f"staff_data_list_text:{li_tag_text}")
                    
                    # 最初の要素から担当役職を取得
                    positions = []
                    position_text = staff_data_list.pop(0)
                    if "・" in position_text:
                        positions = position_text.split("・")
                    else:
                        positions = [position_text]
                    
                    # スタッフ情報の取得
                    for staff_data in staff_data_list:
                        # 不要な文字列を削除
                        staffText = staff_data
                        staffText = re.sub(r"\[.*?\]", "", staffText)
                        staffText = re.sub(r"\(.*?\)", "", staffText)
                        staffText = re.sub(r"（.*?）", "", staffText)
                        staffText = re.sub(r"※.*?\まで", "", staffText)
                        staffText = staffText.replace("　他","")
                        staffText = staffText.replace(" 他","")
                        staffText = staffText.replace("　ほか","")
                        staffText = staffText.replace(" ほか","")
                        staffText = staffText.replace("　","")
                        staffText = staffText.replace(" ","")
                        staffList = []
                        if "、" in staffText:
                            staffList = staffText.split("、")
                        else:
                            staffList = [staffText]
                        
                        # スタッフ情報リストの更新
                        for staff in staffList:
                            staffDataList = add_staff_data_list(staffDataList, staff, positions)
                continue
            
            # 認識していないヘッダーの場合はログ出力
            print(section_tag)
    
    contentsData["copyright"] = get_copyright_from_staff_data(staffDataList)
    
    return contentsData

# スタッフ情報リストの更新処理
def add_staff_data_list(staffDataList,staff,positions):
    if not isinstance(staffDataList,list):
        return []
    if not isinstance(staff,str):
        return staffDataList
    if not isinstance(positions,list):
        return staffDataList
    if len(positions) == 0:
        return staffDataList
    
    # スタッフ情報の初期化
    index = -1
    staffData = {}
    staffData["name"] = staff
    staffData["positions"] = []
                            
    # スタッフ情報が既にあれば取得
    for i, data in enumerate(staffDataList):
        if data["name"] != staff:
            continue
        staffData = data
        index = i
        break
                            
    # スタッフ情報の役職がlistじゃなければ初期化
    if not isinstance(staffData["positions"],list):
        staffData["positions"] = []
                            
    # スタッフ情報に役職が無ければ追加
    for position in positions:
        if position in staffData["positions"]:
            continue;
        staffData["positions"].append(position)
                            
    # スタッフ情報を更新
    if 0 <= index and index < len(staffDataList):
        staffDataList[index] = staffData
    else:
        staffDataList.append(staffData)

    return staffDataList

# スタッフ情報からCopyrightを作成
def get_copyright_from_staff_data(staffDataList):
    print("〇Copyright")
    copyrightList = []
    add_position_list = []
    
    if any("原作" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("原作")
    elif any("原案" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("原案")
    elif any("総監督" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("総監督")
    elif any("監督" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("監督")
    
    if any("原画" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("原画")
    
    if any("漫画" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("漫画")
    
    if any("企画" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("企画")
    elif any("製作" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("製作")
    elif any("制作" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("制作")
    elif any("アニメーション" in position for staff in staffDataList for position in staff["positions"]):
        add_position_list.append("アニメーション")
    
    for staffData in staffDataList:
        # 追加する要素か判別
        add_flag = False
        for position in add_position_list:
            if position in staffData["positions"]:
                add_flag = True
                break;
        
        # 必要なら追加する
        if add_flag:
            copyrightList.append(staffData)
            print(f"＋{staffData["name"]}：{staffData["positions"]}")
        else:
            print(f"　{staffData["name"]}：{staffData["positions"]}")
    
    return copyrightList

get_wiki_contents_list_from_year()