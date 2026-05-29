# AStock 市场认知引擎 — Windows 自启动脚本
# 在 Task Scheduler 中设置延迟 5 分钟运行

$ProjectRoot = $PSScriptRoot

# 合并 PATH（Task Scheduler 上下文）
$env:Path = ([System.Environment]::GetEnvironmentVariable("Path", "User") + ";" +
             [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
             $env:Path)

# 端口配置
$BackendPort = 8005
$FrontendPort = 3000

# 清理旧进程
foreach ($port in @($BackendPort, $FrontendPort)) {
  $procId = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
              Select-Object -ExpandProperty OwningProcess
  if ($procId -and $procId -gt 0) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
}
Start-Sleep 2

# 确保数据目录存在
$null = New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "data")

# 启动后端
Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList "-m backend.main" `
  -WorkingDirectory $ProjectRoot `
  -RedirectStandardOutput (Join-Path $ProjectRoot "data\backend.log") `
  -RedirectStandardError (Join-Path $ProjectRoot "data\backend-err.log")

# 启动前端
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c npm run dev" `
  -WorkingDirectory (Join-Path $ProjectRoot "frontend") `
  -RedirectStandardOutput (Join-Path $ProjectRoot "data\frontend.log") `
  -RedirectStandardError (Join-Path $ProjectRoot "data\frontend-err.log")
