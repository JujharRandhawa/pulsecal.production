#!/bin/bash

# PulseCal Universal Launcher - Works on macOS, Linux, and Windows
# This is the main entry point for all operating systems

echo "🚀 PulseCal Universal Launcher"
echo "=============================="

# Check if we're on Windows and suggest the right approach
if [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "📋 Windows detected!"
    echo ""
    echo "For Windows users, you have two options:"
    echo ""
    echo "1. 🐧 Use WSL (Windows Subsystem for Linux) - Recommended"
    echo "   Run this script from WSL terminal"
    echo ""
    echo "2. 🪟 Use Windows Command Prompt"
    echo "   Run: start_pulsecal.bat"
    echo ""
    echo "3. 🐚 Use Git Bash (if you have it installed)"
    echo "   Run this script from Git Bash"
    echo ""
    read -p "Press Enter to continue with current shell, or Ctrl+C to use Windows batch file..."
fi

# Run the universal script
echo "🏥 Starting PulseCal with universal script..."
./start_pulsecal_universal.sh 