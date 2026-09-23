"""Synthetic-only checks: python tests/check_sync.py."""
import contextlib
import hashlib
import hmac
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.error import HTTPError

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sync',root/'scripts/sync_learning_rules.py')
sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
token='A'*43
class Response(io.BytesIO):
    status=200

def error(code,body):
    return HTTPError('https://example.invalid',code,'test',{},io.BytesIO(body))

with patch.object(sync,'urlopen',side_effect=error(400,b'{"error":"invalid_batch"}')):
    sync.verify_token('https://example.invalid',token)
for bad in [error(400,b'bad request'),error(400,b'{"error":"invalid_json_or_size"}'),error(401,b'{"error":"unauthorized"}')]:
    with patch.object(sync,'urlopen',side_effect=bad):
        try:sync.verify_token('https://example.invalid',token);raise AssertionError('invalid auth accepted')
        except SystemExit:pass
with patch.object(sync,'urlopen',return_value=Response(b'{}')):
    try:sync.verify_token('https://example.invalid',token);raise AssertionError('unexpected success accepted')
    except SystemExit:pass
with tempfile.TemporaryDirectory() as temp:
    home=Path(temp);rules=home/'GEMINI.md';rules.write_text('Other unrelated rules.\n', encoding='utf-8')
    with patch.multiple(sync,GLOBAL_RULES=rules,STATE=home/'rules-state.json',STATUS=home/'sync-status.json',BACKUP=home/'backup.md'), patch.object(sync,'load_config',return_value=('https://example.invalid',token)):
        with patch.object(sync,'verify_token'),patch.object(sync,'urlopen',side_effect=error(410,b'{"error":"client_rule_distribution_retired"}')),contextlib.redirect_stdout(io.StringIO()) as out:
            sync.main()
        assert json.loads(sync.STATUS.read_text(encoding='utf-8'))['status']=='distribution_disabled'
        assert '没有下载或更新规则' in out.getvalue()
        assert rules.read_text(encoding='utf-8')=='Other unrelated rules.\n'
        with patch.object(sync,'verify_token',side_effect=SystemExit('invalid')),patch.object(sync,'fetch_release') as fetch:
            try:sync.main();raise AssertionError('invalid token accepted')
            except SystemExit:pass
            fetch.assert_not_called()
        assert json.loads(sync.STATUS.read_text(encoding='utf-8'))['status']=='check_failed'
        release={'version':1,'created_at':'2026-09-22','rules':[{'category':'用户操作','rule':'缺少商品资料时先补充。'}]}
        payload=json.dumps(release,ensure_ascii=False)
        envelope={'algorithm':'HMAC-SHA256','payload':payload,'signature':hmac.new(token.encode(),payload.encode(),hashlib.sha256).hexdigest()}
        with patch.object(sync,'urlopen',return_value=Response(json.dumps(envelope).encode())):
            fetched=sync.fetch_release('https://example.invalid',token)
        assert sync.install_release(fetched)
        assert rules.read_text(encoding='utf-8').startswith('Other unrelated rules.')
        assert not sync.install_release(fetched)
        envelope['signature']='0'*64
        with patch.object(sync,'urlopen',return_value=Response(json.dumps(envelope).encode())):
            try:sync.fetch_release('https://example.invalid',token);raise AssertionError('bad signature accepted')
            except SystemExit:pass
ps1_bytes = (root / 'scripts/install-wb-learning-client.ps1').read_bytes()
assert ps1_bytes.startswith(b'\xef\xbb\xbf'), "install-wb-learning-client.ps1 must start with UTF-8 BOM for Windows PowerShell 5.1 CP936 compatibility"
print('Learning checks: exact auth response, rejection, retired-download status, no false protection claim, signed rules, unrelated content preservation, and UTF-8 BOM passed')
