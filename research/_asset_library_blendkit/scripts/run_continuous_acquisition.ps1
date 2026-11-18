param([switch]$SetupCheck)
$ErrorActionPreference='Stop'
$entry=Join-Path $PSScriptRoot 'run_official_batch.ps1'
& $entry -Batch batch_003 -SetupCheck:$SetupCheck
exit $LASTEXITCODE
