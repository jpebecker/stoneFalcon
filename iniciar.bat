@echo off
chcp 65001 >nul
cd /d "%~dp0"
title StoneFalcon
rem Variaveis opcionais: STONEFALCON_PORTA (padrao 8765), STONEFALCON_SEM_NAVEGADOR=1, STONEFALCON_SEM_PAUSA=1
set "PORTA=8765"
if defined STONEFALCON_PORTA set "PORTA=%STONEFALCON_PORTA%"
echo.
echo   StoneFalcon - ligando...
echo.

where python >nul 2>nul || (
  echo   O Python 3.11+ nao foi encontrado. Instale em https://www.python.org/downloads/ e marque "Add Python to PATH".
  goto :erro
)
python scripts\iniciar_ajuda.py python || goto :erro
python scripts\iniciar_ajuda.py porta %PORTA% || goto :erro

rem ---- front: compila na primeira vez e de novo sempre que a versao ou o codigo mudou (pasta que ja rodou uma versao anterior) ----
python scripts\iniciar_ajuda.py front
if errorlevel 10 (
  where npm >nul 2>nul || (
    echo   Falta compilar as telas e o Node.js nao foi encontrado.
    echo   Instale o Node.js LTS em https://nodejs.org e rode este arquivo de novo.
    goto :erro
  )
  echo   Compilando as telas - primeira vez ou depois de atualizar...
  call npm --prefix frontend install --no-audit --no-fund || goto :erro
  call npm --prefix frontend run build || goto :erro
  python scripts\iniciar_ajuda.py marcar-front || goto :erro
) else if errorlevel 1 (
  goto :erro
)

rem ---- back: ambiente Python isolado; reinstala as dependencias se o requirements.txt mudou ----
if not exist "backend\.venv\Scripts\python.exe" (
  echo   Preparando o ambiente Python - so na primeira vez...
  python -m venv backend\.venv || goto :erro
)
python scripts\iniciar_ajuda.py deps backend\.venv
if errorlevel 10 (
  echo   Instalando as dependencias do back - primeira vez ou depois de atualizar...
  backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt || goto :erro
  python scripts\iniciar_ajuda.py marcar-deps backend\.venv || goto :erro
) else if errorlevel 1 (
  goto :erro
)

echo   Abrindo http://localhost:%PORTA%  (para desligar: feche esta janela ou Ctrl+C)
if not defined STONEFALCON_SEM_NAVEGADOR start "" http://localhost:%PORTA%
backend\.venv\Scripts\python.exe -m uvicorn --app-dir backend app.main:app --port %PORTA%
goto :fim

:erro
echo.
echo   Nao foi possivel ligar o StoneFalcon. Leia a mensagem acima.
if not defined STONEFALCON_SEM_PAUSA pause
exit /b 1

:fim
if not defined STONEFALCON_SEM_PAUSA pause
