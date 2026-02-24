@echo off
REM Activate virtual environment and run Django server
REM This script ensures reportlab is properly loaded

cd /d "c:\Users\pradip shinde\FacultyProject"
call .venv\Scripts\activate.bat
cd faculty_system
python manage.py runserver 0.0.0.0:8000
pause
