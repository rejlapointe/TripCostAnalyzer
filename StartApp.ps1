$python = "C:\Users\Rej\AppData\Local\Programs\Python\Python311\python.exe"
$port = 8506
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $projectDir

# Kill anything already on port 8506
$pid8506 = (netstat -ano | Select-String ":$port " | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
if ($pid8506) {
    Write-Host "Killing existing process on port $port (PID $pid8506)..."
    Stop-Process -Id $pid8506 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}

# Install dependencies if needed
Write-Host "Checking dependencies..."
& $python -m pip install -r requirements.txt --quiet

# Start FastAPI server in background
Write-Host "Starting Trip Cost Analyzer on port $port..."
$server = Start-Process -FilePath $python -ArgumentList "-m uvicorn server:app --host 127.0.0.1 --port $port --reload" -PassThru -WindowStyle Minimized

# Wait for server to be ready
$url = "http://127.0.0.1:$port/health"
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}

if ($ready) {
    Write-Host "Server ready. Opening Chrome..."
    Start-Process "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" -ArgumentList "http://127.0.0.1:$port"
} else {
    Write-Host "Server did not start in time. Check for errors above."
}
