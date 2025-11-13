import JsonUtility
from bs4 import BeautifulSoup
import re
from datetime import datetime

def get_wiki_contents_list_from_year():
    # 年代リストデータの取得
    yearList = JsonUtility.load_json_file("./Data/YearList.json")
    if not isinstance(yearList,list):
        return
    #JsonUtility.Log(yearList)
    
    # 最初に自動更新するかどうか確認
    autoRequest = False
    inputValue = input(f"全ての年代別のコンテンツタイトルのリストを自動で取得した最新情報に更新しますか？[y/n]:")
    if inputValue == "y": autoRequest = True
    
    for yearData in yearList:
        #JsonUtility.Log(yearData)
        # 年代別にコンテンツリスト取得
        if "text" not in yearData: continue
        
        # 自動更新が無効の場合は更新するか確認する
        if not autoRequest:
            inputValue = input(f"{yearData["text"]}のコンテンツタイトルを自動で取得した最新情報に更新しますか？[y/n]:")
            if inputValue != "y": continue
        
        if "url" not in yearData:
            JsonUtility.Log(f"Jsonから{yearData.text}のurlが取得できませんでした")
            continue
        htmlText = JsonUtility.get_wikipedia_html(yearData["url"])
        if not htmlText:
            JsonUtility.Log(f"{yearData["url"]}のHTMLが取得できませんでした")
            continue
        
        # コンテンツリストの成型
        contentsList = []
        # HTMLからSectionタグを検索
        html = BeautifulSoup(htmlText, "html.parser")
        section_tags = html.find_all("section")
        for section_tag in section_tags:
            # Sectionタグから特定のHeaderタグを探す
            headerYear = 0
            header_tags = section_tag.find_all(["h2", "h3"])
            for header_tag in header_tags:
                header_id = header_tag.get("id")
                index = header_id.find("年")
                if index == -1: continue
                #JsonUtility.Log(header_id)
                headerYear = int(header_id[:index])
                #JsonUtility.Log(headerYear)
                break
            if headerYear == 0: continue
            
            # Sectionタグから特定のTableタグを検索
            table_tags = section_tag.find_all("table")
            for table_tag in table_tags:
                if table_tag.get("class") is None: continue
                if "wikitable" not in table_tag.get("class"): continue
                # TableタグからTrタグを検索
                tr_tags = table_tag.find_all("tr")
                for tr_tag in tr_tags:
                    # TrタグからTdタグを検索
                    td_tags = tr_tag.find_all("td")
                    if len(td_tags) <= 1: continue
                    
                    # 日付テキストの取得（1月7日 - 4月8日）
                    timeText = td_tags[0].get_text()
                    try:
                        # 不要な文字列を削除
                        timeText = re.sub(r"\[.*?\]", "", timeText)
                        timeText = re.sub(r"\(.*?\)", "", timeText)
                        timeText = re.sub(r"（.*?）", "", timeText)
                        timeText = timeText.replace(" ","")
                        timeText = timeText.replace("-","")
                        timeText = timeText.replace("・","")
                    except Exception as e:
                        JsonUtility.Log(f"×get timeText:{e}\ntimeText[{timeText}]\nfrom[{td_tags[0].get_text()}]")
                    #JsonUtility.Log(f"{timeText} from {tds[0].get_text()}")
                    
                    # 日付テキストから日付データ生成
                    startTime = datetime(headerYear, 1, 1)
                    endTime = datetime(headerYear, 1, 1)
                    try:
                        # 開始-終了がある場合は配列化
                        times = []
                        if "日" in timeText:
                            times = timeText.split("日")
                        #JsonUtility.Log(times)
                        
                        # 仮で年始を登録
                        startTimeText = startTime.strftime("%Y年%m月%d日")
                        endTimeText = endTime.strftime("%Y年%m月%d日")
                        
                        # 配列から日付情報として取得
                        if len(times) >= 1:
                            timeText0 = times[0]
                            if "月" in timeText0:
                                # 最後の文字が"月"の場合は何日かが無いので1日にする
                                if "月" == timeText0[-1]:
                                    timeText0 = f"{timeText0}1"
                                if "年" in timeText0:
                                    startTimeText = f"{timeText0}日"
                                else:
                                    startTimeText = f"{headerYear}年{timeText0}日"
                        if len(times) >= 2:
                            timeText1 = times[1]
                            if "月" in timeText1:
                                # 最後の文字が"月"の場合は何日かが無いので1日にする
                                if "月" == timeText1[-1]:
                                    timeText1 = f"{timeText1}1"
                                if "年" in timeText1:
                                    endTimeText = f"{timeText1}日"
                                else:
                                    endTimeText = f"{headerYear}年{timeText1}日"
                        
                        #JsonUtility.Log(f"{startTimeText} - {endTimeText}")
                        startTime = datetime.strptime(startTimeText, "%Y年%m月%d日")
                        endTime = datetime.strptime(endTimeText, "%Y年%m月%d日")
                        
                        # 終了日のほうが過去になっている場合は開始日と合わせる
                        if startTime > endTime:
                            endTime = startTime
                    except Exception as e:
                        JsonUtility.Log(f"×text to time:{e}\ntimeText[{timeText}]\nfrom[{td_tags[0].get_text()}]")
                    
                    # タイトルを取得
                    title = None
                    url = None
                    try:
                        titleLink = td_tags[1].find("a")
                        if titleLink:
                            title = titleLink.get_text()
                            url = titleLink.get("href")
                        else:
                            title = td_tags[1].get_text()
                    except Exception as e:
                        JsonUtility.Log(f"×{td_tags[1]}:{e}")
                        continue
                    
                    # まだ追加されていないコンテンツの場合はリストに追加する
                    startTimeText = startTime.strftime("%Y/%m/%d")
                    endTimeText = endTime.strftime("%Y/%m/%d")
                    jsonData = next((data for data in contentsList if title in data["title"] and startTimeText in data["start_date"] and endTimeText in data["end_date"]), None)
                    if jsonData:
                        JsonUtility.Log(f"　{title}（{startTimeText}～{endTimeText}）は既に追加されているためスキップ")
                    else:
                        contents = {}
                        contents["title"] = title
                        contents["url"] = url
                        contents["start_date"] = startTimeText
                        contents["end_date"] = endTimeText
                        contentsList.append(contents)
                        JsonUtility.Log(f"　{contents["start_date"]}～{contents["end_date"]}：{contents["title"]}")
        
        # コンテンツリストの保存
        JsonUtility.save_json_file(f"./Data/ContentsTitleList_{yearData["text"]}.json",contentsList)
        
        # ログファイル出力
        JsonUtility.SaveLogFile(f"./Data/Log/ContentsTitleList_{yearData["text"]}_Log.txt")

get_wiki_contents_list_from_year()