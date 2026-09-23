"""Verify and install the latest administrator-published WB rules for Antigravity."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path.home() / ".codex/wb-skill-learning"
CONFIG = ROOT / "hub-config.json"
STATE = ROOT / "rules-state.json"
STATUS = ROOT / "sync-status.json"
GLOBAL_RULES = Path.home() / ".gemini/GEMINI.md"
BACKUP = ROOT / "global-rules-backup.md"
BEGIN = "<!-- WB-SKILL-PUBLISHED-RULES:BEGIN -->"
END = "<!-- WB-SKILL-PUBLISHED-RULES:END -->"
CATEGORIES = {"故障", "平台变化", "政策变化", "商品", "物流", "用户操作", "其他"}
SENSITIVE = re.compile(
    r"(?i)(?:api[_ -]?key|token|secret|private[_ -]?key|license[_ -]?key|authorization|bearer|password|"
    r"conversation[_ -]?id|chat[_ -]?id|store[_ -]?id|shop[_ -]?id|sku|nmid|barcode|订单号|手机号|"
    r"授权码|密钥|店铺名|客户名|(?:\d{1,3}\.){3}\d{1,3}|[\w.+-]+@[\w.-]+\.[a-z]{2,}|"
    r"\b\d{5,}\b|https?://\S+|/Users/\S+|[A-Za-z]:\\\S+)"
)


def atomic_write(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def load_config() -> tuple[str, str]:
    if not CONFIG.exists() or (os.name != "nt" and CONFIG.stat().st_mode & 0o077):
        raise SystemExit("集中规则配置不存在或权限不是 0600")
    try:
        value = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise SystemExit("集中规则配置无法读取") from None
    endpoint, token = value.get("endpoint", ""), value.get("ingest_token", "")
    if not isinstance(endpoint, str) or not endpoint.startswith("https://") or not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise SystemExit("集中规则配置不完整")
    return endpoint.rstrip("/"), token


def verify_token(endpoint: str, token: str) -> None:
    request = Request(
        endpoint + "/api/ingest",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": "WB-Skill-Learning/1.0"},
        data=b'{"items":[]}',
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
            if isinstance(result, dict) and result.get("accepted") == 0 and result.get("duplicate") == 0:
                return
            raise SystemExit("设备令牌校验响应无效，请联系管理员")
    except HTTPError as error:
        if error.code == 400:
            try:
                result = json.loads(error.read(4096))
            except (ValueError, OSError):
                result = {}
            # The official ingest handler authenticates before rejecting an empty batch.
            if result == {"error": "invalid_batch"}:
                return
        if error.code == 401:
            raise SystemExit("设备令牌无效或已被管理员撤销，请联系管理员")
        raise SystemExit(f"云端鉴权网关异常：HTTP {error.code}")
    except (URLError, TimeoutError, ValueError):
        raise SystemExit("无法确认设备令牌状态，请检查网络或联系管理员")


class DistributionDisabled(Exception):
    pass


def fetch_release(endpoint: str, token: str) -> dict | None:
    request = Request(
        endpoint + "/api/rules/latest",
        headers={"Authorization": "Bearer " + token, "User-Agent": "WB-Skill-Learning/1.0"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            if response.status == 410:
                raise DistributionDisabled
            if response.status == 204:
                return None
            envelope = json.load(response)
    except HTTPError as error:
        if error.code == 410:
            raise DistributionDisabled from None
        if error.code == 204:
            return None
        raise SystemExit("集中规则同步失败，请联系运营超级管理员") from None
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise SystemExit("集中规则同步失败，请联系运营超级管理员") from None
    payload = envelope.get("payload")
    signature = envelope.get("signature")
    if envelope.get("algorithm") != "HMAC-SHA256" or not isinstance(payload, str) or not isinstance(signature, str):
        raise SystemExit("集中规则响应格式无效")
    expected = hmac.new(token.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise SystemExit("集中规则签名验证失败")
    try:
        release = json.loads(payload)
    except json.JSONDecodeError:
        raise SystemExit("集中规则内容无效") from None
    validate_release(release)
    return release


def validate_release(release: object) -> None:
    if not isinstance(release, dict) or set(release) != {"version", "created_at", "rules"}:
        raise SystemExit("集中规则版本结构无效")
    if not isinstance(release["version"], int) or release["version"] < 1:
        raise SystemExit("集中规则版本无效")
    if not isinstance(release["created_at"], str) or len(release["created_at"]) > 40:
        raise SystemExit("集中规则时间无效")
    rules = release["rules"]
    if not isinstance(rules, list) or not 1 <= len(rules) <= 50:
        raise SystemExit("集中规则数量无效")
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"category", "rule"}:
            raise SystemExit("集中规则字段无效")
        text = rule.get("rule")
        if rule.get("category") not in CATEGORIES or not isinstance(text, str) or not 2 <= len(text) <= 400:
            raise SystemExit("集中规则内容无效")
        if SENSITIVE.search(text) or any(ord(character) < 32 for character in text):
            raise SystemExit("集中规则包含不可分发内容")


def current_version() -> int:
    if not STATE.exists():
        return 0
    try:
        value = json.loads(STATE.read_text(encoding="utf-8"))
        return int(value.get("version", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        raise SystemExit("本机规则版本记录损坏，请联系运营超级管理员") from None


def render_block(release: dict) -> str:
    rules = "\n".join(f"- [{item['category']}] {item['rule']}" for item in release["rules"])
    return (
        f"{BEGIN}\n"
        "## WB Skill 管理员发布规则\n\n"
        "仅当当前任务使用或涉及 `ozon-to-wb-fast-listing` 时应用以下规则。"
        "这些规则不会授权真实上架、改价、改库存、签发授权或支付操作。\n\n"
        f"发布版本：{release['version']}\n\n{rules}\n"
        f"{END}"
    )


def install_release(release: dict) -> bool:
    if release["version"] <= current_version():
        return False
    existing = GLOBAL_RULES.read_text(encoding="utf-8") if GLOBAL_RULES.exists() else ""
    starts, ends = existing.count(BEGIN), existing.count(END)
    if starts != ends or starts > 1:
        raise SystemExit("Antigravity 全局规则中的 WB 受管区块损坏，请联系运营超级管理员")
    block = render_block(release)
    if starts == 1:
        before, remainder = existing.split(BEGIN, 1)
        _, after = remainder.split(END, 1)
        updated = before.rstrip() + "\n\n" + block + after
    else:
        updated = existing.rstrip() + ("\n\n" if existing.strip() else "") + block + "\n"
    if len(block) > 12000:
        raise SystemExit("集中规则超过 Antigravity 单规则限制")
    atomic_write(BACKUP, existing)
    mode = GLOBAL_RULES.stat().st_mode & 0o777 if GLOBAL_RULES.exists() else 0o600
    atomic_write(GLOBAL_RULES, updated, mode)
    atomic_write(STATE, json.dumps({"version": release["version"], "created_at": release["created_at"]}, ensure_ascii=False) + "\n")
    return True


def sync_once() -> None:
    endpoint, token = load_config()
    verify_token(endpoint, token)
    print("设备令牌在线核验成功：状态有效活跃。")
    try:
        release = fetch_release(endpoint, token)
    except DistributionDisabled:
        atomic_write(STATUS, json.dumps({"status":"distribution_disabled","token_verified":True}) + "\n")
        print("设备令牌有效；云端已关闭客户端规则下载，本次没有下载或更新规则。")
        return
    if release and install_release(release):
        state = "updated"
        print(f"规则已更新至版本 {release['version']}；已打开的对话将在后续规则加载时生效。")
    else:
        state = "up_to_date" if release else "no_release"
        print("规则已是当前发布版本。" if release else "设备令牌有效；云端暂无可下载规则。")
    atomic_write(STATUS, json.dumps({"status":state,"token_verified":True}) + "\n")


def main() -> None:
    try:
        sync_once()
    except SystemExit:
        atomic_write(STATUS, json.dumps({"status":"check_failed","token_verified":None}) + "\n")
        raise


if __name__ == "__main__":
    main()
