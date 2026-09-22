@echo off
chcp 65001 > nul
echo ===================================================
echo   財務AIダッシュボード (Life Science Financial AI)
echo ===================================================
echo Webアプリケーションを起動しています...
python -m streamlit run app.py
pause
