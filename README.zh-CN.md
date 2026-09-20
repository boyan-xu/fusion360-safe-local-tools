# Fusion Safe Local Tools

[English](README.md) | **简体中文**

**中文使用说明 · macOS · Autodesk Fusion · Codex**

一个把“先确认设计要求、保护原模型、可恢复导出”落实到日常操作中的开源插件。由两部分组成：

1. **Codex 技能**：指导助手确认尺寸和修改范围、选择 Fusion API/UI、建立参数关系及检查结果。
2. **Fusion 本地 Add-In**：查看用户参数，执行已确认的参数与导出计划，持久记录累计大小和规格完成状态。

**这是早期版本。它不是 Autodesk 或 OpenAI 的官方产品，也不是装好后就能任意远程控制 Fusion 的 MCP 服务器。** 建模仍需要助手可用的本机 UI/API 执行途径；复杂功能必须按任务验证。

## 能做什么

| 功能 | 当前实现 |
| --- | --- |
| 查看当前设计用户参数 | Fusion 工具栏命令，已实机验证 |
| 参数化建模 | 技能协调已审核的主线程脚本/API/UI；提供参数创建和新增对象命名辅助函数 |
| 草图、尺寸、约束、拉伸 | 独立参数化长方体实机验证，草图最终完全约束 |
| 旋转、放样及其他建模 | 不限制操作方式；尚未逐项实机验收，按实际任务核实 |
| STEP/STL/3MF 导出 | 通用执行器支持整个根组件、单文件输出，已实机验证 |
| 多规格 STEP | 同一设计按确认的参数表达式逐项变更；先验证一个样本再批量 |
| 规格生成 | 十进制范围/步长、取值集合、全部组合或逐项配对；其他规则可生成明确规格列表 |
| 原模型保护 | 默认先建立独立副本；核对文档身份、允许修改的参数及副本来源记录 |
| 警告与失败 | API 健康检查暂停；实际导出失败或无效文件不算完成 |
| 导出大小限制 | 同一对话跨任务累计，严格超过十进制 1 MB 时暂停，用户决定是否保存当前文件 |
| 中断恢复 | 保留临时文件、文件哈希和规格游标，不覆盖已有文件，不跳过失败规格 |
| 导入、复杂副本、Fusion AI | 由技能要求逐任务确认和核实；本地 Add-In 没有通用导入或 AI 按钮 |

## 系统要求

- macOS 上可用的 Autodesk Fusion。实机测试版本：**2705.1.15**；其他版本需要验证 API 兼容性。
- 本地 Add-In 使用 Fusion 自带 Python 和标准库，无需 pip 安装运行依赖。
- 使用对话技能需要支持插件的 Codex 桌面环境，以及实际可用的本机 UI 或 Fusion API 执行途径。
- 命令行规格生成和测试需要 Python **3.10+**；执行器使用 POSIX 文件锁，Windows 未支持。
- 导出目标需支持硬链接的本地文件系统。不支持时会暂停，不会降级为覆盖目标文件。

## 安装

### 1. 获取源码

```sh
git clone https://github.com/boyan-xu/fusion360-safe-local-tools.git
cd fusion360-safe-local-tools
```

没有 Git 也可以使用 GitHub 的 **Code → Download ZIP** 并解压到固定位置。

### 2. 安装 Codex 技能（需要对话协作时）

通过支持插件的 Codex CLI 添加此仓库的 marketplace：

```sh
codex plugin marketplace add boyan-xu/fusion360-safe-local-tools --ref main
codex plugin add fusion360-safe-local-tools@fusion360-safe-local-tools
```

也可以克隆后执行 `codex plugin marketplace add .`，再在插件界面选择本仓库的 marketplace 安装。安装后开启新对话以加载技能。不同客户端版本的插件入口可能不同，参见 [OpenAI 官方插件打包说明](https://developers.openai.com/zh-Hans/plugins/build/plugins)。

**安装 Codex 插件不会自动注册或启动 Fusion Add-In。继续完成下面一步。** 若已有旧的个人 marketplace 版本，避免同时启用两个相同技能版本。

### 3. 注册 Fusion 本地 Add-In

推荐直接注册克隆目录中的文件夹，方便维护单一安装：

1. 打开 Fusion，进入 Design 工作环境。
2. 打开 **Utilities → Add-Ins → Scripts and Add-Ins**（名称随版本/语言略有差异）。
3. 在 Add-Ins 页添加已有插件，选择以下**文件夹**：

   ```text
   plugins/fusion360-safe-local-tools/assets/FusionSafeLocalTools
   ```

4. 选择 `FusionSafeLocalTools`，点击 **Run**。
5. 保持 **Run on Startup** 关闭。
6. 在 **Utilities → Safe Local Tools** 查找两个命令：
   - `Inspect User Parameters`
   - `Run Confirmed Export Plan`

仅注册源码目录这一份即可，不要再运行下面的复制安装方式。

可选的标准目录安装方式：

```sh
sh plugins/fusion360-safe-local-tools/scripts/install-macos.sh
```

它复制到 `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/FusionSafeLocalTools`，若目录已经存在则拒绝覆盖。复制后仍需在 Fusion 中手动 Run。

## 怎么使用

### 对话建模

向助手描述目标、尺寸、约束和修改范围，例如：

> 在新的设计里建一个长方体，长 20 mm、宽 10 mm、高 5 mm。创建三个可调整参数，沿用当前显示单位和精度。现在只建模，不导出。

助手先检查 Fusion 和当前设计，再针对缺失的重要条件询问。不要把示例当作对实际模型的授权。草图、拉伸、旋转等根据任务选择，不能为了“自动完成”猜公差、间隙或缺失尺寸。

修改已有模型默认在真正独立的副本中进行；副本应保留所需的参数、时间轴和引用语义。**执行器不会自动创建副本，也不能凭一个名称保证副本正确。** 云端复制/保存可能上传数据，必须先说明并获同意。

新增实体、草图及特征名称后加 ` (ChatGPT)`；新增参数使用 `_ChatGPT`，例如 `length_ChatGPT`。不会为了标记而重命名已有内容。用户可以明确要求在指定范围移除标记。

### 多规格导出

例如：

> 在已确认的副本上，把 length_ChatGPT 从 20 mm 到 40 mm，每次增加 5 mm，包含两端；其他参数不变。导出整个根组件为 STEP，文件名 block-{index}.step，位置是我指定的本地文件夹。先验证第一份样本。

助手应确认受影响范围、规格规则、数量、顺序、文件名、几何范围及路径，再生成计划。大量规格不需要逐项手工列出；有歧义时不能自行选解释。

在 Fusion 点击 **Run Confirmed Export Plan**，选择已经确认的 JSON 计划。第一份成功后暂停，实际检查其尺寸和结构，再记录样本验证，继续运行同一计划。

普通用户不需要手写 JSON。需要自行集成时参见 [计划结构与恢复命令](plugins/fusion360-safe-local-tools/skills/fusion360-safe-local-tools/references/export-workflow.md) 和 [操作示例](docs/WORKFLOW.md)。

### 1 MB 暂停规则

- **1 MB = 1,000,000 字节**。同一对话中的不同计划、不同格式共用一份账本，不能每个文件或每次任务清零。
- 恰好达到阈值不暂停，**严格超过**才暂停。文件先在临时位置生成，报告当前文件和含待确认文件的累计大小。
- 用户同意保存后提交文件，下一阈值从当时累计量再加 1 MB。单个文件 5 MB 也只问一次。
- 用户不同意则只删当前待确认文件；对应规格仍未完成，之后继续会重新生成同一规格。
- “继续”不等于永久取消限制。只有明确要求取消，才关闭限制。

### 黄色警告和红色报错

发现警告/报错先停下，用户检查后明确接受并同意继续才恢复。许可只对应当前规格的相同警告；新的问题仍然暂停。即使用户接受警告，Fusion 实际导出失败也不能算成功。

## 数据和权限边界

- 插件本身不联网、不上传设计、不启动监听端口、不自动调用 Fusion AI。
- 技能要求导入、导出、建模分别获得适用授权。外部上传必须说明数据、接收方和用途。
- **这些规则由助手和本地工作流共同执行，不是系统安全隔离。** JSON 中的 confirmation/evidence 是实际决定的记录，程序不能证明它们来自用户。不要运行陌生人给出的未经审核计划。
- 通用执行器只支持整个根组件导出。涉及受保护区域的参数联动会保守拒绝，需专项依赖和不变量检查，不应通过清空保护名单绕过。
- 文件结构和非空检查不等于复杂几何正确。样本、关键尺寸与受保护内容需要实测，必要时在授权后回读文件。
- 不应同时由多个程序写同一对话账本，也不能用新账本绕过累计量。丢失或损坏时先恢复记录。
- 人工操作、其他插件和外部工具不能被本插件拦截。

## 更新、卸载与故障排查

更新前停止 Fusion Add-In 并备份现有插件目录；拉取新代码后手动运行，检查两个命令。不要在运行过程中替换模块。Codex 技能更新后按客户端方式重新安装/刷新，再开始新对话。

卸载时先在 Fusion 中 **Stop**。外部注册方式只移除注册链接；标准目录副本可使用：

```sh
sh plugins/fusion360-safe-local-tools/scripts/uninstall-macos.sh
```

它把核验过的插件目录移到废纸篓，不永久删除。卸载 Fusion Add-In 和卸载 Codex 技能是两件事。

| 遇到的问题 | 处理方法 |
| --- | --- |
| 工具栏没有命令 | 确认处于 Design，插件已 Run，目录内有同名 `.py`、`.manifest` 及辅助模块 |
| 系统 Python 提示没有 `adsk` | Fusion API 脚本只能在 Fusion 内执行；系统 Python 只运行规格/账本工具及单元测试 |
| 当前设计不一致 | 重新核对 creationId 和目标副本，不要随意改计划绕过检查 |
| 副本来源未验证 | 先真实复制并检查参数/引用，再调用登记辅助函数；不能伪造副本标记 |
| 文件已存在 | 程序拒绝覆盖；确认是否为上次完成项或另一个文件，调整方案后再执行 |
| 有 pending 文件 | 先运行账本 status，按实际状态批准、拒绝或恢复，不另开计划跳过去 |
| Fusion 重启后文档身份变化 | 核实重开的设计和已完成文件，确认修订计划，保留同一累计账本 |
| 文件系统不支持硬链接 | 改用经确认的本地支持目录；不要手动绕过无覆盖提交 |

## 验证与贡献

```sh
python3 -m unittest discover -s plugins/fusion360-safe-local-tools/tests -v
python3 -m compileall -q plugins/fusion360-safe-local-tools
```

当前 17 项测试覆盖大小边界、跨计划累计、拒绝/继续、样本门槛、崩溃恢复、原模型范围及警告许可。它们不需要运行 Fusion。

macOS/Fusion 实机检查覆盖：参数化长方体、约束、命名、STEP 两个规格、STL/3MF、命令加载及停止/重启。尚未实测旋转、放样、复杂装配副本、全部导入格式和 Fusion AI。真实用户模型始终需要独立验收。

提交问题时请说明 macOS/Fusion 版本、可复现步骤及脱敏错误信息；不要默认附上私人模型、绝对路径、账号或对话账本。贡献请参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 仓库结构

```text
.agents/plugins/marketplace.json    Codex marketplace 入口
plugins/fusion360-safe-local-tools/
  .codex-plugin/plugin.json         Codex 插件清单
  assets/FusionSafeLocalTools/      Fusion 本地 Add-In 和工作流代码
  skills/                          对话操作规则和接口说明
  scripts/                         安装/卸载、规格展开和账本命令
  tests/                           不依赖 Fusion 的单元测试
docs/WORKFLOW.md                    可运行的规格示例与恢复说明
LICENSE                            MIT 许可证
```

Copyright © 2026 boyan-xu。按 [MIT License](LICENSE) 开源。Autodesk Fusion、OpenAI、ChatGPT 和 Codex 为各自所有者的名称/商标；本项目无官方隶属或认可关系。
