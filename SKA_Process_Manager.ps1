param(
    [string]$WindowsRepo = 'C:\mycode\SemantiK_Architect\SemantiK_Architect',
    [string]$WslRepo = '/mnt/c/mycode/SemantiK_Architect/SemantiK_Architect',
    [int[]]$ProjectPorts = @(8000, 3000),
    [switch]$IncludeRedisPort6379
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Application]::EnableVisualStyles()

$global:StatusLabel = $null
$global:Grid = $null
$global:Form = $null

function Set-Status {
    param([string]$Message)
    if ($global:StatusLabel -ne $null) {
        $global:StatusLabel.Text = $Message
        $global:StatusLabel.Refresh()
    }
}

function Safe-Trim {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return '' }
    return ([string]$Value).Trim()
}

function Test-ProjectMatch {
    param(
        [string]$CommandLine,
        [string]$ProcessName
    )

    $cmd = Safe-Trim $CommandLine
    $name = (Safe-Trim $ProcessName).ToLowerInvariant()
    $cmdLower = $cmd.ToLowerInvariant()
    $winRepoLower = $WindowsRepo.ToLowerInvariant()
    $wslRepoLower = $WslRepo.ToLowerInvariant()

    if ($cmdLower.Contains($winRepoLower) -or $cmdLower.Contains($wslRepoLower)) {
        return $true
    }

    $markers = @(
        'semantik_architect',
        'app.adapters.api.main:create_app',
        'app.workers.worker.workersettings',
        'python manage.py',
        'uvicorn',
        'next dev',
        'architect_frontend',
        'tools/run',
        'start_api.sh',
        'start_worker.sh'
    )

    foreach ($marker in $markers) {
        if ($cmdLower.Contains($marker)) {
            return $true
        }
    }

    if ($name -in @('python.exe', 'python3', 'python', 'node.exe', 'node', 'wsl.exe', 'bash', 'sh')) {
        if ($cmdLower.Contains('semantik') -or $cmdLower.Contains('architect')) {
            return $true
        }
    }

    return $false
}

function Get-WindowsProcesses {
    $results = @()

    try {
        $procs = Get-CimInstance Win32_Process -ErrorAction Stop |
            Select-Object ProcessId, Name, CommandLine
    }
    catch {
        Set-Status "Failed to query Windows processes: $($_.Exception.Message)"
        return @()
    }

    foreach ($proc in $procs) {
        $cmd = Safe-Trim $proc.CommandLine
        $name = Safe-Trim $proc.Name

        if (-not (Test-ProjectMatch -CommandLine $cmd -ProcessName $name)) {
            continue
        }

        $results += [pscustomobject]@{
            Origin     = 'Windows'
            PID        = [int]$proc.ProcessId
            Name       = $name
            Command    = $cmd
            Ports      = ''
            KillTarget = 'windows'
        }
    }

    return $results
}

function Get-WslProcesses {
    $results = @()

    $bashScript = @"
ps -eo pid=,comm=,args= --no-headers 2>/dev/null | awk 'NF {print}'
"@

    try {
        $lines = & wsl.exe --cd $WslRepo --exec bash -lc $bashScript 2>$null
    }
    catch {
        Set-Status "Failed to query WSL processes: $($_.Exception.Message)"
        return @()
    }

    foreach ($line in $lines) {
        $text = Safe-Trim $line
        if (-not $text) { continue }

        if ($text -match '^\s*(\d+)\s+(\S+)\s+(.*)$') {
            $procId = [int]$matches[1]
            $name = $matches[2]
            $cmd = $matches[3]
        }
        else {
            continue
        }

        if (-not (Test-ProjectMatch -CommandLine $cmd -ProcessName $name)) {
            continue
        }

        $results += [pscustomobject]@{
            Origin     = 'WSL'
            PID        = $procId
            Name       = $name
            Command    = $cmd
            Ports      = ''
            KillTarget = 'wsl'
        }
    }

    return $results
}

function Get-WindowsPortOwners {
    param([int[]]$Ports)

    $map = @{}
    foreach ($port in $Ports) {
        $map[$port] = @()
    }

    try {
        $connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $Ports -contains $_.LocalPort }

        foreach ($conn in $connections) {
            if (-not $map.ContainsKey($conn.LocalPort)) {
                $map[$conn.LocalPort] = @()
            }
            $map[$conn.LocalPort] += [string]$conn.OwningProcess
        }
    }
    catch {
        # ignore and fall back
    }

    $ownerCount = (($map.Values | ForEach-Object { $_.Count } | Measure-Object -Sum).Sum)
    if ($ownerCount -gt 0) {
        return $map
    }

    try {
        $netstat = netstat -ano -p tcp | Select-String 'LISTENING'
        foreach ($line in $netstat) {
            $text = (($line.ToString()) -replace '\s+', ' ').Trim()
            if ($text -match '^[A-Z]+\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)$') {
                $port = [int]$matches[1]
                $procId = $matches[2]
                if ($Ports -contains $port) {
                    if (-not $map.ContainsKey($port)) {
                        $map[$port] = @()
                    }
                    $map[$port] += [string]$procId
                }
            }
        }
    }
    catch {
        # ignore
    }

    return $map
}

function Get-WslPortOwners {
    param([int[]]$Ports)

    $map = @{}
    foreach ($port in $Ports) {
        $map[$port] = @()
    }

    $bashScript = @"
ss -ltnpH 2>/dev/null | awk 'NF {print}'
"@

    try {
        $lines = & wsl.exe --cd $WslRepo --exec bash -lc $bashScript 2>$null
    }
    catch {
        return $map
    }

    foreach ($line in $lines) {
        $text = Safe-Trim $line
        if (-not $text) { continue }

        foreach ($port in $Ports) {
            if ($text -notmatch "[:\.]$port\s") { continue }

            if ($text -match 'pid=(\d+)') {
                $procId = [string]$matches[1]
                if (-not $map.ContainsKey($port)) {
                    $map[$port] = @()
                }
                $map[$port] += $procId
            }
        }
    }

    return $map
}

function Add-PortsToRows {
    param([array]$Rows)

    $ports = @($ProjectPorts)
    if ($IncludeRedisPort6379) {
        $ports += 6379
    }

    $windowsOwners = Get-WindowsPortOwners -Ports $ports
    $wslOwners = Get-WslPortOwners -Ports $ports

    foreach ($row in $Rows) {
        $matchedPorts = @()

        foreach ($port in $ports) {
            $owners = @()

            if ($row.Origin -eq 'Windows') {
                $owners = @($windowsOwners[$port])
            }
            elseif ($row.Origin -eq 'WSL') {
                $owners = @($wslOwners[$port])
            }

            if ($owners -contains ([string]$row.PID)) {
                $matchedPorts += [string]$port
            }
        }

        $row.Ports = ($matchedPorts | Select-Object -Unique) -join ', '
    }

    return $Rows
}

function Get-ProjectProcessRows {
    $rows = @()
    $rows += Get-WindowsProcesses
    $rows += Get-WslProcesses
    $rows = Add-PortsToRows -Rows $rows

    return @($rows | Sort-Object Origin, Name, PID -Unique)
}

function Kill-ProjectProcess {
    param(
        [string]$Origin,
        [int]$ProcessId,
        [string]$FullCommand
    )

    if ($Origin -eq 'Windows') {
        try {
            Stop-Process -Id $ProcessId -Force -ErrorAction Stop
            return $true
        }
        catch {
            [System.Windows.Forms.MessageBox]::Show(
                "Failed to kill Windows process $ProcessId.`r`n$($_.Exception.Message)",
                'Kill failed',
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Error
            ) | Out-Null
            return $false
        }
    }

    if ($Origin -eq 'WSL') {
        $cmd = "kill -TERM $ProcessId 2>/dev/null || true; sleep 1; kill -0 $ProcessId 2>/dev/null && kill -KILL $ProcessId 2>/dev/null || true"
        try {
            & wsl.exe --cd $WslRepo --exec bash -lc $cmd | Out-Null
            return $true
        }
        catch {
            [System.Windows.Forms.MessageBox]::Show(
                "Failed to kill WSL process $ProcessId.`r`n$($_.Exception.Message)`r`n`r`n$FullCommand",
                'Kill failed',
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Error
            ) | Out-Null
            return $false
        }
    }

    return $false
}

function script:Refresh-Grid {
    try {
        Set-Status 'Refreshing process list...'

        $rows = @(Get-ProjectProcessRows)

        if ($null -eq $global:Grid) {
            return
        }

        $global:Grid.SuspendLayout()
        try {
            $global:Grid.Rows.Clear()

            foreach ($row in $rows) {
                $displayCmd = Safe-Trim $row.Command
                if ($displayCmd.Length -gt 180) {
                    $displayCmd = $displayCmd.Substring(0, 180) + ' ...'
                }

                $index = $global:Grid.Rows.Add(
                    'Kill',
                    $row.Origin,
                    [string]$row.PID,
                    $row.Name,
                    $row.Ports,
                    $displayCmd,
                    $row.Command,
                    $row.KillTarget
                )

                $gridRow = $global:Grid.Rows[$index]
                $gridRow.Tag = $row
            }
        }
        finally {
            $global:Grid.ResumeLayout()
        }

        Set-Status ("Found {0} project-related process(es)." -f $rows.Count)
    }
    catch {
        Set-Status "Refresh failed: $($_.Exception.Message)"
        [System.Windows.Forms.MessageBox]::Show(
            "Refresh failed.`r`n$($_.Exception.Message)",
            'Refresh failed',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    }
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'SemantiK Architect - Process Manager'
$form.Size = New-Object System.Drawing.Size(1320, 680)
$form.StartPosition = 'CenterScreen'
$form.MinimumSize = New-Object System.Drawing.Size(1100, 520)
$form.Topmost = $false

$header = New-Object System.Windows.Forms.Label
$header.AutoSize = $true
$header.Location = New-Object System.Drawing.Point(12, 12)
$header.Font = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
$header.Text = 'Project-specific process viewer and killer'
$form.Controls.Add($header)

$sub = New-Object System.Windows.Forms.Label
$sub.AutoSize = $true
$sub.Location = New-Object System.Drawing.Point(12, 38)
$sub.Text = "Windows repo: $WindowsRepo`r`nWSL repo: $WslRepo"
$form.Controls.Add($sub)

$refreshBtn = New-Object System.Windows.Forms.Button
$refreshBtn.Text = 'Refresh'
$refreshBtn.Location = New-Object System.Drawing.Point(12, 78)
$refreshBtn.Size = New-Object System.Drawing.Size(100, 32)
$form.Controls.Add($refreshBtn)

$freePortsLabel = if ($IncludeRedisPort6379) { 'Free 3000/8000/6379' } else { 'Free 3000/8000' }

$killPortsBtn = New-Object System.Windows.Forms.Button
$killPortsBtn.Text = $freePortsLabel
$killPortsBtn.Location = New-Object System.Drawing.Point(124, 78)
$killPortsBtn.Size = New-Object System.Drawing.Size(150, 32)
$form.Controls.Add($killPortsBtn)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.AutoSize = $false
$statusLabel.Location = New-Object System.Drawing.Point(290, 84)
$statusLabel.Size = New-Object System.Drawing.Size(980, 24)
$statusLabel.Text = 'Ready.'
$form.Controls.Add($statusLabel)
$global:StatusLabel = $statusLabel

$grid = New-Object System.Windows.Forms.DataGridView
$grid.Location = New-Object System.Drawing.Point(12, 120)
$grid.Size = New-Object System.Drawing.Size(1280, 500)
$grid.Anchor = 'Top,Bottom,Left,Right'
$grid.AllowUserToAddRows = $false
$grid.AllowUserToDeleteRows = $false
$grid.ReadOnly = $true
$grid.RowHeadersVisible = $false
$grid.SelectionMode = 'FullRowSelect'
$grid.MultiSelect = $false
$grid.AutoSizeRowsMode = 'AllCells'
$grid.BackgroundColor = [System.Drawing.Color]::White
$grid.DefaultCellStyle.WrapMode = [System.Windows.Forms.DataGridViewTriState]::True
$form.Controls.Add($grid)
$global:Grid = $grid
$global:Form = $form

$killColumn = New-Object System.Windows.Forms.DataGridViewButtonColumn
$killColumn.Name = 'Kill'
$killColumn.HeaderText = 'Action'
$killColumn.Text = 'Kill'
$killColumn.UseColumnTextForButtonValue = $true
$killColumn.Width = 70
$grid.Columns.Add($killColumn) | Out-Null

$originCol = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
$originCol.Name = 'Origin'
$originCol.HeaderText = 'Origin'
$originCol.Width = 80
$grid.Columns.Add($originCol) | Out-Null

$pidCol = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
$pidCol.Name = 'PID'
$pidCol.HeaderText = 'PID'
$pidCol.Width = 80
$grid.Columns.Add($pidCol) | Out-Null

$nameCol = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
$nameCol.Name = 'Name'
$nameCol.HeaderText = 'Name'
$nameCol.Width = 140
$grid.Columns.Add($nameCol) | Out-Null

$portsCol = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
$portsCol.Name = 'Ports'
$portsCol.HeaderText = 'Ports'
$portsCol.Width = 120
$grid.Columns.Add($portsCol) | Out-Null

$cmdCol = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
$cmdCol.Name = 'Command'
$cmdCol.HeaderText = 'Command'
$cmdCol.Width = 740
$grid.Columns.Add($cmdCol) | Out-Null

$fullCmdCol = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
$fullCmdCol.Name = 'FullCommand'
$fullCmdCol.HeaderText = 'FullCommand'
$fullCmdCol.Visible = $false
$grid.Columns.Add($fullCmdCol) | Out-Null

$killTargetCol = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
$killTargetCol.Name = 'KillTarget'
$killTargetCol.HeaderText = 'KillTarget'
$killTargetCol.Visible = $false
$grid.Columns.Add($killTargetCol) | Out-Null

$refreshBtn.Add_Click({
    & script:Refresh-Grid
})

$killPortsBtn.Add_Click({
    try {
        $portsToFree = @($ProjectPorts)
        if ($IncludeRedisPort6379) {
            $portsToFree += 6379
        }

        $portOwners = Get-WindowsPortOwners -Ports $portsToFree
        $killed = 0

        foreach ($port in $portsToFree) {
            foreach ($procIdText in @($portOwners[$port] | Select-Object -Unique)) {
                if (-not $procIdText) { continue }

                $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $procIdText" -ErrorAction SilentlyContinue
                if ($null -eq $proc) { continue }

                $cmd = Safe-Trim $proc.CommandLine
                $name = Safe-Trim $proc.Name
                if (-not (Test-ProjectMatch -CommandLine $cmd -ProcessName $name)) { continue }

                try {
                    Stop-Process -Id ([int]$procIdText) -Force -ErrorAction Stop
                    $killed++
                }
                catch {
                    # ignore individual kill failures here
                }
            }
        }

        & script:Refresh-Grid
        Set-Status ("Freed project-owned listeners on requested ports. Killed {0} process(es)." -f $killed)
    }
    catch {
        Set-Status "Free ports failed: $($_.Exception.Message)"
        [System.Windows.Forms.MessageBox]::Show(
            "Free ports failed.`r`n$($_.Exception.Message)",
            'Free ports failed',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    }
})

$grid.Add_CellContentClick({
    param($sender, $e)

    if ($e.RowIndex -lt 0) { return }
    if ($e.ColumnIndex -ne $global:Grid.Columns['Kill'].Index) { return }

    $row = $global:Grid.Rows[$e.RowIndex]
    $origin = [string]$row.Cells['Origin'].Value
    $procId = [int]$row.Cells['PID'].Value
    $fullCommand = [string]$row.Cells['FullCommand'].Value

    $answer = [System.Windows.Forms.MessageBox]::Show(
        "Kill $origin process PID $procId?`r`n`r`n$fullCommand",
        'Confirm kill',
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )

    if ($answer -ne [System.Windows.Forms.DialogResult]::Yes) {
        return
    }

    Set-Status ("Killing $origin process $procId ...")
    $ok = Kill-ProjectProcess -Origin $origin -ProcessId $procId -FullCommand $fullCommand
    Start-Sleep -Milliseconds 500
    & script:Refresh-Grid

    if ($ok) {
        Set-Status ("Killed $origin process $procId.")
    }
})

$form.Add_Shown({
    & script:Refresh-Grid
})

[void]$form.ShowDialog()

