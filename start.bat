@echo off

echo Starting Chatbot Python Server...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found. Please create one based on the template.
    echo Copy .env to .env and fill in your API keys.
    exit /b 1
)

REM Start the server
echo Starting FastAPI server...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload