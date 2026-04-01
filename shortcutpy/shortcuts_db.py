import json, plistlib, sqlite3
from pathlib import Path

SHORTCUTS_DB = Path.home() / "Library/Shortcuts/Shortcuts.sqlite"
KEEP_PARAMS = "WFCommentActionText WFAskActionPrompt WFInputType WFAskActionDefaultAnswer WFAskActionDefaultAnswerDateAndTime".split()
KEEP_PARAMS += "WFChooseFromListActionPrompt WFItemSpecifier WFItemIndex WFGetDictionaryValueType WFDictionaryKey".split()
KEEP_PARAMS += "WFControlFlowMode WFConditionalActionString WFNumberValue WFVariableName CustomOutputName".split()
KEEP_PARAMS += "WFDateFormatStyle WFTimeFormatStyle WFDateFormat WFDateActionMode WFTimeUntilFromDate WFTimeUntilUnit".split()
KEEP_PARAMS += "Script ShowWhenRun UUID".split()


def dump_shortcut_text(name: str) -> str:
    with sqlite3.connect(SHORTCUTS_DB) as con:
        row = con.execute("""select ZACTIONCOUNT, ZHASSHORTCUTINPUTVARIABLES, ZIMPORTQUESTIONSDATA, ZINPUTCLASSESDATA,
            (select ZDATA from ZSHORTCUTACTIONS where Z_PK=ZSHORTCUT.ZACTIONS) from ZSHORTCUT where ZNAME=?""", (name,)).fetchone()
    if row is None: raise FileNotFoundError(f"Shortcut not found: {name}")
    action_count,has_input,import_blob,input_blob,actions_blob = row
    import_questions = plistlib.loads(import_blob) if import_blob else None
    input_classes = plistlib.loads(input_blob) if input_blob else None
    actions = plistlib.loads(actions_blob)
    lines = [f"Name: {name}", f"Action Count: {action_count}", f"Has Shortcut Input Variables: {bool(has_input)}",
        f"Input Classes: {input_classes}", f"Import Questions: {import_questions}", "", "Actions:"]
    for i,action in enumerate(actions, start=1):
        lines += [f"", f"{i:02d}. {action['WFWorkflowActionIdentifier']}"]
        params = {k: v for k,v in action.get("WFWorkflowActionParameters", {}).items() if k in KEEP_PARAMS}
        if params: lines.append(json.dumps(params, indent=2, ensure_ascii=False, default=str))
    return "\n".join(lines) + "\n"
