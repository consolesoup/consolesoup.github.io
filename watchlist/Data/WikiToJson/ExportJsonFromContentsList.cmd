@echo off
chcp 65001

REM �K�v�ȃ��C�u�������Ȃ���΃C���X�g�[��
pip show beautifulsoup4 >nul 2>&1
IF ERRORLEVEL 1 (
    echo beautifulsoup4 ���C���X�g�[����...
    pip install beautifulsoup4
)

REM Python�X�N���v�g�����s
python export_json_from_contents_list.py

pause