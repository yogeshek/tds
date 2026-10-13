# D:\projects\TDS\start.ps1

# ============================================
# CONFIG - Change only these two lines
# ============================================
$EMAIL = "24ds3000035@ds.study.iitm.ac.in"
$NGROK_PATH = "C:\Users\YogeshEkambaramK\AppData\Local\Microsoft\WindowsApps\ngrok.exe"
# ============================================

Write-Host "`n Step 1: Killing all existing Ollama processes..." -ForegroundColor Yellow
taskkill /F /IM ollama.exe /T 2>$null
Start-Sleep -Seconds 3
Write-Host " Ollama killed!" -ForegroundColor Green

Write-Host "`n Step 2: Killing all existing ngrok processes..." -ForegroundColor Yellow
taskkill /F /IM ngrok.exe /T 2>$null
Start-Sleep -Seconds 2
Write-Host " ngrok killed!" -ForegroundColor Green

Write-Host "`n Step 3: Starting Ollama with CORS enabled..." -ForegroundColor Yellow
$env:OLLAMA_ORIGINS = "*"
$env:OLLAMA_HOST = "0.0.0.0:11434"
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
Write-Host " Waiting for Ollama to start..." -ForegroundColor Cyan

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
    Write-Host "   ...waiting ($($i*2)s)" -ForegroundColor Gray
}

if (-not $ready) {
    Write-Host " ERROR: Ollama failed to start! Check if ollama is installed." -ForegroundColor Red
    exit 1
}
Write-Host " Ollama is running!" -ForegroundColor Green

Write-Host "`n Step 4: Starting ngrok tunnel..." -ForegroundColor Yellow
Start-Process -FilePath $NGROK_PATH -ArgumentList "http 11434 --response-header-add `"X-Email: $EMAIL`" --response-header-add `"Access-Control-Allow-Headers: *`" --response-header-add `"Access-Control-Expose-Headers: X-Email`"" -WindowStyle Hidden
Start-Sleep -Seconds 4

Write-Host " Fetching ngrok public URL..." -ForegroundColor Cyan
$PUBLIC_URL = $null
for ($i = 0; $i -lt 10; $i++) {
    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        $https = $tunnels.tunnels | Where-Object { $_.public_url -like "https://*" }
        if ($https) { $PUBLIC_URL = $https[0].public_url; break }
    } catch {}
    Start-Sleep -Seconds 2
    Write-Host "   ...waiting ($($i*2)s)" -ForegroundColor Gray
}

if (-not $PUBLIC_URL) {
    Write-Host " ERROR: Could not get ngrok URL! Check ngrok path or token." -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " SUCCESS! Submit this URL:" -ForegroundColor Green
Write-Host " $PUBLIC_URL" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

$PUBLIC_URL | Set-Clipboard
Write-Host " URL copied to clipboard!" -ForegroundColor Green
Write-Host " Keep this window open until assignment is graded!`n" -ForegroundColor Yellow