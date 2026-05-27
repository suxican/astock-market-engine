@echo off
chcp 65001 >nul
title AStock AI Copilot V2 - 市场认知引擎

echo ============================================
echo   AStock AI Copilot V2 - 市场认知引擎
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [失败] 未检测到 Python，请安装 Python 3.10+
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo [OK] Python %%i

:: 检查 Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [失败] 未检测到 Node.js，请安装 Node.js 18+
    pause
    exit /b 1
)
for /f %%i in ('node --version') do echo [OK] Node %%i
echo.

set ROOT_DIR=%~dp0

:: 清理端口 8005 上残留的旧进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8005" ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: 后端依赖
echo [1/4] 安装后端依赖...
cd /d "%ROOT_DIR%"
pip install -r backend\requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo [OK] 后端依赖安装完成

:: 前端依赖
echo [2/4] 安装前端依赖...
cd /d "%ROOT_DIR%frontend"
if not exist node_modules (
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [SKIP] node_modules 已存在
)
echo [OK] 前端依赖安装完成
echo.

:: 启动后端（新窗口，reload 模式）
:: 必须从项目根目录启动 uvicorn，否则 backend.main 模块无法被发现。
echo [3/4] 启动后端服务...
cd /d "%ROOT_DIR%"
start "AStock-Backend" cmd /c "title AStock-Backend && cd /d %ROOT_DIR% && uvicorn backend.main:app --host 127.0.0.1 --port 8005"
timeout /t 4 /nobreak >nul

:: 启动前端（新窗口，dev 模式）
echo [4/4] 启动前端服务...
cd /d "%ROOT_DIR%frontend"
start "AStock-Frontend" cmd /c "title AStock-Frontend && npm run dev"
echo.

timeout /t 2 /nobreak >nul

echo ============================================
echo   [OK] 启动完成！
echo.
echo   前端地址：http://localhost:3000
echo   后端地址：http://localhost:8005
echo   API文档：http://localhost:8005/docs
echo ============================================
echo.
echo 按任意键关闭所有服务...
pause >nul

echo 正在关闭服务...
taskkill /fi "WINDOWTITLE eq AStock-Backend" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq AStock-Frontend" /f >nul 2>&1
echo [OK] 已关闭
timeout /t 2 /nobreak >nul
