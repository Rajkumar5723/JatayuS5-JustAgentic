# Deploy Hiresy frontend + backend services on Render via API.
# Usage:
#   $env:RENDER_API_KEY = "rnd_..."
#   powershell -File scripts/render-deploy.ps1
# Optional:
#   -ValidateOnly
#   -SkipFrontendCreate

param(
    [string]$ApiKey = $env:RENDER_API_KEY,
    [string]$OwnerId = "tea-d1nou1k9c44c73ejn8fg",
    [string]$Repo = "https://github.com/Rajkumar5723/JatayuS5-JustAgentic",
    [string]$Branch = "main",
    [string]$MainApiServiceId = "srv-d86qp7n7f7vs73f1r6jg",
    [switch]$ValidateOnly,
    [switch]$SkipFrontendCreate
)

$ErrorActionPreference = "Stop"
$BaseUrl = "https://api.render.com/v1"
$Headers = @{
    Authorization = "Bearer $ApiKey"
    Accept        = "application/json"
}

if (-not $ApiKey) {
    throw "Set RENDER_API_KEY (Render Dashboard > Account Settings > API Keys)."
}

function Invoke-RenderApi {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $uri = "$BaseUrl$Path"
    $params = @{
        Method  = $Method
        Uri     = $uri
        Headers = $Headers
    }

    if ($null -ne $Body) {
        $params["Body"] = ($Body | ConvertTo-Json -Depth 20)
        $params["ContentType"] = "application/json"
    }

    return Invoke-RestMethod @params
}

function Test-RenderBlueprint {
    param([string]$YamlPath)

    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if (-not $curl) {
        Write-Warning "curl.exe not found; skipping blueprint validation."
        return
    }

    & curl.exe -sS -f `
        -H "Authorization: Bearer $ApiKey" `
        -F "ownerId=$OwnerId" `
        -F "file=@$YamlPath" `
        "$BaseUrl/blueprints/validate" | Out-Null
}

function Get-ServiceByName {
    param([string]$Name)

    $cursor = $null
    do {
        $query = "ownerId=$OwnerId&limit=100"
        if ($cursor) { $query += "&cursor=$cursor" }
        $page = Invoke-RenderApi -Method GET -Path "/services?$query"
        foreach ($entry in @($page)) {
            if ($entry.service.name -eq $Name) {
                return $entry.service
            }
        }
        $cursor = $page[-1].cursor
    } while ($cursor)
    return $null
}

function Start-Deploy {
    param([string]$ServiceId)
    Invoke-RenderApi -Method POST -Path "/services/$ServiceId/deploys" -Body @{ clearCache = "do_not_clear" } | Out-Null
}

Write-Host "Validating render.yaml..."
$renderYaml = Join-Path $PSScriptRoot "..\render.yaml"
if (-not (Test-Path $renderYaml)) {
    throw "Missing render.yaml at $renderYaml"
}

Test-RenderBlueprint -YamlPath $renderYaml
Write-Host "Blueprint validation OK."

if ($ValidateOnly) {
    exit 0
}

Write-Host "Updating main API service ($MainApiServiceId)..."
$mainApiPatch = @{
    name           = "hiresy-main-api"
    rootDir        = "Backend"
    serviceDetails = @{
        env                  = "docker"
        healthCheckPath      = "/health"
        envSpecificDetails   = @{
            dockerfilePath = "./Dockerfile"
            dockerContext  = "."
            dockerCommand  = ""
        }
    }
}
Invoke-RenderApi -Method PATCH -Path "/services/$MainApiServiceId" -Body $mainApiPatch | Out-Null
Start-Deploy -ServiceId $MainApiServiceId
Write-Host "Triggered deploy for hiresy-main-api."

if (-not $SkipFrontendCreate) {
    $existingFrontend = Get-ServiceByName -Name "hiresy-frontend"
    if ($existingFrontend) {
        Write-Host "Frontend service already exists: $($existingFrontend.id)"
        Start-Deploy -ServiceId $existingFrontend.id
    }
    else {
        Write-Host "Creating static frontend service..."
        $frontendCreate = @{
            type    = "static_site"
            name    = "hiresy-frontend"
            ownerId = $OwnerId
            repo    = $Repo
            branch  = $Branch
            rootDir = "Frontend"
            serviceDetails = @{
                buildCommand    = "npm ci && npm run build"
                publishPath     = "dist"
                pullRequestPreviewsEnabled = "no"
            }
        }
        $created = Invoke-RenderApi -Method POST -Path "/services" -Body $frontendCreate
        $frontendId = $created.service.id
        Write-Host "Created hiresy-frontend ($frontendId)."

        $routes = @(
            @{
                type        = "rewrite"
                source      = "/*"
                destination = "/index.html"
            }
        )
        foreach ($route in $routes) {
            Invoke-RenderApi -Method POST -Path "/services/$frontendId/routes" -Body $route | Out-Null
        }

        Start-Deploy -ServiceId $frontendId
        Write-Host "Triggered deploy for hiresy-frontend."
        Write-Host "After main-api URL is live, set frontend env vars in Render:"
        Write-Host "  VITE_MAIN_API_BASE, VITE_TEST_API_BASE, VITE_CODING_API_BASE, VITE_LIVEHR_API_BASE"
        Write-Host "  VITE_LIVEHR_WS_BASE=wss://<live-hr-host>/livehr/ws"
    }
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Push render.yaml to GitHub and create a Blueprint in Render (recommended for all 6 services)."
Write-Host "2. Add secrets from .env.example to the hiresy-backend-shared env group in Render."
Write-Host "3. Set LI_REDIRECT_URI to https://<main-api-host>/linkedin/callback"
Write-Host "4. Run: python Backend/seed_hr_user.py (Render shell) after first deploy."
