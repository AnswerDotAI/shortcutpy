# DEV

`shortcutpy` is a tiny compiler:

1. Parse a Python file into an AST.
2. Lower a restricted subset into a small IR.
3. Emit the Shortcut payload plist.
4. Ask macOS to sign it with `shortcuts sign`.

## Key Files

- [shortcutpy/compiler.py](/Users/jhoward/git/shortcutpy/shortcutpy/compiler.py): parser/lowerer/emitter/signing path
- [shortcutpy/dsl.py](/Users/jhoward/git/shortcutpy/shortcutpy/dsl.py): runtime stubs for the DSL surface
- [shortcutpy/dsl.pyi](/Users/jhoward/git/shortcutpy/shortcutpy/dsl.pyi): typing for the DSL
- [shortcutpy/cli.py](/Users/jhoward/git/shortcutpy/shortcutpy/cli.py): `shortcutpy ...`
- [tests/test_compiler.py](/Users/jhoward/git/shortcutpy/tests/test_compiler.py): focused compiler/signing tests

## Compiler Shape

`compile_source()` is the entrypoint for in-memory compilation. It parses Python, runs `Lowerer`, then runs `Emitter`.

`Lowerer` does two jobs:

- enforce the MVP language subset
- convert Python AST into a simpler IR (`Assign`, `IfStmt`, `RepeatEach`, `CallExpr`, and so on)

This keeps AST weirdness out of emission. If you're adding syntax, it usually belongs here first.

`Emitter` turns that IR into the plist structure Shortcuts expects. The main thing to keep in mind is that Shortcuts values are often references, not raw values:

- variables are referenced by name
- action outputs are referenced by output name plus UUID
- text interpolation uses `WFTextTokenString` attachments

`Ref` is the glue for that. If a new action returns a value, make sure it returns the right kind of `Ref`.

## Signing

Unsigned output is a normal binary plist written by `plistlib`.

Signed `.shortcut` files are not plists. They are packaged by Apple's `shortcuts sign` tool, and the result starts with `AEA1`. So this is expected:

- `plutil -p unsigned.shortcut` works
- `plutil -p signed.shortcut` fails

If signing fails while hacking from Codex, the first thing to suspect is sandboxing, not plist format. Native `shortcuts sign` works fine outside the sandbox.

## Adding A DSL Action

For most new actions, the loop is:

1. Add the runtime stub in [shortcutpy/dsl.py](/Users/jhoward/git/shortcutpy/shortcutpy/dsl.py) and typing in [shortcutpy/dsl.pyi](/Users/jhoward/git/shortcutpy/shortcutpy/dsl.pyi).
2. Validate its argument shape in `Lowerer.validate_call()`.
3. Emit the action in `Emitter.emit_call()`.
4. Add a small test in [tests/test_compiler.py](/Users/jhoward/git/shortcutpy/tests/test_compiler.py).

Keep it direct. Most actions only need parameter shaping plus either `emit_action_value()` or `add_action()`.

## Useful Commands

```bash
pip install -e .[dev]
pytest -q
chkstyle shortcutpy tests
```

Compile without signing:

```bash
shortcutpy path/to/file.py --skip-sign
```

Compile and sign:

```bash
shortcutpy path/to/file.py
```

Compile, sign, and open:

```bash
shortcutpy -o path/to/file.py
```

## Versioning And Release

Version lives in [shortcutpy/__init__.py](/Users/jhoward/git/shortcutpy/shortcutpy/__init__.py) as `__version__`.

Bump it with:

```bash
ship-bump --part 2   # patch
ship-bump --part 1   # minor
ship-bump --part 0   # major
```

Release flow:

1. Ensure GitHub issues are labeled `bug`, `enhancement`, or `breaking`.
2. Run:

```bash
ship-gh
ship-pypi
```
