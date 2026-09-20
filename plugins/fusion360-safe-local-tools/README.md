# Fusion 360 Safe Local Tools

根据用户确认的要求在 Fusion 中建模、处理参数和导入导出。包含 Codex 操作技能、Fusion 主线程适配器和可恢复的导出账本，不启动网络服务。

## 使用

在 Codex 对话中描述建模或修改要求。助手先读当前设计、单位和参数，确认影响结果的缺失条件；默认保护已有模型并在已验证的独立副本上修改。建模不会自动触发导出。

Fusion 手动运行 `FusionSafeLocalTools` 后，在 Utilities > Safe Local Tools 使用：

- **Inspect User Parameters**：只读查看活动设计参数。
- **Run Confirmed Export Plan**：加载助手依据已确认要求生成的计划，执行参数变更和 STEP/STL/3MF 导出。

批量先验证样本，再继续。默认按同一对话每新增超过十进制 1 MB 暂停，用户决定待确认文件是否保存。警告/报错暂停，失败不算完成，恢复不漏规格。规格支持范围、步长、集合和组合规则。

操作规则在 `skills/fusion360-safe-local-tools/SKILL.md`；导出计划格式、恢复命令在其 `references/export-workflow.md`。`scripts/expand_specs.py` 展开规则；`scripts/export_ledger.py` 管理暂停和用户决定。请勿伪造 confirmation/evidence，也不要通过新账本绕过累计限制。

## 能力边界

- 通用导出执行器支持整个根组件 STEP/STL/3MF，以及已授权用户参数表达式调整。
- 草图、约束、拉伸、旋转、放样等由技能按任务选择已核实的 API/UI 或专项脚本，不是固定按钮清单。接口和几何结果都需实际验证。
- 存在受保护区域且需要更改参数时，通用执行器暂停，要求专项依赖/不变量验证，不以包围盒和体积相同冒充没有改变。
- 副本必须真正独立且验证；不会未经确认自动上传云端、断开引用或导入文件。
- 文件校验包括 Fusion 执行结果、参数核对、健康检查、格式结构和 SHA-256；并非通用 CAD 语义解析器。首样本和关键尺寸必须实测。
- 插件不能拦截用户手动操作或其他插件的导出；Codex 所有导出路径必须遵守同一技能和账本。

## 安装/更新

优先将单一 `assets/FusionSafeLocalTools` 目录注册为外部插件。已注册时更新同一路径，不重复安装。保留备份，停止旧插件，更新文件后手动 Run；保持 Run on Startup 关闭。

标准 AddIns 安装脚本仅用于不存在的目标目录，拒绝覆盖；卸载前先停止，外部注册先 unlink。不要混用标准副本与外部注册。

## 测试

`python3 -m unittest discover -s tests -v`

纯 Python 测试覆盖大小边界、跨计划累计、拒绝/继续、首样本、文件冲突、无效文件、崩溃恢复、精确十进制规则。安装步骤、实机验证范围与已知限制见[仓库使用说明](../../README.md)；不要把单元测试当作 Fusion 实机验证。
