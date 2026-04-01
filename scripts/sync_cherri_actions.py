from __future__ import annotations

import argparse, ast, json, keyword, re
from dataclasses import dataclass
from pathlib import Path

MANUAL_ACTIONS = {"ask_for_text", "choose_from_menu", "get_files", "raw_action", "resize_image", "save_file", "shortcut", "show_result"}
ACTION_RENAMES = {"saveFile": "save_file_to_path"}
SKIP_ACTIONS = {"resizeImage"}
PRIMITIVE_KINDS = {"array", "bool", "color", "dictionary", "float", "number", "rawtext", "text", "variable"}
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
DOC_COMMENT = re.compile(r"^\s*// \[Doc\]:\s*(.*)$")
TOKEN_RE = re.compile(r"'[^']*'|\S+")


@dataclass(slots=True)
class Param:
    py_name: str
    key: str
    kind: str
    optional: bool
    enum: str | None = None


def snake(name: str) -> str:
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def pascal(name: str) -> str: return "".join(part.capitalize() for part in snake(name).split("_"))


def strip_line_comment(line: str) -> str:
    out,quote,escape = [],None,False
    for i,ch in enumerate(line):
        if quote:
            out.append(ch)
            if escape: escape = False
            elif ch == "\\": escape = True
            elif ch == quote: quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "/" and i + 1 < len(line) and line[i + 1] == "/": break
        out.append(ch)
    return "".join(out).rstrip()


def split_top(text: str, sep: str = ",") -> list[str]:
    out,chunk,stack,quote,escape = [],[],[],None,False
    opens,closes = {"(": ")", "[": "]", "{": "}"}, {")": "(", "]": "[", "}": "{"}
    for ch in text:
        if quote:
            chunk.append(ch)
            if escape: escape = False
            elif ch == "\\": escape = True
            elif ch == quote: quote = None
            continue
        if ch in "\"'":
            quote = ch
            chunk.append(ch)
            continue
        if ch in opens:
            stack.append(ch)
            chunk.append(ch)
            continue
        if ch in closes:
            if stack and stack[-1] == closes[ch]: stack.pop()
            chunk.append(ch)
            continue
        if ch == sep and not stack:
            piece = "".join(chunk).strip()
            if piece: out.append(piece)
            chunk = []
            continue
        chunk.append(ch)
    piece = "".join(chunk).strip()
    if piece: out.append(piece)
    return out


def split_top_once(text: str, sep: str) -> tuple[str, str | None]:
    stack,quote,escape = [],None,False
    opens,closes = {"(": ")", "[": "]", "{": "}"}, {")": "(", "]": "[", "}": "{"}
    for i,ch in enumerate(text):
        if quote:
            if escape: escape = False
            elif ch == "\\": escape = True
            elif ch == quote: quote = None
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch in opens:
            stack.append(ch)
            continue
        if ch in closes:
            if stack and stack[-1] == closes[ch]: stack.pop()
            continue
        if ch == sep and not stack: return text[:i], text[i + 1:]
    return text, None


def parse_single_quoted_items(text: str) -> tuple[str, ...]:
    items,buf,in_item,escape = [],[],False,False
    for ch in text:
        if not in_item:
            if ch == "'":
                in_item = True
                buf = []
            continue
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == "'":
            items.append("".join(buf))
            in_item = False
            continue
        buf.append(ch)
    return tuple(items)


def sanitize_name(name: str) -> str:
    name = snake(name)
    name = re.sub(r"[^0-9a-zA-Z_]", "_", name).strip("_") or "value"
    if name[0].isdigit(): name = f"_{name}"
    if keyword.iskeyword(name): name += "_"
    return name


def enum_alias(name: str, aliases: dict[str, str]) -> str:
    alias = pascal(name)
    if alias in aliases.values(): return f"{alias}Value"
    return alias


def parse_block(path: Path) -> tuple[list, dict]:
    text = BLOCK_COMMENT.sub("", path.read_text())
    actions, enums = [], {}
    pending_doc = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        if m := DOC_COMMENT.match(raw):
            pending_doc = m.group(1).strip()
            i += 1
            continue
        if stripped.startswith("enum "):
            block = [strip_line_comment(raw)]
            brace = block[0].count("{") - block[0].count("}")
            i += 1
            while brace > 0 and i < len(lines):
                line = strip_line_comment(lines[i])
                block.append(line)
                brace += line.count("{") - line.count("}")
                i += 1
            name = re.match(r"\s*enum\s+([A-Za-z_][A-Za-z0-9_]*)", block[0]).group(1)
            enums[name] = parse_single_quoted_items("\n".join(block))
            pending_doc = None
            continue
        if stripped.startswith("action "):
            block = [strip_line_comment(raw)]
            paren = block[0].count("(") - block[0].count(")")
            brace = block[0].count("{") - block[0].count("}")
            i += 1
            while i < len(lines) and (paren > 0 or brace > 0):
                line = strip_line_comment(lines[i])
                block.append(line)
                paren += line.count("(") - line.count(")")
                brace += line.count("{") - line.count("}")
                i += 1
            actions.append(parse_action("\n".join(block), pending_doc, enums))
            pending_doc = None
            continue
        pending_doc = None
        i += 1
    return actions, enums


def parse_action(text: str, doc: str | None, enums: dict[str, tuple]) -> dict:
    text = text.strip()
    start = text.index("(")
    depth = 1
    end = start + 1
    while end < len(text) and depth:
        if text[end] == "(": depth += 1
        elif text[end] == ")": depth -= 1
        end += 1
    prefix = text[len("action"):start].strip()
    params_text = text[start + 1:end - 1].strip()
    tail = text[end:].strip()
    body = {}
    if "{" in tail:
        body_text = tail[tail.index("{"):]
        body = ast.literal_eval(re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", body_text)))
        tail = tail[:tail.index("{")].strip()
    output = None
    if tail.startswith(":"): output = tail[1:].strip().split()[0]
    tokens = TOKEN_RE.findall(prefix)
    quoted = [o[1:-1] for o in tokens if o.startswith("'")]
    names = [o for o in tokens if not o.startswith("'") and o not in {"default", "mac", "!mac"} and not re.fullmatch(r"v\d+(?:\.\d+)?", o)]
    source_name = names[-1]
    py_name = ACTION_RENAMES.get(source_name, sanitize_name(source_name))
    ident = quoted[0] if quoted else source_name.lower()
    if source_name in SKIP_ACTIONS: py_name = ""
    params = parse_params(params_text, enums)
    return dict(source_name=source_name, py_name=py_name, identifier=ident, params=params, fixed=body, output=output, doc=doc or "")


def parse_params(text: str, enums: dict[str, tuple]) -> list[Param]:
    params = []
    used = set()
    for part in split_top(text):
        left,default = split_top_once(part, "=")
        left,key = split_top_once(left, ":")
        bits = left.split()
        if not bits: continue
        kind = bits[0].removesuffix("!")
        raw_name = bits[-1].lstrip("?")
        optional = "?" in left or default is not None
        enum = kind if kind not in PRIMITIVE_KINDS and kind in enums else None
        kind = "enum" if enum else kind
        py_name = sanitize_name(raw_name)
        if py_name in used:
            fallback = sanitize_name((key or raw_name).removeprefix("WF"))
            py_name = fallback if fallback not in used else f"{py_name}_{len(used)}"
        used.add(py_name)
        params.append(Param(py_name=py_name, key=(key or raw_name).strip().strip("'"), kind=kind, optional=optional, enum=enum))
    return params


def build_catalog(cherri_actions: Path) -> tuple[dict, dict]:
    actions, enums = [], {}
    for path in sorted(cherri_actions.glob("*.cherri")):
        file_actions,file_enums = parse_block(path)
        actions.extend(file_actions)
        enums |= file_enums
    enum_aliases = {name: enum_alias(name, {}) for name in enums}
    for name in enums: enum_aliases[name] = enum_alias(name, enum_aliases)
    catalog = {}
    for action in actions:
        py_name = action["py_name"]
        if not py_name or py_name in MANUAL_ACTIONS: continue
        catalog[py_name] = dict(source_name=action["source_name"], identifier=action["identifier"],
            params=[dict(py_name=o.py_name, key=o.key, kind=o.kind, optional=o.optional, enum=enum_aliases[o.enum] if o.enum else None) for o in action["params"]],
            fixed=action["fixed"], output=action["output"], doc=action["doc"])
    return dict(sorted(catalog.items())),dict(sorted((enum_aliases[k], v) for k,v in enums.items()))


RETURN_TYPES = dict(array="List[Any]", bool="Bool", dictionary="Dictionary", number="Number", text="Text")


def param_type(param: dict) -> str:
    if param["enum"]: return f'{param["enum"]} | Input'
    return dict(array="ArrayLike | Value[Any]", bool="BoolLike | Value[Any]", dictionary="DictLike | Value[Any]",
        float="NumberLike | Value[Any]", number="NumberLike | Value[Any]").get(param["kind"], "Input")


def return_type(output: str | None) -> str: return RETURN_TYPES.get(output or "", "Value[Any]")


def render_pyi(catalog: dict, enums: dict) -> str:
    lines = """from typing import Any, Callable, Generic, Literal, TypeAlias, TypeVar, overload

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

class Value(Generic[T]): ...
class Text(Value[str]): ...
class Number(Value[int | float]): ...
class Bool(Value[bool]): ...
class File(Value[object]): ...
class Image(Value[object]): ...
class Dictionary(Value[dict[str, Any]]): ...
class List(Value[list[T]]): ...

Input: TypeAlias = Value[Any] | str | int | float | bool | None | list[Any] | dict[str, Any]
NumberLike: TypeAlias = Number | int | float
BoolLike: TypeAlias = Bool | bool
ArrayLike: TypeAlias = List[Any] | list[Any]
DictLike: TypeAlias = Dictionary | dict[str, Any]

@overload
def shortcut(fn: F, /) -> F: ...
@overload
def shortcut(*, name: str | None = None, color: str | int | None = None, glyph: str | int | None = None) -> Callable[[F], F]: ...
def ask_for_text(prompt: str, /, *, default: str | None = None) -> Text: ...
def choose_from_menu(prompt: str, options: list[str], /) -> Text: ...
def show_result(value: Text | Number | Bool | str | int | float | bool, /) -> None: ...
def get_files(*, prompt: str | None = None) -> List[File]: ...
def resize_image(image: Image | File, /, *, width: int, height: int | None = None) -> Image: ...
def save_file(value: File | Image, /, *, ask_where: bool = True) -> File: ...
def raw_action(action_id: str, /, **params: Any) -> Value[Any]: ...
""".splitlines()
    for name,values in enums.items():
        vals = ", ".join(repr(o) for o in values) or '""'
        lines.append(f"{name}: TypeAlias = Literal[{vals}]")
    lines.append("")
    for name,spec in catalog.items():
        params = []
        for param in spec["params"]:
            annot = param_type(param)
            params.append(f'{param["py_name"]}: {annot}' + (" | None = None" if param["optional"] else ""))
        joined = ", ".join(params)
        if spec["doc"]: lines.append(f"# {spec['doc']}")
        lines.append(f"def {name}({joined}) -> {return_type(spec['output'])}: ...")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cherri-root", type=Path, default=Path("~/aai-ws/links/cherri").expanduser())
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = p.parse_args()
    catalog,enums = build_catalog(args.cherri_root / "actions")
    pkg = args.repo_root / "shortcutpy"
    (pkg / "action_catalog.json").write_text(json.dumps({"actions": catalog, "enums": enums}, indent=2, sort_keys=True))
    (pkg / "dsl.pyi").write_text(render_pyi(catalog, enums))
    print(f"wrote {len(catalog)} generated actions and {len(enums)} enums")


if __name__ == "__main__": main()
