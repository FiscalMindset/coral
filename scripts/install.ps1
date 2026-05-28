param(
    [string]$Repo = $(if ($env:CORAL_REPO) { $env:CORAL_REPO } else { "withcoral/coral" }),
    [string]$InstallDir = $(if ($env:CORAL_INSTALL_DIR) { $env:CORAL_INSTALL_DIR } else { Join-Path $HOME ".local\bin" }),
    [string]$Version = $env:CORAL_VERSION,
    [switch]$NoModifyPath
)

$ErrorActionPreference = "Stop"

function Get-LatestVersion {
    param([string]$Repository)

    $headers = @{
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent" = "withcoral-install"
    }

    $token = if ($env:GITHUB_TOKEN) { $env:GITHUB_TOKEN } else { $env:GH_TOKEN }
    if ($token) {
        $headers.Authorization = "Bearer $token"
    }

    $release = Invoke-RestMethod `
        -Uri "https://api.github.com/repos/$Repository/releases/latest" `
        -Headers $headers

    return $release.tag_name
}

function Save-ReleaseAsset {
    param(
        [string]$Url,
        [string]$OutputPath
    )

    Invoke-WebRequest `
        -Uri $Url `
        -OutFile $OutputPath `
        -Headers @{ "User-Agent" = "withcoral-install" }
}

function Add-UserPath {
    param([string]$PathToAdd)

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $entries = @()
    if ($userPath) {
        $entries = $userPath -split ";" | Where-Object { $_ }
    }

    if ($entries -notcontains $PathToAdd) {
        $nextPath = if ($userPath) { "$userPath;$PathToAdd" } else { $PathToAdd }
        [Environment]::SetEnvironmentVariable("Path", $nextPath, "User")
    }

    $processEntries = $env:Path -split ";" | Where-Object { $_ }
    if ($processEntries -notcontains $PathToAdd) {
        $env:Path = "$PathToAdd;$env:Path"
    }
}

function Test-X64Windows {
    $isWindows = $PSVersionTable.Platform -eq "Win32NT" -or $env:OS -eq "Windows_NT"
    if (-not $isWindows) {
        throw "This installer is for native Windows. Use install.sh on macOS/Linux."
    }

    if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne [System.Runtime.InteropServices.Architecture]::X64) {
        throw "Coral currently publishes Windows x86_64 artifacts only."
    }
}

Test-X64Windows

$target = "x86_64-pc-windows-msvc"
if (-not $Version) {
    $Version = Get-LatestVersion -Repository $Repo
}

if (-not $Version) {
    throw "Could not determine a Coral release version. Set CORAL_VERSION explicitly."
}

$archive = "coral-$target.zip"
$baseUrl = "https://github.com/$Repo/releases/download/$Version"
$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("coral-install-" + [System.Guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

try {
    Write-Host "Installing Coral $Version for $target..."

    $archivePath = Join-Path $tmpDir $archive
    $checksumsPath = Join-Path $tmpDir "checksums.sha256"

    Save-ReleaseAsset -Url "$baseUrl/$archive" -OutputPath $archivePath
    Save-ReleaseAsset -Url "$baseUrl/checksums.sha256" -OutputPath $checksumsPath

    $checksumLine = Get-Content $checksumsPath | Where-Object { $_ -match [regex]::Escape($archive) } | Select-Object -First 1
    if (-not $checksumLine) {
        throw "Checksum entry for $archive not found."
    }

    $expectedHash = ($checksumLine -split "\s+")[0].ToLowerInvariant()
    $actualHash = (Get-FileHash -Algorithm SHA256 -Path $archivePath).Hash.ToLowerInvariant()
    if ($actualHash -ne $expectedHash) {
        throw "Checksum verification failed for $archive."
    }

    Expand-Archive -Path $archivePath -DestinationPath $tmpDir -Force

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Copy-Item -Path (Join-Path $tmpDir "coral.exe") -Destination (Join-Path $InstallDir "coral.exe") -Force

    if (-not $NoModifyPath) {
        Add-UserPath -PathToAdd $InstallDir
    }

    Write-Host ""
    Write-Host "Installed Coral to $(Join-Path $InstallDir "coral.exe")"
    if ($NoModifyPath) {
        Write-Host ""
        Write-Host "Add $InstallDir to your PATH."
    }
    Write-Host ""
    Write-Host "Verify:"
    Write-Host "  coral --help"
    Write-Host "Next:"
    Write-Host "  coral onboard"
    Write-Host ""
    Write-Host "To upgrade a direct install, re-run this script."
} finally {
    Remove-Item -Path $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
}
