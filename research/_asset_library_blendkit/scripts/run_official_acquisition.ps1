param([string]$Attempt='intake_user_001',[string]$Query='backpack',[switch]$SetupCheck,[switch]$ManualSelection)
$ErrorActionPreference='Stop'
$libraryRoot=Split-Path $PSScriptRoot -Parent
if($Attempt -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Simple Attempt name required'}
if(-not $ManualSelection -and -not $SetupCheck){
    $registryPath=Join-Path $libraryRoot 'registry/assets.json'
    if(Test-Path -LiteralPath $registryPath){
        $registered=Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $saved=$registered.assets | Where-Object {$_.source.asset_base_id -eq 'fa971768-8e7e-49dd-93e5-c225b578899e' -and $_.local_qualification.outcome -eq 'PASS'} | Select-Object -First 1
        if($saved){
            Write-Host 'The first official backpack is already saved and locally qualified. No re-download is needed.'
            Write-Host (Join-Path $libraryRoot 'comparison.html')
            exit 0
        }
    }
}
$env:BLENDER_USER_RESOURCES=Join-Path $libraryRoot 'blender_profile'
$env:BLENDER_USER_CONFIG=Join-Path $libraryRoot 'blender_profile/config'
$env:BLENDER_USER_SCRIPTS=Join-Path $libraryRoot 'blender_profile/scripts'
# GUI must use saved isolated preferences: official 3.21.5 GUI registration fails with --factory-startup.
$blenderArgs=@('--disable-autoexec','--python-exit-code','1','--python',(Join-Path $PSScriptRoot 'official_acquisition_session.py'),'--','--attempt',$Attempt,'--query',$Query)
if($SetupCheck){$blenderArgs+='--setup-check'}
if(-not $ManualSelection){$blenderArgs+='--auto-recommended'}
Write-Host 'Opening Blender. Previous attempt records are preserved; a new attempt number is chosen automatically.'
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' @blenderArgs
if($LASTEXITCODE -ne 0){throw 'Official acquisition GUI exited with an error; see sources attempt session.json'}
exit 0
