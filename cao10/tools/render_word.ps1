param([Parameter(Mandatory=$true)][string]$InputDocx,[Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference='Stop'
$inputPath=(Resolve-Path -LiteralPath $InputDocx).Path
$outputPath=[IO.Path]::GetFullPath($OutputPdf)
New-Item -ItemType Directory -Force ([IO.Path]::GetDirectoryName($outputPath)) | Out-Null
$word=$null
$document=$null
try {
    $word=New-Object -ComObject Word.Application
    $word.Visible=$false
    $word.DisplayAlerts=0
    $document=$word.Documents.Open($inputPath,$false,$true)
    $document.ExportAsFixedFormat($outputPath,17)
    Write-Output "Rendered $($document.ComputeStatistics(2)) pages to $outputPath"
} finally {
    if ($document) { $document.Close(0) }
    if ($word) { $word.Quit() }
}
