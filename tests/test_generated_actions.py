import shortcutpy.dsl as dsl

from shortcutpy import compile_source
from shortcutpy.action_catalog import ACTION_SPECS


def test_generated_surface_is_exposed():
    assert len(ACTION_SPECS) >= 300
    for name in ["alert", "show_notification", "toggle_dnd", "save_file_to_path", "get_object_of_class"]:
        assert callable(getattr(dsl, name))


def test_generated_alert_action_uses_fixed_params():
    src = """
from shortcutpy.dsl import shortcut, alert

@shortcut(name="Alert")
def main():
    alert("Hello", title="World")
"""
    artifact = compile_source(src, filename="alert.py")
    action = artifact.payload["WFWorkflowActions"][0]
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.alert"
    params = action["WFWorkflowActionParameters"]
    assert params["WFAlertActionCancelButtonShown"] is False
    assert params["WFAlertActionMessage"] == "Hello"
    assert params["WFAlertActionTitle"] == "World"


def test_generated_action_prefixes_shortcut_identifier_and_fixed_body():
    src = """
from shortcutpy.dsl import shortcut, toggle_dnd

@shortcut(name="Toggle")
def main():
    toggle_dnd()
"""
    artifact = compile_source(src, filename="toggle.py")
    action = artifact.payload["WFWorkflowActions"][0]
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.dnd.set"
    assert action["WFWorkflowActionParameters"]["Operation"] == "Toggle"
    assert action["WFWorkflowActionParameters"]["FocusModes"]["Identifier"] == "com.apple.donotdisturb.mode.default"


def test_generated_save_file_rename_compiles():
    src = """
from shortcutpy.dsl import shortcut, save_file_to_path

@shortcut(name="Save")
def main():
    save_file_to_path("/tmp/out.txt", "hi")
"""
    artifact = compile_source(src, filename="save.py")
    action = artifact.payload["WFWorkflowActions"][-1]
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.documentpicker.save"
    assert action["WFWorkflowActionParameters"]["WFAskWhereToSave"] is False
    assert action["WFWorkflowActionParameters"]["WFFileDestinationPath"] == "/tmp/out.txt"
