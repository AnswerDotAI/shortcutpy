import plistlib, sqlite3

from shortcutpy.shortcuts_db import dump_shortcut_text


def test_dump_shortcut_text_reads_shortcuts_db(monkeypatch, tmp_path):
    db = tmp_path / "Shortcuts.sqlite"
    with sqlite3.connect(db) as con:
        con.execute("create table ZSHORTCUT (ZNAME text, ZACTIONCOUNT integer, ZHASSHORTCUTINPUTVARIABLES integer, ZIMPORTQUESTIONSDATA blob, ZINPUTCLASSESDATA blob, ZACTIONS integer)")
        con.execute("create table ZSHORTCUTACTIONS (Z_PK integer primary key, ZDATA blob)")
        actions = [{"WFWorkflowActionIdentifier": "is.workflow.actions.ask", "WFWorkflowActionParameters": {"WFAskActionPrompt": "When?", "WFInputType": "Date and Time"}}]
        con.execute("insert into ZSHORTCUTACTIONS (Z_PK, ZDATA) values (?, ?)", (1, plistlib.dumps(actions, fmt=plistlib.FMT_BINARY, sort_keys=False)))
        con.execute("insert into ZSHORTCUT values (?, ?, ?, ?, ?, ?)", ("Timestamp", 1, 1, plistlib.dumps([], fmt=plistlib.FMT_BINARY),
            plistlib.dumps(["WFDateContentItem"], fmt=plistlib.FMT_BINARY), 1))
    monkeypatch.setattr("shortcutpy.shortcuts_db.SHORTCUTS_DB", db)
    text = dump_shortcut_text("Timestamp")
    assert "Name: Timestamp" in text
    assert "Input Classes: ['WFDateContentItem']" in text
    assert "01. is.workflow.actions.ask" in text
    assert '"WFAskActionPrompt": "When?"' in text
