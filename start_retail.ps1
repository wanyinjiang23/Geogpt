$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\python.exe" -m streamlit run ui/retail_app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
