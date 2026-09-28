"""Synthetic migration checks; --windows-task also exercises native Task Scheduler."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import install_learning_rule_sync as installer

sid = 'S-1-5-21-100-200-300-1001'
ns = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
with tempfile.TemporaryDirectory(prefix='WB learning 中文 ') as temp:
    home = Path(temp)
    root = home / 'learning'
    root.mkdir()
    (root / 'hub-config.json').write_text('{}', encoding='utf-8')
    config = home / 'config.json'
    sidecars = home / 'sidecars'
    original = {'other': True, 'sidecars': {'unrelated': {'enabled': True},
                'wb-skill-rules-sync': {'enabled': True, 'custom': 'keep'}}}
    config.write_text(json.dumps(original), encoding='utf-8')
    rules = sidecars / 'wb-skill-rules-sync/sidecar.json'
    rules.parent.mkdir(parents=True)
    rules.write_text('{"builtin":"schedule"}', encoding='utf-8')
    with patch.multiple(installer, ROOT=root, ANTIGRAVITY_CONFIG=config, SIDECARS=sidecars):
        with patch.object(installer, 'register_task', side_effect=RuntimeError('denied')):
            try:
                installer.install(sid)
                raise AssertionError('registration failure accepted')
            except RuntimeError:
                pass
        assert json.loads(config.read_text(encoding='utf-8')) == original
        assert rules.exists()
        with patch.object(installer, 'register_task') as register:
            installer.install(sid)
            installer.install(sid)
        assert register.call_count == 2
        assert register.call_args_list[0].args[0] == register.call_args_list[1].args[0]
        xml = ET.fromstring(register.call_args.args[1])
        assert xml.findtext('t:Settings/t:MultipleInstancesPolicy', namespaces=ns) == 'IgnoreNew'
        assert xml.findtext('t:Settings/t:ExecutionTimeLimit', namespaces=ns) == 'PT5M'
        assert xml.findtext('t:Principals/t:Principal/t:UserId', namespaces=ns) == sid
        assert xml.findtext('t:Principals/t:Principal/t:LogonType', namespaces=ns) == 'InteractiveToken'
        assert xml.findtext('t:Triggers/t:TimeTrigger/t:Repetition/t:Interval', namespaces=ns) == 'PT15M'
        assert str(root / 'sync_learning_rules.py') in xml.findtext('t:Actions/t:Exec/t:Arguments', namespaces=ns)
        changed = json.loads(config.read_text(encoding='utf-8'))
        assert changed['other'] and changed['sidecars']['unrelated']['enabled']
        assert changed['sidecars']['wb-skill-rules-sync'] == {'enabled': False, 'custom': 'keep'}
        assert not rules.exists()
        assert list((root / 'scheduler-backups').glob('*/wb-skill-rules-sync.json'))
        assert (root / 'sync_learning_rules.py').is_file()

        legacy = sidecars / 'wb-skill-auto-update/sidecar.json'
        legacy.parent.mkdir(parents=True)
        updater = legacy.with_name('update_skill_from_git.py')
        updater.write_text('# synthetic fixture', encoding='utf-8')
        old = {'builtin': 'schedule', 'args': ['0 6 * * *', sys.executable, '-X', 'utf8', str(updater)]}
        legacy.write_text(json.dumps(old), encoding='utf-8')
        with patch.object(installer, 'register_task') as register:
            installer.install(sid)
        assert register.call_count == 2
        xml = ET.fromstring(register.call_args.args[1])
        assert xml.findtext('t:Triggers/t:CalendarTrigger/t:StartBoundary', namespaces=ns).endswith('T06:00:00')
        assert xml.findtext('t:Settings/t:ExecutionTimeLimit', namespaces=ns) == 'PT10M'
        assert not legacy.exists() and updater.exists()
        assert not json.loads(config.read_text(encoding='utf-8'))['sidecars']['wb-skill-auto-update']['enabled']

        for invalid in ({'builtin': 'schedule', 'args': ['* * * * *', sys.executable, str(updater)]}, []):
            legacy.write_text(json.dumps(invalid), encoding='utf-8')
            before = config.read_bytes()
            with patch.object(installer, 'register_task') as register:
                try:
                    installer.install(sid)
                    raise AssertionError('unknown legacy config accepted')
                except ValueError:
                    pass
                register.assert_not_called()
            assert config.read_bytes() == before and legacy.exists()

if '--windows-task' in sys.argv:
    # Real Windows API check, no token/network or changes to the runner's real WB tasks.
    name = 'WBSkill_Test_' + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='WB task 中文 ') as temp:
        root = Path(temp)
        marker = root / 'ran.txt'
        script = root / 'probe.py'
        script.write_text('from pathlib import Path\nPath(__file__).with_name("ran.txt").write_text("ok")\n', encoding='utf-8')
        try:
            with patch.object(installer, 'ROOT', root):
                installer.register_task(name, installer.task_xml(installer.current_sid(), sys.executable, ['-X', 'utf8', str(script)]))
            subprocess.run(['schtasks.exe', '/Run', '/TN', name], check=True)
            for _ in range(30):
                if marker.exists():
                    break
                time.sleep(1)
            assert marker.read_text() == 'ok', 'Native task did not run'
        finally:
            subprocess.run(['schtasks.exe', '/Delete', '/TN', name, '/F'], check=True)
print('Scheduler checks passed: failure preservation, repeat install, account isolation, bounded tasks, legacy migration and backups')
