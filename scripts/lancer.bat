@echo off
rem ==========================================================
rem  Findrive Assistant - lancement du projet (Windows)
rem  Double-cliquez sur ce fichier, ou dans un terminal :
rem     scripts\lancer.bat          lance l'application
rem     scripts\lancer.bat tests    execute les tests automatises
rem ==========================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo.
echo   Findrive Assistant - Assistant de recherche automobile
echo   ------------------------------------------------
echo.

rem --- 1. Trouver Python (lanceur "py" ou "python")
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERREUR] Python est introuvable. Installez Python 3.10 ou plus recent
    echo          depuis https://www.python.org/downloads/ en cochant "Add Python to PATH".
    goto :fin_erreur
)
for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo [OK] %%v

rem --- 2. Installer les dependances si necessaire
%PY% -c "import streamlit, pytest" >nul 2>nul
if errorlevel 1 (
    echo [..] Installation des dependances ^(streamlit, pytest^)...
    %PY% -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [ERREUR] L'installation des dependances a echoue.
        goto :fin_erreur
    )
)
echo [OK] Dependances presentes

rem --- 3. Generer la base de donnees si elle est absente
if not exist "data\cars.json" (
    echo [..] Generation de cars.json ^(200 annonces, graine 42^)...
    %PY% -m automind.generate_cars --count 200 --seed 42
    if errorlevel 1 (
        echo [ERREUR] La generation ou la validation des donnees a echoue.
        goto :fin_erreur
    )
)
echo [OK] Base de donnees data\cars.json

rem --- 4a. Mode tests
if /i "%~1"=="tests" (
    echo.
    echo [..] Execution des tests...
    %PY% -m pytest -v
    goto :fin
)

rem --- 4b. Lancement de l'application
echo.
echo [..] Ouverture de l'application sur http://localhost:8501
echo      Pour arreter : fermez cette fenetre ou appuyez sur Ctrl+C.
echo.
%PY% -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
if errorlevel 1 goto :fin_erreur
goto :fin

:fin_erreur
echo.
pause
exit /b 1

:fin
echo.
pause
endlocal
