@echo off
echo Starting CLI Agent Demo...
echo.

echo Starting CLI Agent Server...
start "CLI Agent Server" cmd /c "cd CLIServer && dotnet run && pause"

echo Waiting for server to start...
timeout /t 3 /nobreak > nul

echo Starting CLI Agent Client...
start "CLI Agent Client" cmd /c "cd CLIClient && dotnet run && pause"

echo.
echo Both CLI Agent Server and Client are starting in separate windows.
echo The server runs on http://localhost:5003
echo.
echo Press any key to exit this script...
pause > nul
