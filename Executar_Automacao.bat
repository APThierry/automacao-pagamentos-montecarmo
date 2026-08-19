@echo off
title Monte Carmo Shopping - Automacao de Pagamentos
chcp 65001 > nul

echo ==================================================================
echo   MONTE CARMO SHOPPING - AUTOMAÇÃO DE PROGRAMAÇÃO DE PAGAMENTOS
echo ==================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Inicializando ambiente virtual de primeira execução...
    python -m venv .venv
    .\.venv\Scripts\pip.exe install -r requirements.txt
)

echo [INFO] Abrindo a interface grafica do sistema...
.\.venv\Scripts\python.exe gui.py

pause
