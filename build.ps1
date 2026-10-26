# Build the Web assets and Pyodide static site without Make or a Unix shell.
[CmdletBinding()]
param(
    [string]$Python
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-BuildCommand {
    param(
        [string]$Executable,
        [string[]]$CommandArguments
    )
    & $Executable @CommandArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Build command failed (exit $LASTEXITCODE): $Executable $($CommandArguments -join ' ')"
    }
}

Push-Location $PSScriptRoot
try {
    $nodeCommand = (Get-Command node -CommandType Application -ErrorAction Stop).Source
    # Use the native launcher instead of npx.ps1, which may be blocked by policy.
    $npxCommand = (Get-Command npx.cmd -CommandType Application -ErrorAction Stop).Source
    $pythonPrefix = @()
    $localPython = Join-Path $PSScriptRoot 'env/Scripts/python.exe'
    if ($Python) {
        $pythonCommand = (Get-Command $Python -CommandType Application -ErrorAction Stop).Source
    } elseif (Test-Path $localPython) {
        $pythonCommand = $localPython
    } elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts/python.exe'))) {
        $pythonCommand = Join-Path $env:VIRTUAL_ENV 'Scripts/python.exe'
    } elseif (Get-Command py -CommandType Application -ErrorAction SilentlyContinue) {
        $pythonCommand = (Get-Command py -CommandType Application).Source
        $pythonPrefix = @('-3')
    } else {
        $pythonCommand = (Get-Command python -CommandType Application -ErrorAction Stop).Source
    }
    Invoke-BuildCommand -Executable $pythonCommand -CommandArguments ($pythonPrefix + @(
        '-c', "import sys; sys.exit('Python 3.9 or newer is required') if sys.version_info < (3, 9) else None"
    ))

    Write-Host 'Installing locked browser dependencies...'
    New-Item -ItemType Directory -Force 'env/web-client' | Out-Null
    Copy-Item -Path 'browser-client/package.json', 'browser-client/pnpm-lock.yaml', 'browser-client/pnpm-workspace.yaml' -Destination 'env/web-client/' -Force
    Invoke-BuildCommand -Executable $npxCommand -CommandArguments @(
        '--yes', 'pnpm@11.25.0', '--dir', 'env/web-client', 'install', '--ignore-scripts', '--frozen-lockfile'
    )

    Write-Host 'Building Web assets...'
    Invoke-BuildCommand -Executable $nodeCommand -CommandArguments @('browser-client/build.mjs')

    Write-Host 'Building Pyodide static site...'
    # This packager only needs the standard library; running it directly avoids
    # importing optional PUI runtime integrations in the build environment.
    Invoke-BuildCommand -Executable $pythonCommand -CommandArguments ($pythonPrefix + @('PUI/cookbook/build_pyodide.py'))
    Invoke-BuildCommand -Executable $nodeCommand -CommandArguments @('browser-client/build-pyodide.mjs')

    Write-Host 'Build complete: PUI/web/static/ and dist/pyodide/'
} finally {
    Pop-Location
}
