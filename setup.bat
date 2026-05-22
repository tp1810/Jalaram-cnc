@echo off
echo ===========================================
echo  Jalaram CNC Art & Craft - Project Setup
echo ===========================================
echo.

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is installed.
    pause
    exit /b 1
)

echo.
echo [2/3] Creating database tables...
python manage.py makemigrations core
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Migration failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Creating admin superuser...
python manage.py createsuperuser
echo.

echo ===========================================
echo  Setup complete! Run the server with:
echo  python manage.py runserver
echo  Then open: http://127.0.0.1:8000/
echo ===========================================
pause
