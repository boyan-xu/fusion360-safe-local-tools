"""Check refusal behavior without importing the Fusion native runtime."""
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets'))
fake=ModuleType('adsk'); fake.core=ModuleType('adsk.core'); fake.fusion=ModuleType('adsk.fusion')
with patch.dict(sys.modules,{'adsk':fake,'adsk.core':fake.core,'adsk.fusion':fake.fusion}):
    fw=importlib.import_module('FusionSafeLocalTools.fusion_workflow')

class ScopeTests(unittest.TestCase):
    def plan(self):
        return {'scope':{'target_id':'copy','mode':'copy','source_id':'original','parameters':['width'],
                         'protected':[],'impact_review':'dependency checked'},'specs':[{'parameters':{'width':'20 mm'}}]}
    def doc(self,marker='original'):
        return SimpleNamespace(creationId='copy',attributes=SimpleNamespace(itemByName=lambda *args:SimpleNamespace(value=marker) if marker else None))
    def test_copy_required(self):
        with self.assertRaises(fw.Paused): fw.require_scope(self.doc(None),self.plan())
        fw.require_scope(self.doc(),self.plan())
    def test_no_original_without_explicit_authorization(self):
        p=self.plan();p['scope']['mode']='original'
        with self.assertRaises(fw.Paused): fw.require_scope(self.doc(),p)
    def test_unapproved_parameter(self):
        p=self.plan();p['specs'][0]['parameters']['height']='100 mm'
        with self.assertRaises(fw.Paused): fw.require_scope(self.doc(),p)
    def test_protected_dependency_stops(self):
        p=self.plan();p['scope']['protected']=['do-not-touch-body']
        with self.assertRaises(fw.Paused): fw.require_scope(self.doc(),p)
    def test_warning_acceptance_exact_spec_and_issue(self):
        job={'next':0,'status':'ready'}
        ledger=SimpleNamespace(save=lambda:None)
        issue=[{'state':'warning','name':'Sketch1','message':'lost reference'}]
        with patch.object(fw,'health',return_value=issue):
            with self.assertRaises(fw.Paused):fw.check_health(None,job,ledger,'before_parameters')
            self.assertEqual(job['status'],'warning')
            job['health_approval']={'signature':job['health_pending'],'evidence':'user checked and accepted'}
            fw.check_health(None,job,ledger,'after_parameters')
            job['next']=1
            with self.assertRaises(fw.Paused):fw.check_health(None,job,ledger,'before_parameters')
        job['next']=0
        with patch.object(fw,'health',return_value=[{'state':'error','message':'new error'}]):
            with self.assertRaises(fw.Paused):fw.check_health(None,job,ledger,'after_parameters')

if __name__=='__main__': unittest.main()
