# ======================================================================
# OilMine Analytics — Arranque del FRONTEND (React + Vite)
# ======================================================================
# Uso:  .\start_frontend.ps1
#
# Qué hace:
#   1. Verifica Node.js 18+ y npm
#   2. Instala node_modules (solo la primera vez o si cambió package.json)
#   3. Verifica que el backend esté respondiendo (aviso, no bloqueante)
#   4. Arranca Vite en http://localhost:5173
# ======================================================================

$ErrorActionPreference = "Stop"

function Write-Step  ($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok    ($msg) { Write-Host "[OK] $msg"  -ForegroundColor Green }
function Write-Warn  ($msg) { Write-Host "[!]  $msg"  -ForegroundColor Yellow }
function Write-Fail  ($msg) { Write-Host "[X]  $msg"  -ForegroundColor Red }

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$FrontDir   = Join-Path $ScriptDir "frontend"

Set-Location $FrontDir
Write-Host ""
Write-Host "OilMine Analytics  |  Frontend" -ForegroundColor White -BackgroundColor DarkMagenta
Write-Host "Directorio: $FrontDir"
Write-Host ""

# ---- 1. Node / npm ---------------------------------------------------
Write-Step "Verificando Node.js y npm..."
try {
    $nodeVer = node --version
    $npmVer  = npm --version
    Write-Ok "Node $nodeVer  |  npm $npmVer"
} catch {
    Write-Fail "Node.js no está instalado o no está en PATH."
    Write-Host "   Descarga Node 18+ de https://nodejs.org/ (LTS)."
    exit 1
}

# Check versión mínima
$major = [int]($nodeVer -replace "v(\d+).*", '$1')
if ($major -lt 18) {
    Write-Warn "Node $nodeVer detectado. Se recomienda Node 18 o superior."
}

# ---- 2. Dependencias -------------------------------------------------
$NodeModulesDir = Join-Path $FrontDir "node_modules"
$PkgJson        = Join-Path $FrontDir "package.json"
$StampFile      = Join-Path $FrontDir ".pkg.hash"

if (-not (Test-Path $PkgJson)) {
    Write-Fail "No se encontró package.json dentro de /frontend"
    exit 1
}

$pkgHash = (Get-FileHash $PkgJson -Algorithm SHA256).Hash
$needInstall = $true
if ((Test-Path $NodeModulesDir) -and (Test-Path $StampFile)) {
    $lastHash = Get-Content $StampFile
    if ($lastHash -eq $pkgHash) { $needInstall = $false }
}

if ($needInstall) {
    Write-Step "Instalando dependencias de npm (puede tomar 1-2 min)..."
    npm install
    $pkgHash | Out-File -Encoding ascii $StampFile
    Write-Ok "Dependencias instaladas."
} else {
    Write-Ok "node_modules ya está listo (package.json sin cambios)."
}

# ---- 3. Check del backend (no bloqueante) ----------------------------
Write-Step "Comprobando si el backend responde en http://localhost:8000 ..."
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        Write-Ok "Backend OK."
    }
} catch {
    Write-Warn "El backend todavia no responde en :8000."
    Write-Host "   Ejecuta en OTRA ventana de PowerShell:   .\start_backend.ps1"
    Write-Host "   (el frontend arrancara igualmente; las llamadas a la API fallaran hasta que suba el backend)"
}

# ---- 4. Arrancar Vite ------------------------------------------------
Write-Host ""
Write-Host "======================================================" -ForegroundColor DarkMagenta
Write-Host "  Frontend en:       http://localhost:5173"            -ForegroundColor White
Write-Host "  API proxificada:   /api -> http://localhost:8000"    -ForegroundColor White
Write-Host "  Ctrl+C para detener"                                 -ForegroundColor DarkGray
Write-Host "======================================================" -ForegroundColor DarkMagenta
Write-Host ""

npm run dev
