# Resend first-round assessment invites after fixing SMTP credentials.
$Base = $env:MAIN_API_URL
if (-not $Base) { $Base = "https://jatayus5-justagentic.onrender.com" }
$r = Invoke-RestMethod -Method POST -Uri "$Base/applications/resend-failed-invites" -ContentType "application/json"
$r | ConvertTo-Json -Depth 8
