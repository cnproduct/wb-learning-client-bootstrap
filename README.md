# WB 上架与学习同步统一安装

已并入 WB Fast Listing 云端客户端。主安装入口和本仓库使用同一个安装器。
安装器自动准备缺失的 Python，交付 4 个允许分发的客户端文件，包含学习同步工具。
不再安装 Git、克隆完整业务仓库或恢复旧更新 sidecar。

## Windows 安装

先安装 Antigravity，在独立 PowerShell 中运行：

```powershell
$installer = Join-Path $env:TEMP 'wb-setup.ps1'
Invoke-WebRequest -UseBasicParsing -Uri 'https://wb-private-executor.cnproduct.workers.dev/client/install.ps1' -OutFile $installer
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer
Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
```

也可下载本仓库 ZIP、解压后双击 `install.cmd`。不要复制 PS 提示符或执行输出。

1. 安装器显示真实 Windows 用户 SID。
2. 管理员在学习管理后台单独签发 43 位学习设备码；用户在第一个隐藏提示输入。在线验证通过后保存并同步已发布规则；没有规则时明确提示。
3. 在 Antigravity 新建准备上架的窗口，取得真实窗口 ID。代理商或管理员从 [代理商平台](https://diytale.com/agent) 按窗口 ID 签发上架卡密；当前后台同时要求 SID。
4. 用户输入该窗口 ID，并在第二个隐藏提示输入其独立上架卡密。只有服务器确认有效才显示授权成功。

管理员与代理商在各自后台生成凭据，客户端不生成。未拿到码可回车跳过，稍后重新运行安装器。
学习设备码、上架卡密和 WB 店铺令牌不能互换。自助免费试用（包括 1 天、2 天）均不提供。
凭据只在 PowerShell 隐藏输入，不发到 Antigravity 对话，不写命令参数。

## 更新与后续同步

安装完成后重启 Antigravity；旧窗口可能保留旧内容。每个新上架窗口独立激活。
安装时会停用已知旧 WB 更新入口、备份旧安装和旧 WB 发布规则块，保留其他项目文件。
学习规则在输入有效设备码时同步；后续可在对话中请求“同步学习规则”。不会自动上传原始对话。
本次不安装定时后台服务；上架客户端在线检查会提示新版本。

`skill-update-status.json` 的 `status: ok` 仅表示安装完成，不能当作授权或学习同步通过。
静默更新可使用 `-SkipSetup`，凭据不会变更，也不会代替当前窗口授权检查。
