$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$script = Join-Path $PSScriptRoot "dashboard.py"

# Python is often installed without being on PATH, and the WindowsApps
# "python" alias only opens the Microsoft Store. Find a real 3.12+ interpreter.
function Find-Python {
    $candidates = @()
    $py = Get-Command py -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($py) { $candidates += , @($py.Source, '-3') }
    $python = Get-Command python -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notlike '*\WindowsApps\*' } | Select-Object -First 1
    if ($python) { $candidates += , @($python.Source) }
    foreach ($base in "$env:LOCALAPPDATA\Programs\Python", "$env:ProgramFiles") {
        Get-ChildItem "$base\Python3*\python.exe" -ErrorAction SilentlyContinue |
            Sort-Object { [int]($_.Directory.Name -replace '\D', '') } -Descending |
            ForEach-Object { $candidates += , @($_.FullName) }
    }
    foreach ($candidate in $candidates) {
        $exe = $candidate[0]; $prefix = @($candidate | Select-Object -Skip 1)
        & $exe @prefix -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { return , $candidate }
    }
    throw "Python 3.12+ is required. Install it from python.org or with: winget install --id Python.Python.3.13 --exact"
}

$python = Find-Python
$exe = $python[0]; $prefix = @($python | Select-Object -Skip 1)
Set-Location $root
& $exe @prefix $script
