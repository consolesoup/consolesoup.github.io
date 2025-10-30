import wiki_to_json_common
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime

def get_wiki_contents_list_from_year():
    #----------------------------------
    # YearListデータの取得
    #----------------------------------
    yearList = []
    with open("./Data/YearList.json", "r", encoding="utf-8") as f:
        yearList = json.load(f)
    #print(yearList)
    
    for yearData in yearList:
        #print(yearData)
        #----------------------------------
        # 年代別にコンテンツリスト取得
        #----------------------------------
        if "text" not in yearData: continue
        if "url" not in yearData:
            print(f"Jsonから{yearData.text}のurlが取得できませんでした")
            continue
        htmlText = wiki_to_json_common.get_wikipedia_html(yearData["url"])
        if not htmlText:
            print(f"{yearData["url"]}のHTMLが取得できませんでした")
            continue
        
        #----------------------------------
        # コンテンツリストの成型
        #----------------------------------
        contentsList = []
        # HTMLからSectionタグを検索
        html = BeautifulSoup(htmlText, "html.parser")
        sections = html.find_all("section")
        for section in sections:
            # Sectionタグから特定のHeaderタグを探す
            headerYear = 0
            headers = section.find_all(["h2", "h3"])
            for header in headers:
                headerId = header.get("id")
                index = headerId.find("年")
                if index == -1: continue
                #print(headerId)
                headerYear = int(headerId[:index])
                #print(headerYear)
                break
            if headerYear == 0: continue
            
            # Sectionタグから特定のTableタグを検索
            tables = section.find_all("table")
            for table in tables:
                if table.get("class") is None: continue
                if "wikitable" not in table.get("class"): continue
                # TableタグからTrタグを検索
                trs = table.find_all("tr")
                for tr in trs:
                    # TrタグからTdタグを検索
                    tds = tr.find_all("td")
                    if len(tds) <= 1: continue
                    
                    # 日付テキストの取得
                    timeText = tds[0].get_text()
                    try:
                        # 不要な文字列を削除
                        timeText = re.sub(r"\[.*?\]", "", timeText)
                        timeText = re.sub(r"(.*?)", "", timeText)
                        timeText = re.sub(r"（.*?）", "", timeText)
                        timeText = timeText.replace(" ","")
                        timeText = timeText.replace("-","")
                        timeText = timeText.replace("・","")
                    except Exception as e:
                        print(f"×get timeText:{e}\ntimeText[{timeText}]\nfrom[{tds[0].get_text()}]")
                    
                    # 日付テキストから日付データ生成
                    startTime = datetime(headerYear, 1, 1)
                    endTime = datetime(headerYear, 1, 1)
                    try:
                        # 開始-終了がある場合は配列化
                        times = []
                        if "日" in timeText:
                            times = timeText.split("日")
                        
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
                        
                        startTime = datetime.strptime(startTimeText, "%Y年%m月%d日")
                        endTime = datetime.strptime(endTimeText, "%Y年%m月%d日")
                    except Exception as e:
                        print(f"×text to time:{e}\ntimeText[{timeText}]\nfrom[{tds[0].get_text()}]")
                    
                    # タイトルを取得
                    title = None
                    url = None
                    try:
                        titleLink = tds[1].find("a")
                        if titleLink:
                            title = titleLink.get_text()
                            url = titleLink.get("href")
                        else:
                            title = tds[1].get_text()
                    except Exception as e:
                        print(f"×{tds[1]}:{e}")
                        continue
                    
                    contents = {}
                    contents["title"] = title
                    contents["url"] = url
                    contents["start_date"] = startTime.strftime("%Y/%m/%d")
                    contents["end_date"] = endTime.strftime("%Y/%m/%d")
                    contentsList.append(contents)
        
        #----------------------------------
        # コンテンツリストの保存
        #----------------------------------
        with open(f"./Data/{yearData["text"]}.json", "w", encoding="utf-8") as f:
            json.dump(contentsList, f, ensure_ascii=False, indent=2)
        print(f"{yearData["text"]}のコンテンツリストを保存しました。")

get_wiki_contents_list_from_year()