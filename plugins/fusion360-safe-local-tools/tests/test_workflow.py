import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets'/'FusionSafeLocalTools'))
from workflow import Ledger, MB, Paused, expand_rules, marked, validate_file


def step(path,size):
    prefix=b'ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n'
    suffix=b'\nENDSEC;\nEND-ISO-10303-21;'
    path.write_bytes(prefix+b' '*(size-len(prefix)-len(suffix))+suffix)

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.plan={'conversation_id':'chat','job_id':'one','confirmation':'user confirmed','unresolved':[],
                   'format':'step','output_dir':str(self.root),
                   'specs':[{'id':str(i),'parameters':{},'filename':str(i)+'.step'} for i in range(4)]}
    def ledger(self): return Ledger(self.root/'ledger.json','chat').locked()
    def produce(self,l,size):
        path=l.begin('one'); step(path,size); l.produced({'parameters':{},'checked':True})
    def test_exact_threshold_and_overshoot(self):
        with self.ledger() as l:
            l.add_job(self.plan); self.produce(l,MB)
            self.assertEqual(l.data['total_bytes'],MB)
            l.verify_sample('one','sample checked')
            self.produce(l,100)
            self.assertEqual(l.report()['cumulative_with_pending'],MB+100)
            with self.assertRaises(Paused): l.begin('one')
            with self.assertRaises(Paused): l.commit(False)
            l.commit(True,'user saved this file')
            self.assertEqual(l.data['threshold_bytes'],2*MB+100)
    def test_large_file_single_pause_and_next_increment(self):
        with self.ledger() as l:
            l.add_job(self.plan); self.produce(l,5*MB)
            self.assertEqual(l.report()['pending_bytes'],5*MB)
            l.commit(True,'save 5 MB'); l.verify_sample('one','checked')
            self.assertEqual(l.data['threshold_bytes'],6*MB)
            self.produce(l,MB)
            self.assertIsNone(l.data['pending'])
            self.produce(l,100)
            self.assertIsNotNone(l.data['pending'])
    def test_rejection_and_restart_no_skip(self):
        with self.ledger() as l:
            l.add_job(self.plan); self.produce(l,MB+1)
            name=l.data['pending']['path']; l.reject('do not save')
            self.assertFalse(Path(name).exists())
            self.assertEqual(l.data['jobs']['one']['next'],0)
        with self.ledger() as l:
            with self.assertRaises(Paused): l.begin('one')
            l.resume('one','continue'); self.produce(l,MB+1)
            self.assertEqual(l.data['pending']['index'],0)
            self.assertTrue(l.data['limit_enabled'])
    def test_cross_job_cumulative(self):
        with self.ledger() as l:
            l.add_job(self.plan); self.produce(l,600000)
            other=copy.deepcopy(self.plan); other['job_id']='two'
            other['specs']=[{'id':'a','parameters':{},'filename':'a.step'}]
            l.add_job(other); path=l.begin('two'); step(path,500000); l.produced({'checked':True})
            self.assertEqual(l.report()['cumulative_with_pending'],1100000)
            self.assertTrue(l.data['pending']['crosses_limit'])
    def test_sample_gate(self):
        with self.ledger() as l:
            l.add_job(self.plan); self.produce(l,100)
            with self.assertRaises(Paused): l.begin('one')
    def test_commit_crash_recovery(self):
        with self.ledger() as l:
            l.add_job(self.plan); self.produce(l,MB+1)
            p=l.data['pending']; p['phase']='committing'; p['approval']='save'; l.save()
            os.link(p['path'],p['destination'])
        with self.ledger() as l:
            l.commit(True,'recover')
            self.assertEqual(l.data['total_bytes'],MB+1)
            self.assertEqual(l.data['jobs']['one']['next'],1)
            self.assertEqual(len(l.data['jobs']['one']['completed']),1)
    def test_collision_no_overwrite(self):
        with self.ledger() as l:
            l.add_job(self.plan); self.produce(l,MB+1)
            p=l.data['pending']; Path(p['destination']).write_text('existing')
            with self.assertRaises(Paused): l.commit(True,'save')
            self.assertEqual(Path(p['destination']).read_text(encoding='utf-8'),'existing')
    def test_invalid_file_never_success(self):
        with self.ledger() as l:
            l.add_job(self.plan); p=l.begin('one'); p.write_text('not step')
            with self.assertRaises(ValueError): l.produced({'checked':True})
            self.assertEqual(l.data['jobs']['one']['next'],0)
            self.assertEqual(l.data['total_bytes'],0)
    def test_immutable_plan_and_conversation(self):
        with self.ledger() as l:
            l.add_job(self.plan); changed=copy.deepcopy(self.plan); changed['specs'][0]['parameters']={'a':'2 mm'}
            with self.assertRaises(Paused): l.add_job(changed)
        with self.assertRaises(ValueError):
            with Ledger(self.root/'ledger.json','other').locked(): pass
    def test_fail_retains_spec(self):
        with self.ledger() as l:
            l.add_job(self.plan); l.begin('one'); l.fail('one','export false')
            self.assertEqual(l.data['jobs']['one']['next'],0)
            with self.assertRaises(Paused): l.begin('one')
    def test_decimal_product_zip_and_ambiguities(self):
        r={'a':{'start':'0.1','stop':'0.3','step':'0.1','unit':'mm'},'b':{'values':['1 mm','2 mm','3 mm']}}
        self.assertEqual(len(expand_rules(r,'product','{index}.step')),9)
        self.assertEqual(expand_rules(r,'zip','{index}.step')[-1]['parameters']['a'],'0.3 mm')
        with self.assertRaises(ValueError): expand_rules(r,'unspecified','{index}.step')
        with self.assertRaises(ValueError): expand_rules(r,'product','same.step')
        with self.assertRaises(ValueError): expand_rules(r,'zip','../{index}.step')
        r['a']['stop']='0.35'
        with self.assertRaises(ValueError): expand_rules(r,'zip','{index}.step')
    def test_names(self):
        self.assertEqual(marked('width',True),'width_ChatGPT')
        self.assertEqual(marked('Body (ChatGPT)'),'Body (ChatGPT)')
        with self.assertRaises(ValueError): marked('bad name',True)

if __name__=='__main__': unittest.main()
