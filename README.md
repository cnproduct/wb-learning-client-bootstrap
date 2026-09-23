# WB 规则学习客户端 Windows 一键安装

在新的 64 位 Windows 电脑上安装 WB 规则学习同步客户端与 Antigravity 后台自动同步。需要准备管理员签发的 **43 位设备令牌**。

> [!NOTE]
> **设备令牌与 WB 店铺商业授权完全解耦**：
> 设备令牌用于设备级规则同步通道，**不是**代理商签发的窗口上架卡密，也**不是** Wildberries 店铺后台的 API Token。安装本客户端无需准备上架卡密或绑定店铺。

---

## 快速使用

1. 在本仓库页面选择 **Code → Download ZIP** 并解压至本机。
2. 双击解压目录中的 `install.cmd`。
3. 终端提示时，粘贴管理员签发的 43 位设备令牌（出于安全保护输入不会回显）。
4. 提示“安装成功”后，完全重启 Antigravity 即可生效。

---

## 安装器核心能力

- **环境检测**：自动检测官方 Python 3.10+，若缺失则静默下载并安装官方安全安装包；
- **配置持久化**：将设备专属令牌加密保存在 `%USERPROFILE%\.codex\wb-skill-learning\hub-config.json`；
- **签名规则验证**：连接云端验证网关，拉取管理员最新发布的 HMAC-SHA256 签名规则并安全写入全局 `GEMINI.md`；
- **Sidecar 后台自动化**：注册 Antigravity 后台 `wb-skill-rules-sync` 调度服务，每 15 分钟静默检测并同步最新云端防错规则。

---

## 验证与排查

- **验证配置文件**：`%USERPROFILE%\.codex\wb-skill-learning\hub-config.json`
- **验证已生效规则**：打开 `%USERPROFILE%\.gemini\GEMINI.md`，可看到 `<!-- WB-SKILL-PUBLISHED-RULES:BEGIN -->` 区块已成功注入。
- **与上架技能的关系**：安装完成后，若需执行商品上架业务，请在 Antigravity 中运行独立的 `ozon-to-wb-fast-listing` 技能。
