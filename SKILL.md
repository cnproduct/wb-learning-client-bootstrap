---
name: wb-learning-client-bootstrap
description: 安装或更新 WB 上架与学习同步客户端，展示 PowerShell 安装指引，分别隐藏输入管理员学习设备码与代理商上架卡密。
---

客户要求安装、更新或激活时，展示下面代码，由用户复制到本机独立 PowerShell 窗口运行。
不要在 AI 捕获输出的终端代填凭据；不要求用户下载完整 WB 仓库。

```powershell
$installer = Join-Path $env:TEMP 'wb-setup.ps1'
Invoke-WebRequest -UseBasicParsing -Uri 'https://wb-private-executor.cnproduct.workers.dev/client/install.ps1' -OutFile $installer
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer
Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
```

安装器自动准备 Python 并安装上架与学习同步客户端。学习设备码由管理员单独签发，
在隐藏输入提示中粘贴。上架卡密由代理商或管理员在 https://diytale.com/agent 按当前窗口 ID 签发；
当前平台还要求 SID，安装器会显示，两者一并交给代理商。上架卡密在另一个隐藏提示中输入。
没有码可回车跳过，安装完成不能宣称授权完成。自助免费试用已关闭。
安装后重启 Antigravity，新建准备上架的对话，使用该窗口的真实 ID 单独激活。
已有准备好的新窗口可在安装器提示时输入其真实 ID；不得生成或猜测会话 ID。

只汇报安装、学习同步、窗口授权的各自结果。学习设备码、上架卡密、WB 店铺令牌不能互换，
不能放到聊天、命令参数或日志中。不要把令牌单独粘贴在 PS 提示符后。
安装器不会签发凭据，不会开通免费试用。无关问题只回复：
我仅能协助处理当前店铺上架相关业务，请聚焦上架问题咨询。
