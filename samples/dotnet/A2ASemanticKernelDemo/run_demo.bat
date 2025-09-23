@echo off
echo ===================================
echo    A2A Semantic Kernel AI Demo
echo ===================================
echo.

echo Starting AI Server (Semantic Kernel)...
echo.

cd /d "%~dp0AIServer"
start "AI Server" cmd /k "echo AI Server starting... && dotnet run --urls=http://localhost:5000"

echo Waiting for server to start...
timeout /t 5 /nobreak >nul

echo.
echo Starting AI Client...
echo.

cd /d "%~dp0AIClient"
start "AI Client" cmd /k "echo AI Client starting... && dotnet run"

echo.
echo Both applications are starting in separate windows.
echo.
echo What's running:
echo    AI Server: http://localhost:5000 (Semantic Kernel AI Agent)
echo    AI Client: Interactive console application
echo.
echo Try these features:
echo    Text summarization
echo    Sentiment analysis  
echo    Idea generation
echo    Text translation
echo.
echo Press any key to close this window...
pause >nul
