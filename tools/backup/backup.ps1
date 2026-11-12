<#
  tools/backup/backup.ps1 — Windows version of backup.sh.
  Copies the school's data into your own OneDrive / Google Drive via rclone:
  the year/month/day archive files, and a full pg_dump when pg_dump is
  installed.

  Usage (PowerShell, from the repository root):

    $env:ARCHIVE_EMAIL='principal@astro-school.test'
    $env:ARCHIVE_PASSWORD='Astro-Principal-2026'
    $env:RCLONE_REMOTE='onedrive:astro-smart-attendance'
    .\tools\backup\backup.ps1 -NoUpload      # write files, upload nothing
    .\tools\backup\backup.ps1                # write + upload

  Optional environment:
    SUPABASE_DB_URL    postgres connection string (only needed for the dump)
    BACKUP_DIR         where the copies land (default .\backups)
    KEEP_LOCAL         how many local dumps to keep (default 14)
    SUPABASE_URL / SUPABASE_KEY   default to this project's public values

  Switches: -NoUpload, -SkipDb, -SkipArchive
#>
[CmdletBinding()]
param(
  [switch]$NoUpload,
  [switch]$SkipDb,
  [switch]$SkipArchive,
  [int]$KeepLocal = 14,
  [string]$BackupDir = ''
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root
if (-not $BackupDir) { $BackupDir = Join-Path $root 'backups' }
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$remote = $env:RCLONE_REMOTE

function Say($m) { Write-Host $m }
function Fail($m) { Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------- 1. dump ---
$dump = Join-Path $BackupDir "astro-$stamp.sql.gz"
if ($SkipDb) {
  Say '== database dump: skipped (-SkipDb) =='
} elseif (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
  Say '== database dump: skipped — pg_dump is not installed =='
  Say '   (install the PostgreSQL client and rerun for a full dump; the day archive still runs)'
} else {
  if (-not $env:SUPABASE_DB_URL) { Fail 'SUPABASE_DB_URL is not set (Supabase dashboard -> Project Settings -> Database -> Connection string -> URI, replace [YOUR-PASSWORD])' }
  Say '== database dump =='
  $sql = Join-Path $env:TEMP "astro-$stamp.sql"
  try {
    & pg_dump --no-owner --no-privileges --clean --if-exists $env:SUPABASE_DB_URL |
      Out-File -FilePath $sql -Encoding utf8
    if ($LASTEXITCODE -ne 0) { Fail "pg_dump failed (exit $LASTEXITCODE) — check the password in SUPABASE_DB_URL" }

    $in = [System.IO.File]::OpenRead($sql)
    try {
      $out = [System.IO.File]::Create($dump)
      try {
        $gz = New-Object System.IO.Compression.GZipStream($out, [System.IO.Compression.CompressionLevel]::Optimal)
        try { $in.CopyTo($gz) } finally { $gz.Dispose() }
      } finally { $out.Dispose() }
    } finally { $in.Dispose() }
    $mbTrunc = [math]::Round((Get-Item $dump).Length / 1MB, 2)
    Say "   $dump  (${mbTrunc} MB)"
  } finally {
    Remove-Item $sql -Force -ErrorAction SilentlyContinue
  }
}

# ------------------------------------------------------------- 2. archive ---
$aOut = Join-Path $BackupDir 'archive'
if ($SkipArchive) {
  Say '== day archive: skipped (-SkipArchive) =='
} else {
  if (-not $env:ARCHIVE_EMAIL -or -not $env:ARCHIVE_PASSWORD) {
    Fail 'ARCHIVE_EMAIL / ARCHIVE_PASSWORD are not set (a staff login; the archive signs in as that user)'
  }
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail 'Node.js is not installed — needed for the archive step' }
  $env:SUPABASE_URL = if ($env:SUPABASE_URL) { $env:SUPABASE_URL } else { 'https://nrjchonjlncamfyzmfye.supabase.co' }
  $env:SUPABASE_KEY = if ($env:SUPABASE_KEY) { $env:SUPABASE_KEY } else { 'sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_' }
  $month = (Get-Date).AddDays(-1).ToString('yyyy-MM')
  Say "== day archive ($month) =="
  & node tools/archive/archive.mjs --month $month --out $aOut --skip-empty
  if ($LASTEXITCODE -ne 0) { Fail "archive failed (exit $LASTEXITCODE)" }
}

# -------------------------------------------------------------- 3. upload ---
if ($NoUpload) {
  Say '== upload: skipped (-NoUpload) — files are in'
  Say "   $BackupDir"
  exit 0
}

if (-not $remote) { Fail "RCLONE_REMOTE is not set (e.g. onedrive:astro-smart-attendance)" }
if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) { Fail 'rclone is not installed — see https://rclone.org/downloads/' }
$known = (rclone listremotes) -join "`n"
if ($known -notmatch ("(?m)^" + [regex]::Escape(($remote -split ':')[0]) + ":$")) {
  Fail "rclone has no remote named '$($remote -split ':')[0]'. Configure it with: rclone config"
}

Say "== upload to $remote =="
if (Test-Path $dump) { rclone copy $dump "$remote/database" --stats-one-line }
if (Test-Path $aOut)  { rclone copy $aOut "$remote/archive" --stats-one-line }
rclone delete "$remote/database" --min-age 90d 2>$null | Out-Null

# keep only the newest $KeepLocal dumps on this PC
Get-ChildItem $BackupDir -Filter 'astro-*.sql.gz' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip $KeepLocal |
  Remove-Item -Force -ErrorAction SilentlyContinue

Say "done. Latest copy: $remote/database/$(Split-Path -Leaf $dump)"
