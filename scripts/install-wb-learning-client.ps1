#requires -Version 5.1
<#
Run from Windows PowerShell:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-wb-learning-client.ps1
The device token is requested interactively and is never accepted as a command-line argument.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$learningDirectory = Join-Path $HOME '.codex\wb-skill-learning'
$configPath = Join-Path $learningDirectory 'hub-config.json'
$endpoint = 'https://wb-skill-learning-hub.cnproduct.workers.dev'
$scriptsRoot = $PSScriptRoot

function Step([string]$message) { Write-Host "[WB 学习客户端安装] $message" }
function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user;$env:Path"
}
function Find-Executable([string]$name, [string[]]$locations) {
    $commands = Get-Command $name -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notlike '*\WindowsApps\*' }
    if ($commands) {
        $first = $commands | Select-Object -First 1
        if ($first -and $first.Source) { return $first.Source }
    }
    foreach ($location in $locations) {
        if ($location -and (Test-Path -LiteralPath $location -PathType Leaf)) { return $location }
    }
    return $null
}
function Download-VerifiedInstaller([string]$url, [string]$file) {
    Step "下载官方安装包：$([IO.Path]::GetFileName($file))"
    Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing
    $signature = Get-AuthenticodeSignature -LiteralPath $file
    if ($signature.Status -ne 'Valid') { throw "安装包签名无效：$($signature.Status)" }
}
function Run-Installer([string]$file, [string[]]$arguments) {
    $process = Start-Process -FilePath $file -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) { throw "安装程序失败，退出码 $($process.ExitCode)" }
    Refresh-Path
}
function Get-Python {
    $candidates = @(
        (Find-Executable 'python.exe' @()),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:ProgramFiles 'Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:ProgramFiles 'Python312\python.exe')
    ) | Where-Object { $_ }
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            $version = & $candidate -c 'import sys; print(int(sys.version_info >= (3, 10)))' 2>$null
            if ($LASTEXITCODE -eq 0 -and $version -eq '1') { return $candidate }
        } catch { continue }
    }
    return $null
}
function Save-DeviceToken {
    param([switch]$Force)
    if (-not $Force -and (Test-Path -LiteralPath $configPath -PathType Leaf)) {
        try {
            $existing = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($existing.endpoint -eq $endpoint -and $existing.ingest_token -cmatch '^[A-Za-z0-9_-]{43}$') {
                Step '检测到当前用户已有设备令牌配置。'
                return
            }
        } catch { }
    }
    New-Item -ItemType Directory -Path $learningDirectory -Force | Out-Null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $secure = Read-Host '请粘贴管理员签发的 43 位设备令牌（输入不会显示）' -AsSecureString
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try {
            $rawToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
            $token = if ($rawToken) { "$rawToken".Trim() } else { '' }
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        }
        try {
            if ($token -cnotmatch '^[A-Za-z0-9_-]{43}$') {
                Write-Warning "格式无效（第 $attempt/3 次）。令牌应为严格 43 位英文字母/数字/下划线/减号。请只复制令牌文本，勿复制前后标签或 PS 提示符。"
                continue
            }
            $payload = @{ endpoint = $endpoint; ingest_token = $token } | ConvertTo-Json
            $temporary = Join-Path $learningDirectory ([IO.Path]::GetRandomFileName())
            try {
                [IO.File]::WriteAllText($temporary, $payload, [Text.UTF8Encoding]::new($false))
                Move-Item -LiteralPath $temporary -Destination $configPath -Force
            } finally {
                if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
            }
            try {
                $clip = Get-Clipboard -Raw -ErrorAction SilentlyContinue
                if ($clip -and "$clip".Trim() -ceq $token) { Set-Clipboard -Value ' ' }
            } catch { }
            Step '设备令牌已保存至当前用户配置，请勿分享该配置文件。'
            return
        } finally {
            $token = $null
            $secure = $null
        }
    }
    throw '三次输入均无效；请重新运行安装器。'
}
function Sync-SkillDirectory {
    $currentRoot = [IO.Path]::GetFullPath((Join-Path $scriptsRoot '..'))
    $targetRoot = [IO.Path]::GetFullPath((Join-Path $HOME '.gemini\config\skills\wb-learning-client-bootstrap'))
    if ($currentRoot -ne $targetRoot) {
        Step '正在同步学习客户端至 Antigravity 全局技能目录...'
        New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
        foreach ($file in @('SKILL.md', 'README.md', 'install.cmd')) {
            $src = Join-Path $currentRoot $file
            if (Test-Path -LiteralPath $src -PathType Leaf) {
                Copy-Item -LiteralPath $src -Destination (Join-Path $targetRoot $file) -Force
            }
        }
        $targetScripts = Join-Path $targetRoot 'scripts'
        New-Item -ItemType Directory -Path $targetScripts -Force | Out-Null
        Get-ChildItem -LiteralPath $scriptsRoot -File | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $targetScripts -Force
        }
        Step '已就绪：Antigravity 可自动识别并调用 wb-learning-client-bootstrap 技能。'
    }
}

try {
    if ($env:OS -ne 'Windows_NT' -or -not [Environment]::Is64BitOperatingSystem) { throw '需要 64 位 Windows。' }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Refresh-Path

    $python = Get-Python
    if (-not $python) {
        $setup = Join-Path $env:TEMP 'python-3.13.15-amd64.exe'
        Download-VerifiedInstaller 'https://www.python.org/ftp/python/3.13.15/python-3.13.15-amd64.exe' $setup
        Run-Installer $setup @('/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_launcher=1', 'InstallLauncherAllUsers=0', 'Include_test=0')
        $python = Get-Python
        if (-not $python) { throw 'Python 安装后仍无法找到 Python 3.10+。' }
    }
    Step "Python 环境就绪：$(& $python --version)"

    $syncScript = Join-Path $scriptsRoot 'sync_learning_rules.py'
    $installScript = Join-Path $scriptsRoot 'install_learning_rule_sync.py'
    foreach ($script in @($syncScript, $installScript)) {
        if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
            throw "缺少必需脚本：$([IO.Path]::GetFileName($script))"
        }
    }

    Save-DeviceToken
    $env:PYTHONUTF8 = '1'
    Step '验证设备令牌并同步管理员已发布规则...'
    & $python -X utf8 $syncScript
    if ($LASTEXITCODE -ne 0) {
        Write-Warning '首次同步验证失败。请重新粘贴设备令牌；若再次失败，请检查网络或联系管理员。'
        Save-DeviceToken -Force
        & $python -X utf8 $syncScript
        if ($LASTEXITCODE -ne 0) { throw '设备令牌验证或规则同步失败；请核对令牌与网络连接。' }
    }

    Sync-SkillDirectory
    Step '登记当前 Windows 用户的规则同步计划任务，并迁移旧 WB 调度器...'
    & $python -X utf8 $installScript
    if ($LASTEXITCODE -ne 0) { throw 'Windows 计划任务登记或旧调度器迁移未完成，请检查上方错误。' }

    Step '安装成功！'
    Step '规则检查计划任务已登记（每 15 分钟，仅当前用户登录期间运行，无需保持 Antigravity 打开）。'
    Step '旧用户请保存工作、退出 Antigravity，并注销 Windows 后重新登录一次，释放旧会话进程。'
    Step '请在任务计划程序核对执行结果，并检查 sync-status.json 的 checked_at；登记不等于运行成功。'
} catch {
    Write-Error "WB 学习客户端安装未完成：$($_.Exception.Message)"
    exit 1
}
