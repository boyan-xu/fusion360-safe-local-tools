# 导出计划与恢复

## 计划由助手整理

不要让用户填写 JSON。先读活动设计，确认尺寸、规则、范围及文件输出，再由助手写计划。`confirmation` 和各类 `evidence` 必须来自实际用户指示/实际验证，不是绕过确认的布尔开关。该程序只约束经过它的导出，助手通过 UI 或专项脚本操作时仍必须遵守全部规则。

每个对话在固定 `work/fusion-export-ledger.json` 使用同一账本。当前工作目录变化时保留原绝对路径。`job_id` 是每份已确认计划的稳定 ID；恢复使用相同计划，不能修改它或换 ID 重跑已完成规格。

计划结构（值须用真实确认结果替换）：

```json
{
  "conversation_id": "实际对话ID",
  "ledger_path": "/当前任务/work/fusion-export-ledger.json",
  "job_id": "本次已确认计划ID",
  "confirmation": "用户确认依据",
  "unresolved": [],
  "scope": {
    "mode": "copy",
    "source_id": "源文档creationId",
    "target_id": "副本creationId",
    "parameters": ["length_ChatGPT"],
    "protected": [],
    "impact_review": "已核实长度只影响已授权区域的依据"
  },
  "geometry": "root_component",
  "format": "step",
  "settings": {},
  "output_dir": "/用户确认且已存在的输出目录",
  "specs": [
    {"id": "1", "parameters": {"length_ChatGPT": "20 mm"}, "filename": "size-20.step"},
    {"id": "2", "parameters": {"length_ChatGPT": "30 mm"}, "filename": "size-30.step"}
  ]
}
```

`copy` 需要真正创建的独立副本及 `register_working_copy` 验证记录。`original` 额外需要 `original_edit_confirmation`；`new` 需要 `new_design_confirmation`。`protected` 非空且需要改参数时通用执行器保守拒绝；使用逐任务验证的专用脚本完成，不得清空 protected 绕过。

STEP settings 为 `{}`。STL 必须明确 `{"refinement":"high","unit":"mm","binary":true}` 等实际选项；3MF 为 `{"refinement":"high"}`。refinement 可用 low/medium/high，单位需核实，不自动统一。通用执行器仅支持整个根组件、单文件输出，禁止自动发送到打印软件。

取值规则示例：

```json
{
 "rules": {
   "length_ChatGPT": {"start":"10", "stop":"30", "step":"5", "unit":"mm"},
   "width_ChatGPT": {"values":["5 mm", "10 mm"]}
 },
 "combination":"product",
 "filename_template":"size-{index}.step"
}
```

`expand_specs.py rules.json specs.json` 只展开并汇报数量，不批准也不执行导出。product 为全部组合，zip 为逐项配对且列表长度必须相等。范围包含端点；终点无法被步长精确到达时拒绝并询问。文件名支持 `{index}` 和参数名，拒绝重名和路径穿越。其他组合规则可明确生成 specs，不受这两个快捷规则限制。

## 执行

Fusion 手动运行插件后，通过 Utilities > Safe Local Tools > **Run Confirmed Export Plan** 选择计划，或在已审查的 Fusion 主线程脚本调用 `fusion_workflow.run_plan(path)`。插件不会自动执行目录里的计划，没有后台监听。

首个文件完成后停止，检查样本真实尺寸、结构、参数与文件有效性，记录验证后再调用执行器。失败和警告不会前进规格游标。

## 决定和恢复命令

`python3 scripts/export_ledger.py ACTION --ledger ABS_PATH --conversation ID [--job JOB_ID] [--evidence-file UTF8_FILE]`

- `status`：读取累计量、pending、完成状态。
- `verify-sample`：实际检查样本后记录验证依据；需要 job。
- `approve-file`：用户同意保存超限文件后提交，重设下一暂停阈值。不能因“继续”而永久解除限制。
- `reject-file`：用户拒绝保存，删除该临时文件，规格未完成，任务暂停。
- `resume`：用户要求继续后恢复任务；需要 job，不重置累计量和大小限制。
- `accept-health`：用户检查模型后明确接受对应警告并继续；需要 job。只接受本规格记录的警告；新警告仍暂停。
- `discard-incomplete`：诊断中断/失败后丢弃未通过验证的临时输出，不前进规格；后续 resume 重试同一规格。不要用于拒绝后偷偷跳过。
- `cancel-size-limit`：只有用户明确取消累计限制才使用。

每次写操作都要求 evidence-file。助手不能把自己的判断写成用户批准。样本检查可以记录实际验证结果；警告接受、超限文件保存/删除与限制取消必须引用用户决定。

中断时先读取账本：

- `exporting`：文件可能不存在、部分生成或已生成但未记录。核对实际参数/几何和文件，能证明正确才调用 `produced`；否则报告并丢弃未验证临时输出，再从同一规格恢复。
- `validated`：文件和参数已核验，若超限先等用户决定。
- `committing`：读取已记录的批准，在哈希和硬链接身份一致时恢复提交；不用再次生成文件。
- 已完成项：核对文件存在及哈希；若文件被外部改动/删除，说明异常并询问，不能默默重新生成或把它算成功。

文件采用同目录临时文件及无覆盖硬链接提交。目标目录须是支持硬链接的本地文件系统；不支持时会暂停，不退化为可能覆盖旧文件的复制。未保存的副本意外关闭后不能只靠旧 creationId 恢复：重新建立/核实副本，与用户确认修订计划，保留同一对话累计账本和已完成记录。

## 验证边界

代码检查 Fusion 导出返回值、实际参数值、可见 API 健康状态和文件结构，并记录 SHA-256。这不等于通用 CAD 语义解析器：结构合法不保证复杂几何正确。首样本以及任务要求的重要不变量必须实测；必要时在得到导入授权后回读文件检查。现场 UI 出现 API 未覆盖的警告同样必须暂停。
