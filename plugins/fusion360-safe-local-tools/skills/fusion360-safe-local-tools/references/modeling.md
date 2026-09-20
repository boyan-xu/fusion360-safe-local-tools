# 建模与接口

## 执行途径

插件包含运行于 Fusion 的 `assets/FusionSafeLocalTools/fusion_workflow.py`，以及不依赖 Fusion 的 `workflow.py`。前者必须在 Fusion 主线程导入，不能在系统 Python 中执行建模。

通过 Scripts and Add-Ins 运行本地审查脚本时，用脚本目录中的标准 Fusion 入口 `run(context)`。可将插件的 assets 父目录加入脚本导入路径，`from FusionSafeLocalTools import fusion_workflow`，调用已核实的 Fusion API。UI 自动化只用当前已提供的电脑使用工具。没有现成 MCP 连接不是偷偷添加网络服务的理由。

`active_design(expected_id)` 检查目标文档；`inventory` 读取单位、参数和健康状态；`create_parameter` 不覆盖同名参数；`mark_created` 只处理操作后新增对象。建模脚本须逐任务设计并核对，不接受未经审查的任意脚本输入。草图的几何约束和尺寸仍需脚本显式建立，不把画出的外形当成完全约束。

## 复制已有设计

首选真正独立的设计副本，保留参数、时间轴和引用语义。不能拿 STEP 导出后导入代替参数化副本。

- 本地 F3D 归档/重新导入可用于已核实的无外部引用设计，但必须先有归档导出和重新导入授权，执行大小限制；归档不是自动豁免的文件。
- 有外部引用、装配依赖、配置设计时检查 Fusion 当前支持的副本方式；无法确保独立性时暂停。不得自动 break link、替换引用或云端复制。
- 云端另存为/复制可能上传设计。按照主技能说明数据、目的地和用途，取得同意再做。
- 副本建立后比对参数表达式、组件/实体、时间轴和受保护内容。确认源文档未修改。调用 `register_working_copy(source_doc, copy_doc, evidence)` 记录来源。该标记是已完成验证的记录，不能用来把任意文档伪装为副本。

## 建模范围与保护

复杂约束、旋转、放样、布尔运算、装配操作等按当前 API 和用户需求生成专项脚本；不要把已提供的批量参数接口当成整个插件能力边界。受保护内容不能只比较名称、外包围盒或体积，这些相同不保证拓扑和特征没变。需要明确的不变量和依赖分析，不能验证就向用户说明并暂停。

如需去掉 ChatGPT 后缀，对用户指定对象精确匹配，用户参数及模型参数引用交由 Fusion 处理并重算核实。不要去掉旧内容中本就存在的相似字符串。

## 格式核实

本机 API 定义位于 `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Python/defs/adsk/`。根据安装版本检查，不把示例版本当作本机接口。

已查到的入口：ExportManager 的 `createSTEPExportOptions(filename, geometry)`、`createSTLExportOptions(geometry, filename)`、`createC3MFExportOptions(geometry, filename)`。创建 Options 不会生成文件，必须执行 `execute` 并验证。

STEP/F3D 可使用 ImportManager 的 `createSTEPImportOptions` / `createFusionArchiveImportOptions` + `importToNewDocument`。STL 网格导入可检查 `MeshBodies.add`；3MF 导入是否有适用 API 必须另行验证，不能把 3MF 导出支持当成导入支持，可核实 UI 路径。

来源：[Autodesk ExportManager](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_ExportManager.htm)、[Import 示例](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ImportManager_Sample.htm)、[Document.creationId](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Document_creationId.htm)。
