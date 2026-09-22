# 財務AIダッシュボード PowerShell 起動スクリプト
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  財務AIダッシュボード (Life Science Financial AI)" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Webアプリケーションを起動しています..." -ForegroundColor Yellow

python -m streamlit run app.py
