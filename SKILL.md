---
name: wb-learning-client-bootstrap
description: 在 Windows 安装独立学习客户端、核验管理员签发的 43 位学习服务令牌并登记规则检查服务。仅用于管理员学习同步安装和维护；无需上架卡密或窗口 ID。
---

# 独立学习客户端安装

让用户登录实际使用的 Windows 账户，在本机独立交互终端运行 `install.cmd`，或：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<本工具目录>\scripts\install-wb-learning-client.ps1"
```

安装器准备 Python 3.10+（`install-wb-learning-client.ps1` 必须带 UTF-8 BOM 以兼容中文版 Windows PowerShell 5.1/CP936 语法解析）；管理员签发的 43 位令牌仅在终端隐藏输入。令牌不能放在聊天、命令行参数或工具输出中。当前配置保存为用户目录中的 JSON，不能称为加密存储。

根据实际输出分别报告：环境安装、令牌在线核验、规则下载状态、后台检查服务登记。
- `distribution_disabled`：令牌核验有效，云端规则下载已关闭，没有下载新规则。
- `no_release`：当前没有可下载的发布版本。
- `updated` / `up_to_date`：规则已更新 / 已是当前发布版本。
- 核验、网络或格式错误：报告未完成，不把错误或任意 HTTP 400 当作有效授权。

云端当前关闭客户规则下载。服务每 15 分钟的调度配置不代表实际运行或即时远程控制。状态见 `.codex/wb-skill-learning/sync-status.json`；提示重启 Antigravity 后在本机核对实际执行。

只维护本工具的令牌、同步服务与受管规则区块，保留其他全局内容。规则只用于允许公开的操作提醒；本地规则可以读取，不能承担核心算法保密或上架授权职责。

本工具不要求上架卡密、会话 ID 或店铺绑定。上架请求转由独立的上架助手处理；本工具安装失败不改变上架授权。不得宣称设备令牌已具备硬件锁、自动分账或完整防复刻能力。
