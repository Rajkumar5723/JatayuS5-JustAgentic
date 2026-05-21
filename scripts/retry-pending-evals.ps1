# Queue AI evaluation for every application missing eval_score.
$Base = $env:MAIN_API_URL
if (-not $Base) { $Base = "https://jatayus5-justagentic.onrender.com" }
$r = Invoke-RestMethod -Method POST -Uri "$Base/applications/retry-pending-eval" -ContentType "application/json"
$r | ConvertTo-Json
