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
    autoRequest = False
    inputValue = input(f"全ての年代別のリストデータを自動で最新の情報を取得して更新しますか？[y/n]:")
    if inputValue == "y": autoRequest = True
    
    for yearData in yearList:
        #print(yearData)
        # 年代別にコンテンツリスト取得
        if "text" not in yearData: continue
        
        # 自動更新が無効の場合は更新するか確認する
        if not autoRequest:
            inputValue = input(f"{yearData["text"]}から最新の情報を取得して更新しますか？[y/n]:")
            if inputValue != "y": continue
        
        if "url" not in yearData:
            print(f"Jsonから{yearData.text}のurlが取得できませんでした")
            continue
        htmlText = wiki_to_json_common.get_wikipedia_html(yearData["url"])
        if not htmlText:
            print(f"{yearData["url"]}のHTMLが取得できませんでした")
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
                #print(header_id)
                headerYear = int(header_id[:index])
                #print(headerYear)
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
                        print(f"×get timeText:{e}\ntimeText[{timeText}]\nfrom[{td_tags[0].get_text()}]")
                    #print(f"{timeText} from {tds[0].get_text()}")
                    
                    # 日付テキストから日付データ生成
                    startTime = datetime(headerYear, 1, 1)
                    endTime = datetime(headerYear, 1, 1)
                    try:
                        # 開始-終了がある場合は配列化
                        times = []
                        if "日" in timeText:
                            times = timeText.split("日")
                        #print(times)
                        
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
                        
                        #print(f"{startTimeText} - {endTimeText}")
                        startTime = datetime.strptime(startTimeText, "%Y年%m月%d日")
                        endTime = datetime.strptime(endTimeText, "%Y年%m月%d日")
                        
                        # 終了日のほうが過去になっている場合は開始日と合わせる
                        if startTime > endTime:
                            endTime = startTime
                    except Exception as e:
                        print(f"×text to time:{e}\ntimeText[{timeText}]\nfrom[{td_tags[0].get_text()}]")
                    
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
                        print(f"×{td_tags[1]}:{e}")
                        continue
                    
                    contents = {}
                    contents["title"] = title
                    contents["url"] = url
                    contents["start_date"] = startTime.strftime("%Y/%m/%d")
                    contents["end_date"] = endTime.strftime("%Y/%m/%d")
                    contentsList.append(contents)
                    print(f"　{contents["start_date"]}～{contents["end_date"]}：{contents["title"]}")
        
        # コンテンツリストの保存
        with open(f"./Data/{yearData["text"]}.json", "w", encoding="utf-8") as f:
            json.dump(contentsList, f, ensure_ascii=False, indent=2)
        print(f"{yearData["text"]}のコンテンツリストを保存しました。")

get_wiki_contents_list_from_year()