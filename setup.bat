@echo off
echo ================================================
echo   AI Pharmacy Management System - Setup
echo ================================================

echo Installing dependencies...
pip install -r requirements.txt

echo Creating database tables...
python manage.py makemigrations
python manage.py migrate

echo Loading sample data...
python manage.py seed_data

echo.
echo ================================================
echo   Setup Complete!
echo   Run: python manage.py runserver
echo   Open: http://127.0.0.1:8000
echo   Login: admin / admin123
echo ================================================
pause
