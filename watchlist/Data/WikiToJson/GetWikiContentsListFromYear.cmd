@echo off
chcp 65001

REM 必要なライブラリがなければインストール
python -m pip show requests >nul 2>&1
IF ERRORLEVEL 1 (
    echo requests をインストール中...
    python -m pip install requests
)

pip show beautifulsoup4 >nul 2>&1
IF ERRORLEVEL 1 (
    echo beautifulsoup4 をインストール中...
    pip install beautifulsoup4
)

REM Pythonスクリプトを実行
py get_wiki_contents_list_from_year.py

pause