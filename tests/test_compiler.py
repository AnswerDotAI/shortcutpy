import subprocess
from pathlib import Path
from types import SimpleNamespace

from shortcutpy import compile_file, compile_source
from shortcutpy.compiler import CompileError, SIGNING_STDERR_NOISE, sign_shortcut


def test_compile_greeting_payload():
    src = """
from shortcutpy.dsl import shortcut, ask_for_text, choose_from_menu, show_result

@shortcut(name="Greeting", color="yellow", glyph="hand")
def main():
    name = ask_for_text("What is your name?")
    tone = choose_from_menu("Tone", ["formal", "casual"])
    if tone == "formal":
        message = f"Good day, {name}."
    else:
        message = f"Hey {name}!"
    show_result(message)
"""
    artifact = compile_source(src, filename="greeting.py")
    actions = artifact.payload["WFWorkflowActions"]
    assert artifact.payload["WFWorkflowName"] == "Greeting"
    ids = [o["WFWorkflowActionIdentifier"] for o in actions]
    assert ids == [
        "is.workflow.actions.ask",
        "is.workflow.actions.setvariable",
        "is.workflow.actions.list",
        "is.workflow.actions.choosefromlist",
        "is.workflow.actions.setvariable",
        "is.workflow.actions.conditional",
        "is.workflow.actions.gettext",
        "is.workflow.actions.setvariable",
        "is.workflow.actions.conditional",
        "is.workflow.actions.gettext",
        "is.workflow.actions.setvariable",
        "is.workflow.actions.conditional",
        "is.workflow.actions.showresult"]
    assert artifact.payload["WFWorkflowIcon"]["WFWorkflowIconStartColor"] == 4274264319
    assert artifact.payload["WFWorkflowIcon"]["WFWorkflowIconGlyphNumber"] == 59751
    choose = actions[3]["WFWorkflowActionParameters"]
    assert choose["WFChooseFromListActionPrompt"] == "Tone"
    show = actions[-1]["WFWorkflowActionParameters"]["Text"]["Value"]["attachmentsByRange"]
    assert show["{0, 1}"]["VariableName"] == "message"


def test_return_uses_output_action():
    src = """
from shortcutpy.dsl import shortcut, ask_for_text

@shortcut(name="Greeting")
def main():
    name = ask_for_text("Name")
    return f"Hi {name}"
"""
    artifact = compile_source(src, filename="returning.py")
    assert artifact.payload["WFWorkflowActions"][-1]["WFWorkflowActionIdentifier"] == "is.workflow.actions.output"


def test_bare_shortcut_uses_function_name():
    src = """
from shortcutpy.dsl import shortcut, show_result

@shortcut
def hello_world():
    show_result("hi")
"""
    artifact = compile_source(src, filename="hello.py")
    assert artifact.program.meta.name == "Hello World"
    assert artifact.payload["WFWorkflowName"] == "Hello World"
    assert artifact.payload["WFWorkflowActions"][-1]["WFWorkflowActionIdentifier"] == "is.workflow.actions.showresult"


def test_shortcut_name_defaults_when_omitted():
    src = """
from shortcutpy.dsl import shortcut, show_result

@shortcut(color="yellow")
def get_current_weather():
    show_result("hi")
"""
    artifact = compile_source(src, filename="weather.py")
    assert artifact.program.meta.name == "Get Current Weather"
    assert artifact.program.meta.color == "yellow"


def test_ask_for_datetime_and_unix_timestamp_emit_expected_actions():
    src = """
from shortcutpy.dsl import shortcut, ask_for_datetime, current_date, show_result, unix_timestamp

@shortcut(name="Timestamp")
def main():
    picked = ask_for_datetime("When?", default=current_date())
    show_result(unix_timestamp(picked))
"""
    artifact = compile_source(src, filename="timestamp.py")
    actions = artifact.payload["WFWorkflowActions"]
    assert [o["WFWorkflowActionIdentifier"] for o in actions] == [
        "is.workflow.actions.date",
        "is.workflow.actions.ask",
        "is.workflow.actions.setvariable",
        "is.workflow.actions.gettimebetweendates",
        "is.workflow.actions.showresult"]
    ask = actions[1]["WFWorkflowActionParameters"]
    assert ask["WFInputType"] == "Date and Time"
    assert ask["WFAskActionPrompt"] == "When?"
    assert ask["WFAskActionDefaultAnswerDateAndTime"]["Value"]["attachmentsByRange"]["{0, 1}"]["OutputName"] == "Text"
    ts = actions[3]["WFWorkflowActionParameters"]
    assert ts["WFTimeUntilFromDate"] == "1970-01-01T00:00Z"
    assert ts["WFTimeUntilUnit"] == "Seconds"


def test_shortcut_input_sets_payload_flag():
    src = """
from shortcutpy.dsl import shortcut, shortcut_input, show_result

@shortcut(name="Input")
def main():
    shared = shortcut_input()
    show_result(shared)
"""
    artifact = compile_source(src, filename="input.py")
    assert artifact.payload["WFWorkflowHasShortcutInputVariables"] is True
    setvar = artifact.payload["WFWorkflowActions"][0]["WFWorkflowActionParameters"]
    assert setvar["WFInput"]["Value"]["Type"] == "ExtensionInput"


def test_preferred_language_emits_shell_script():
    src = """
from shortcutpy.dsl import preferred_language, shortcut, show_result

@shortcut(name="Lang")
def main():
    show_result(preferred_language())
"""
    artifact = compile_source(src, filename="lang.py")
    actions = artifact.payload["WFWorkflowActions"]
    assert [o["WFWorkflowActionIdentifier"] for o in actions] == [
        "is.workflow.actions.gettext",
        "is.workflow.actions.runshellscript",
        "is.workflow.actions.showresult"]
    params = actions[1]["WFWorkflowActionParameters"]
    assert params["Script"] == "defaults read -g AppleLocale | cut -c1-2 | tr -d '\\n'"
    assert params["Shell"] == "/bin/zsh"


def test_shortcut_input_types_override_default_classes():
    src = """
from shortcutpy.dsl import shortcut, shortcut_input, show_result

@shortcut(name="Input", input_types=["text", "date"])
def main():
    shared = shortcut_input()
    show_result(shared)
"""
    artifact = compile_source(src, filename="typed_input.py")
    assert artifact.payload["WFWorkflowInputContentItemClasses"] == ["WFStringContentItem", "WFDateContentItem"]


def test_dict_indexing_emits_getvalueforkey():
    src = """
from shortcutpy.dsl import *

@shortcut(name="Lookup")
def main():
    labels = {"formal": "Good day", "casual": "Hey"}
    tone = "formal"
    show_result(labels[tone])
"""
    artifact = compile_source(src, filename="lookup.py")
    action = artifact.payload["WFWorkflowActions"][-2]
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.getvalueforkey"
    params = action["WFWorkflowActionParameters"]
    assert params["WFGetDictionaryValueType"] == "Value"
    assert params["WFDictionaryKey"]["WFSerializationType"] == "WFTextTokenString"
    attachment = params["WFDictionaryKey"]["Value"]["attachmentsByRange"]["{0, 1}"]
    assert attachment["VariableName"] == "tone"


def test_dictionary_literal_accepts_runtime_keys():
    src = """
from shortcutpy.dsl import *

@shortcut(name="Lookup")
def main():
    key = "formal"
    labels = {key: "Good day"}
    show_result(labels[key])
"""
    artifact = compile_source(src, filename="lookup.py")
    dictionary = artifact.payload["WFWorkflowActions"][2]["WFWorkflowActionParameters"]["WFItems"]["Value"]["WFDictionaryFieldValueItems"][0]
    assert dictionary["WFKey"]["Value"]["attachmentsByRange"]["{0, 1}"]["VariableName"] == "key"


def test_list_indexing_uses_python_zero_based_indices():
    src = """
from shortcutpy.dsl import *

@shortcut(name="Lookup")
def main():
    dates = get_dates("today or tomorrow")
    show_result(dates[0])
"""
    artifact = compile_source(src, filename="lookup.py")
    action = artifact.payload["WFWorkflowActions"][-2]
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.getitemfromlist"
    params = action["WFWorkflowActionParameters"]
    assert params["WFItemSpecifier"] == "Item At Index"
    assert params["WFItemIndex"] == 1


def test_dynamic_list_index_is_rejected():
    src = """
from shortcutpy.dsl import *

@shortcut
def main():
    items = ["a", "b"]
    i = 0
    show_result(items[i])
"""
    try: compile_source(src, filename="lookup.py")
    except CompileError as e: assert "List indices must be integer literals" in str(e)
    else: raise AssertionError("Expected compile_source() to reject dynamic list indexing")


def test_negative_list_index_is_rejected():
    src = """
from shortcutpy.dsl import *

@shortcut
def main():
    items = ["a"]
    show_result(items[-1])
"""
    try: compile_source(src, filename="lookup.py")
    except CompileError as e: assert "Negative list indices are not supported" in str(e)
    else: raise AssertionError("Expected compile_source() to reject negative list indexing")


def test_compile_file_signs_via_shortcuts(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, check, capture_output, text):
        calls.append((cmd, check, capture_output, text))
        Path(cmd[-1]).write_bytes(b"signed")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("shortcutpy.compiler.subprocess.run", fake_run)
    src = tmp_path / "hello.py"
    src.write_text(
        """
from shortcutpy.dsl import shortcut, show_result

@shortcut(name="Hello")
def main():
    show_result("hi")
""")
    out = tmp_path / "hello.shortcut"
    compile_file(src, output=out)
    assert calls == [([
        "shortcuts", "sign", "--mode", "people-who-know-me", "--input", str(tmp_path / "hello.unsigned.shortcut"), "--output", str(out)], False, True, True)]
    assert out.read_bytes() == b"signed"


def test_compile_file_defaults_output_to_shortcut_name(tmp_path):
    src = tmp_path / "weather.py"
    src.write_text(
        """
from shortcutpy.dsl import shortcut, show_result

@shortcut(name="Current Weather")
def main():
    show_result("hi")
""")
    compile_file(src, sign=False)
    out = tmp_path / "Current Weather.shortcut"
    assert out.exists()


def test_sign_shortcut_filters_known_apple_noise(monkeypatch, capsys, tmp_path):
    out = tmp_path / "hello.shortcut"

    def fake_run(cmd, check, capture_output, text):
        Path(cmd[-1]).write_bytes(b"signed")
        stderr = f"{SIGNING_STDERR_NOISE}\nreal warning\n{SIGNING_STDERR_NOISE}\n"
        return SimpleNamespace(returncode=0, stdout="", stderr=stderr)

    monkeypatch.setattr("shortcutpy.compiler.subprocess.run", fake_run)
    sign_shortcut(tmp_path / "hello.unsigned.shortcut", out)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "real warning\n"


def test_sign_shortcut_raises_with_filtered_stderr(monkeypatch, tmp_path):
    def fake_run(cmd, check, capture_output, text):
        stderr = f"{SIGNING_STDERR_NOISE}\nactual failure\n"
        return SimpleNamespace(returncode=1, stdout="", stderr=stderr)

    monkeypatch.setattr("shortcutpy.compiler.subprocess.run", fake_run)
    try: sign_shortcut(tmp_path / "hello.unsigned.shortcut", tmp_path / "hello.shortcut")
    except subprocess.CalledProcessError as e: assert e.stderr == "actual failure\n"
    else: raise AssertionError("Expected sign_shortcut() to raise")
