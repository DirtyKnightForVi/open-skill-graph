@echo off
echo ========================================
echo AgentScope Human-in-the-Loop Demo
echo ========================================
echo.

echo 1. Checking Python installation...
python --version
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+.
    pause
    exit /b 1
)

echo.
echo 2. Checking AgentScope installation...
python -c "import agentscope; print('✅ AgentScope version:', agentscope.__version__)" 2>nul
if errorlevel 1 (
    echo ⚠️  AgentScope not installed. Running in simulation mode.
    echo    To install: pip install agentscope
)

echo.
echo 3. Available demos:
echo    [1] hitl_official_example.py - Core implementation
echo    [2] agentscope_hitl_tutorial.py - Full tutorial
echo.

set /p choice="Select demo (1 or 2): "

if "%choice%"=="1" (
    echo.
    echo Running: hitl_official_example.py
    echo ========================================
    python hitl_official_example.py
) else if "%choice%"=="2" (
    echo.
    echo Running: agentscope_hitl_tutorial.py
    echo ========================================
    python agentscope_hitl_tutorial.py
) else (
    echo ❌ Invalid choice
)

echo.
pause