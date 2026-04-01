import ast, plistlib, subprocess, sys, uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .action_catalog import ACTION_SPECS

OBJECT_REPLACEMENT = "\uFFFC"
DEFAULT_GLYPH = 61440
DEFAULT_COLOR = 3031607807
CLIENT_VERSION = "4033.0.4.3"
MINIMUM_CLIENT_VERSION = 900
DEFAULT_INPUT_CLASSES = """
WFGenericFileContentItem
WFPDFContentItem
WFSafariWebPageContentItem
WFURLContentItem
WFAppStoreAppContentItem
WFDateContentItem
WFImageContentItem
WFRichTextContentItem
WFArticleContentItem
WFContactContentItem
WFLocationContentItem
WFPhoneNumberContentItem
WFDictionaryContentItem
WFEmailAddressContentItem
WFFolderContentItem
WFiTunesProductContentItem
WFDCMapsLinkContentItem
WFAVAssetContentItem
WFStringContentItem
WFNumberContentItem
""".split()
COLORS = dict(red=4282601983, darkorange=4251333119, orange=4271458815, yellow=4274264319, green=4292093695, teal=431817727,
    lightblue=1440408063, blue=463140863, darkblue=946986751, violet=2071128575, purple=3679049983, pink=3980825855,
    darkgray=255, gray=3031607807, taupe=2846468607)
GLYPHS = dict(smileyFace=59834, apple=59420, alert=59424, chatBubble=59414, clipboard=59711, folder=59737, hand=59751,
    handTap=62215, image=59784, laptop=59436, magicWand=61511, microphone=59780, paperAirplane=59836, phone=59814,
    picture=59784, server=59722, textBubble=59779)
INPUT_TYPE_ALIASES = dict(file="WFGenericFileContentItem", pdf="WFPDFContentItem", webpage="WFSafariWebPageContentItem",
    url="WFURLContentItem", app="WFAppStoreAppContentItem", date="WFDateContentItem", image="WFImageContentItem",
    rich_text="WFRichTextContentItem", article="WFArticleContentItem", contact="WFContactContentItem", location="WFLocationContentItem",
    phone="WFPhoneNumberContentItem", dictionary="WFDictionaryContentItem", email="WFEmailAddressContentItem",
    folder="WFFolderContentItem", itunes="WFiTunesProductContentItem", maps_link="WFDCMapsLinkContentItem",
    media="WFAVAssetContentItem", text="WFStringContentItem", string="WFStringContentItem", number="WFNumberContentItem")
CONDITION_CODES = {"==": 4, "!=": 5, ">": 2, ">=": 3, "<": 0, "<=": 1}
CF_START = 0
CF_ELSE = 1
CF_END = 2
SIGNING_STDERR_NOISE = 'ERROR: Unrecognized attribute string flag \'?\' in attribute string "T@"NSString",?,R,C" for property debugDescription'
FULL_ACTION_PREFIXES = ("app.", "com.", "dev.", "io.", "is.workflow.actions.", "net.", "org.")
PAYLOAD_TEMPLATE = dict(WFQuickActionSurfaces=[], WFWorkflowClientVersion=CLIENT_VERSION, WFWorkflowHasOutputFallback=False)
PAYLOAD_TEMPLATE |= dict(WFWorkflowHasShortcutInputVariables=False, WFWorkflowImportQuestions=[], WFWorkflowMinimumClientVersion=MINIMUM_CLIENT_VERSION)
PAYLOAD_TEMPLATE |= dict(WFWorkflowMinimumClientVersionString=str(MINIMUM_CLIENT_VERSION), WFWorkflowNoInputBehavior={})
PAYLOAD_TEMPLATE |= dict(WFWorkflowOutputContentItemClasses=[], WFWorkflowTypes=[])
Pathish = str | Path
DictItem = tuple["Expr", "Expr"]
Block = list["Stmt"]
ExprKind = str | None
BlockResult = tuple[Block, set[str], dict[str, ExprKind]]


class CompileError(Exception):
    def __init__(self, message: str, node: ast.AST | None = None, filename: str | None = None):
        self.message,self.node,self.filename = message,node,filename
        super().__init__(self.format())

    def format(self) -> str:
        if not self.node or not self.filename or not hasattr(self.node, "lineno"): return self.message
        return f"{self.filename}:{self.node.lineno}:{self.node.col_offset+1}: {self.message}"


@dataclass(slots=True)
class ShortcutArtifact:
    program: "ShortcutProgram"
    payload: dict[str, Any]


@dataclass(slots=True)
class ShortcutMeta:
    name: str
    color: str | int | None = None
    glyph: str | int | None = None
    input_types: list[str] | None = None


@dataclass(slots=True)
class ShortcutProgram:
    meta: ShortcutMeta
    body: list["Stmt"]


class Stmt: ...
class Expr: ...


@dataclass(slots=True)
class Assign(Stmt):
    name: str
    value: Expr


@dataclass(slots=True)
class ExprStmt(Stmt):
    value: "CallExpr"


@dataclass(slots=True)
class IfStmt(Stmt):
    predicate: "Predicate"
    then_body: list[Stmt]
    else_body: list[Stmt]
    assigned_names: tuple[str, ...]


@dataclass(slots=True)
class RepeatEach(Stmt):
    target: str
    source: Expr
    body: list[Stmt]


@dataclass(slots=True)
class RepeatCount(Stmt):
    target: str
    count: int
    body: list[Stmt]


@dataclass(slots=True)
class Return(Stmt):
    value: Expr | None


@dataclass(slots=True)
class NameExpr(Expr):
    name: str


@dataclass(slots=True)
class LiteralExpr(Expr):
    value: str | int | float | bool | None


@dataclass(slots=True)
class FormattedText(Expr):
    parts: list[str | NameExpr]


@dataclass(slots=True)
class ListExpr(Expr):
    items: list[Expr]


@dataclass(slots=True)
class DictExpr(Expr):
    items: list[DictItem]


@dataclass(slots=True)
class DictLookupExpr(Expr):
    source: Expr
    key: Expr


@dataclass(slots=True)
class ListLookupExpr(Expr):
    source: Expr
    index: int


@dataclass(slots=True)
class CallExpr(Expr):
    func: str
    args: list[Expr]
    kwargs: dict[str, Expr]


@dataclass(slots=True)
class Predicate:
    left: Expr
    op: str
    right: Expr


@dataclass(slots=True)
class Ref:
    kind: str
    name: str
    uuid: str | None = None

    def action_value(self) -> dict[str, Any]:
        if self.kind == "variable": return {"Type": "Variable", "VariableName": self.name}
        if self.kind == "action_output": return dict(Type="ActionOutput", OutputName=self.name, OutputUUID=self.uuid)
        if self.kind == "special": return {"Type": self.name}
        raise ValueError(f"Unknown ref kind: {self.kind}")


def compile_source(source: str, filename: str = "<string>") -> ShortcutArtifact:
    tree = ast.parse(source, filename=filename)
    program = Lowerer(filename).lower(tree)
    return ShortcutArtifact(program=program, payload=Emitter().emit(program))


def compile_file(src: Pathish, output: Pathish | None = None, *, sign: bool = True, mode: str = "people-who-know-me", keep_unsigned: bool = False) -> ShortcutArtifact:
    src = Path(src)
    artifact = compile_source(src.read_text(), filename=str(src))
    materialize_artifact(artifact, src, output=output, sign=sign, mode=mode, keep_unsigned=keep_unsigned)
    return artifact


def write_payload(payload: dict[str, Any], path: Pathish) -> None:
    path = Path(path)
    with path.open("wb") as f: plistlib.dump(payload, f, fmt=plistlib.FMT_BINARY, sort_keys=False)


def materialize_artifact(artifact: ShortcutArtifact, src: Pathish, output: Pathish | None = None, *, sign: bool = True,
    mode: str = "people-who-know-me", keep_unsigned: bool = False) -> Path:
    src = Path(src)
    output = Path(output) if output else default_output_path(src, artifact.program.meta.name)
    if sign:
        unsigned = output.with_name(f"{output.stem}.unsigned.shortcut")
        write_payload(artifact.payload, unsigned)
        sign_shortcut(unsigned, output, mode=mode)
        if not keep_unsigned: unsigned.unlink(missing_ok=True)
    else: write_payload(artifact.payload, output)
    return output


def sign_shortcut(unsigned_path: Pathish, signed_path: Pathish, *, mode: str = "people-who-know-me") -> None:
    cmd = ["shortcuts", "sign", "--mode", mode, "--input", str(unsigned_path), "--output", str(signed_path)]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    stdout,stderr = proc.stdout or "",clean_signing_stderr(proc.stderr)
    if stdout: print(stdout, end="")
    if stderr: print(stderr, end="", file=sys.stderr)
    if proc.returncode: raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=stderr)


def clean_signing_stderr(stderr: str | None) -> str:
    if not stderr: return ""
    lines = [o for o in stderr.splitlines() if o != SIGNING_STDERR_NOISE]
    return "\n".join(lines) + ("\n" if lines and stderr.endswith("\n") else "")


def default_output_path(src: Pathish, name: str) -> Path: return Path(src).with_name(f"{default_output_name(name)}.shortcut")
def default_output_name(name: str) -> str: return name.replace("/", "-")


def bind_action_spec(spec: dict[str, Any], args: list["Expr"], kwargs: dict[str, "Expr"]) -> dict[str, "Expr"]:
    params,bound = spec["params"],{}
    if len(args) > len(params): raise ValueError("Unsupported argument shape")
    for param,arg in zip(params, args): bound[param["key"]] = arg
    for param in params[:len(args)]:
        if param["py_name"] in kwargs: raise ValueError(f"Multiple values for argument: {param['py_name']}")
    for param in params[len(args):]:
        if param["py_name"] in kwargs: bound[param["key"]] = kwargs[param["py_name"]]
        elif not param["optional"]: raise ValueError(f"Missing required argument: {param['py_name']}")
    unexpected = set(kwargs) - {o["py_name"] for o in params}
    if unexpected: raise ValueError(f"Unexpected keyword arguments: {', '.join(sorted(unexpected))}")
    return bound


HANDWRITTEN_OUTPUT_KINDS = dict(get_files="list")


class Lowerer:
    def __init__(self, filename: str): self.filename = filename

    def error(self, message: str, node: ast.AST) -> CompileError: return CompileError(message, node=node, filename=self.filename)
    def default_shortcut_name(self, name: str) -> str: return " ".join(o[:1].upper() + o[1:] for o in name.split("_") if o) or name

    def lower(self, tree: ast.Module) -> ShortcutProgram:
        body = list(tree.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        fn = None
        for node in body:
            if isinstance(node, ast.ImportFrom):
                if node.module != "shortcutpy.dsl": raise self.error("Only imports from shortcutpy.dsl are supported", node)
                continue
            if isinstance(node, ast.FunctionDef):
                if fn is not None: raise self.error("Only one @shortcut function is supported", node)
                fn = node
                continue
            raise self.error("Only imports and a single @shortcut function are allowed at module scope", node)
        if fn is None: raise CompileError("No @shortcut function found", filename=self.filename)
        meta = self.lower_meta(fn)
        body,_,_ = self.lower_block(fn.body, set(), {})
        return ShortcutProgram(meta=meta, body=body)

    def lower_meta(self, fn: ast.FunctionDef) -> ShortcutMeta:
        if fn.args.args or fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg: raise self.error("Shortcut functions cannot take parameters", fn)
        if len(fn.decorator_list) != 1: raise self.error("Shortcut functions must have exactly one decorator", fn)
        dec = fn.decorator_list[0]
        if isinstance(dec, ast.Name) and dec.id == "shortcut": return ShortcutMeta(name=self.default_shortcut_name(fn.name))
        if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Name) or dec.func.id != "shortcut":
            raise self.error("Shortcut functions must be decorated with @shortcut or @shortcut(...)", dec)
        if dec.args: raise self.error("@shortcut only supports keyword arguments", dec)
        seen = {}
        for kw in dec.keywords:
            if kw.arg is None: raise self.error("@shortcut does not support **kwargs", dec)
            seen[kw.arg] = self.literal_string_list(kw.value, f"@shortcut {kw.arg}") if kw.arg == "input_types" else self.literal_value(kw.value, f"@shortcut {kw.arg}")
        name = seen.get("name", self.default_shortcut_name(fn.name))
        if not isinstance(name, str) or not name: raise self.error("@shortcut requires a non-empty name=", dec)
        input_types = seen.get("input_types")
        if input_types is not None: input_types = [self.resolve_input_type(o, dec) for o in input_types]
        return ShortcutMeta(name=name, color=seen.get("color"), glyph=seen.get("glyph"), input_types=input_types)

    def lower_block(self, stmts: list[ast.stmt], assigned: set[str], kinds: dict[str, ExprKind]) -> BlockResult:
        body,current,current_kinds = [],set(assigned),dict(kinds)
        for stmt in stmts:
            if isinstance(stmt, ast.Assign):
                assign = self.lower_assign(stmt, current, current_kinds)
                body.append(assign)
                current.add(assign.name)
                current_kinds[assign.name] = self.expr_kind(assign.value, current_kinds)
                continue
            if isinstance(stmt, ast.Expr):
                if not isinstance(stmt.value, ast.Call): raise self.error("Only action calls may be used as bare expressions", stmt)
                body.append(ExprStmt(self.lower_call(stmt.value, current, current_kinds)))
                continue
            if isinstance(stmt, ast.If):
                pred = self.lower_predicate(stmt.test, current, current_kinds)
                then_body,then_assigned,then_kinds = self.lower_block(stmt.body, current, current_kinds)
                if stmt.orelse: else_body,else_assigned,else_kinds = self.lower_block(stmt.orelse, current, current_kinds)
                else: else_body,else_assigned,else_kinds = [],set(current),dict(current_kinds)
                merged = then_assigned & else_assigned if stmt.orelse else set()
                body.append(IfStmt(pred, then_body, else_body, tuple(sorted(merged - current))))
                current |= merged
                for name in merged: current_kinds[name] = self.merge_kind(then_kinds.get(name), else_kinds.get(name))
                continue
            if isinstance(stmt, ast.For):
                loop = self.lower_for(stmt, current, current_kinds)
                body.append(loop)
                continue
            if isinstance(stmt, ast.Return):
                body.append(Return(self.lower_expr(stmt.value, current, current_kinds) if stmt.value else None))
                continue
            raise self.error(f"Unsupported statement: {stmt.__class__.__name__}", stmt)
        return body,current,current_kinds

    def lower_assign(self, stmt: ast.Assign, assigned: set[str], kinds: dict[str, ExprKind]) -> Assign:
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            raise self.error("Only simple name assignment is supported", stmt)
        return Assign(stmt.targets[0].id, self.lower_expr(stmt.value, assigned, kinds))

    def lower_for(self, stmt: ast.For, assigned: set[str], kinds: dict[str, ExprKind]) -> RepeatEach | RepeatCount:
        if not isinstance(stmt.target, ast.Name): raise self.error("Loop targets must be simple names", stmt.target)
        target = stmt.target.id
        inner_assigned = set(assigned)|{target}
        inner_kinds = dict(kinds)
        inner_kinds[target] = None
        if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name) and stmt.iter.func.id == "range":
            if len(stmt.iter.args) != 1 or stmt.iter.keywords: raise self.error("Only range(<int>) is supported", stmt.iter)
            count = self.literal_value(stmt.iter.args[0], "range count")
            if not isinstance(count, int): raise self.error("range() requires an integer literal", stmt.iter.args[0])
            body,_,_ = self.lower_block(stmt.body, inner_assigned, inner_kinds)
            return RepeatCount(target, count, body)
        source = self.lower_expr(stmt.iter, assigned, kinds)
        body,_,_ = self.lower_block(stmt.body, inner_assigned, inner_kinds)
        return RepeatEach(target, source, body)

    def lower_predicate(self, node: ast.expr, assigned: set[str], kinds: dict[str, ExprKind]) -> Predicate:
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or len(node.comparators) != 1: raise self.error("Only simple comparisons are supported", node)
            op = node.ops[0]
            if isinstance(op, ast.Eq): op_str = "=="
            elif isinstance(op, ast.NotEq): op_str = "!="
            elif isinstance(op, ast.Gt): op_str = ">"
            elif isinstance(op, ast.GtE): op_str = ">="
            elif isinstance(op, ast.Lt): op_str = "<"
            elif isinstance(op, ast.LtE): op_str = "<="
            else: raise self.error("Unsupported comparison operator", op)
            return Predicate(self.lower_expr(node.left, assigned, kinds), op_str, self.lower_expr(node.comparators[0], assigned, kinds))
        if isinstance(node, ast.Name):
            if node.id not in assigned: raise self.error(f"Unknown name: {node.id}", node)
            return Predicate(NameExpr(node.id), "==", LiteralExpr(True))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and isinstance(node.operand, ast.Name):
            if node.operand.id not in assigned: raise self.error(f"Unknown name: {node.operand.id}", node)
            return Predicate(NameExpr(node.operand.id), "==", LiteralExpr(False))
        raise self.error("Only simple comparisons and boolean names are supported in if statements", node)

    def lower_expr(self, node: ast.expr, assigned: set[str], kinds: dict[str, ExprKind]) -> Expr:
        if isinstance(node, ast.Name):
            if node.id not in assigned: raise self.error(f"Unknown name: {node.id}", node)
            return NameExpr(node.id)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float, bool)) or node.value is None: return LiteralExpr(node.value)
            raise self.error(f"Unsupported literal: {node.value!r}", node)
        if isinstance(node, ast.JoinedStr):
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str): parts.append(value.value)
                elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name):
                    if value.value.id not in assigned: raise self.error(f"Unknown name: {value.value.id}", value)
                    parts.append(NameExpr(value.value.id))
                else: raise self.error("Only simple names may be interpolated into f-strings", value)
            return FormattedText(parts)
        if isinstance(node, ast.List): return ListExpr([self.lower_expr(o, assigned, kinds) for o in node.elts])
        if isinstance(node, ast.Dict):
            items = []
            for key,value in zip(node.keys, node.values):
                if key is None: raise self.error("Dictionary unpacking is not supported", node)
                items.append((self.lower_expr(key, assigned, kinds), self.lower_expr(value, assigned, kinds)))
            return DictExpr(items)
        if isinstance(node, ast.Subscript): return self.lower_subscript(node, assigned, kinds)
        if isinstance(node, ast.Call): return self.lower_call(node, assigned, kinds)
        raise self.error(f"Unsupported expression: {node.__class__.__name__}", node)

    def lower_subscript(self, node: ast.Subscript, assigned: set[str], kinds: dict[str, ExprKind]) -> Expr:
        if isinstance(node.slice, ast.Slice): raise self.error("Slices are not supported", node.slice)
        source = self.lower_expr(node.value, assigned, kinds)
        source_kind = self.expr_kind(source, kinds)
        if source_kind == "list": return ListLookupExpr(source, self.literal_list_index(node.slice))
        if source_kind == "dict": return DictLookupExpr(source, self.lower_expr(node.slice, assigned, kinds))
        if self.is_negative_int_literal(node.slice): raise self.error("Negative list indices are not supported", node.slice)
        if self.is_int_literal(node.slice): return ListLookupExpr(source, self.literal_list_index(node.slice))
        return DictLookupExpr(source, self.lower_expr(node.slice, assigned, kinds))

    def lower_call(self, node: ast.Call, assigned: set[str], kinds: dict[str, ExprKind]) -> CallExpr:
        if not isinstance(node.func, ast.Name): raise self.error("Only direct DSL function calls are supported", node.func)
        if any(isinstance(arg, ast.Starred) for arg in node.args): raise self.error("Starred arguments are not supported", node)
        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None: raise self.error("**kwargs are not supported", node)
            kwargs[kw.arg] = self.lower_expr(kw.value, assigned, kinds)
        call = CallExpr(node.func.id, [self.lower_expr(arg, assigned, kinds) for arg in node.args], kwargs)
        self.validate_call(call, node)
        return call

    def validate_call(self, call: CallExpr, node: ast.Call) -> None:
        args,kwargs = call.args,call.kwargs
        match call.func:
            case "ask_for_text":
                self.expect_args(node, args, kwargs, min_args=1, max_args=1, allowed_kwargs={"default"})
            case "ask_for_datetime":
                self.expect_args(node, args, kwargs, min_args=1, max_args=1, allowed_kwargs={"default"})
            case "choose_from_menu":
                self.expect_args(node, args, kwargs, min_args=2, max_args=2, allowed_kwargs=set())
            case "show_result":
                self.expect_args(node, args, kwargs, min_args=1, max_args=1, allowed_kwargs=set())
            case "get_files":
                self.expect_args(node, args, kwargs, min_args=0, max_args=0, allowed_kwargs={"prompt"})
            case "preferred_language":
                self.expect_args(node, args, kwargs, min_args=0, max_args=0, allowed_kwargs=set())
            case "resize_image":
                self.expect_args(node, args, kwargs, min_args=1, max_args=1, allowed_kwargs={"width", "height"})
                if "width" not in kwargs: raise self.error("resize_image() requires width=", node)
            case "save_file":
                self.expect_args(node, args, kwargs, min_args=1, max_args=1, allowed_kwargs={"ask_where"})
            case "shortcut_input":
                self.expect_args(node, args, kwargs, min_args=0, max_args=0, allowed_kwargs=set())
            case "unix_timestamp":
                self.expect_args(node, args, kwargs, min_args=1, max_args=1, allowed_kwargs=set())
            case "raw_action":
                if not args: raise self.error("raw_action() requires an action identifier", node)
                if not isinstance(args[0], LiteralExpr) or not isinstance(args[0].value, str): raise self.error("raw_action() requires a string literal action identifier", node)
            case _ if spec := ACTION_SPECS.get(call.func):
                try: bind_action_spec(spec, args, kwargs)
                except ValueError as e: raise self.error(str(e), node) from e
            case "shortcut":
                raise self.error("shortcut() may only be used as a decorator", node)
            case _:
                raise self.error(f"Unknown DSL function: {call.func}", node)

    def expect_args(self, node: ast.AST, args: list[Expr], kwargs: dict[str, Expr], *, min_args: int, max_args: int, allowed_kwargs: set[str]) -> None:
        if not (min_args <= len(args) <= max_args): raise self.error("Unsupported argument shape", node)
        unexpected = set(kwargs) - allowed_kwargs
        if unexpected: raise self.error(f"Unexpected keyword arguments: {', '.join(sorted(unexpected))}", node)

    def literal_list_index(self, node: ast.expr) -> int:
        if self.is_negative_int_literal(node): raise self.error("Negative list indices are not supported", node)
        if not self.is_int_literal(node): raise self.error("List indices must be integer literals", node)
        assert isinstance(node, ast.Constant) and isinstance(node.value, int)
        return node.value

    def literal_string_list(self, node: ast.expr, context: str) -> list[str]:
        if not isinstance(node, (ast.List, ast.Tuple)): raise self.error(f"{context} must be a list or tuple of string literals", node)
        values = [self.literal_value(o, context) for o in node.elts]
        if not all(isinstance(o, str) for o in values): raise self.error(f"{context} must contain only string literals", node)
        return list(values)

    def literal_value(self, node: ast.expr, context: str) -> Any:
        if isinstance(node, ast.Constant): return node.value
        raise self.error(f"{context} must be a literal", node)

    def resolve_input_type(self, value: str, node: ast.AST) -> str:
        if value in DEFAULT_INPUT_CLASSES: return value
        try: return INPUT_TYPE_ALIASES[value]
        except KeyError as e: raise self.error(f"Unknown input type: {value}", node) from e

    def expr_kind(self, expr: Expr, kinds: dict[str, ExprKind]) -> ExprKind:
        match expr:
            case ListExpr():
                return "list"
            case DictExpr():
                return "dict"
            case NameExpr(name=name):
                return kinds.get(name)
            case CallExpr(func=func):
                if func in HANDWRITTEN_OUTPUT_KINDS: return HANDWRITTEN_OUTPUT_KINDS[func]
                if spec := ACTION_SPECS.get(func):
                    if spec["output"] == "array": return "list"
                    if spec["output"] == "dictionary": return "dict"
        return None

    def is_int_literal(self, node: ast.expr) -> bool:
        return isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool)

    def is_negative_int_literal(self, node: ast.expr) -> bool:
        return isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and self.is_int_literal(node.operand)

    def merge_kind(self, a: ExprKind, b: ExprKind) -> ExprKind: return a if a == b else None


class Emitter:
    def __init__(self):
        self.actions = []
        self.output_counts = {}
        self.symbols = [dict()]
        self.repeat_depth = 0
        self.has_shortcut_input_variables = False

    def emit(self, program: ShortcutProgram) -> dict[str, Any]:
        self.emit_block(program.body)
        icon = dict(WFWorkflowIconGlyphNumber=self.resolve_glyph(program.meta.glyph), WFWorkflowIconStartColor=self.resolve_color(program.meta.color))
        return PAYLOAD_TEMPLATE | dict(WFWorkflowActions=self.actions, WFWorkflowIcon=icon,
            WFWorkflowHasShortcutInputVariables=self.has_shortcut_input_variables,
            WFWorkflowInputContentItemClasses=(program.meta.input_types or DEFAULT_INPUT_CLASSES).copy(), WFWorkflowName=program.meta.name)

    def resolve_color(self, color: str | int | None) -> int:
        if color is None: return DEFAULT_COLOR
        if isinstance(color, int): return color
        try: return COLORS[color]
        except KeyError as e: raise CompileError(f"Unknown shortcut color: {color}") from e

    def resolve_glyph(self, glyph: str | int | None) -> int:
        if glyph is None: return DEFAULT_GLYPH
        if isinstance(glyph, int): return glyph
        try: return GLYPHS[glyph]
        except KeyError as e: raise CompileError(f"Unknown shortcut glyph: {glyph}") from e

    def push_scope(self) -> None: self.symbols.append(self.symbols[-1].copy())
    def pop_scope(self) -> None: self.symbols.pop()
    def bind(self, name: str, ref: Ref) -> None: self.symbols[-1][name] = ref
    def lookup(self, name: str) -> Ref: return self.symbols[-1][name]

    def emit_block(self, body: list[Stmt]) -> None:
        for stmt in body:
            match stmt:
                case Assign():
                    self.emit_assign(stmt)
                case ExprStmt():
                    self.emit_call(stmt.value, want_result=False)
                case IfStmt():
                    self.emit_if(stmt)
                case RepeatEach():
                    self.emit_repeat_each(stmt)
                case RepeatCount():
                    self.emit_repeat_count(stmt)
                case Return():
                    self.emit_return(stmt)

    def emit_assign(self, stmt: Assign) -> None:
        ref = self.eval_expr(stmt.value, hint=stmt.name)
        self.add_action("setvariable", dict(WFInput=self.attachment(ref), WFSerializationType="WFTextTokenAttachment", WFVariableName=stmt.name))
        self.bind(stmt.name, Ref("variable", stmt.name))

    def emit_if(self, stmt: IfStmt) -> None:
        group = str(uuid.uuid4())
        self.add_action("conditional", self.condition_start(group, stmt.predicate))
        self.push_scope()
        self.emit_maybe_empty(stmt.then_body)
        self.pop_scope()
        if stmt.else_body:
            self.add_action("conditional", {"GroupingIdentifier": group, "WFControlFlowMode": CF_ELSE})
            self.push_scope()
            self.emit_maybe_empty(stmt.else_body)
            self.pop_scope()
        self.add_action("conditional", dict(GroupingIdentifier=group, UUID=str(uuid.uuid4()), WFControlFlowMode=CF_END))
        for name in stmt.assigned_names: self.bind(name, Ref("variable", name))

    def emit_repeat_each(self, stmt: RepeatEach) -> None:
        group = str(uuid.uuid4())
        source = self.eval_expr(stmt.source, hint="List")
        self.add_action("repeat.each", dict(GroupingIdentifier=group, WFControlFlowMode=CF_START, WFInput=self.attachment(source)))
        self.repeat_depth += 1
        repeat_name = "Repeat Item" if self.repeat_depth == 1 else f"Repeat Item {self.repeat_depth}"
        self.push_scope()
        self.bind(stmt.target, Ref("variable", repeat_name))
        self.emit_maybe_empty(stmt.body)
        self.pop_scope()
        self.repeat_depth -= 1
        self.add_action("repeat.each", dict(GroupingIdentifier=group, UUID=str(uuid.uuid4()), WFControlFlowMode=CF_END))

    def emit_repeat_count(self, stmt: RepeatCount) -> None:
        group = str(uuid.uuid4())
        self.add_action("repeat.count", dict(GroupingIdentifier=group, WFControlFlowMode=CF_START, WFRepeatCount=stmt.count))
        self.repeat_depth += 1
        repeat_name = "Repeat Index" if self.repeat_depth == 1 else f"Repeat Index {self.repeat_depth}"
        self.push_scope()
        self.bind(stmt.target, Ref("variable", repeat_name))
        self.emit_maybe_empty(stmt.body)
        self.pop_scope()
        self.repeat_depth -= 1
        self.add_action("repeat.count", dict(GroupingIdentifier=group, UUID=str(uuid.uuid4()), WFControlFlowMode=CF_END))

    def emit_return(self, stmt: Return) -> None:
        if stmt.value is None:
            self.add_action("nothing", {})
            return
        self.add_action("output", {"WFOutput": self.text_value(stmt.value)})

    def emit_maybe_empty(self, body: list[Stmt]) -> None:
        if body: self.emit_block(body)
        else: self.add_action("nothing", {})

    def eval_expr(self, expr: Expr, hint: str | None = None) -> Ref:
        match expr:
            case NameExpr(name=name):
                return self.lookup(name)
            case LiteralExpr() | FormattedText():
                return self.emit_value_action("gettext" if self.is_text(expr) else "number", self.value_params(expr), hint or self.default_output(expr))
            case ListExpr():
                return self.emit_value_action("list", {"WFItems": [self.list_item(item) for item in expr.items]}, hint or "List")
            case DictExpr():
                return self.emit_value_action("dictionary", {"WFItems": self.dictionary_value(expr)}, hint or "Dictionary")
            case DictLookupExpr():
                return self.emit_value_action("getvalueforkey", self.dict_lookup_params(expr), hint or "Dictionary Value")
            case ListLookupExpr():
                return self.emit_value_action("getitemfromlist", self.list_lookup_params(expr), hint or "List Item")
            case CallExpr():
                return self.emit_call(expr, want_result=True, hint=hint or expr.func)
        raise ValueError(f"Unsupported expr: {expr}")

    def emit_call(self, call: CallExpr, *, want_result: bool, hint: str | None = None) -> Ref | None:
        def arg(i: int) -> Expr: return call.args[i]
        def kw(name: str, default: Expr | None = None) -> Expr | None: return call.kwargs.get(name, default)
        match call.func:
            case "ask_for_text":
                params = {"WFAskActionPrompt": self.text_value(arg(0))}
                if default := kw("default"): params["WFAskActionDefaultAnswer"] = self.text_value(default)
                return self.emit_action_value("ask", params, want_result, hint or "Ask")
            case "ask_for_datetime":
                params = {"WFAskActionPrompt": self.text_value(arg(0)), "WFInputType": "Date and Time"}
                if default := kw("default"): params["WFAskActionDefaultAnswerDateAndTime"] = self.text_value(default)
                return self.emit_action_value("ask", params, want_result, hint or "Input Date and Time")
            case "choose_from_menu":
                params = dict(WFInput=self.attachment(self.eval_expr(arg(1), hint="List")), WFChooseFromListActionPrompt=self.text_value(arg(0)))
                return self.emit_action_value("choosefromlist", params, want_result, hint or "Chosen Item")
            case "show_result":
                self.add_action("showresult", {"Text": self.text_value(arg(0))})
                return None
            case "get_files":
                params = {"SelectMultiple": True}
                return self.emit_action_value("file.select", params, want_result, hint or "Selected Files")
            case "preferred_language":
                empty = self.emit_value_action("gettext", {"WFTextActionText": ""}, "Text")
                params = dict(Script="defaults read -g AppleLocale | cut -c1-2 | tr -d '\\n'", Input=self.attachment(empty), Shell="/bin/zsh")
                return self.emit_action_value("runshellscript", params, want_result, hint or "Preferred Language")
            case "resize_image":
                params = dict(WFImage=self.attachment(self.eval_expr(arg(0), hint="Image")), WFImageResizeWidth=str(self.require_numberish(kw("width"))))
                if height := kw("height"): params["WFImageResizeHeight"] = str(self.require_numberish(height))
                return self.emit_action_value("image.resize", params, want_result, hint or "Resize Image")
            case "save_file":
                ask_where = kw("ask_where")
                if isinstance(ask_where, LiteralExpr) and ask_where.value is False:
                    raise CompileError("save_file(..., ask_where=False) is not supported in the MVP")
                params = {"WFInput": self.attachment(self.eval_expr(arg(0), hint="File"))}
                return self.emit_action_value("documentpicker.save", params, want_result, hint or "Saved File")
            case "shortcut_input":
                self.has_shortcut_input_variables = True
                return Ref("special", "ExtensionInput") if want_result else None
            case "unix_timestamp":
                params = dict(WFInput=self.text_value(arg(0)), WFTimeUntilFromDate="1970-01-01T00:00Z", WFTimeUntilUnit="Seconds")
                return self.emit_action_value("gettimebetweendates", params, want_result, hint or "Unix Timestamp")
            case "raw_action":
                ident = call.args[0]
                assert isinstance(ident, LiteralExpr) and isinstance(ident.value, str)
                params = {k: self.raw_value(v) for k,v in call.kwargs.items()}
                return self.emit_action_value(ident.value, params, want_result, hint or self.short_name(ident.value))
            case _ if spec := ACTION_SPECS.get(call.func):
                bound = bind_action_spec(spec, call.args, call.kwargs)
                params = dict(spec["fixed"])
                for param in spec["params"]:
                    if param["key"] not in bound: continue
                    params[param["key"]] = self.encode_action_param(bound[param["key"]], param["kind"])
                return self.emit_action_value(spec["identifier"], params, want_result, hint or call.func.replace("_", " ").title())
        raise ValueError(f"Unsupported call: {call.func}")

    def emit_action_value(self, ident: str, params: dict[str, Any], want_result: bool, hint: str) -> Ref | None:
        if not want_result:
            self.add_action(ident, params)
            return None
        return self.emit_value_action(ident, params, hint)

    def emit_value_action(self, ident: str, params: dict[str, Any], hint: str) -> Ref:
        output_name = self.next_output_name(hint)
        output_uuid = str(uuid.uuid4())
        full_params = {"CustomOutputName": output_name, "UUID": output_uuid, **params}
        self.add_action(ident, full_params)
        return Ref("action_output", output_name, output_uuid)

    def add_action(self, ident: str, params: dict[str, Any]) -> None:
        if not ident.startswith(FULL_ACTION_PREFIXES): ident = f"is.workflow.actions.{ident}"
        self.actions.append({"WFWorkflowActionIdentifier": ident, "WFWorkflowActionParameters": params})

    def next_output_name(self, base: str) -> str:
        count = self.output_counts.get(base, 0)
        self.output_counts[base] = count + 1
        return base if count == 0 else f"{base} {count}"

    def attachment(self, ref: Ref) -> dict[str, Any]:
        return {"Value": ref.action_value(), "WFSerializationType": "WFTextTokenAttachment"}

    def text_value(self, expr: Expr) -> Any:
        match expr:
            case LiteralExpr(value=value) if isinstance(value, str):
                return value
            case FormattedText(parts=parts):
                return self.formatted_text(parts)
            case NameExpr():
                return self.formatted_text([self.lookup(expr.name)])
            case _:
                ref = self.eval_expr(expr, hint="Text")
                return self.formatted_text([ref])

    def formatted_text(self, parts: list[str | NameExpr | Ref]) -> dict[str, Any]:
        attachments,text,pos = {},[],0
        for part in parts:
            if isinstance(part, str):
                text.append(part)
                pos += utf16_len(part)
                continue
            ref = part if isinstance(part, Ref) else self.lookup(part.name)
            attachments[f"{{{pos}, 1}}"] = ref.action_value()
            text.append(OBJECT_REPLACEMENT)
            pos += 1
        return {"Value": {"attachmentsByRange": attachments, "string": "".join(text)}, "WFSerializationType": "WFTextTokenString"}

    def condition_start(self, group: str, predicate: Predicate) -> dict[str, Any]:
        left = self.eval_expr(predicate.left, hint="Condition")
        template = dict(WFCondition=CONDITION_CODES[predicate.op], WFInput=dict(Type="Variable", Variable=self.attachment(left)))
        match predicate.right:
            case LiteralExpr(value=value) if isinstance(value, bool):
                template["WFNumberValue"] = 1 if value else 0
            case LiteralExpr(value=value) if isinstance(value, (int, float)):
                template["WFNumberValue"] = value
            case _:
                template["WFConditionalActionString"] = self.text_value(predicate.right)
        conditions = dict(Value=dict(WFActionParameterFilterPrefix=1, WFActionParameterFilterTemplates=[template]), WFSerializationType="WFContentPredicateTableTemplate")
        return dict(GroupingIdentifier=group, WFConditions=conditions, WFControlFlowMode=CF_START)

    def list_item(self, expr: Expr) -> dict[str, Any]:
        if isinstance(expr, DictExpr): return {"WFItemType": 1, "WFValue": self.dictionary_field(expr)}
        if isinstance(expr, ListExpr): return {"WFItemType": 2, "WFValue": self.array_field(expr)}
        if isinstance(expr, LiteralExpr) and isinstance(expr.value, bool): return {"WFItemType": 4, "WFValue": {"Value": expr.value, "WFSerializationType": "WFNumberSubstitutableState"}}
        if isinstance(expr, LiteralExpr) and isinstance(expr.value, (int, float)): return {"WFItemType": 3, "WFValue": self.text_token(str(expr.value))}
        return {"WFItemType": 0, "WFValue": self.text_field(expr)}

    def dict_lookup_params(self, expr: DictLookupExpr) -> dict[str, Any]:
        return dict(WFDictionaryKey=self.dictionary_lookup_key(expr.key), WFGetDictionaryValueType="Value",
            WFInput=self.attachment(self.eval_expr(expr.source, hint="Dictionary")))

    def dictionary_lookup_key(self, expr: Expr) -> Any:
        if isinstance(expr, LiteralExpr) and isinstance(expr.value, str): return expr.value
        return self.text_value(expr)

    def list_lookup_params(self, expr: ListLookupExpr) -> dict[str, Any]:
        return dict(WFInput=self.attachment(self.eval_expr(expr.source, hint="List")), WFItemIndex=expr.index + 1, WFItemSpecifier="Item At Index")

    def dictionary_value(self, expr: DictExpr) -> dict[str, Any]:
        return {"Value": {"WFDictionaryFieldValueItems": [self.dictionary_item(k, v) for k,v in expr.items]}, "WFSerializationType": "WFDictionaryFieldValue"}

    def dictionary_item(self, key: Expr, value: Expr) -> dict[str, Any]:
        item = self.list_item(value)
        return dict(WFItemType=item["WFItemType"], WFKey=self.text_field(key), WFValue=item["WFValue"])

    def dictionary_field(self, expr: DictExpr) -> dict[str, Any]:
        return {"Value": {"Value": {"WFDictionaryFieldValueItems": [self.dictionary_item(k, v) for k,v in expr.items]}, "WFSerializationType": "WFDictionaryFieldValue"}, "WFSerializationType": "WFDictionaryFieldValue"}

    def array_field(self, expr: ListExpr) -> dict[str, Any]:
        return {"Value": [self.list_item(item) for item in expr.items], "WFSerializationType": "WFArrayParameterState"}

    def text_field(self, expr: Expr) -> dict[str, Any]:
        value = self.text_value(expr)
        if isinstance(value, str): return self.text_token(value)
        return value

    def text_token(self, value: str) -> dict[str, Any]:
        return {"Value": {"string": value}, "WFSerializationType": "WFTextTokenString"}

    def encode_action_param(self, expr: Expr, kind: str) -> Any:
        if kind == "variable": return self.attachment(self.eval_expr(expr))
        if kind in {"rawtext", "text"}: return self.text_value(expr)
        return self.raw_value(expr)

    def raw_value(self, expr: Expr) -> Any:
        match expr:
            case LiteralExpr(value=value):
                if isinstance(value, str): return self.text_value(expr)
                return value
            case NameExpr():
                return self.attachment(self.lookup(expr.name))
            case FormattedText() | CallExpr():
                return self.text_value(expr)
            case DictLookupExpr() | ListLookupExpr():
                return self.attachment(self.eval_expr(expr))
            case ListExpr(items=items):
                return [self.raw_value(item) for item in items]
            case DictExpr(items=items):
                return {self.raw_dict_key(k): self.raw_value(v) for k,v in items}
        raise ValueError(f"Unsupported raw value: {expr}")

    def raw_dict_key(self, expr: Expr) -> str:
        if isinstance(expr, LiteralExpr) and isinstance(expr.value, str): return expr.value
        raise CompileError("Dictionary keys must be string literals in raw action parameters")

    def value_params(self, expr: LiteralExpr | FormattedText) -> dict[str, Any]:
        if self.is_text(expr): return {"WFTextActionText": self.text_value(expr)}
        value = expr.value if isinstance(expr, LiteralExpr) else None
        if isinstance(value, bool): value = 1 if value else 0
        return {"WFNumberActionNumber": value}

    def require_numberish(self, expr: Expr | None) -> str | int | float:
        if not isinstance(expr, LiteralExpr) or not isinstance(expr.value, (int, float, str)):
            raise CompileError("This parameter requires a literal number or string")
        return expr.value

    def default_output(self, expr: Expr) -> str:
        if isinstance(expr, LiteralExpr): return "Text" if isinstance(expr.value, str) or expr.value is None else "Number"
        if isinstance(expr, FormattedText): return "Text"
        return "Value"

    def is_text(self, expr: Expr) -> bool:
        return isinstance(expr, FormattedText) or isinstance(expr, LiteralExpr) and isinstance(expr.value, (str, type(None)))

    def short_name(self, ident: str) -> str: return ident.rsplit(".", maxsplit=1)[-1]


def utf16_len(text: str) -> int: return len(text.encode("utf-16-le")) // 2
