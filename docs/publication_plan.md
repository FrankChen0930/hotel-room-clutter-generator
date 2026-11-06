# P5.2 Private GitHub Publication Plan - REMOTE ACTIONS NOT AUTHORIZED

Target: `FrankChen0930/hotel-room-clutter-generator`, PRIVATE. Recheck the authenticated personal owner before any later remote action. This preparation creates only local main and a first commit; no remote, tag, Release, LFS transfer or asset upload.

Version: `0.1.0-rc.1-internal`. INTERNAL_EVALUATION_ONLY / REDISTRIBUTION_NOT_CLEARED / LICENSE_PENDING_HUMAN_APPROVAL remain in force. A private repository still distributes code. Human must approve exact files, rights, audience, destination and first push. No open-source license is selected. Asset authorization is separate.

## Proposed first push after explicit Human authorization

Use PowerShell from this isolated repository. Read the separate Final QA Report and its exact approved First Commit SHA. Stop on every mismatch or nonzero exit. These commands are a review plan, not an upload script to execute during preparation.

1. Confirm `gh api user --jq '{id,login}'` returns ID 113695822 and login FrankChen0930. Confirm `git status --porcelain=v1` is empty, `git branch --show-current` is main, `git rev-parse HEAD` equals the approved SHA, `git rev-list --count HEAD` is 1, `git remote -v` is empty, and tracked files/hashes match the approved inventory. Re-run local QA if content changes.
2. Check the exact destination using `gh repo view FrankChen0930/hotel-room-clutter-generator --json nameWithOwner,visibility,isPrivate,url`. If it exists, stop for a separate decision; do not automatically reuse it. A failed lookup is not proof of absence: distinguish authentication/network errors and verify absence through GitHub before creation.
3. After approval and confirmed absence, create an empty PRIVATE repository without automatic push, README, license, template or gitignore:

~~~powershell
gh repo create FrankChen0930/hotel-room-clutter-generator --private --disable-wiki
if ($LASTEXITCODE -ne 0) { throw 'Creation failed; inspect actual remote state before retrying' }
$repo = gh repo view FrankChen0930/hotel-room-clutter-generator --json nameWithOwner,visibility,isPrivate,url | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $repo.nameWithOwner -cne 'FrankChen0930/hotel-room-clutter-generator' -or $repo.visibility -ne 'PRIVATE' -or $repo.isPrivate -ne $true) { throw 'Private destination verification failed; do not push' }
git remote add origin https://github.com/FrankChen0930/hotel-room-clutter-generator.git
if ($LASTEXITCODE -ne 0) { throw 'Remote configuration failed' }
git remote get-url --all origin
git config --get-all remote.origin.pushurl
~~~

The only fetch URL must be the exact URL above; no pushurl override may exist (a missing pushurl normally gives exit 1). Review effective Git URL rewrites and credential configuration. Verify the remote has no refs using `git ls-remote origin`; check its exit code. If refs exist, stop. Recheck exact PRIVATE identity immediately before the approved push. Do not use --all, --mirror, --tags or --force.

~~~powershell
git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push -u origin main:main
if ($LASTEXITCODE -ne 0) { throw 'Push failed; inspect remote refs before retrying' }
gh repo view FrankChen0930/hotel-room-clutter-generator --json nameWithOwner,visibility,isPrivate,defaultBranchRef,url
git ls-remote origin refs/heads/main
git status --porcelain=v1
~~~

Verify PRIVATE, exact owner/name, default branch main, remote main equal to the approved SHA, and a clean tree. Verify GitHub shows the expected 39-file code inventory, no assets/QA evidence, no Release/tag, intended audience, and noreply author. Do not add collaborators or change visibility as part of the first push. The credential helper is command-scoped; never print tokens or write global configuration.

## Asset plan and rollback

Asset Package stays outside Git; asset_lock.json contains identifiers/hashes, not data. Do not use Git LFS, commit assets, create an archive, tag or Release now. A future `yazhi-assets-0.1.0-rc.1-internal.zip` requires separate exact-file rights/recipient/upload approval, pinned compatible code commit and package SHA256, safe extraction/relative-USD closure checks and fresh downloaded-pair preflight. No LFS need is established by the roughly 8 MB package; verify current service limits at upload time.

If remote creation fails ambiguously, inspect actual server state before retrying. If creation succeeds but push is withheld, leave the empty private repository and report; deletion requires a separate decision. Local `git remote remove origin` removes only the local association. For an incorrect published commit, retain evidence and use a reviewed corrective commit/revert; do not force-push or delete history automatically. For exposure, stop distribution and seek a rights/security decision; deletion cannot undo access already granted.

For deployment rollback, select the retained prior code/asset pair and its own saved manifests. Never edit immutable locks or replace candidate data. Preserve local first commit, source hashes, evidence and old outputs. No destructive reset, clean, source cleanup or remote deletion is authorized by this plan.
