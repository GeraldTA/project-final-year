# Keep-alive script for API server
Write-Host "🚀 Starting API Server with keep-alive..." -ForegroundColor Green
Write-Host "📍 Server will run at: http://127.0.0.1:8001" -ForegroundColor Cyan
Write-Host "⏹️  Close this window to stop the server" -ForegroundColor Yellow
Write-Host ""

Set-Location "C:\Users\Banda\Documents\code for project\backend"

while ($true) {
    try {
        & python -m uvicorn api_server:app --host 127.0.0.1 --port 8001
        Write-Host "Server stopped. Restarting in 2 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
    catch {
        Write-Host "Error: $_" -ForegroundColor Red
        Start-Sleep -Seconds 5
    }
}
