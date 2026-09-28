"""Install per-user Windows tasks; retire the two legacy WB schedule sidecars."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from sync_learning_rules import atomic_write

HOME = Path.home()
ROOT = HOME / '.codex/wb-skill-learning'
ANTIGRAVITY_CONFIG = HOME / '.gemini/config/config.json'
SIDECARS = HOME / '.gemini/config/sidecars'


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError(f'Expected a JSON object: {path.name}')
    return value


def current_sid() -> str:
    result = subprocess.run(['whoami.exe', '/user', '/fo', 'csv', '/nh'],
                            check=True, capture_output=True)
    # Only the ASCII SID is consumed; account names may use the OEM code page.
    rows = list(csv.reader(io.StringIO(result.stdout.decode('ascii', errors='replace'))))
    sid = rows[-1][-1].strip()
    if not re.fullmatch(r'S-1-5-\d+(?:-\d+)+', sid):
        raise ValueError('Cannot determine current Windows user SID')
    return sid


def task_xml(sid: str, executable: str, arguments: list[str], daily: bool = False) -> str:
    task = ET.Element('Task', version='1.2', xmlns='http://schemas.microsoft.com/windows/2004/02/mit/task')
    triggers = ET.SubElement(task, 'Triggers')
    trigger = ET.SubElement(triggers, 'CalendarTrigger' if daily else 'TimeTrigger')
    start = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0) if daily else datetime.now() + timedelta(minutes=15)
    if not daily:
        repetition = ET.SubElement(trigger, 'Repetition')
        ET.SubElement(repetition, 'Interval').text = 'PT15M'
        ET.SubElement(repetition, 'StopAtDurationEnd').text = 'false'
    ET.SubElement(trigger, 'StartBoundary').text = start.isoformat(timespec='seconds')
    ET.SubElement(trigger, 'Enabled').text = 'true'
    if daily:
        ET.SubElement(ET.SubElement(trigger, 'ScheduleByDay'), 'DaysInterval').text = '1'
    principal = ET.SubElement(ET.SubElement(task, 'Principals'), 'Principal', id='CurrentUser')
    for key, value in [('UserId', sid), ('LogonType', 'InteractiveToken'), ('RunLevel', 'LeastPrivilege')]:
        ET.SubElement(principal, key).text = value
    settings = ET.SubElement(task, 'Settings')
    for key, value in [('MultipleInstancesPolicy', 'IgnoreNew'), ('DisallowStartIfOnBatteries', 'false'),
                       ('StopIfGoingOnBatteries', 'false'), ('StartWhenAvailable', 'true'),
                       ('ExecutionTimeLimit', 'PT10M' if daily else 'PT5M')]:
        ET.SubElement(settings, key).text = value
    action = ET.SubElement(ET.SubElement(task, 'Actions', Context='CurrentUser'), 'Exec')
    ET.SubElement(action, 'Command').text = executable
    ET.SubElement(action, 'Arguments').text = subprocess.list2cmdline(arguments)
    ET.SubElement(action, 'WorkingDirectory').text = str(ROOT)
    return ET.tostring(task, encoding='unicode')


def register_task(name: str, xml: str) -> None:
    descriptor, temporary = tempfile.mkstemp(suffix='.xml')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-16') as stream:
            stream.write('<?xml version="1.0" encoding="UTF-16"?>\n' + xml)
        result = subprocess.run(['schtasks.exe', '/Create', '/TN', name, '/XML', temporary, '/F'],
                                capture_output=True)
        if result.returncode:
            # Do not echo task arguments or arbitrary legacy configuration.
            raise RuntimeError(f'Task registration failed: {name} (exit {result.returncode}); check Task Scheduler permissions')
    finally:
        os.unlink(temporary)


def install(sid: str) -> None:
    if not (ROOT / 'hub-config.json').is_file():
        raise ValueError('Install the current user learning configuration first')
    config = read_object(ANTIGRAVITY_CONFIG) if ANTIGRAVITY_CONFIG.exists() else {}
    sidecars = config.setdefault('sidecars', {})
    if not isinstance(sidecars, dict):
        raise ValueError('Antigravity sidecars configuration must be an object')
    names = ['wb-skill-rules-sync', 'wb-skill-auto-update']
    for name in names:
        if name in sidecars and not isinstance(sidecars[name], dict):
            raise ValueError(f'Invalid sidecar settings: {name}')
    # Stable runtime path survives deleting the downloaded ZIP/checkout.
    target = ROOT / 'sync_learning_rules.py'
    python = Path(sys.executable)
    pythonw = python.with_name('pythonw.exe')
    executable = str(pythonw if pythonw.is_file() else python)
    jobs = [('wb-skill-rules-sync', f'WBSkill_RulesSync_{sid}', executable, ['-X', 'utf8', str(target)], False)]
    legacy = SIDECARS / 'wb-skill-auto-update/sidecar.json'
    if legacy.exists():
        old = read_object(legacy)
        args = old.get('args')
        # Only migrate the known daily Python updater, never guess custom commands.
        if old.get('builtin') != 'schedule' or not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            raise ValueError('Unrecognized legacy auto-update sidecar; configuration left unchanged')
        if len(args) not in (3, 5) or args[0] != '0 6 * * *' or (len(args) == 5 and args[2:4] != ['-X', 'utf8']):
            raise ValueError('Unsupported legacy auto-update schedule/arguments; configuration left unchanged')
        script = Path(args[-1])
        if not Path(args[1]).is_file() or not script.is_file() or script.name != 'update_skill_from_git.py':
            raise ValueError('Legacy updater executable/script missing; configuration left unchanged')
        jobs.append(('wb-skill-auto-update', f'WBSkill_AutoUpdate_{sid}', args[1], ['-X', 'utf8', str(script)], True))
    elif sidecars.get('wb-skill-auto-update', {}).get('enabled'):
        raise ValueError('Enabled legacy updater has no sidecar.json; repair it before migration')

    backup = ROOT / 'scheduler-backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    if ANTIGRAVITY_CONFIG.exists():
        shutil.copy2(ANTIGRAVITY_CONFIG, backup / 'config.json')
    for name, *_ in jobs:
        old_path = SIDECARS / name / 'sidecar.json'
        if old_path.exists():
            shutil.copy2(old_path, backup / f'{name}.json')
    atomic_write(target, Path(__file__).with_name('sync_learning_rules.py').read_text(encoding='utf-8'))
    for name, task_name, exe, args, daily in jobs:
        register_task(task_name, task_xml(sid, exe, args, daily))
        # Retire each sidecar only after its replacement was registered successfully.
        sidecars.setdefault(name, {})['enabled'] = False
        atomic_write(ANTIGRAVITY_CONFIG, json.dumps(config, ensure_ascii=False, indent=2) + '\n')
        (SIDECARS / name / 'sidecar.json').unlink(missing_ok=True)
        print(f'Registered: {task_name}')
    print(f'Legacy configuration backup: {backup}')
    print('Tasks run only while this Windows user is logged on. Registration is not proof of a successful run.')
    print('Close Antigravity and sign out/in once to retire existing processes; no processes were killed.')


def main() -> None:
    if os.name != 'nt':
        raise SystemExit('This installer requires Windows; no sidecar was installed.')
    try:
        install(current_sid())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Scheduler installation incomplete: {error}') from None


if __name__ == '__main__':
    main()
