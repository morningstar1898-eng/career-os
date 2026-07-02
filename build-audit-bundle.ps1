# Builds CareerOS-Audit-Bundle.zip on OneDrive Desktop.
# Run from anywhere:  & 'C:\Users\morni\career-os-explore\build-audit-bundle.ps1'
# Then drag the zip into ChatGPT with: "Unzip this and follow _START_HERE.txt"
#
# Uses git archive: packages exactly what the latest commit tracks. The repo
# .gitignore keeps .env, google_credentials.json, kaggle.json, and *.db out of
# git, so they can never end up in the bundle.
# COMMIT YOUR CHANGES FIRST - uncommitted edits are not included.
#
# NOTE: this repo has a GitHub remote. This clone (career-os-explore) is the
# synced one - the OneDrive\Assistant\career_os copy is stale. The script
# warns if this clone is behind origin/master.

$project = 'C:\Users\morni\career-os-explore'
$zipPath = 'C:\Users\morni\OneDrive\Desktop\CareerOS-Audit-Bundle.zip'

Set-Location $project

$dirty = git status --porcelain
if ($dirty) {
    Write-Warning "Uncommitted changes exist - they will NOT be in the bundle:"
    $dirty | ForEach-Object { Write-Warning "  $_" }
    Write-Warning "Commit first (git add -A; git commit -m '...') then rerun."
}

git fetch origin 2>$null
$behind = git rev-list HEAD..origin/master --count
if ([int]$behind -gt 0) {
    Write-Warning "This clone is $behind commit(s) BEHIND GitHub master - run 'git pull' first for the latest code."
}

git archive --format=zip -o $zipPath HEAD

# Safety net: fail loudly if a known secret file ever ends up inside the zip.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
$bad = $zip.Entries | Where-Object {
    $_.Name -eq '.env' -or $_.Name -like '*.env' -or
    $_.Name -eq 'google_credentials.json' -or $_.Name -eq 'kaggle.json' -or
    $_.Name -like '*.db'
} | Where-Object { $_.Name -ne '.env.template' }
$zip.Dispose()
if ($bad) {
    Remove-Item $zipPath -Force
    $names = ($bad | ForEach-Object { $_.FullName }) -join ', '
    throw "SECRET LEAK BLOCKED: sensitive files were tracked by git ($names). Fix .gitignore / git rm --cached them, then rerun."
}

$zipItem = Get-Item $zipPath
Write-Host ("Built {0} ({1:N0} KB) from commit {2} - drag into ChatGPT with: 'Unzip this and follow _START_HERE.txt'" -f $zipItem.Name, ($zipItem.Length / 1KB), (git rev-parse --short HEAD))
