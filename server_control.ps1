# server_control.ps1

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = "Server Control"
$form.Size = New-Object System.Drawing.Size(350, 250)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$font = New-Object System.Drawing.Font("Segoe UI", 10)
$form.Font = $font

# Labels for PIDs
$djangoPidLabel = New-Object System.Windows.Forms.Label
$djangoPidLabel.Text = "Django PID: N/A"
$djangoPidLabel.Location = New-Object System.Drawing.Point(20, 20)
$djangoPidLabel.AutoSize = $true
$form.Controls.Add($djangoPidLabel)

$vitePidLabel = New-Object System.Windows.Forms.Label
$vitePidLabel.Text = "Vite PID: N/A"
$vitePidLabel.Location = New-Object System.Drawing.Point(20, 50)
$vitePidLabel.AutoSize = $true
$form.Controls.Add($vitePidLabel)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = "Status: Idle"
$statusLabel.Location = New-Object System.Drawing.Point(20, 80)
$statusLabel.AutoSize = $true
$form.Controls.Add($statusLabel)

$djangoProcess = $null
$viteProcess = $null

function Start-DjangoServer {
    $script:statusLabel.Text = "Status: Starting Django..."
    $script:statusLabel.Refresh()
    try {
        $proc = Start-Process python -ArgumentList "manage.py runserver" -NoNewWindow -PassThru -ErrorAction Stop -RedirectStandardOutput "django_output.log" -RedirectStandardError "django_error.log"
        $script:djangoProcess = $proc
        $script:djangoPidLabel.Text = "Django PID: $($proc.Id)"
        $script:djangoPidLabel.Refresh()
        $script:statusLabel.Text = "Status: Django Running (PID: $($proc.Id))"
    } catch {
        $script:statusLabel.Text = "Status: Failed to start Django: $($_.Exception.Message)"
        $script:djangoProcess = $null
    }
    $script:statusLabel.Refresh()
}

function Start-ViteServer {
    $script:statusLabel.Text = "Status: Starting Vite..."
    $script:statusLabel.Refresh()
    try {
        # Using cmd /c to ensure npm is found and handled correctly
        # Output redirected to files to prevent blocking
        $proc = Start-Process cmd -ArgumentList "/c npm run dev" -NoNewWindow -PassThru -WorkingDirectory "frontend" -ErrorAction Stop -RedirectStandardOutput "vite_output.log" -RedirectStandardError "vite_error.log"
        $script:viteProcess = $proc
        $script:vitePidLabel.Text = "Vite PID: $($proc.Id)"
        $script:vitePidLabel.Refresh()
        $script:statusLabel.Text = "Status: Vite Running (PID: $($proc.Id))"
    } catch {
        $script:statusLabel.Text = "Status: Failed to start Vite: $($_.Exception.Message)"
        $script:viteProcess = $null
    }
    $script:statusLabel.Refresh()
}

function Stop-AllServers {
    $script:statusLabel.Text = "Status: Stopping servers..."
    $script:statusLabel.Refresh()

    if ($script:djangoProcess -ne $null -and !(Get-Process -Id $script:djangoProcess.Id -ErrorAction SilentlyContinue)) {
        $script:djangoProcess = $null # Process already dead
    }
    if ($script:viteProcess -ne $null -and !(Get-Process -Id $script:viteProcess.Id -ErrorAction SilentlyContinue)) {
        $script:viteProcess = $null # Process already dead
    }

    if ($script:djangoProcess -ne $null) {
        try {
            Stop-Process -Id $script:djangoProcess.Id -Force -ErrorAction Stop
            $script:djangoPidLabel.Text = "Django PID: N/A (Stopped)"
            $script:djangoProcess = $null
        } catch {
            $script:statusLabel.Text = "Status: Error stopping Django: $($_.Exception.Message)"
        }
    }
    if ($script:viteProcess -ne $null) {
        try {
            Stop-Process -Id $script:viteProcess.Id -Force -ErrorAction Stop
            $script:vitePidLabel.Text = "Vite PID: N/A (Stopped)"
            $script:viteProcess = $null
        } catch {
            $script:statusLabel.Text = "Status: Error stopping Vite: $($_.Exception.Message)"
        }
    }
    if ($script:djangoProcess -eq $null -and $script:viteProcess -eq $null) {
        $script:statusLabel.Text = "Status: All servers stopped."
    }
    $script:djangoPidLabel.Refresh()
    $script:vitePidLabel.Refresh()
    $script:statusLabel.Refresh()
}

# Start All Button
$startAllButton = New-Object System.Windows.Forms.Button
$startAllButton.Text = "Start All Servers"
$startAllButton.Location = New-Object System.Drawing.Point(20, 120)
$startAllButton.Size = New-Object System.Drawing.Size(120, 30)
$startAllButton.Add_Click({
    Stop-AllServers # Ensure clean start
    Start-DjangoServer
    Start-ViteServer
})
$form.Controls.Add($startAllButton)

# Stop All Button
$stopAllButton = New-Object System.Windows.Forms.Button
$stopAllButton.Text = "Stop All Servers"
$stopAllButton.Location = New-Object System.Drawing.Point(150, 120)
$stopAllButton.Size = New-Object System.Drawing.Size(120, 30)
$stopAllButton.Add_Click({ Stop-AllServers })
$form.Controls.Add($stopAllButton)

# Exit Button
$exitButton = New-Object System.Windows.Forms.Button
$exitButton.Text = "Exit"
$exitButton.Location = New-Object System.Drawing.Point(20, 160)
$exitButton.Size = New-Object System.Drawing.Size(120, 30)
$exitButton.Add_Click({
    Stop-AllServers
    $form.Close()
})
$form.Controls.Add($exitButton)

$form.Add_Shown({
    # Initial check if any processes are already running on default ports
    $form.Refresh()
})

# Handle form closing to stop servers
$form.Add_FormClosing({
    Stop-AllServers
})

# Show the form
$form.ShowDialog()
