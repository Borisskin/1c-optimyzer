$paths = @(
    'C:\Program Files\1cv8\conf'
    'C:\Program Files (x86)\1cv8\conf'
    'C:\BUFFER'
    'D:\1C-Optimyzer\research'
    "$env:APPDATA\1C"
    "$env:LOCALAPPDATA\1C"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        $files = Get-ChildItem $p -Recurse -Filter 'logcfg.xml' -ErrorAction SilentlyContinue
        foreach ($f in $files) {
            Write-Host "$($f.FullName)  ($([math]::Round($f.Length/1KB,2)) KB)"
        }
    }
}
