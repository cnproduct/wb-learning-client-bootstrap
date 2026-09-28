# 独立学习客户端

管理员为指定 Windows 用户安装学习服务访问与规则检查工具。它独立于上架助手，安装时无需上架卡密、店铺令牌或窗口 ID；普通上架客户不必安装本工具。

## 安装

1. 登录实际使用的 Windows 账户，下载本仓库 ZIP 并解压。
2. 在本机独立终端双击 `install.cmd`，按提示隐藏输入管理员签发的 43 位学习服务令牌。
3. 读取在线检查结果；安装器登记每 15 分钟运行的 `WBSkill_RulesSync_<当前账户SID>` Windows 计划任务。
4. 旧版迁移后保存工作，退出 Antigravity 并注销 Windows 后重新登录一次；这会释放旧会话的遗留进程。新任务不需要 Antigravity 运行。
5. 在 Windows「任务计划程序」中运行规则同步任务，核对最近运行结果为 `0`，并检查 `.codex/wb-skill-learning/sync-status.json` 的 `checked_at` 是否更新。登记成功不等于实际运行成功。

## 当前能力与状态

- 自动检测 Python 3.10+，缺少时准备官方安装包。
- 令牌保存在当前用户的 `.codex/wb-skill-learning/hub-config.json`，当前为 JSON 配置；隐藏输入不等于加密存储。
- 令牌访问能力来自学习服务的有效/撤销状态；本客户端没有实现硬件 SID 绑定，不提供上架商业授权。
- 当云端 `/api/rules/latest` 关闭客户规则分发、返回 410 时，会显示“设备令牌有效；云端已关闭客户端规则下载”，安装成功不等于已收到规则，更不代表防复刻已验收。
- 状态文件 `.codex/wb-skill-learning/sync-status.json` 区分 `distribution_disabled`、`no_release`、`updated`、`up_to_date`。
- 如果服务以后提供允许分发的规则包，客户端验证 HMAC 并更新自身管理的全局规则区块。HMAC 校验不隐藏规则，已写入本机的内容可被本机用户读取。

仅分发可向客户公开的操作提醒；核心解析、映射、定价、写入实现及机密策略留在私有执行服务。学习令牌不作为“100% 防复刻”、毫秒撤销、完整设备台账、自动分账或司法级审计证明。

## 共存约定

本工具不安装上架助手，也不修改商业卡密或店铺配置。兼容迁移只改变已有每日更新脚本的调度方式，不下载或替换该脚本。上架助手的安装和更新应保留本工具、学习配置和同步服务；上架版本状态使用独立的 `.codex/wb-cloud-client` 目录。

学习服务撤销只影响学习访问，上架卡密的有效期和撤销由独立商业授权服务管理。两个系统不以彼此的凭据作为前置条件。

## 旧版迁移与低内存 Windows

- 在真正使用 Skill 的账户内运行，不要在 `Administrator` 下代装 `user1`。任务绑定当前账户 SID，使用普通权限和交互登录，不保存 Windows 密码；用户注销期间不运行，保持登录但关闭 Antigravity 时仍可执行。
- 不再安装 Antigravity 常驻 schedule Sidecar。任务使用 `IgnoreNew` 防止重复实例；规则检查限时 5 分钟，兼容的每日更新限时 10 分钟。未到执行时间不会常驻一个 Python/Go 调度进程。
- 同步脚本存放在稳定的 `.codex/wb-skill-learning/` 路径；删除下载 ZIP 或安装源目录不会影响规则任务。全局 Skill 脚本复制同时修复了 PowerShell `-LiteralPath` 不展开通配符的问题。
- 旧 `sidecar.json` 和 Antigravity 配置备份到 `.codex/wb-skill-learning/scheduler-backups/<时间>/`；原更新脚本保留。每个替代任务注册成功后，才禁用对应配置并移除旧 `sidecar.json`。中途失败会明确报错；修复原因后重跑即可，已经迁移的任务仍使用同名覆盖。
- 只迁移已知每日 06:00、直接执行 `update_skill_from_git.py` 的旧自动更新配置。自定义命令、其他时间或文件缺失会停止迁移，保留原配置供检查。新用户不会凭空安装每日上架 Skill 更新任务。
- 如果已按人工修复方案创建 `WBSkill_AutoUpdate_User1` / `WBSkill_RulesSync_User1` 等任务，新安装器不会擅自删除这些自定义任务。确认新 SID 任务成功运行后，在任务计划程序核对旧任务的账户、脚本和时间；只禁用确认重复的旧任务，避免两套任务重叠运行。

已有配置、只需修复调度时，在本仓库目录运行：

```powershell
python -X utf8 scripts/install_learning_rule_sync.py
```

此入口不重新请求令牌，也不做在线鉴权。完整安装仍使用 `install.cmd`。

任务设置依据 [Microsoft Task Scheduler 文档](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-multipleinstances)。若注册被组织策略拒绝，安装器报错，不回退为常驻 Sidecar；请检查实际用户的任务创建权限。

本次变更针对可复现的调度风险，不等于已验收客户 VPS 的所有崩溃。不会批量杀进程、删除诊断日志、修改快捷方式、设置全局 Go 内存参数或默认关闭 GPU。需要进一步排查时保留原始崩溃日志、Windows 事件、任务最近运行结果和同步状态，不分享令牌配置。

## 校验与兼容性

- 运行 `python tests/check_scheduler.py` 验证重复安装、用户隔离、任务限时、迁移失败保留配置及备份；Windows 下加 `--windows-task` 会创建并执行一个临时测试任务，完成后删除。GitHub Actions 同时运行真实 Windows 任务和 PowerShell 5.1 语法检查。
- 运行 `python tests/check_sync.py` 验证令牌校验失败关闭、410 状态、签名校验、受管区块更新以及 PowerShell 脚本 UTF-8 BOM 签名。
- **Windows PowerShell 5.1 编码兼容**：中文版 Windows（默认代码页 CP936 / GBK）下，`powershell.exe` 若读取无 BOM 的 UTF-8 脚本会按 ANSI 解码并导致语法解析错误（`TerminatorExpectedAtEndOfString`）。本仓库 `scripts/install-wb-learning-client.ps1` 严格保留 UTF-8 BOM，确保在所有中文 Windows 终端及双击 `install.cmd` 时稳定执行。
