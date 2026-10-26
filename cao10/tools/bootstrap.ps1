$ErrorActionPreference='Stop'
$vendor=Join-Path $PSScriptRoot 'vendor'
New-Item -ItemType Directory -Force $vendor | Out-Null
$downloads=@(
    @('https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/win64/nasm-2.16.03-win64.zip','nasm.zip','3ee4782247bcb874378d02f7eab4e294a84d3d15f3f6ee2de2f47a46aa7226e6'),
    @('https://github.com/skeeto/w64devkit/releases/download/v2.5.0/w64devkit-x64-2.5.0.7z.exe','w64devkit.exe','7ac8f55befb93720f048f2c788704543fbc632c0164a8239ecbdefc9559481c5')
)
foreach ($item in $downloads) {
    $path=Join-Path $vendor $item[1]
    if (!(Test-Path -LiteralPath $path)) { Invoke-WebRequest -UseBasicParsing $item[0] -OutFile $path }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item[2]) { throw "Checksum mismatch: $path" }
}
Expand-Archive (Join-Path $vendor 'nasm.zip') $vendor -Force
& (Join-Path $vendor 'w64devkit.exe') -y "-o$vendor"
if ($LASTEXITCODE -ne 0) { throw 'Toolchain extraction failed' }
Write-Output 'NASM 2.16.03 and w64devkit 2.5.0 ready. Run build.bat.'
