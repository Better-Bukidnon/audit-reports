# Save the list numbers Word shows in each COA Word report, so scripts/extract_phase1.py can
# check its own count of them ("findings: numbers match Word's").
#
# Usage (Windows with Microsoft Word installed):
#     powershell -NoProfile -ExecutionPolicy Bypass -File scripts\word_list_numbers.ps1 [-Force]
#
# For every raw/<year>/<lgu>/extracted/**/*.docx it writes <report>.word-lists.tsv beside it:
# one line per list paragraph, "start offset <tab> number as Word shows it <tab> first 80
# characters". Reports that already have one are skipped unless -Force.
#
# Word opens a copy of each report, read-only, invisible and with macros off, and reads
# Document.ListParagraphs; nothing is laid out, saved or printed. Each report gets its own Word
# process. After each report the driver stops that Word if it is still running, whatever
# happened, and it stops one that takes longer than -TimeoutSec. On 2026-11-07 each report
# took about 10 seconds and Word about 300 MB. (Saving a report as text through Word instead
# stalled for over 8 minutes; don't.) The run stops if less than 4 GB of memory is free.
param(
    [string]$Repo = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [int]$TimeoutSec = 300,
    [switch]$Force,
    # internal: one report, run in its own process. (PowerShell names ignore case, so no
    # variable below may share a name with these.)
    [switch]$Worker,
    [string]$ReportPath,
    [string]$OutFile,
    [string]$PidFile
)
$ErrorActionPreference = 'Stop'

if ($Worker) {
    $workDir = Join-Path $env:TEMP ('coa-word-lists-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force $workDir | Out-Null
    $copyPath = Join-Path $workDir 'report.docx'
    Copy-Item -LiteralPath $ReportPath -Destination $copyPath
    $wordApp = $null; $document = $null; $wordProc = $null; $status = 1
    $already = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    try {
        $wordApp = New-Object -ComObject Word.Application
        $wordProc = Get-Process WINWORD | Where-Object { $already -notcontains $_.Id } | Select-Object -First 1
        if ($wordProc -and $PidFile) { Set-Content -LiteralPath $PidFile -Value $wordProc.Id }
        $wordApp.Visible = $false
        $wordApp.DisplayAlerts = 0           # wdAlertsNone
        $wordApp.ScreenUpdating = $false
        $wordApp.AutomationSecurity = 3      # msoAutomationSecurityForceDisable: no macros
        # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles, PasswordDocument, PasswordTemplate,
        #      Revert, WritePasswordDocument, WritePasswordTemplate, Format, Encoding, Visible)
        $document = $wordApp.Documents.Open($copyPath, $false, $true, $false, '', '', $false, '', '', 0, 0, $false)
        $paragraphs = $document.ListParagraphs
        $total = $paragraphs.Count
        if ($total -lt 1) { throw "Word found no list paragraphs" }
        $sb = New-Object System.Text.StringBuilder
        for ($k = 1; $k -le $total; $k++) {
            $range = $paragraphs.Item($k).Range
            $text = $range.Text
            if ($text.Length -gt 80) { $text = $text.Substring(0, 80) }
            $text = $text -replace "[\t\r\n\a\v]", ' '
            [void]$sb.AppendLine(("{0}`t{1}`t{2}" -f $range.Start, $range.ListFormat.ListString, $text))
        }
        [IO.File]::WriteAllText($OutFile, $sb.ToString(), (New-Object Text.UTF8Encoding $false))
        $status = 0
    }
    catch {
        [Console]::Error.WriteLine("worker: " + $_.Exception.Message)
    }
    finally {
        # each step on its own, so one failing can't skip the rest
        try { if ($document) { $document.Close() | Out-Null } } catch {}
        try { if ($document) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document) } } catch {}
        try { if ($wordApp) { $wordApp.Quit() } } catch {}
        try { if ($wordApp) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp) } } catch {}
        try { [GC]::Collect(); [GC]::WaitForPendingFinalizers() } catch {}
        try { Start-Sleep -Seconds 2 } catch {}
        try { if ($wordProc) { Get-Process -Id $wordProc.Id -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue } } catch {}
        try { Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue } catch {}
    }
    exit $status
}

$self = $MyInvocation.MyCommand.Path
$rawDir = Join-Path $Repo 'raw'
$reports = Get-ChildItem $rawDir -Recurse -Filter '*.docx' |
    Where-Object { $_.FullName -match '\\extracted\\' -and $_.Name -notlike '~$*' } | Sort-Object FullName
$pidPath = Join-Path $env:TEMP 'coa-word-lists.pid'
foreach ($r in $reports) {
    $target = Join-Path $r.DirectoryName ($r.BaseName + '.word-lists.tsv')
    $name = $r.FullName.Substring($rawDir.Length + 1)
    if ((Test-Path $target) -and -not $Force) { continue }
    $free = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
    if ($free -lt 4) { "STOP: only {0:N1} GB of memory free" -f $free; break }
    Remove-Item $pidPath -ErrorAction SilentlyContinue
    Remove-Item $target -ErrorAction SilentlyContinue
    $t0 = Get-Date
    # quote every path: some report file names have spaces
    $argv = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $self + '"'), '-Worker',
              '-ReportPath', ('"' + $r.FullName + '"'), '-OutFile', ('"' + $target + '"'), '-PidFile', ('"' + $pidPath + '"'))
    $proc = Start-Process powershell -ArgumentList $argv -WindowStyle Hidden -PassThru
    $finished = $proc.WaitForExit($TimeoutSec * 1000)
    if (-not $finished) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
    # whatever happened, this report's Word goes
    if (Test-Path $pidPath) {
        Get-Process -Id ([int](Get-Content $pidPath)) -ErrorAction SilentlyContinue |
            Where-Object { $_.ProcessName -eq 'WINWORD' } | Stop-Process -Force -ErrorAction SilentlyContinue
    }
    $ok = (Test-Path $target) -and ((Get-Item $target).Length -gt 0)
    if (-not $ok) { Remove-Item $target -ErrorAction SilentlyContinue }
    $result = if (-not $finished) { "TIMEOUT after $TimeoutSec s" } elseif ($ok) { 'ok' } else { 'FAILED' }
    "{0}: {1} in {2}s" -f $name, $result, [int]((Get-Date) - $t0).TotalSeconds
}
Remove-Item $pidPath -ErrorAction SilentlyContinue
"WINWORD processes left: {0}" -f @(Get-Process WINWORD -ErrorAction SilentlyContinue).Count
