param([string]$OutputName='official_gui_probe_user_001',[string]$Query='towel',[ValidateSet('cc_zero','ANY')][string]$License='cc_zero',[switch]$Quit)
$ErrorActionPreference='Stop'
$libraryRoot=Split-Path $PSScriptRoot -Parent
if($OutputName -notmatch '^[a-zA-Z0-9_-]+$'){throw 'OutputName must be a simple attempt name'}
$env:BLENDER_USER_RESOURCES=Join-Path $libraryRoot 'blender_profile'
$env:BLENDER_USER_CONFIG=Join-Path $libraryRoot 'blender_profile/config'
$env:BLENDER_USER_SCRIPTS=Join-Path $libraryRoot 'blender_profile/scripts'
$probeArgs=@('--disable-autoexec','--python-exit-code','1','--python',(Join-Path $PSScriptRoot 'official_gui_probe.py'),'--','--output',(Join-Path $libraryRoot ('reports/'+$OutputName)),'--query',$Query,'--license',$License,'--timeout','60')
if($Quit){$probeArgs+='--quit'}
# The GUI is intentionally visible for the requested official search/login workflow.
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' @probeArgs
if($LASTEXITCODE -ne 0){throw 'Blender GUI probe exited with an error; see attempt status.'}
