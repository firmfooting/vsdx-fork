# Visio ground-truth validator: opens .vsdx files in Visio (InvisibleApp)
# and reports pages, shapes, connectors, and glue formula fidelity.
# Usage: visio_check.ps1 -Paths <file-or-dir> [<file-or-dir> ...]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Paths
)

$ErrorActionPreference = 'Stop'

function Get-VsdxFiles {
    param([string]$p)
    if (Test-Path $p -PathType Container) {
        return Get-ChildItem -Path $p -Filter *.vsdx | ForEach-Object { $_.FullName }
    }
    return @((Resolve-Path $p).Path)
}

$files = @()
foreach ($p in $Paths) { $files += Get-VsdxFiles $p }

if ($files.Count -eq 0) { Write-Output 'NO FILES'; exit 1 }

$app = $null
try {
    $app = New-Object -ComObject Visio.InvisibleApp
    foreach ($f in $files) {
        try {
            $doc = $app.Documents.Open($f)
            $totalConnectors = 0
            $walkglueCount = 0
            $details = @()
            foreach ($page in $doc.Pages) {
                $oneD = @()
                foreach ($shape in $page.Shapes) {
                    $hasBeginX = $false
                    try { $null = $shape.Cells('BeginX'); $hasBeginX = $true } catch { $hasBeginX = $false }
                    if ($hasBeginX) {
                        $oneD += $shape.NameID
                        $totalConnectors++
                        try {
                            $formula = $shape.Cells('BeginX').FormulaU
                            if ($formula -like '*_WALKGLUE*') { $walkglueCount++ }
                            $details += ("  page={0} conn={1} BeginX={2}" -f $page.Index, $shape.NameID, $formula)
                        } catch {
                            $details += ("  page={0} conn={1} BeginX=<unreadable>" -f $page.Index, $shape.NameID)
                        }
                    }
                }
                $details += ("  page={0} name={1} shapes={2} connectors={3}" -f $page.Index, $page.Name, $page.Shapes.Count, $oneD.Count)
            }
            Write-Output ("PASS {0}: pages={1} connectors={2} walkglue={3}" -f (Split-Path $f -Leaf), $doc.Pages.Count, $totalConnectors, $walkglueCount)
            $details | ForEach-Object { Write-Output $_ }
            $doc.Close()
        } catch {
            Write-Output ("FAIL {0}: {1}" -f (Split-Path $f -Leaf), $_.Exception.Message)
        }
    }
} finally {
    if ($app -ne $null) {
        try { $app.Quit() } catch { }
    }
}
