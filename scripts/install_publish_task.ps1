# Planifie `clipper publish` toutes les heures (Windows, Planificateur de tâches).
# À lancer une fois depuis le dossier du projet :  powershell -ExecutionPolicy Bypass -File scripts\install_publish_task.ps1
$ErrorActionPreference = "Stop"
$project = (Resolve-Path "$PSScriptRoot\..").Path
$clipper = (Get-Command clipper -ErrorAction SilentlyContinue).Source
if (-not $clipper) { throw "Commande 'clipper' introuvable : active ton venv puis 'pip install -e .'" }

$action  = New-ScheduledTaskAction -Execute $clipper -Argument "publish" -WorkingDirectory $project
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(17) -RepetitionInterval (New-TimeSpan -Hours 1)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "Clipper - publication" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "Tâche 'Clipper - publication' créée : toutes les heures à :17, dossier $project"
