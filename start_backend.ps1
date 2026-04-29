# ======================================================================
# OilMine Analytics — Arranque del BACKEND (FastAPI + modelos ML)
# ======================================================================
# Uso:  .\start_backend.ps1
#
# Qué hace:
#   1. Verifica Python 3.10+
#   2. Crea / reutiliza el entorno virtual .venv
#   3. Instala dependencias (solo la primera vez o si cambió requirements.txt)
#   4. Valida que existan el Excel fuente y los modelos .pkl
#   5. Precarga los 3 modelos y arranca uvicorn en http://localhost:8000
# ======================================================================

$ErrorActionPreference = "Stop"

# Color helpers ---------------------------------------------------------
function Write-Step  ($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok    ($msg) { Write-Host "[OK] $msg"  -ForegroundColor Green }
function Write-Warn  ($msg) { Write-Host "[!]  $msg"  -ForegroundColor Yellow }
function Write-Fail  ($msg) { Write-Host "[X]  $msg"  -ForegroundColor Red }

# Cambia al directorio del script ---------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir
Write-Host ""
Write-Host "OilMine Analytics  |  Backend" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "Directorio: $ScriptDir"
Write-Host ""

# ---- 1. Python --------------------------------------------------------
Write-Step "Verificando Python..."
try {
    $pyVer = python --version 2>&1
    Write-Ok "$pyVer"
} catch {
    Write-Fail "Python no está instalado o no está en PATH."
    Write-Host "   Descarga Python 3.10+ de https://www.python.org/downloads/ y marca 'Add to PATH'."
    exit 1
}

# ---- 2. Entorno virtual ----------------------------------------------
$VenvPath = Join-Path $ScriptDir ".venv"
if (-not (Test-Path $VenvPath)) {
    Write-Step "Creando entorno virtual en .venv ..."
    python -m venv .venv
    Write-Ok "Entorno virtual creado."
} else {
    Write-Ok "Entorno virtual ya existe."
}

# Activar
$Activate = Join-Path $VenvPath "Scripts\Activate.ps1"
Write-Step "Activando entorno virtual..."
. $Activate
Write-Ok "Entorno virtual activado."

# ---- 3. Dependencias -------------------------------------------------
$ReqFile      = Join-Path $ScriptDir "requirements.txt"
$ReqStampFile = Join-Path $VenvPath  ".requirements.hash"

if (-not (Test-Path $ReqFile)) {
    Write-Fail "No se encontró requirements.txt"
    exit 1
}

$reqHash = (Get-FileHash $ReqFile -Algorithm SHA256).Hash
$needInstall = $true
if (Test-Path $ReqStampFile) {
    $lastHash = Get-Content $ReqStampFile
    if ($lastHash -eq $reqHash) { $needInstall = $false }
}

if ($needInstall) {
    Write-Step "Instalando dependencias (puede tomar 1-3 min la primera vez)..."
    python -m pip install --upgrade pip | Out-Null
    pip install -r requirements.txt
    $reqHash | Out-File -Encoding ascii $ReqStampFile
    Write-Ok "Dependencias instaladas."
} else {
    Write-Ok "Dependencias ya instaladas (requirements.txt sin cambios)."
}

# ---- 4. Validar datos y modelos --------------------------------------
Write-Step "Validando datos y modelos..."

$ExcelFile = Join-Path $ScriptDir "DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx"
if (-not (Test-Path $ExcelFile)) {
    Write-Fail "No se encontró el Excel fuente:"
    Write-Host "   $ExcelFile"
    exit 1
}
Write-Ok "Excel fuente OK."

$ModelsDir = Join-Path $ScriptDir "models"
$RequiredModels = @(
    "clasificador_estado_xgboost.pkl",
    "estimador_horas_hasta_critico.pkl",
    "feat_cols.json"
)
foreach ($m in $RequiredModels) {
    $p = Join-Path $ModelsDir $m
    if (-not (Test-Path $p)) {
        Write-Fail "Falta el modelo: $m"
        exit 1
    }
}

$regresores = @(Get-ChildItem -Path $ModelsDir -Filter "regresor_*.pkl" -ErrorAction SilentlyContinue)
if ($regresores.Count -lt 10) {
    Write-Warn "Se encontraron solo $($regresores.Count) regresores (se esperan 12)."
} else {
    Write-Ok "Se encontraron $($regresores.Count) regresores por variable."
}
Write-Ok "Modelos listos."

# ---- 5. Arrancar API -------------------------------------------------
Write-Host ""
Write-Host "======================================================" -ForegroundColor DarkCyan
Write-Host "  API escuchando en:  http://localhost:8000"          -ForegroundColor White
Write-Host "  Docs interactivas:  http://localhost:8000/docs"      -ForegroundColor White
Write-Host "  Ctrl+C para detener"                                 -ForegroundColor DarkGray
Write-Host "======================================================" -ForegroundColor DarkCyan
Write-Host ""

python run_api.py
