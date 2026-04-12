#!/bin/bash

echo "========================================"
echo "AgentScope Human-in-the-Loop Demo"
echo "========================================"
echo

echo "1. Checking Python installation..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python not found. Please install Python 3.8+."
    exit 1
fi

echo
echo "2. Checking AgentScope installation..."
python3 -c "import agentscope; print('✅ AgentScope version:', agentscope.__version__)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  AgentScope not installed. Running in simulation mode."
    echo "   To install: pip install agentscope"
fi

echo
echo "3. Available demos:"
echo "   [1] hitl_official_example.py - Core implementation"
echo "   [2] agentscope_hitl_tutorial.py - Full tutorial"
echo

read -p "Select demo (1 or 2): " choice

echo
if [ "$choice" = "1" ]; then
    echo "Running: hitl_official_example.py"
    echo "========================================"
    python3 hitl_official_example.py
elif [ "$choice" = "2" ]; then
    echo "Running: agentscope_hitl_tutorial.py"
    echo "========================================"
    python3 agentscope_hitl_tutorial.py
else
    echo "❌ Invalid choice"
    exit 1
fi

echo
read -p "Press Enter to continue..."