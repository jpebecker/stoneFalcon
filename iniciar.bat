@echo off
chcp 65001 >nul
cd /d "%~dp0"
title StoneFalcon
echo.
echo   StoneFalcon - ligando...
echo.

where python >nul 2>nul || (
  echo   O Python 3.11+ nao foi encontrado. Instale em https://www.python.org/downloads/ e marque "Add Python to PATH".
  pause & exit /b 1
)

rem ---- front: compila uma vez (precisa do Node.js so nesta primeira vez) ----
if not exist "frontend\dist\index.html" (
  where npm >nul 2>nul || (
    echo   Falta compilar as telas e o Node.js nao foi encontrado.
    echo   Instale o Node.js LTS em https://nodejs.org e rode este arquivo de novo.
    pause & exit /b 1
  )
  echo   Compilando as telas - so na primeira vez...
  call npm --prefix frontend install --no-audit --no-fund || (pause & exit /b 1)
  call npm --prefix frontend run build || (pause & exit /b 1)
)

rem ---- back: ambiente Python isolado ----
if not exist "backend\.venv\Scripts\python.exe" (
  echo   Preparando o ambiente Python - so na primeira vez...
  python -m venv backend\.venv || (pause & exit /b 1)
  backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt || (pause & exit /b 1)
)

echo   Abrindo http://localhost:8765  (para desligar: feche esta janela ou Ctrl+C)
start "" http://localhost:8765
backend\.venv\Scripts\python.exe -m uvicorn --app-dir backend app.main:app --port 8765
pause
