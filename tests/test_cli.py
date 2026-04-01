from types import SimpleNamespace

from shortcutpy.cli import main


def test_cli_open_uses_temp_output_when_no_output(monkeypatch, tmp_path):
    calls = []
    artifact = SimpleNamespace(program=SimpleNamespace(meta=SimpleNamespace(name="Hello World")))

    def fake_compile_source(source, filename):
        calls.append(("compile_source", source, filename))
        return artifact

    def fake_materialize(artifact_, source, output, sign, mode, keep_unsigned):
        calls.append(("materialize", artifact_, source, output, sign, mode, keep_unsigned))

    def fake_run(cmd, check): calls.append(("open", cmd, check))

    monkeypatch.setattr("shortcutpy.cli.compile_source", fake_compile_source)
    monkeypatch.setattr("shortcutpy.cli.materialize_artifact", fake_materialize)
    monkeypatch.setattr("shortcutpy.cli.subprocess.run", fake_run)
    monkeypatch.setattr("shortcutpy.cli.tempfile.mkdtemp", lambda prefix: str(tmp_path / "temp-shortcut"))
    src = tmp_path / "hello.py"
    src.write_text("print('hello')")
    main([str(src), "-o"])
    assert calls == [
        ("compile_source", "print('hello')", str(src)),
        ("materialize", artifact, src, tmp_path / "temp-shortcut" / "Hello World.shortcut", True, "people-who-know-me", False),
        ("open", ["open", str(tmp_path / "temp-shortcut" / "Hello World.shortcut")], True)]


def test_cli_open_with_explicit_output_uses_that_output(monkeypatch, tmp_path):
    calls = []
    artifact = SimpleNamespace(program=SimpleNamespace(meta=SimpleNamespace(name="Hello World")))

    def fake_compile_file(source, output, sign, mode, keep_unsigned):
        calls.append(("compile", source, output, sign, mode, keep_unsigned))
        return artifact

    def fake_run(cmd, check): calls.append(("open", cmd, check))

    monkeypatch.setattr("shortcutpy.cli.compile_file", fake_compile_file)
    monkeypatch.setattr("shortcutpy.cli.subprocess.run", fake_run)
    src = tmp_path / "hello.py"
    out = tmp_path / "custom.shortcut"
    main([str(src), "-o", "-O", str(out)])
    assert calls == [
        ("compile", src, out, True, "people-who-know-me", False),
        ("open", ["open", str(out)], True)]


def test_cli_dump_writes_stdout(monkeypatch, capsys):
    monkeypatch.setattr("shortcutpy.cli.dump_shortcut_text", lambda name: f"Name: {name}\n")
    main(["dump", "Timestamp"])
    assert capsys.readouterr().out == "Name: Timestamp\n"


def test_cli_dump_writes_file(monkeypatch, tmp_path):
    monkeypatch.setattr("shortcutpy.cli.dump_shortcut_text", lambda name: f"Name: {name}\n")
    out = tmp_path / "timestamp.txt"
    main(["dump", "Timestamp", "-O", str(out)])
    assert out.read_text() == "Name: Timestamp\n"
