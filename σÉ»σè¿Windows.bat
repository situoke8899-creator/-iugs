@echo off
cd /d "%~dp0"
if not exist .env (
 echo Please copy .env.example to .env and set a strong QUANT_ADMIN_TOKEN
 pause
 exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%A in (".env") do if "%%A"=="QUANT_ADMIN_TOKEN" set "QUANT_ADMIN_TOKEN=%%B"
if "%QUANT_ADMIN_TOKEN%"=="" (
 echo Missing admin token
 pause
 exit /b 1
)
python -m pip install -r requirements.txt
start "QuantLab API" cmd /k python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
python -m streamlit run dashboard.py
pause
