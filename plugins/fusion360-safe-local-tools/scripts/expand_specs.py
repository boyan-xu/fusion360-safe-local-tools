#!/usr/bin/env python3
"""Expand reviewed rules for inspection; this command does not authorize or export."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assets' / 'FusionSafeLocalTools'))
from workflow import expand_rules
p=argparse.ArgumentParser()
p.add_argument('rules_json')
p.add_argument('output_json')
a=p.parse_args()
r=json.loads(Path(a.rules_json).read_text(encoding='utf-8'))
specs=expand_rules(r['rules'],r['combination'],r['filename_template'])
with open(a.output_json,'x',encoding='utf-8') as f: json.dump(specs,f,ensure_ascii=False,indent=2)
print(json.dumps({'count':len(specs),'first':specs[0],'last':specs[-1]},ensure_ascii=False))
