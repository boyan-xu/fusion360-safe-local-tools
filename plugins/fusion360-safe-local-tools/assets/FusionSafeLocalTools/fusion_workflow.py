"""Fusion main-thread adapters. Import from a reviewed task script or toolbar command."""
import contextlib
import json
import math
from pathlib import Path
import adsk.core
import adsk.fusion
from .workflow import Ledger, Paused, marked, atomic_json

GROUP = 'ChatGPT_SafeTools'


def active_design(expected_id=None):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not doc or not design:
        raise Paused('请先打开并确认目标 Fusion Design 文档')
    if expected_id and doc.creationId != expected_id:
        raise Paused('当前设计与确认的目标设计不一致')
    return app, doc, design


def health(design):
    issues = []
    for i in range(design.timeline.count):
        obj = design.timeline.item(i)
        if obj.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            issues.append({'index':i,'name':obj.name,'state':str(obj.healthState),'message':obj.errorOrWarningMessage})
    for comp in design.allComponents:
        for sketch in comp.sketches:
            if sketch.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
                issues.append({'name':sketch.name,'state':str(sketch.healthState),'message':sketch.errorOrWarningMessage})
    return issues


def inventory(design):
    return {'document_id':design.parentDocument.creationId,
            'document_name':design.parentDocument.name,
            'length_unit':design.unitsManager.defaultLengthUnits,
            'parameters':{p.name:{'expression':p.expression,'value':p.value,'unit':p.unit} for p in design.userParameters},
            'health':health(design),
            'components': [{'name':c.name,'bodies':[b.name for b in c.bRepBodies]} for c in design.allComponents]}


def named_objects(design):
    objects = list(design.allComponents) + list(design.allParameters)
    for comp in design.allComponents:
        objects += list(comp.sketches) + list(comp.bRepBodies) + list(comp.features)
    return objects


@contextlib.contextmanager
def mark_created(design):
    """Use only inside an already approved modeling scope; never relabel old objects."""
    old = {o.entityToken for o in named_objects(design)}
    try:
        yield
    finally:
        for obj in named_objects(design):
            if obj.entityToken not in old:
                is_param = bool(adsk.fusion.Parameter.cast(obj))
                obj.name = marked(obj.name, is_param)
                if hasattr(obj, 'attributes'):
                    obj.attributes.add(GROUP, 'created_by', 'ChatGPT')
        # Timeline names follow their entities; mark distinct new timeline items too.


def create_parameter(design, name, expression, unit, comment=''):
    name = marked(name, True)
    if design.allParameters.itemByName(name):
        raise Paused('同名参数已存在，不自动修改：' + name)
    p = design.userParameters.add(name, adsk.core.ValueInput.createByString(expression), unit, comment)
    if not p:
        raise RuntimeError('Fusion 创建参数失败')
    return p


def register_working_copy(source_doc, copy_doc, evidence):
    """Call only after making and verifying a real independent design copy."""
    if not evidence.strip() or source_doc.creationId == copy_doc.creationId:
        raise Paused('未验证独立副本')
    copy_doc.attributes.add(GROUP, 'copy_source', source_doc.creationId)
    copy_doc.attributes.add(GROUP, 'copy_verification', evidence)


def require_scope(doc, plan):
    scope = plan['scope']
    if scope.get('target_id') != doc.creationId or not scope.get('impact_review'):
        raise Paused('目标设计或关联影响尚未确认')
    mode = scope.get('mode')
    if mode == 'original':
        if not scope.get('original_edit_confirmation'):
            raise Paused('没有修改原设计的明确授权')
    elif mode == 'copy':
        marker = doc.attributes.itemByName(GROUP, 'copy_source')
        if not marker or marker.value != scope.get('source_id') or marker.value == doc.creationId:
            raise Paused('请先创建并验证独立副本，禁止直接修改原设计')
    elif mode == 'new':
        if not scope.get('new_design_confirmation'):
            raise Paused('尚未确认新建设计归属')
    else:
        raise Paused('修改范围必须明确为 copy/new/original')
    if 'protected' not in scope or 'parameters' not in scope:
        raise Paused('必须明确允许修改的参数及受保护内容')
    # Automatic parameter changes can affect arbitrarily distant geometry. Do not pretend
    # a bounding-box comparison proves protected topology unchanged.
    if scope['protected'] and any(s['parameters'] for s in plan['specs']):
        raise Paused('存在受保护部分：需先通过专项脚本验证不变量，本通用批量执行器不自动更改参数')
    for spec in plan['specs']:
        if not set(spec['parameters']) <= set(scope['parameters']):
            raise Paused('规格包含未授权修改的参数')


def check_health(design, job, ledger, stage):
    issues = health(design)
    if issues:
        approval = job.get('health_approval')
        signature = {'index':job['next'],'issues':issues}
        if not approval or approval['signature'] != signature:
            job['health_pending'] = signature
            job['status'] = 'warning'
            ledger.save()
            raise Paused('发现黄色警告/红色报错，已暂停。请检查模型并明确决定是否继续。\n' + json.dumps(issues,ensure_ascii=False))
    return issues


def export_options(design, fmt, filename, settings):
    manager = design.exportManager
    root = design.rootComponent
    if fmt == 'step':
        if settings != {}:
            raise ValueError('STEP 不接受未经核实的额外选项')
        return manager.createSTEPExportOptions(str(filename), root)
    if set(settings) != ({'refinement','unit','binary'} if fmt == 'stl' else {'refinement'}):
        raise Paused('网格导出需要明确 refinement；STL 还需要 unit 和 binary')
    refinements = {'low':adsk.fusion.MeshRefinementSettings.MeshRefinementLow,
                  'medium':adsk.fusion.MeshRefinementSettings.MeshRefinementMedium,
                  'high':adsk.fusion.MeshRefinementSettings.MeshRefinementHigh}
    if settings['refinement'] not in refinements:
        raise ValueError('refinement 必须是 low/medium/high')
    options = manager.createSTLExportOptions(root,str(filename)) if fmt == 'stl' else manager.createC3MFExportOptions(root,str(filename))
    options.sendToPrintUtility = False
    options.isOneFilePerBody = False
    options.meshRefinement = refinements[settings['refinement']]
    if fmt == 'stl':
        units = {'mm':adsk.fusion.DistanceUnits.MillimeterDistanceUnits,
                 'cm':adsk.fusion.DistanceUnits.CentimeterDistanceUnits,
                 'm':adsk.fusion.DistanceUnits.MeterDistanceUnits,
                 'in':adsk.fusion.DistanceUnits.InchDistanceUnits,
                 'ft':adsk.fusion.DistanceUnits.FootDistanceUnits}
        if settings['unit'] not in units or not isinstance(settings['binary'],bool):
            raise ValueError('STL 单位或二进制选项无效')
        options.unitType = units[settings['unit']]
        options.isBinaryFormat = settings['binary']
    return options


def run_plan(plan_path):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    # A stable per-conversation sibling ledger; plans in this conversation must share it.
    ledger_path = Path(plan['ledger_path']).resolve()
    app, doc, design = active_design(plan['scope']['target_id'])
    require_scope(doc, plan)
    if plan.get('geometry') != 'root_component':
        raise Paused('此通用执行器只支持已确认的整个根组件；局部导出需专项脚本')
    with Ledger(ledger_path, plan['conversation_id']).locked() as ledger:
        job = ledger.add_job(plan)
        if ledger.data['pending']:
            raise Paused('账本有待处理文件：\n' + json.dumps(ledger.report(),ensure_ascii=False,indent=2))
        while job['next'] < len(plan['specs']):
            if job['status'] != 'ready':
                raise Paused('任务已暂停：' + job['status'])
            if job['next'] > 0 and not job['sample_verified']:
                return '首个样本已生成。检查实际尺寸、结构及文件后，确认样本再继续。'
            active_design(plan['scope']['target_id'])
            check_health(design, job, ledger, 'before_parameters')
            spec = plan['specs'][job['next']]
            expected = {}
            for name, expr in spec['parameters'].items():
                p = design.userParameters.itemByName(name)
                if not p or not design.unitsManager.isValidExpression(expr, p.unit):
                    raise Paused('参数不存在或表达式无效：' + name)
                expected[name] = expr
            try:
                for name, expr in spec['parameters'].items():
                    design.userParameters.itemByName(name).expression = expr
                if spec['parameters'] and not design.computeAll():
                    raise RuntimeError('Fusion 重算失败')
                check_health(design, job, ledger, 'after_parameters')
                for name, expression in expected.items():
                    value = design.unitsManager.evaluateExpression(expression, design.userParameters.itemByName(name).unit)
                    if not math.isclose(design.userParameters.itemByName(name).value,value,rel_tol=1e-9,abs_tol=1e-9):
                        raise RuntimeError('实际参数与确认值不一致：' + name)
                if not any(c.bRepBodies.count for c in design.allComponents):
                    raise RuntimeError('设计没有 BRep 实体，未生成有效规格')
                temp = ledger.begin(plan['job_id'])
                options = export_options(design,plan['format'],temp,plan['settings'])
                if not options or not design.exportManager.execute(options):
                    raise RuntimeError('Fusion 导出失败')
                check_health(design, job, ledger, 'after_export')
                report = ledger.produced({'parameters':inventory(design)['parameters'],'health':health(design),
                                          'validation':'Fusion export success + file structure; sample geometry review required'})
                if report['pending']:
                    return '超过累计大小阈值，已暂停；等待用户决定是否保存。\n' + json.dumps(report,ensure_ascii=False,indent=2)
            except Paused:
                raise
            except Exception as e:
                ledger.fail(plan['job_id'],str(e))
                raise
        return '计划全部完成。\n' + json.dumps(ledger.report(),ensure_ascii=False,indent=2)


def select_plan():
    ui = adsk.core.Application.get().userInterface
    dialog = ui.createFileDialog()
    dialog.title = '选择已经确认的导出计划 JSON'
    dialog.filter = 'JSON (*.json)'
    if dialog.showOpen() == adsk.core.DialogResults.DialogOK:
        try:
            ui.messageBox(run_plan(dialog.filename),'ChatGPT 导出工作流')
        except Exception as e:
            ui.messageBox(str(e),'ChatGPT 导出暂停')
