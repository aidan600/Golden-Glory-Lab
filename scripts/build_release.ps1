#Requires -Version 5.1
<#
.SYNOPSIS
    Single-command release builder for Golden Glory Calculator.

.DESCRIPTION
    1. Verifies the git working tree is clean.
    2. Records the current git SHA.
    3. Builds GoldenGloryCalculator.exe (portable one-file build).
    4. Launches it briefly as a smoke check, then closes it.
    5. Locates ISCC.exe (Inno Setup 7.0.2) and fails clearly if it is missing.
    6. Compiles installer/GoldenGloryCalculator.iss into
       GoldenGloryCalculator-Setup.exe.
    7. Prints path, size, and SHA-256 for both artifacts.

    Neither artifact is committed. Both are written to the git-ignored
    release/ directory (override with -OutputDir).

.PARAMETER Version
    Product version passed to the Inno Setup script. Defaults to 0.1.0.

.PARAMETER OutputDir
    Directory to write both release artifacts to. Defaults to release/ at
    the repository root.

.PARAMETER SkipCleanCheck
    Skip the clean-working-tree check. Useful for local iteration only; do
    not use this for an actual release build.
#>

[CmdletBinding()]
param(
    [string]$Version = "0.1.0",
    [string]$OutputDir,
    [switch]$SkipCleanCheck
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    if (-not $OutputDir) {
        $OutputDir = Join-Path $repoRoot "release"
    }
    $OutputDir = (New-Item -ItemType Directory -Force -Path $OutputDir).FullName

    Write-Host "== 1/7: checking git working tree ==" -ForegroundColor Cyan
    $status = git status --porcelain
    if ($status -and -not $SkipCleanCheck) {
        Write-Host $status
        throw "Working tree is not clean. Commit or stash changes first, or pass -SkipCleanCheck for a local test build."
    }
    if ($status -and $SkipCleanCheck) {
        Write-Warning "Working tree is not clean, continuing because -SkipCleanCheck was passed."
    }

    Write-Host "== 2/7: recording git SHA ==" -ForegroundColor Cyan
    $sha = (git rev-parse HEAD).Trim()
    Write-Host "source git SHA: $sha"

    Write-Host "== 3/7: building portable GoldenGloryCalculator.exe ==" -ForegroundColor Cyan
    $exePath = Join-Path $OutputDir "GoldenGloryCalculator.exe"
    py -3.13 scripts/build_calculator_exe.py --output $exePath --overwrite
    if ($LASTEXITCODE -ne 0) {
        throw "portable EXE build failed (exit $LASTEXITCODE)"
    }
    if (-not (Test-Path $exePath)) {
        throw "expected portable EXE not found: $exePath"
    }

    Write-Host "== 4/7: launch smoke check ==" -ForegroundColor Cyan
    $proc = Start-Process -FilePath $exePath -PassThru
    Start-Sleep -Seconds 3
    if ($proc.HasExited) {
        throw "GoldenGloryCalculator.exe exited immediately (exit code $($proc.ExitCode)); packaging is broken"
    }
    Stop-Process -Id $proc.Id -Force
    Write-Host "portable EXE launched and stayed running for 3s; closed for the build."

    Write-Host "== 5/7: locating Inno Setup (ISCC.exe) ==" -ForegroundColor Cyan
    $isccPath = $null
    $onPath = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($onPath) {
        $isccPath = $onPath.Source
    } else {
        $candidates = @(
            "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
        )
        $isccPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not $isccPath) {
        throw ("Inno Setup (ISCC.exe) was not found. Install Inno Setup 7.0.2 from " +
            "https://jrsoftware.org/ (or `winget install --id JRSoftware.InnoSetup.7 " +
            "--version 7.0.2`) and re-run this script.")
    }
    Write-Host "using ISCC.exe: $isccPath"

    Write-Host "== 6/7: compiling GoldenGloryCalculator-Setup.exe ==" -ForegroundColor Cyan
    $issPath = Join-Path $repoRoot "installer\GoldenGloryCalculator.iss"
    & $isccPath "/DMyAppVersion=$Version" "/DSourceExePath=$exePath" "/DOutputDirPath=$OutputDir" $issPath
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compilation failed (exit $LASTEXITCODE)"
    }
    $setupPath = Join-Path $OutputDir "GoldenGloryCalculator-Setup.exe"
    if (-not (Test-Path $setupPath)) {
        throw "expected installer not found: $setupPath"
    }

    Write-Host "== 7/7: hashing artifacts ==" -ForegroundColor Cyan
    $exeItem = Get-Item $exePath
    $setupItem = Get-Item $setupPath
    $exeHash = (Get-FileHash $exePath -Algorithm SHA256).Hash
    $setupHash = (Get-FileHash $setupPath -Algorithm SHA256).Hash

    Write-Host ""
    Write-Host "source git SHA: $sha"
    Write-Host "product version: $Version"
    Write-Host ""
    Write-Host "portable exe: $exePath"
    Write-Host "  size:   $($exeItem.Length) bytes"
    Write-Host "  sha256: $exeHash"
    Write-Host ""
    Write-Host "installer exe: $setupPath"
    Write-Host "  size:   $($setupItem.Length) bytes"
    Write-Host "  sha256: $setupHash"
    Write-Host ""
    Write-Host "Neither artifact is committed to the repository." -ForegroundColor Yellow
}
finally {
    Pop-Location
}
