#!/usr/bin/env python3
"""Operate the shared conversation ledger after recording the user's actual decision."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assets' / 'FusionSafeLocalTools'))
from workflow import Ledger, Paused


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['status','approve-file','reject-file','discard-incomplete','resume','verify-sample','accept-health','cancel-size-limit'])
    p.add_argument('--ledger',required=True)
    p.add_argument('--conversation',required=True)
    p.add_argument('--job')
    p.add_argument('--evidence-file', help='UTF-8 file containing the actual user decision or sample validation findings')
    a = p.parse_args()
    evidence = Path(a.evidence_file).read_text(encoding='utf-8').strip() if a.evidence_file else ''
    with Ledger(a.ledger,a.conversation).locked() as l:
        if a.action != 'status' and not evidence:
            raise Paused('状态变更必须记录真实决定/验证依据；不能代替用户批准')
        if a.action == 'approve-file': l.commit(True,evidence)
        elif a.action == 'reject-file':
            pending = l.data['pending']
            if not pending or pending['phase'] != 'validated': raise Paused('只有检查完成的待确认文件可拒绝保存')
            l.reject(evidence)
        elif a.action == 'discard-incomplete':
            pending = l.data['pending']
            if not pending or pending['phase'] != 'exporting': raise Paused('没有未完成的临时导出')
            l.reject(evidence)
        elif a.action == 'resume': l.resume(a.job,evidence)
        elif a.action == 'verify-sample': l.verify_sample(a.job,evidence)
        elif a.action == 'accept-health':
            job = l.data['jobs'][a.job]
            if not job.get('health_pending'): raise Paused('没有待检查的模型警告')
            job['health_approval'] = {'signature':job['health_pending'],'evidence':evidence}
            job['status'] = 'ready'
            l.save()
        elif a.action == 'cancel-size-limit': l.cancel_limit(evidence)
        print(json.dumps({'report':l.report(),'jobs':l.data['jobs']},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
