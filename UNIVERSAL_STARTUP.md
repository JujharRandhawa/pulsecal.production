# 🌍 PulseCal Universal Startup Guide

## 🚀 One Command for All Operating Systems

### **Universal Command (Works Everywhere)**
```bash
./start.sh
```

### **Alternative Universal Script**
```bash
./start_pulsecal_universal.sh
```

## 📋 **Operating System Support**

### 🍎 **macOS**
- ✅ Native support
- ✅ Docker Desktop for Mac
- ✅ Terminal or iTerm2

### 🐧 **Linux**
- ✅ Native support
- ✅ Docker Engine
- ✅ Any terminal

### 🪟 **Windows**
- ✅ WSL (Windows Subsystem for Linux) - **Recommended**
- ✅ Git Bash
- ✅ Docker Desktop for Windows
- ✅ Command Prompt (using batch file)

## 🎯 **What the Universal Script Does**

1. **🔍 OS Detection** - Automatically detects your operating system
2. **🐳 Docker Check** - Verifies Docker is running with OS-specific instructions
3. **📦 Docker Compose** - Checks for docker-compose or docker compose
4. **🛑 Clean Start** - Stops any existing containers
5. **🏗️ Build & Start** - Builds and starts all containers
6. **⏳ Wait & Verify** - Waits for services to be ready
7. **🗄️ Database Setup** - Runs migrations and collects static files
8. **✅ Health Check** - Verifies application is accessible
9. **📱 OS Tips** - Shows OS-specific tips and commands

## 🚀 **Quick Start Commands**

### **For Everyone (Universal)**
```bash
./start.sh
```

### **For macOS Users**
```bash
./start_pulsecal_universal.sh
```

### **For Linux Users**
```bash
./start_pulsecal_universal.sh
```

### **For Windows Users**
```cmd
# Option 1: WSL (Recommended)
./start.sh

# Option 2: Git Bash
./start_pulsecal_universal.sh

# Option 3: Command Prompt
start_pulsecal.bat
```

## 🔧 **Prerequisites by OS**

### **macOS**
- Docker Desktop for Mac installed
- Terminal or iTerm2

### **Linux**
- Docker Engine installed
- Docker Compose installed
- Terminal access

### **Windows**
- Docker Desktop for Windows installed
- WSL2 (recommended) or Git Bash
- Or use Command Prompt with batch file

## 📱 **OS-Specific Features**

### **macOS Features**
- 🍎 Native macOS integration
- 🖱️ Cmd+Click to open URLs
- 📱 Menu bar Docker Desktop
- 🎨 Beautiful terminal colors

### **Linux Features**
- 🐧 Native Linux commands
- 🔧 System service integration
- 📊 System monitoring
- 🎨 Terminal color support

### **Windows Features**
- 🪟 Windows integration
- 🐧 WSL2 support
- 🎨 Git Bash color support
- 📋 Batch file alternative

## 🛠️ **Troubleshooting by OS**

### **macOS Issues**
```bash
# If Docker Desktop isn't running
open -a Docker

# If permissions issue
sudo chmod +x *.sh

# If port 8000 is busy
lsof -ti:8000 | xargs kill -9
```

### **Linux Issues**
```bash
# If Docker service isn't running
sudo systemctl start docker

# If user not in docker group
sudo usermod -aG docker $USER

# If port 8000 is busy
sudo netstat -tulpn | grep :8000
```

### **Windows Issues**
```cmd
# If Docker Desktop isn't running
# Start Docker Desktop from Start Menu

# If WSL issues
wsl --update

# If port 8000 is busy
netstat -ano | findstr :8000
```

## 🎉 **Success Indicators**

When everything works, you'll see:
```
🎉 PulseCal Enhanced Healthcare Management System is READY!
==================================================

[SUCCESS] 🌐 Application URL: http://localhost:8000
[SUCCESS] 📊 Admin Interface: http://localhost:8000/admin
[SUCCESS] 🗄️  Database: PostgreSQL on localhost:5432
[SUCCESS] ⚡ Redis Cache: localhost:6379
```

## 🏥 **Features Available**

- 🏥 **Medical Records Management**
- 💊 **Prescription Management**
- 🛡️ **Insurance Management**
- 💳 **Payment Processing**
- 📞 **Emergency Contacts**
- ⏰ **Medication Reminders**
- 📹 **Telemedicine Sessions**
- 📊 **Health Analytics Dashboard**

## 🚀 **Quick Commands After Startup**

### **Stop Application**
```bash
docker-compose down
```

### **View Logs**
```bash
docker-compose logs -f
```

### **Restart Application**
```bash
docker-compose restart
```

### **Check Status**
```bash
docker-compose ps
```

### **Update Application**
```bash
git pull && ./start.sh
```

## 🌍 **Universal Benefits**

- ✅ **One Command** - Works on all operating systems
- ✅ **Auto-Detection** - Detects your OS automatically
- ✅ **Smart Fallbacks** - Handles different Docker versions
- ✅ **OS-Specific Help** - Provides relevant instructions
- ✅ **Error Handling** - Graceful error handling and recovery
- ✅ **Color Output** - Beautiful colored terminal output
- ✅ **Health Checks** - Verifies everything is working

## 🎯 **Ready to Use!**

Just run **one command** and you'll have the complete enhanced healthcare management system running:

```bash
./start.sh
```

**That's it! One command for all operating systems!** 🚀✨ 