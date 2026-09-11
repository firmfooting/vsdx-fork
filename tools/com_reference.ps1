# COM reference corpus generator.
# Builds scenario .vsdx files with real Visio (InvisibleApp) and captures
# connector cell formulas so the Python rewrite has ground truth to match.
# Run from WSL via: powershell.exe -NoProfile -ExecutionPolicy Bypass -File <this file>
# Output: C:\tmp\vsdx_corpus\<scenario>.vsdx + manifest.json

$ErrorActionPreference = 'Continue'
$OutDir = 'C:\tmp\vsdx_corpus'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$app = New-Object -ComObject Visio.InvisibleApp
$manifest = [ordered]@{
    generated = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
    visio_version = $app.Version
    scenarios = @()
}

$CellNames = @('BeginX','BeginY','EndX','EndY','BegTrigger','EndTrigger','EndXTrigger',
               'GlueType','ObjType','ShapeRouteStyle','ConLineRouteExt','ConFixedCode',
               'BegPrompt','EndPrompt','DirX','DirY','Type')

function Get-MasterName($shape) {
    try { return $shape.Master.Name } catch { return $null }
}

function Get-ShapeText($shape) {
    try { return $shape.Text.Trim() } catch { return '' }
}

function Capture-Connector($shape) {
    $cells = [ordered]@{}
    foreach ($n in $CellNames) {
        try { $cells[$n] = $shape.Cells($n).FormulaU } catch { $cells[$n] = $null }
    }
    return [ordered]@{
        name = $shape.Name
        id = $shape.ID
        one_d = $shape.OneD
        master = (Get-MasterName $shape)
        cells = $cells
    }
}

function Capture-Page($page) {
    $shapes = @()
    foreach ($s in $page.Shapes) {
        $isConn = ($s.OneD -eq -1)
        if ($isConn) { $shapes += Capture-Connector $s }
        else {
            $containerInfo = $null
            try {
                $cp2 = $s.ContainerProperties
                if ($cp2) { $containerInfo = [ordered]@{ style = $cp2.ContainerStyle; lockMembership = $cp2.LockMembership } }
            } catch {}
            $shapes += [ordered]@{
                name = $s.Name; id = $s.ID; one_d = $s.OneD
                master = (Get-MasterName $s)
                text = (Get-ShapeText $s)
                container = $containerInfo
                cells = [ordered]@{}
            }
        }
    }
    return $shapes
}

function Save-Scenario($doc, $page, $scenName, $notes) {
    $path = Join-Path $OutDir "$scenName.vsdx"
    $doc.SaveAs($path) | Out-Null
    $manifest.scenarios += [ordered]@{
        scenario = $scenName
        file = "$scenName.vsdx"
        shapes = (Capture-Page $page)
        notes = $notes
    }
    Write-Output "SAVED $path"
}

# ---- s01: AutoConnect right (shape glue, dynamic connector) ----
$doc = $app.Documents.Add('')
$page = $app.ActivePage
$a = $page.DrawRectangle(1, 9, 3, 8); $a.Text = 'A'
$b = $page.DrawRectangle(5, 9, 7, 8); $b.Text = 'B'
$before = $page.Shapes.Count
$a.AutoConnect($b, 4)   # 4 = right
$conn = $null
foreach ($s in $page.Shapes) { if ($s.OneD -eq -1) { $conn = $s } }
$notes = if ($conn) { "AutoConnect(right) created $($page.Shapes.Count - $before) shape(s); connector=$($conn.Name)" } else { 'AutoConnect produced no 1-D shape' }
Save-Scenario $doc $page 's01_autoconnect_right' $notes
$doc.Close()

# ---- s02: dropped connector tool, GlueTo PinX (dynamic shape glue) ----
$doc = $app.Documents.Add('')
$page = $app.ActivePage
$a = $page.DrawRectangle(1, 9, 3, 8); $a.Text = 'A'
$b = $page.DrawRectangle(5, 9, 7, 8); $b.Text = 'B'
$conn = $page.Drop($app.ConnectorToolDataObject, 4, 8.5)
try {
    $conn.Cells('BeginX').GlueTo($a.Cells('PinX')) | Out-Null
    $conn.Cells('EndX').GlueTo($b.Cells('PinX')) | Out-Null
    $notes = 'GlueTo(PinX) on both ends succeeded'
} catch { $notes = "GlueTo failed: $($_.Exception.Message)" }
Save-Scenario $doc $page 's02_glue_pin' $notes
$doc.Close()

# ---- s03: route variants (right-angle / straight / curved) ----
$doc = $app.Documents.Add('')
$page = $app.ActivePage
$a = $page.DrawRectangle(1, 9, 3, 8); $a.Text = 'A'
$b = $page.DrawRectangle(5, 6, 7, 5); $b.Text = 'B'
$routeNotes = @()
$conn1 = $page.Drop($app.ConnectorToolDataObject, 2, 7)
$conn1.Cells('BeginX').GlueTo($a.Cells('PinX')) | Out-Null
$conn1.Cells('EndX').GlueTo($b.Cells('PinX')) | Out-Null
try { $conn1.CellsU('ShapeRouteStyle').FormulaU = 'USE(' + $conn1.CellsU('ShapeRouteStyle').FormulaU + ')'; $conn1.CellsU('ShapeRouteStyle').FormulaU = '1' } catch { $routeNotes += "rightangle set failed: $($_.Exception.Message)" }
$routeNotes += "conn1(ShapeRouteStyle=1 right angle): $($conn1.Cells('ShapeRouteStyle').FormulaU)"

$conn2 = $page.Drop($app.ConnectorToolDataObject, 4, 7)
$conn2.Cells('BeginX').GlueTo($a.Cells('PinX')) | Out-Null
$conn2.Cells('EndX').GlueTo($b.Cells('PinX')) | Out-Null
try { $conn2.CellsU('ShapeRouteStyle').FormulaU = '16' } catch { $routeNotes += "straight set failed: $($_.Exception.Message)" }
$routeNotes += "conn2(ShapeRouteStyle=16 straight): $($conn2.Cells('ShapeRouteStyle').FormulaU)"

$conn3 = $page.Drop($app.ConnectorToolDataObject, 6, 7)
$conn3.Cells('BeginX').GlueTo($a.Cells('PinX')) | Out-Null
$conn3.Cells('EndX').GlueTo($b.Cells('PinX')) | Out-Null
try {
    $conn3.CellsU('ShapeRouteStyle').FormulaU = '17'
    $conn3.CellsU('ConLineRouteExt').FormulaU = '2'   # curved ext
} catch { $routeNotes += "curved set failed: $($_.Exception.Message)" }
$routeNotes += "conn3(ShapeRouteStyle=17 + ConLineRouteExt=2 curved): $($conn3.Cells('ShapeRouteStyle').FormulaU)"

Save-Scenario $doc $page 's03_route_variants' ($routeNotes -join '; ')
$doc.Close()

# ---- s04: point glue to connection points ----
$doc = $app.Documents.Add('')
$page = $app.ActivePage
$a = $page.DrawRectangle(1, 9, 3, 8); $a.Text = 'A'
$b = $page.DrawRectangle(5, 9, 7, 8); $b.Text = 'B'
$conn = $page.Drop($app.ConnectorToolDataObject, 4, 8.5)
$pointNotes = @()
$beginCell = $null; $endCell = $null
foreach ($candidate in @('ConnectionXY1', 'Connections.X1')) {
    try { $beginCell = $a.Cells($candidate); $pointNotes += "begin cell name that worked: $candidate on A"; break } catch {}
}
foreach ($candidate in @('ConnectionXY1', 'Connections.X1')) {
    try { $endCell = $b.Cells($candidate); $pointNotes += "end cell name that worked: $candidate on B"; break } catch {}
}
if ($beginCell -and $endCell) {
    try {
        $conn.Cells('BeginX').GlueTo($beginCell) | Out-Null
        $conn.Cells('EndX').GlueTo($endCell) | Out-Null
        $pointNotes += 'point glue succeeded'
    } catch { $pointNotes += "point glue failed: $($_.Exception.Message)" }
} else { $pointNotes += 'no connection-point cell resolved on target shapes' }
Save-Scenario $doc $page 's04_point_glue' ($pointNotes -join '; ')
$doc.Close()

# ---- s05: cross-functional flowchart (swimlanes) from built-in template ----
$templateUsed = $null
$cffDoc = $null
foreach ($t in @('CFF_HORIZONTAL_M.VSTX', 'CFF_VERTICAL_M.VSTX', 'XFUNC_M.VSTX', 'NEW_XFUNC_M.VSTX')) {
    try { $cffDoc = $app.Documents.Add($t); $templateUsed = $t; break } catch {}
}
if ($cffDoc) {
    $cffPage = $app.ActivePage
    $cffNotes = @("template=$templateUsed")
    # enumerate stencil documents opened alongside the template
    $stencil = $null
    foreach ($d in $app.Documents) {
        if ($d.Type -eq 2) { # visStencil
            $cffNotes += "stencil open: $($d.Name) masters=$($d.Masters.Count)"
            if (-not $stencil) { $stencil = $d }
        }
    }
    # find first lane container on the page
    $lane = $null
    foreach ($s in $cffPage.Shapes) {
        try { if ($s.ContainerProperties) { $lane = $s; break } } catch {}
    }
    if ($lane) {
        $cffNotes += "lane=$($lane.Name) style=$($lane.ContainerProperties.ContainerStyle) locked=$($lane.ContainerProperties.LockMembership)"
        # drop a dynamic connector master? no - drop a basic process-ish master into lane if stencil has one
        if ($stencil) {
            foreach ($m in $stencil.Masters) { $cffNotes += "  master: $($m.Name)" }
            try {
                $proc = $stencil.Masters.Item(1)
                $dropped = $cffPage.Drop($proc, 3.0, 7.0)
                try { $lane.ContainerProperties.AddMember($dropped) | Out-Null; $cffNotes += "dropped $($dropped.Name) and added to lane membership" } catch { $cffNotes += "dropped $($dropped.Name); AddMember failed: $($_.Exception.Message)" }
            } catch { $cffNotes += "drop failed: $($_.Exception.Message)" }
        }
        # attempt to add a lane
        try { $lane.ContainerProperties.InsertRow(2) | Out-Null; $cffNotes += 'InsertRow(2) lane added' } catch { $cffNotes += "InsertRow failed: $($_.Exception.Message)" }
    } else {
        $cffNotes += 'no container shapes found on template page'
    }
    Save-Scenario $cffDoc $cffPage 's05_swimlanes_cfflow' ($cffNotes -join '; ')
    $cffDoc.Close()
} else {
    $manifest.scenarios += [ordered]@{
        scenario = 's05_swimlanes_cfflow'; file = $null
        shapes = @(); notes = 'no cross-functional template resolved by name; corpus lacks real swimlane XML'
    }
    Write-Output 'S05: no CFFLOW template found'
}

# ---- s06: basic flowchart template with stencil masters ----
$templateUsed = $null
$basDoc = $null
foreach ($t in @('BASFLO_M.vstx', 'Basic Flowchart - Metric.vstx', 'Basic Flowchart Shapes (Metric).vssx')) {
    try { $basDoc = $app.Documents.Add($t); $templateUsed = $t; break } catch {}
}
if ($basDoc) {
    $basPage = $app.ActivePage
    $basNotes = "template=$templateUsed; top shapes=$($basPage.Shapes.Count)"
    Save-Scenario $basDoc $basPage 's06_basflow_stencils' $basNotes
    $basDoc.Close()
} else {
    Write-Output 'S06: no BASFLO template found'
}

$manifest | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $OutDir 'manifest.json')
Write-Output "MANIFEST written to $OutDir\manifest.json"

try { $app.Quit() } catch {}
