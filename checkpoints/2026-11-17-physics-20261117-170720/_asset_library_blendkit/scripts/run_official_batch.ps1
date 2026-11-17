param([string]$Attempt='',[switch]$SetupCheck,[string]$Batch='batch_001')
$ErrorActionPreference='Stop'
$libraryRoot=Split-Path $PSScriptRoot -Parent
if($Batch -notmatch '^batch_[0-9]{3}$'){throw 'Batch must be batch_NNN'}
if(-not $Attempt){$Attempt=$Batch+'_001'}
if($Attempt -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Simple attempt name required'}
$env:BLENDER_USER_RESOURCES=Join-Path $libraryRoot 'blender_profile'
$env:BLENDER_USER_CONFIG=Join-Path $libraryRoot 'blender_profile/config'
$env:BLENDER_USER_SCRIPTS=Join-Path $libraryRoot 'blender_profile/scripts'
$blenderArgs=@('--disable-autoexec','--python-exit-code','1','--python',(Join-Path $PSScriptRoot 'official_batch_session.py'),'--','--attempt',$Attempt)
$blenderArgs+=@('--config',(Join-Path $libraryRoot ('config/'+$Batch+'_acquisition.json')))
if($SetupCheck){$blenderArgs+='--setup-check'}
Write-Host 'Official hotel asset batch: keep Blender open; sources save automatically and the batch closes when finished.'
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' @blenderArgs
if($LASTEXITCODE -ne 0){throw 'Official batch failed; attempt evidence is preserved under sources.'}
exit 0
