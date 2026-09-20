# 规格生成与暂停恢复示例

以下示例只生成规格列表，不创建或修改任何模型，不导出 CAD 文件。

在仓库根目录创建临时工作目录：

```sh
mkdir -p work
```

将下列内容保存为 `work/rules.json`：

```json
{
  "rules": {
    "length_ChatGPT": {"start":"20","stop":"40","step":"5","unit":"mm"},
    "width_ChatGPT": {"values":["10 mm","15 mm"]}
  },
  "combination":"product",
  "filename_template":"block-{index}.step"
}
```

```sh
python3 plugins/fusion360-safe-local-tools/scripts/expand_specs.py work/rules.json work/specs.json
```

结果为 10 个规格，长度轴按 20、25、30、35、40 mm 排列，宽度轴在每个长度下按 10、15 mm 排列。`zip` 表示逐项配对，要求各集合长度相同。范围包含两端，步长不能精确到达终点时会拒绝，避免悄悄舍弃尾端。表达式不会作为 Python 代码执行。

这只解决规格生成；真正导出前仍需确认目标设计/副本、参数关联影响、输出路径、格式与选项，随后整理完整计划。完整格式见 [导出工作流参考](../plugins/fusion360-safe-local-tools/skills/fusion360-safe-local-tools/references/export-workflow.md)。

## 查看状态

替换为该对话已经使用的稳定 ID 和账本位置。不要为恢复工作而新建账本：

```sh
python3 plugins/fusion360-safe-local-tools/scripts/export_ledger.py status \
  --ledger /absolute/task/work/fusion-export-ledger.json \
  --conversation ACTUAL_CONVERSATION_ID
```

账本报告 `saved_bytes`、`pending_bytes`、`cumulative_with_pending` 和 `next_threshold`。多个计划共用这一份记录。

## 记录实际决定

文件 `work/decision.txt` 应写入用户的真实决定，或样本检查的真实结果。不要复制例句来伪造批准。

```sh
python3 plugins/fusion360-safe-local-tools/scripts/export_ledger.py approve-file \
  --ledger /absolute/task/work/fusion-export-ledger.json \
  --conversation ACTUAL_CONVERSATION_ID \
  --evidence-file work/decision.txt
```

| action | 使用条件 |
| --- | --- |
| `verify-sample --job JOB_ID` | 已实测首样本，记录尺寸、结构和文件检查依据 |
| `approve-file` | 用户明确同意保存当前超限文件 |
| `reject-file` | 用户拒绝保存当前已验证临时文件；规格不前进 |
| `resume --job JOB_ID` | 用户要求继续，且没有未处理 pending；不重置累计阈值 |
| `accept-health --job JOB_ID` | 用户检查后明确接受当前规格的具体警告并同意继续 |
| `discard-incomplete` | 已确认如何处理未验证的中断/失败临时文件；不是跳过该规格 |
| `cancel-size-limit` | 用户明确取消大小限制；单说“继续”不适用 |

批准文件只提交该文件；处理后回到 Fusion，再运行**同一份**计划继续。失败/拒绝规格仍然在原位置。若临时文件、实际参数或目标设计无法核实，先暂停诊断。

提交阶段中断时，不应盲目调用 `approve-file` 创建新许可；先确认账本保存了先前批准，再以该批准恢复已有提交。目标路径若不是同一临时文件的硬链接，程序会拒绝覆盖。

## 重要限制

- 只允许已明确授权的用户参数变更；模型参数和受保护不变量需要专项处理。
- 通用执行器仅导出根组件整体。局部实体、装配引用或不支持格式需核实另一路径。
- 同一计划保持不可变。需求改变时先核对已完成规格和关联影响，确认修订方案；保留原累计账本。
- 文件校验是结构和参数层面的检查，不是对所有 CAD 几何的正确性证明。
