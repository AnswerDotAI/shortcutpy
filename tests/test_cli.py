from shortcutpy.cli import main


def test_cli_open_uses_default_output(monkeypatch, tmp_path):
    calls = []

    def fake_compile_file(source, output, sign, mode, keep_unsigned):
        calls.append(("compile", source, output, sign, mode, keep_unsigned))

    def fake_run(cmd, check): calls.append(("open", cmd, check))

    monkeypatch.setattr("shortcutpy.cli.compile_file", fake_compile_file)
    monkeypatch.setattr("shortcutpy.cli.subprocess.run", fake_run)
    src = tmp_path / "hello.py"
    main([str(src), "-o"])
    assert calls == [
        ("compile", src, src.with_suffix(".shortcut"), True, "people-who-know-me", False),
        ("open", ["open", str(src.with_suffix(".shortcut"))], True)]
