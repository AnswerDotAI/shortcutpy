import subprocess
from pathlib import Path
from types import SimpleNamespace

from shortcutpy import compile_file, compile_source
from shortcutpy.compiler import SIGNING_STDERR_NOISE, sign_shortcut


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
