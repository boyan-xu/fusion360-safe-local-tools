"""Local Fusion inspector and confirmed parameter/export workflow. No network service."""

import traceback
from . import fusion_workflow

import adsk.core
import adsk.fusion


ADDIN_NAME = "Fusion Safe Local Tools"
COMMAND_ID = "local_xby_fusion_safe_inspect_parameters"
COMMAND_NAME = "Inspect User Parameters"
COMMAND_DESCRIPTION = "Show user parameters from the active Fusion design (read-only)."
WORKSPACE_ID = "FusionSolidEnvironment"
TAB_ID = "ToolsTab"
PANEL_ID = "local_xby_fusion_safe_tools_panel"
PANEL_NAME = "Safe Local Tools"
MAX_DISPLAYED_PARAMETERS = 40

_handlers = []
_active_command_handlers = []
_owned_ui = []


def _app():
    return adsk.core.Application.get()


def _ui():
    app = _app()
    return app.userInterface if app else None


def _log(message, is_error=False):
    """Best-effort diagnostic logging to Fusion's existing console."""
    try:
        app = _app()
        if app:
            level = adsk.core.LogLevels.ErrorLogLevel if is_error else adsk.core.LogLevels.InfoLogLevel
            app.log(f"[{ADDIN_NAME}] {message}", level, adsk.core.LogTypes.ConsoleLogType)
    except Exception:
        pass


def _format_parameter(parameter):
    unit = parameter.unit or "unitless"
    expression = parameter.expression or ""
    return f"{parameter.name[:120]}: {expression[:240]} [{unit[:40]}]"


def _inspect_active_design():
    app = _app()
    if not app:
        return "Fusion application is not available."

    document = app.activeDocument
    if not document:
        return "No document is open. Open a Fusion design and run the command again."

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return (
            f'Active document: "{document.name}"\n\n'
            "The active product is not a Fusion Design, so it has no design user-parameter list."
        )

    parameters = design.userParameters
    lines = []
    total = parameters.count
    for index in range(min(total, MAX_DISPLAYED_PARAMETERS)):
        parameter = parameters.item(index)
        formatted = _format_parameter(parameter)
        lines.append(formatted)

    header = f'Active design: "{document.name}"\nUser parameters: {total}'
    if not lines:
        return header + "\n\nNo user parameters were found."

    body = "\n".join(lines)
    if total > MAX_DISPLAYED_PARAMETERS:
        body += (
            f"\n\nOnly the first {MAX_DISPLAYED_PARAMETERS} parameters are shown here. "
            "Use Fusion's Change Parameters dialog for the complete list."
        )
    return header + "\n\n" + body


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, action="inspect"):
        super().__init__()
        self.action = action

    def notify(self, args):
        try:
            if self.action == "export":
                fusion_workflow.select_plan()
                return
            ui = _ui()
            message = _inspect_active_design()
            if ui:
                ui.messageBox(message, ADDIN_NAME)
        except Exception:
            details = traceback.format_exc()
            _log(f"Command failed:\n{details}", is_error=True)


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, action="inspect"):
        super().__init__()
        self.action = action

    def notify(self, args):
        execute_handler = None
        execute_attached = False
        try:
            execute_handler = _ExecuteHandler(self.action)
            destroy_handler = _CommandDestroyedHandler(execute_handler)
            if not args.command.execute.add(execute_handler):
                raise RuntimeError("Cannot attach execute handler")
            execute_attached = True
            if not args.command.destroy.add(destroy_handler):
                raise RuntimeError("Cannot attach destroy handler")
            _active_command_handlers.extend((execute_handler, destroy_handler))
        except Exception:
            if execute_attached:
                try:
                    args.command.execute.remove(execute_handler)
                except Exception:
                    _log("Could not detach partially attached execute handler", is_error=True)
            _log(f"Could not attach command handler:\n{traceback.format_exc()}", is_error=True)


class _CommandDestroyedHandler(adsk.core.CommandEventHandler):
    def __init__(self, execute_handler):
        super().__init__()
        self.execute_handler = execute_handler

    def notify(self, args):
        # Release handlers associated with the completed transient command.
        for handler in (self.execute_handler, self):
            if handler in _active_command_handlers:
                _active_command_handlers.remove(handler)


def _remove_ui():
    """Release only objects created by this module, in reverse order."""
    failed = []
    for obj in reversed(_owned_ui):
        try:
            if obj.isValid and not obj.deleteMe():
                raise RuntimeError("Fusion refused UI deletion")
        except Exception:
            failed.append(obj)
            _log(traceback.format_exc(), is_error=True)
    _owned_ui[:] = list(reversed(failed))
    if not failed:
        _active_command_handlers.clear()
        _handlers.clear()
    return not failed


def run(context):
    try:
        ui = _ui()
        if not ui:
            raise RuntimeError("Fusion user interface is not available.")

        # Release this module's previous UI before a repeated run.
        if not _remove_ui():
            raise RuntimeError("Previous UI cleanup incomplete; retry Stop before Run")

        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        if not workspace:
            raise RuntimeError("Fusion Design workspace was not found.")

        tab = workspace.toolbarTabs.itemById(TAB_ID)
        if not tab:
            raise RuntimeError("Fusion Utilities/Tools tab was not found.")

        if tab.toolbarPanels.itemById(PANEL_ID) or ui.commandDefinitions.itemById(COMMAND_ID):
            raise RuntimeError("UI identifier already exists; refusing to replace an unowned object")
        panel = tab.toolbarPanels.add(PANEL_ID, PANEL_NAME)
        if not panel:
            raise RuntimeError("Could not create the add-in toolbar panel.")
        _owned_ui.append(panel)

        command_definition = ui.commandDefinitions.addButtonDefinition(
            COMMAND_ID,
            COMMAND_NAME,
            COMMAND_DESCRIPTION,
        )
        if not command_definition:
            raise RuntimeError("Could not create the add-in command definition.")
        _owned_ui.append(command_definition)

        created_handler = _CommandCreatedHandler()
        if not command_definition.commandCreated.add(created_handler):
            raise RuntimeError("Cannot attach command-created handler")
        _handlers.append(created_handler)

        control = panel.controls.addCommand(command_definition)
        if not control:
            raise RuntimeError("Cannot create toolbar button")
        _owned_ui.append(control)
        control.isPromoted = False

        export_id = COMMAND_ID + "_export_plan"
        if ui.commandDefinitions.itemById(export_id):
            raise RuntimeError("Export command already exists")
        export_def = ui.commandDefinitions.addButtonDefinition(export_id, "Run Confirmed Export Plan", "Run a reviewed local export plan; pause on sample, warnings and size limits.")
        _owned_ui.append(export_def)
        export_handler = _CommandCreatedHandler("export")
        if not export_def.commandCreated.add(export_handler):
            raise RuntimeError("Cannot attach export handler")
        _handlers.append(export_handler)
        _owned_ui.append(panel.controls.addCommand(export_def))

        _log("Loaded successfully. Inspection and confirmed export commands are available in Utilities > Safe Local Tools.")
    except Exception:
        details = traceback.format_exc()
        _log(f"Load failed:\n{details}", is_error=True)
        try:
            _remove_ui()
        except Exception:
            _log(f"Cleanup after load failure also failed:\n{traceback.format_exc()}", is_error=True)
        return False
    return True


def stop(context):
    try:
        if not _remove_ui():
            return False
        _log("Stopped and removed its command UI.")
        return True
    except Exception:
        _log(f"Stop/cleanup failed:\n{traceback.format_exc()}", is_error=True)
        return False
