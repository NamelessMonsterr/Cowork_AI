$port = 8765
$tcp = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($tcp) {
    Write-Host "Killing process on port $port (PID: $($tcp.OwningProcess))..."
    Stop-Process -Id $tcp.OwningProcess -Force
    Start-Sleep -Seconds 2
} else {
    Write-Host "No process found on port $port."
}
Write-Host "Starting Flash Assistant..."
python -m uvicorn assistant.main:app --host 127.0.0.1 --port 8765
