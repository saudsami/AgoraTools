Set-Location output-indexed

$exclude = @("images","voice-calling","broadcast-streaming","interactive-live-streaming")

Get-ChildItem -Directory | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
    Compress-Archive -Path $_.FullName -DestinationPath "$($_.Name).zip" -Force
}
