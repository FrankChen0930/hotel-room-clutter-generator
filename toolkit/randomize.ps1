param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$ErrorActionPreference='Stop'
$explicitRoot=$null;$configFile=$null
for($i=0;$i -lt $CliArgs.Count;$i++){
 if($CliArgs[$i] -eq '--isaac-root' -and $i+1 -lt $CliArgs.Count){$explicitRoot=$CliArgs[$i+1]}
 if($CliArgs[$i].StartsWith('--isaac-root=')){$explicitRoot=$CliArgs[$i].Substring(13)}
 if($CliArgs[$i] -eq '--config' -and $i+1 -lt $CliArgs.Count){$configFile=$CliArgs[$i+1]}
}
$configRoot=$null
if($configFile){
 try{
  $full=[IO.Path]::GetFullPath($configFile)
  $code=[IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))+[IO.Path]::DirectorySeparatorChar
  $outputs=[IO.Path]::GetFullPath((Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'local-test-outputs'))+[IO.Path]::DirectorySeparatorChar
  if($full.StartsWith($code,[StringComparison]::OrdinalIgnoreCase) -or $full.StartsWith($outputs,[StringComparison]::OrdinalIgnoreCase)){
   if(Test-Path -LiteralPath $full -PathType Leaf){$configRoot=(Get-Content -LiteralPath $full -Raw -Encoding UTF8|ConvertFrom-Json).isaac_root}
  }
 }catch{$configRoot=$null} # Let Python report malformed/unsupported config consistently.
}
$root=$explicitRoot
if(-not $root){$root=$configRoot}
if(-not $root){$root=$env:YAZHI_ISAAC_ROOT}
if(-not $root){$root='C:\isaac_sim'}
if($root -match '^[\\/]{2}|^[a-z]+://'){[Console]::Error.WriteLine('ENVIRONMENT_INVALID: only local Isaac paths are allowed.');exit 10}
$python=Join-Path $root 'kit\python\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){[Console]::Error.WriteLine('ENVIRONMENT_MISSING: set YAZHI_ISAAC_ROOT or --isaac-root to an existing supported Isaac installation. No install attempted.');exit 10}
& $python -I -B (Join-Path $PSScriptRoot 'randomize.py') @CliArgs
exit $LASTEXITCODE
