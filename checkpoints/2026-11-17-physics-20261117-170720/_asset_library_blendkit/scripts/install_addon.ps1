param([Parameter(Mandatory=$true)][string]$OfficialZip)
$ErrorActionPreference='Stop'
$libraryRoot=Split-Path $PSScriptRoot -Parent
$zipPath=(Resolve-Path -LiteralPath $OfficialZip).Path
# This installer only consumes the user's official ZIP. It never fetches models or reads credentials.
$env:BLENDER_USER_RESOURCES=Join-Path $libraryRoot 'blender_profile'
$env:BLENDER_USER_CONFIG=Join-Path $libraryRoot 'blender_profile/config'
$env:BLENDER_USER_SCRIPTS=Join-Path $libraryRoot 'blender_profile/scripts'
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot 'install_addon_blender.py') -- $zipPath
if($LASTEXITCODE -ne 0){throw 'Official add-on installation failed. Inspect Blender output.'}
