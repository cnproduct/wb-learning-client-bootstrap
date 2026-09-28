---
name: wb-learning-client-bootstrap
description: 在 Windows 安装独立学习客户端、核验管理员签发的 43 位学习服务令牌并登记当前用户的 Windows 规则检查计划任务。仅用于管理员学习同步安装和维护；无需上架卡密或窗口 ID。
---

# 独立学习客户端安装

让用户登录实际使用的 Windows 账户，在本机独立交互终端运行 `install.cmd`，或：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<本工具目录>\scripts\install-wb-learning-client.ps1"
```

安装器准备 Python 3.10+（`install-wb-learning-client.ps1` 必须带 UTF-8 BOM 以兼容中文版 Windows PowerShell 5.1/CP936 语法解析）；管理员签发的 43 位令牌仅在终端隐藏输入。令牌不能放在聊天、命令行参数或工具输出中。当前配置保存为用户目录中的 JSON，不能称为加密存储。

根据实际输出分别报告：环境安装、令牌在线核验、规则下载状态、Windows 计划任务登记与实际运行。
- `distribution_disabled`：令牌核验有效，云端规则下载已关闭，没有下载新规则。
- `no_release`：当前没有可下载的发布版本。
- `updated` / `up_to_date`：规则已更新 / 已是当前发布版本。
- 核验、网络或格式错误：报告未完成，不把错误或任意 HTTP 400 当作有效授权。

规则检查使用 Windows 计划任务，每 15 分钟执行后退出；仅实际安装账户登录期间运行，不依赖 Antigravity 常驻。任务名为 `WBSkill_RulesSync_<当前账户SID>`；重复安装覆盖同名任务，禁止并发实例，单次最多 5 分钟。登记不代表执行成功；核对任务最近执行结果和 `.codex/wb-skill-learning/sync-status.json` 的 `checked_at`、`status`。云端是否开放下载以本次响应为准。

旧版迁移会备份并停用 `wb-skill-rules-sync` Sidecar；如果发现已知每日 06:00 的 `wb-skill-auto-update`，保留原更新脚本和时间，迁移为最长 10 分钟的当前用户任务。任务登记成功后才停用对应 Sidecar；不识别或缺失的旧更新命令必须报错，不能猜测或静默丢弃。备份在 `.codex/wb-skill-learning/scheduler-backups/`。迁移后请用户保存工作并注销 Windows 再登录，清退旧会话进程。不要重建 `builtin: schedule` / `restart_policy: always` 调度器。

仅修复调度且已有配置时，可在实际用户终端运行 `python -X utf8 scripts/install_learning_rule_sync.py`，无需重新签发令牌；此操作不核验令牌或下载规则。若用户已手工创建旧计划任务（例如 `WBSkill_RulesSync_User1`），按 README 的复核步骤处理，不可删除其他用户任务。

低内存/RDP 崩溃记录不能直接证明所有崩溃都来自本 Skill。不要批量结束语言服务或 conhost、清除崩溃证据、设置系统全局 GOMEMLIMIT，或默认添加 GPU 禁用参数。先保留日志并区分调度、内存和渲染问题。

只维护本工具的令牌、同步服务与受管规则区块，保留其他全局内容。规则只用于允许公开的操作提醒；本地规则可以读取，不能承担核心算法保密或上架授权职责。

本工具不要求上架卡密、会话 ID 或店铺绑定。上架请求转由独立的上架助手处理；本工具安装失败不改变上架授权。不得宣称设备令牌已具备硬件锁、自动分账或完整防复刻能力。
