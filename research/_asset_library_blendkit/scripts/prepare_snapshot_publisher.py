"""Prepare a user-run official Git/GCM publisher for the network-isolated agent."""
import argparse
from pathlib import Path
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);a=p.parse_args();snapshot=a.snapshot.resolve();delivery=snapshot.parent
    assert snapshot.is_relative_to(ROOT.parent/'_project_delivery')
    files=[dict(path=p.relative_to(snapshot).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(snapshot.rglob('*')) if p.is_file() and '.git' not in p.relative_to(snapshot).parts]
    write(delivery/'snapshot_files.json',dict(snapshot=snapshot.name,files=files))
    script=r'''param([switch]$SkipLogin, [switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$deliveryRoot = $PSScriptRoot
$snapshotManifest = Get-Content -LiteralPath (Join-Path $deliveryRoot 'snapshot_files.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$snapshotRoot = [IO.Path]::GetFullPath((Join-Path $deliveryRoot $snapshotManifest.snapshot))
$remoteUrl = 'https://github.com/FrankChen0930/hotel-room-clutter-generator.git'
function Run-Git {
    param([string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) { throw ('Git command failed. No force push or cleanup will be attempted. Exit code: ' + $LASTEXITCODE) }
}
function Child-Path {
    param([string]$Parent, [string]$Relative)
    $basePath = [IO.Path]::GetFullPath($Parent).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $targetPath = [IO.Path]::GetFullPath((Join-Path $Parent $Relative))
    if (-not $targetPath.StartsWith($basePath, [StringComparison]::OrdinalIgnoreCase)) { throw 'Manifest path escaped the intended directory' }
    return $targetPath
}
foreach ($file in $snapshotManifest.files) {
    $sourcePath = Child-Path $snapshotRoot $file.path
    if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) { throw ('Snapshot changed: ' + $file.path) }
}
Write-Host 'Snapshot hashes verified. No model, texture, SDK or login files are in this snapshot.'
if ($ValidateOnly) { Write-Host 'VALIDATION ONLY: no login, clone, commit or push was performed.'; exit 0 }
if (-not $SkipLogin) {
    Write-Host 'Sign in using the official Git Credential Manager browser flow if requested.'
    Run-Git -GitArgs @('credential-manager','github','login','--browser')
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$checkoutRoot = Join-Path $deliveryRoot ('publish-checkout-' + $stamp)
if (Test-Path -LiteralPath $checkoutRoot) { throw 'Checkout directory already exists; rerun after one second. Nothing was overwritten.' }
Run-Git -GitArgs @('-c','credential.helper=manager','clone','--no-tags',$remoteUrl,$checkoutRoot)
$branch = 'checkpoint/2026-11-17-physics-' + $stamp
Run-Git -GitArgs @('-C',$checkoutRoot,'checkout','-b',$branch)
$relativeTarget = 'checkpoints/2026-11-17-physics-' + $stamp
$targetRoot = Child-Path $checkoutRoot $relativeTarget
New-Item -ItemType Directory -Path $targetRoot | Out-Null
foreach ($file in $snapshotManifest.files) {
    $sourcePath = Child-Path $snapshotRoot $file.path
    $targetPath = Child-Path $targetRoot $file.path
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($targetPath)) -Force | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath
    if ((Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) { throw ('Copied snapshot hash mismatch: ' + $file.path) }
}
Run-Git -GitArgs @('-C',$checkoutRoot,'add','--',$relativeTarget)
Run-Git -GitArgs @('-C',$checkoutRoot,'-c','user.name=Hotel Room Local Development','-c','user.email=hotel-room@localhost','commit','-m','Checkpoint hotel room asset library and full-room rigid physics results')
$commit = (& git -C $checkoutRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot read local commit identity' }
Run-Git -GitArgs @('-C',$checkoutRoot,'-c','credential.helper=manager','push','--set-upstream','origin',('HEAD:refs/heads/' + $branch))
$remoteLine = & git -C $checkoutRoot -c credential.helper=manager ls-remote origin ('refs/heads/' + $branch)
if ($LASTEXITCODE -ne 0 -or -not $remoteLine) { throw 'Push command completed but remote verification failed. No success receipt written.' }
$remoteCommit = ($remoteLine -split [char]9)[0]
if ($remoteCommit -ne $commit) { throw 'Remote commit does not match the prepared local commit' }
$receipt = [ordered]@{ outcome='PASS'; repository=$remoteUrl; branch=$branch; commit=$commit; remote_commit=$remoteCommit; checkpoint_path=$relativeTarget; pushed_at=(Get-Date).ToUniversalTime().ToString('o'); commit_url=('https://github.com/FrankChen0930/hotel-room-clutter-generator/commit/' + $commit); checkout=$checkoutRoot }
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $deliveryRoot 'push_receipt.json') -Encoding UTF8
Write-Host 'PUSH VERIFIED. Original remote branches and all local project baselines were preserved.'
Write-Host $receipt.commit_url
Write-Host ('Receipt: ' + (Join-Path $deliveryRoot 'push_receipt.json'))
'''
    (delivery/'Publish-Checkpoint.ps1').write_text(script,encoding='utf-8-sig')
    print('PUBLISHER_PREPARED',delivery/'Publish-Checkpoint.ps1','files',len(files))

if __name__=='__main__':main()
