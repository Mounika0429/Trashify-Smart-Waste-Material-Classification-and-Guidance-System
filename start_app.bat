@echo off
echo =======================================
echo Preparing Trashify App Environment...
echo =======================================

:: Use the existing venv_new environment
if exist venv_new\Scripts\activate.bat (
    call venv_new\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment 'venv_new' not found.
    pause
    exit /b
)

echo Installing/Verifying dependencies...
echo Please wait! Downloading the AI Brain (TensorFlow) may take several minutes...
pip install Flask Werkzeug numpy googletrans==4.0.0-rc1 gTTS pandas openpyxl tensorflow --quiet

echo.
echo =======================================
echo Starting the Application...
echo Please open http://127.0.0.1:8080 
echo =======================================
python app.py

echo.
echo App closed or crashed!
pause
