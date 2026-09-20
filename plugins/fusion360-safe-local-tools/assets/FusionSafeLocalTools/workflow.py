"""Local, durable export ledger. No Fusion imports, services or network access."""
import contextlib
import copy
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import struct
import tempfile
import zipfile
import xml.etree.ElementTree as ET

MB = 1_000_000

class Paused(RuntimeError):
    pass


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.state-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def marked(name, parameter=False):
    suffix = '_ChatGPT' if parameter else ' (ChatGPT)'
    if not isinstance(name, str) or not name.strip():
        raise ValueError('名称不能为空')
    result = name if name.endswith(suffix) else name + suffix
    if parameter and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', result):
        raise ValueError('请提供可用于公式的参数名：字母、数字和下划线，不能以数字开头')
    return result


def expand_rules(rules, combination, filename_template, limit=100000):
    """Decimal inclusive ranges or explicit expression sets; never eval formulas."""
    if combination not in ('product', 'zip') or not rules:
        raise ValueError('必须明确 product（所有组合）或 zip（逐项配对）及参数规则')
    names, axes = [], []
    for name, rule in rules.items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            raise ValueError('参数名无效')
        if set(rule) == {'values'}:
            vals = rule['values']
            if not isinstance(vals, list) or not vals or not all(isinstance(x, str) and x.strip() for x in vals):
                raise ValueError('取值集合必须是非空的 Fusion 表达式字符串列表')
        elif set(rule) == {'start', 'stop', 'step', 'unit'}:
            try:
                a, b, step = (Decimal(str(rule[k])) for k in ('start', 'stop', 'step'))
            except InvalidOperation:
                raise ValueError('范围必须是明确的十进制数字')
            if not all(x.is_finite() for x in (a,b,step)) or step == 0 or (b-a)*step < 0:
                raise ValueError('范围/步长不合法')
            if (b-a) % step != 0:
                raise ValueError('终点不能由步长到达，请确认终点或取值规则')
            n = int((b-a)/step) + 1
            if n > limit or not isinstance(rule['unit'], str):
                raise ValueError('规则过大或单位未明确')
            vals = [(format(a+i*step, 'f') + ' ' + rule['unit']).strip() for i in range(n)]
        else:
            raise ValueError('每个参数只能提供 values 或 start/stop/step/unit')
        if len(vals) != len(set(vals)):
            raise ValueError('参数集合包含重复值，请确认是否需要重复规格')
        names.append(name)
        axes.append(vals)
    if combination == 'zip' and len(set(map(len, axes))) != 1:
        raise ValueError('逐项配对需要各集合长度相同')
    count = math.prod(map(len, axes)) if combination == 'product' else len(axes[0])
    if count > limit:
        raise ValueError('超过单计划 100000 项，请分计划；对话账本保持共用')
    rows = itertools.product(*axes) if combination == 'product' else zip(*axes)
    specs, seen = [], set()
    for index, row in enumerate(rows, 1):
        params = dict(zip(names, row))
        # str.format_map cannot execute code; forbid attribute/index traversal.
        import string
        for _, field, fmt, conv in string.Formatter().parse(filename_template):
            if field is not None and (field not in names + ['index'] or conv or fmt):
                raise ValueError('文件名只允许 {index} 和 {参数名} 占位符，不使用格式代码')
        filename = filename_template.format_map(dict(params, index=index))
        safe_filename(filename)
        if filename.casefold() in seen:
            raise ValueError('生成了重复文件名，请修改命名规则')
        seen.add(filename.casefold())
        specs.append({'id': str(index), 'parameters': params, 'filename': filename})
    return specs


def safe_filename(name):
    if not isinstance(name, str) or not name or name in ('.', '..') or any(c in name for c in '/\\\x00:') or name.startswith('.'):
        raise ValueError('文件名必须是普通文件名，不能包含路径或隐藏前缀')


def validate_file(path, format_name):
    """Structural validation only; Fusion runtime additionally verifies model/parameters."""
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size == 0:
        raise ValueError('导出文件缺失或为空')
    if format_name == 'step':
        data = p.read_bytes().strip()
        if not data.startswith(b'ISO-10303-21;') or not data.endswith(b'END-ISO-10303-21;') or b'DATA;' not in data or b'ENDSEC;' not in data:
            raise ValueError('STEP 结构无效或文件不完整')
    elif format_name == 'stl':
        data = p.read_bytes()
        binary = len(data) >= 84 and len(data) == 84 + 50 * struct.unpack('<I', data[80:84])[0] and struct.unpack('<I', data[80:84])[0] > 0
        ascii_ok = data.lstrip().startswith(b'solid') and b'facet normal' in data and b'endsolid' in data
        if not (binary or ascii_ok):
            raise ValueError('STL 结构无效')
    elif format_name == '3mf':
        with zipfile.ZipFile(p) as z:
            if z.testzip() is not None or '[Content_Types].xml' not in z.namelist():
                raise ValueError('3MF 压缩包无效')
            models = [n for n in z.namelist() if n.lower().endswith('.model')]
            if not models or not any(any(e.tag.endswith('}triangle') for e in ET.fromstring(z.read(n)).iter()) for n in models):
                raise ValueError('3MF 缺少网格')
    else:
        raise ValueError('此导出执行器仅支持 step/stl/3mf；其他格式需单独核实')
    return {'bytes': p.stat().st_size, 'sha256': digest(p)}


class Ledger:
    """One file per conversation, shared by every export job. Serialize all operations."""
    def __init__(self, path, conversation_id):
        self.path = Path(path).resolve()
        self.conversation_id = conversation_id
        if not isinstance(conversation_id, str) or not conversation_id.strip():
            raise ValueError('需要稳定的当前对话 ID')

    @contextlib.contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self.path) + '.lock', 'a') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Paused('同一对话已有导出操作正在执行')
            try:
                self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {
                    'schema': 1, 'conversation_id': self.conversation_id, 'total_bytes': 0,
                    'threshold_bytes': MB, 'limit_enabled': True, 'pending': None, 'jobs': {}, 'events': []}
                if self.data['schema'] != 1 or self.data['conversation_id'] != self.conversation_id:
                    raise ValueError('账本版本或对话 ID 不匹配，不能新建账本绕过累计量')
                yield self
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def save(self):
        atomic_json(self.path, self.data)

    def add_job(self, plan):
        if not plan.get('confirmation') or plan.get('unresolved') != []:
            raise Paused('先确认完整导出计划并解决所有不明确条件')
        if plan.get('format') not in ('step','stl','3mf') or not plan.get('specs'):
            raise ValueError('导出格式或规格缺失')
        if plan.get('conversation_id') != self.conversation_id:
            raise ValueError('计划与账本的对话不一致')
        out = Path(plan['output_dir'])
        if not out.is_absolute() or not out.is_dir():
            raise ValueError('需要已确认且存在的绝对导出目录')
        ids, names = set(), set()
        for spec in plan['specs']:
            safe_filename(spec['filename'])
            if Path(spec['filename']).suffix.lower() not in {'step':('.step','.stp'),'stl':('.stl',),'3mf':('.3mf',)}[plan['format']]:
                raise ValueError('扩展名与格式不匹配')
            if spec['id'] in ids or spec['filename'].casefold() in names:
                raise ValueError('重复规格编号或文件名')
            ids.add(spec['id']); names.add(spec['filename'].casefold())
        key = plan['job_id']
        if key in self.data['jobs']:
            if self.data['jobs'][key]['plan'] != plan:
                raise Paused('原计划已改变，请先确认变更并使用新的任务 ID；仍使用同一账本')
            return self.data['jobs'][key]
        job = {'plan': copy.deepcopy(plan), 'next': 0, 'sample_verified': False, 'status': 'ready', 'completed': [], 'failure': None}
        self.data['jobs'][key] = job
        self.save()
        return job

    def begin(self, job_id):
        if self.data['pending']:
            raise Paused('先处理当前待确认/恢复文件，不能开始另一项导出')
        job = self.data['jobs'][job_id]
        if job['status'] != 'ready':
            raise Paused('任务暂停：' + job['status'])
        if job['next'] == len(job['plan']['specs']):
            return None
        if job['next'] > 0 and not job['sample_verified']:
            raise Paused('必须先验证首个样本再批量导出')
        spec = job['plan']['specs'][job['next']]
        dest = Path(job['plan']['output_dir']) / spec['filename']
        if dest.exists():
            raise Paused('目标文件已存在，拒绝覆盖：' + str(dest))
        # Same filesystem permits atomic no-clobber hard-link commit.
        stage = dest.parent / '.fusion-chatgpt-pending'
        stage.mkdir(mode=0o700, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=stage, suffix=dest.suffix)
        os.close(fd)
        self.data['pending'] = {'job_id': job_id, 'index': job['next'], 'path': name,
                                'destination': str(dest), 'phase': 'exporting'}
        self.save()
        return Path(name)

    def produced(self, verification):
        p = self.data['pending']
        if not p or p['phase'] != 'exporting':
            raise Paused('没有进行中的导出')
        if not verification:
            raise ValueError('必须记录实际参数与模型检查结果')
        info = validate_file(p['path'], self.data['jobs'][p['job_id']]['plan']['format'])
        p.update(info, verification=verification, phase='validated')
        p['crosses_limit'] = self.data['limit_enabled'] and self.data['total_bytes'] + p['bytes'] > self.data['threshold_bytes']
        self.save()
        if not p['crosses_limit']:
            self.commit(False)
        return self.report()

    def report(self):
        p = self.data['pending']
        return {'saved_bytes': self.data['total_bytes'], 'pending_bytes': p.get('bytes',0) if p else 0,
                'cumulative_with_pending': self.data['total_bytes'] + (p.get('bytes',0) if p else 0),
                'next_threshold': self.data['threshold_bytes'], 'pending': copy.deepcopy(p)}

    def commit(self, approved, evidence=''):
        p = self.data['pending']
        if not p or p['phase'] not in ('validated', 'committing'):
            raise Paused('文件尚未通过检查')
        if p['phase'] == 'validated' and p['crosses_limit'] and not (approved and evidence.strip()):
            raise Paused('超过累计阈值，等待用户决定是否保存')
        if digest(p['path']) != p['sha256']:
            raise Paused('待确认文件发生变化，请重新检查')
        if p['phase'] == 'validated':
            p['phase'] = 'committing'
            p['approval'] = evidence
            self.save()  # write-ahead record for recovery after interruption
        destination = Path(p['destination'])
        if destination.exists():
            # Only an interrupted hard-link publication of OUR pending file is recoverable.
            if not os.path.samefile(p['path'], destination):
                raise Paused('目标已存在且不属于本次提交，不能覆盖')
        else:
            os.link(p['path'], destination)
        job = self.data['jobs'][p['job_id']]
        self.data['total_bytes'] += p['bytes']
        if p['crosses_limit']:
            self.data['threshold_bytes'] = self.data['total_bytes'] + MB
        job['completed'].append(copy.deepcopy(p))
        job['next'] += 1
        self.data['pending'] = None
        self.save()
        Path(p['path']).unlink(missing_ok=True)

    def reject(self, evidence):
        p = self.data['pending']
        if not p or p['phase'] == 'committing' or not evidence.strip():
            raise Paused('无可拒绝的待确认文件，或缺少用户决定')
        Path(p['path']).unlink(missing_ok=True)
        job = self.data['jobs'][p['job_id']]
        job['status'] = 'rejected'
        self.data['events'].append({'action':'reject','job_id':p['job_id'],'index':p['index'],'evidence':evidence})
        self.data['pending'] = None
        self.save()  # next is intentionally unchanged

    def fail(self, job_id, reason):
        job = self.data['jobs'][job_id]
        job['status'] = 'failed'
        job['failure'] = reason
        self.save()  # retain temporary file for diagnosis; never counts as complete

    def resume(self, job_id, evidence):
        if not evidence.strip() or self.data['pending']:
            raise Paused('先处理待确认文件，并记录用户继续指示')
        job = self.data['jobs'][job_id]
        job['status'] = 'ready'
        self.data['events'].append({'action':'resume','job_id':job_id,'evidence':evidence})
        self.save()  # never disables/rebases the size limit

    def verify_sample(self, job_id, evidence):
        job = self.data['jobs'][job_id]
        if not job['completed'] or not evidence.strip():
            raise Paused('先导出并检查首个样本')
        job['sample_verified'] = True
        self.data['events'].append({'action':'sample_verified','job_id':job_id,'evidence':evidence})
        self.save()

    def cancel_limit(self, explicit_evidence):
        if not explicit_evidence.strip():
            raise Paused('取消限制需要用户明确指示，继续不等于取消')
        self.data['limit_enabled'] = False
        self.data['events'].append({'action':'cancel_limit','evidence':explicit_evidence})
        self.save()
