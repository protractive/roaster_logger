Write-Host "Building RoasterLogger (onefile)..."

$argsList = @("--noconsole", "--onefile", "--name", "RoasterLogger")
if (Test-Path "icon.ico") {
    $argsList += @("--icon", "icon.ico")
} else {
    Write-Host "Warning: icon.ico not found; building without custom icon."
}
$argsList += @("--add-data", "config;config", "--add-data", "data;data", "ui/desktop/app.py")

python -m PyInstaller @argsList

Write-Host "Build finished. Output is under dist\RoasterLogger"
