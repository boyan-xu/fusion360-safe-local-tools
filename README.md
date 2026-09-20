# Fusion Safe Local Tools

**English** | [简体中文](README.zh-CN.md)

**macOS · Autodesk Fusion · Codex**

Local tools for modeling from confirmed requirements, protecting existing designs, and exporting parameter variants with a resumable workflow.

The project includes a **Codex skill** for clarifying dimensions, scope and modeling operations, and a **Fusion add-in** for inspecting user parameters and executing confirmed export plans.

This is an early version, not an official Autodesk or OpenAI product. It does not include a general-purpose MCP server. Modeling requires an available local UI or Fusion API execution route; complex operations must be verified for each task.

## Capabilities

| Feature | Current support |
| --- | --- |
| User parameters | Inspection command and helpers for creating and updating confirmed parameters |
| Parametric modeling | Skill-guided API/UI operations; a fully constrained parametric block and extrusion were tested in Fusion |
| Revolves, lofts and other modeling | Supported by the workflow when APIs are available; not individually tested |
| STEP, STL and 3MF export | Whole root component to a single file; tested in Fusion |
| Multiple variants | Decimal ranges, steps, value sets, Cartesian products and pairwise combinations |
| Design protection | Verified independent working copies by default; document identity and modification-scope checks |
| Export recovery | Persistent size totals, temporary files, hashes and variant completion records |
| Warnings and errors | Pause for inspection; failed exports never count as completed variants |
| Imports, complex copies and Fusion AI | Require task-specific confirmation and verification; no generic import or AI button |

## Requirements

- Autodesk Fusion on macOS. Tested version: **2705.1.15**; verify compatibility for other versions.
- The add-in uses Fusion's bundled Python and standard library, with no pip runtime dependencies.
- Conversational use requires Codex plugin support and an available local UI or Fusion API execution route.
- CLI utilities and tests require **Python 3.10+**. POSIX file locks are used; Windows is not supported.
- Export destinations must support hard links. Unsupported destinations cause a pause rather than an overwrite fallback.

## Installation

### 1. Get the source

```sh
git clone https://github.com/boyan-xu/fusion360-safe-local-tools.git
cd fusion360-safe-local-tools
```

Alternatively, use **Code → Download ZIP** and extract it to a permanent location.

### 2. Install the Codex skill

With a Codex CLI version that supports plugins:

```sh
codex plugin marketplace add boyan-xu/fusion360-safe-local-tools --ref main
codex plugin add fusion360-safe-local-tools@fusion360-safe-local-tools
```

You can also run `codex plugin marketplace add .` from the cloned repository, then install from this marketplace in the plugin interface. Start a new conversation after installation. Avoid enabling an older personal-marketplace copy of the same skill at the same time.

**Installing the Codex plugin does not register or start the Fusion add-in. Complete the next step.**

### 3. Register the Fusion add-in

1. Open Fusion and enter the Design workspace.
2. Open **Utilities → Add-Ins → Scripts and Add-Ins**. Labels may vary by version or language.
3. On the Add-Ins tab, add an existing add-in and select this **folder**:

   ```text
   plugins/fusion360-safe-local-tools/assets/FusionSafeLocalTools
   ```

4. Select `FusionSafeLocalTools` and click **Run**. Leave **Run on Startup** off.
5. Under **Utilities → Safe Local Tools**, check for **Inspect User Parameters** and **Run Confirmed Export Plan**.

Alternatively, copy the add-in into the standard directory:

```sh
sh plugins/fusion360-safe-local-tools/scripts/install-macos.sh
```

This installs to `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/FusionSafeLocalTools`, refuses to overwrite an existing directory, and still requires clicking Run in Fusion. Use one installation method, not both.

## Usage

### Modeling

Describe the goal, dimensions, constraints and permitted changes. For example:

> In a new design, create a block 20 mm long, 10 mm wide and 5 mm high. Create three adjustable parameters and preserve the current display units and precision. Model only; do not export yet.

The assistant checks Fusion and the current design, then asks about missing conditions that affect the result. It must not guess dimensions, clearances or tolerances. Examples do not authorize changes to real designs.

Existing models are modified in a verified independent copy by default, preserving the required parameters, timeline and reference behavior. **The executor does not create copies automatically.** A name alone cannot prove independence. Cloud copy/save operations may upload data and require prior explanation and consent.

New bodies, sketches and features receive ` (ChatGPT)`; new parameters use `_ChatGPT`, such as `length_ChatGPT`. Existing content is not renamed to add labels. Users may request label removal within a specified scope.

### Exporting variants

> In the confirmed working copy, vary length_ChatGPT from 20 mm through 40 mm in 5 mm steps, including both endpoints. Keep other parameters unchanged. Export the whole root component as STEP to my specified local folder, using block-{index}.step. Validate the first sample before continuing.

Confirm the affected scope, generation rules, count, order, filenames, geometry scope and destination before preparing the plan. Large batches do not require manually listing every variant, but ambiguous rules must be clarified.

In Fusion, click **Run Confirmed Export Plan** and select the confirmed JSON plan. After the first successful file, check its actual dimensions and structure, record sample validation, then run the same plan again. The assistant can prepare JSON plans; users do not need to write them manually.

Detailed integration references are currently in Chinese: [plan format and recovery](plugins/fusion360-safe-local-tools/skills/fusion360-safe-local-tools/references/export-workflow.md), [CLI example](docs/WORKFLOW.md).

### The 1 MB pause rule

- **1 MB = 1,000,000 bytes.** All plans and formats in the same conversation share one ledger; do not reset it for each task or file.
- Pause only when the cumulative total **exceeds** the next threshold. Generate into a temporary location first and report the current file size and cumulative size including that file.
- After the user approves saving it, commit the file and set the next threshold to the new total plus 1 MB. A single 5 MB file requires only one size approval.
- If rejected, delete only the pending file. Its variant remains unfinished and is regenerated when work resumes.
- “Continue” does not disable the limit. Only an explicit cancellation does.

### Warnings and errors

Pause on yellow warnings or red errors. Resume only after the user inspects and explicitly accepts the issue. Approval applies to the same issue for the current variant; new issues require another pause. An accepted warning never turns a failed export into a successful one.

## Data and permission boundaries

- The add-in itself does not connect to the internet, upload designs, open listening ports or automatically invoke Fusion AI.
- Modeling, importing and exporting each require appropriate authorization. External uploads require an explanation of the data, destination and purpose.
- These rules are enforced by the assistant and workflow, **not by a system security sandbox**. JSON confirmation/evidence fields record decisions; the program cannot authenticate their origin. Do not run unreviewed plans from others.
- The generic executor exports the whole root component. Changes affecting protected geometry require specific dependency and invariant checks; do not bypass protection by clearing the protected list.
- File structure checks do not prove complex geometry is correct. Validate samples, critical dimensions and protected content; re-import files only when authorized.
- Do not have multiple programs write the same conversation ledger, or use a new ledger to bypass accumulated sizes. Recover lost or damaged records first.
- Manual operations, other plugins and external tools cannot be intercepted by this plugin.

## Updating and uninstalling

Stop the Fusion add-in and back up its directory before updating. Pull the new source, run it manually and check both commands. Do not replace modules while running. Refresh or reinstall the Codex skill as required by the client, then start a new conversation.

To uninstall, first click **Stop** in Fusion. For an externally registered folder, remove its registration. For a standard-directory installation:

```sh
sh plugins/fusion360-safe-local-tools/scripts/uninstall-macos.sh
```

The script verifies the target and moves it to Trash. Uninstalling the Fusion add-in and the Codex skill are separate steps.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Toolbar commands are missing | Use Design, run the add-in, and check for matching `.py` and `.manifest` files plus helper modules |
| System Python cannot import `adsk` | Run Fusion API scripts inside Fusion; system Python is for CLI tools and tests |
| Document identity mismatch | Verify creationId and the intended working copy; do not edit a plan just to bypass checks |
| Unverified copy provenance | Create and inspect a real independent copy before registering it |
| Existing output file | Determine whether it is a completed output or an unrelated file; the workflow refuses to overwrite it |
| Pending file | Check ledger status, then approve, reject or recover according to the actual state |
| Document identity changes after restart | Verify the reopened design and completed files, confirm a revised plan, and keep the same ledger |
| Hard links are unsupported | Choose an approved local destination that supports them |

## Validation and contributions

```sh
python3 -m unittest discover -s plugins/fusion360-safe-local-tools/tests -v
python3 -m compileall -q plugins/fusion360-safe-local-tools
```

The 17 tests cover size thresholds, cross-plan totals, rejection and resumption, sample validation, crash recovery, modification scope and warning approvals. They do not require Fusion.

Checks in Fusion covered a parametric block, constraints, naming, two STEP variants, STL/3MF exports, command loading, stopping and restarting. Revolves, lofts, complex assembly copies, all import formats and Fusion AI remain untested. Real user models need their own acceptance checks.

For issues, include macOS/Fusion versions, reproduction steps and sanitized errors. Do not attach private models, personal paths, accounts or conversation ledgers by default. See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance (Chinese).

## Repository layout

```text
.agents/plugins/marketplace.json    Codex marketplace entry
plugins/fusion360-safe-local-tools/
  .codex-plugin/plugin.json         Codex plugin manifest
  assets/FusionSafeLocalTools/      Fusion add-in and workflow code
  skills/                          Assistant rules and API references
  scripts/                         Installation, variant and ledger tools
  tests/                           Tests that do not require Fusion
docs/WORKFLOW.md                    CLI example and recovery instructions
README.zh-CN.md                     Complete Chinese usage guide
LICENSE                            License terms
```

Copyright © 2026 boyan-xu. See [LICENSE](LICENSE) for terms of use. Autodesk Fusion, OpenAI, ChatGPT and Codex are names or trademarks of their respective owners. This project is not affiliated with or endorsed by them.
