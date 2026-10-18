$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$script = Join-Path $PSScriptRoot "dashboard.py"
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $script
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $script
} else {
    throw "Python 3.12+ is required"
}
