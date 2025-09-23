@echo off
echo.
echo Basic A2A .NET Demo
echo ======================
echo.
echo This script will start both agent servers and then run the client.
echo.
echo Starting agents in separate windows...
echo.

REM Start Echo Agent in a new window
start "Echo Agent Server" cmd /k "cd EchoServer && dotnet run && pause"

REM Wait a moment for the first server to start
timeout /t 3 /nobreak > nul

REM Start Calculator Agent in a new window  
start "Calculator Agent Server" cmd /k "cd CalculatorServer && dotnet run && pause"

REM Wait a moment for servers to fully start
echo Waiting for servers to start...
timeout /t 5 /nobreak > nul

echo.
echo Agent servers should be starting in separate windows
echo Echo Agent: http://localhost:5001
echo Calculator Agent: http://localhost:5002
echo.
echo Press any key to run the client demo...
pause > nul

REM Run the client
echo.
echo Running client demo...
cd SimpleClient
dotnet run

echo.
echo Demo completed! The agent servers are still running in separate windows.
echo Close those windows when you're done experimenting.
pause
