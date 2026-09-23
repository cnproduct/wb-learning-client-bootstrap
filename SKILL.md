---
name: wb-learning-client-bootstrap
description: 在新 Windows 电脑安装管理员签发的 WB 规则学习客户端与 Antigravity 后台自动同步服务。适用于缺少 Python 或未配置设备令牌的新设备；运行随附 PowerShell 安装器并由用户在本机隐藏粘贴管理员签发的 43 位设备令牌。
---

# WB 规则学习客户端 Windows 一键安装与同步

当用户要求在 Windows 上安装或配置 WB 规则学习同步客户端时，运行同目录的 [安装器](scripts/install-wb-learning-client.ps1)。

本安装器专职负责 64 位 Windows 下的基础环境就绪与规则同步服务注入：
1. 自动检测并安装缺失的 Python 3.10+ 环境；
2. 交互式接收管理员签发的 **43 位设备令牌**（保存在 `%USERPROFILE%\.codex\wb-skill-learning\hub-config.json`）；
3. 执行规则在线验证，拉取管理员最新发布的签名规则并注入全局 `GEMINI.md`；
4. 注册 Antigravity 后台 `wb-skill-rules-sync` Sidecar 服务，实现后台每 15 分钟静默拉取最新规则。

### 执行方式
在新电脑上双击文件夹中的 `install.cmd`，或在 Windows PowerShell 中执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<本 Skill 目录>\scripts\install-wb-learning-client.ps1"
```

### 独立性与业务边界说明
- **彻底独立于上架业务**：本安装器**仅负责学习规则同步与底座环境**，完全独立于 WB 上架业务。
- **无需上架卡密**：本工具绝不要求输入上架卡密、不绑定 WB 店铺、不要求提供会话/窗口 ID (CID)，也不执行商品搬家上架。
- **业务操作解耦**：若需开展 Wildberries 商品上架业务，请使用独立的 `ozon-to-wb-fast-listing` 技能。
- **安全输入**：设备令牌严格为 43 位（`^[A-Za-z0-9_-]{43}$`），由用户在 PowerShell 隐藏输入提示处粘贴，输入时不显示字符。不要发到聊天窗口，不要放在命令行参数中。
