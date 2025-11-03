@echo off
chcp 65001

REM 必要なライブラリがなければインストール
pip show beautifulsoup4 >nul 2>&1
IF ERRORLEVEL 1 (
    echo beautifulsoup4 をインストール中...
    pip install beautifulsoup4
)

REM Pythonスクリプトを実行
py export_json_from_contents_list.py

pause