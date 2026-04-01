# shortcutpy

Compile a small Python-shaped DSL into Apple Shortcuts on macOS.

Shoutout to Cherri for inspiration and ideas.

## Example

```python
from shortcutpy.dsl import shortcut, ask_for_text, choose_from_menu, show_result

@shortcut(color="yellow", glyph="hand")
def greeting():
    name = ask_for_text("What is your name?")
    tone = choose_from_menu("Tone", ["formal", "casual"])
    if tone == "formal": message = f"Good day, {name}."
    else: message = f"Hey {name}!"
    show_result(message)
```

With bare `@shortcut`, the shortcut name defaults from the function name, so `greeting` becomes `Greeting` and `get_current_weather` becomes `Get Current Weather`.

## Status

- one file = one shortcut
- one `@shortcut`-decorated function
- assignments, action calls, `if/else`, `for item in items`, `for _ in range(n)`, and `return`
- literals, f-strings, list literals, dict literals, and `x[...]` lookups
- native signing via `shortcuts sign`

## Usage

Install in editable mode:

```bash
pip install -e .[dev]
```

Compile and sign:

```bash
shortcutpy path/to/shortcut.py
```

By default this writes `<shortcut name>.shortcut` next to the source file. For instance, `@shortcut(name="Current Weather")` writes `Current Weather.shortcut`.

Compile, sign, and open the result in Shortcuts.app:

```bash
shortcutpy -o path/to/shortcut.py
```

With `-o` and no `-O`, `shortcutpy` builds into a temp directory first, so it doesn't leave a `.shortcut` file next to your source.

Write somewhere else:

```bash
shortcutpy -O /tmp/my.shortcut path/to/shortcut.py
```

Dump an installed shortcut from Shortcuts.app to the text reference format used in `examples/`:

```bash
shortcutpy dump "timestamp discord" -O examples/timestamp_discord.original.txt
```

Write an unsigned shortcut file instead:

```bash
shortcutpy path/to/shortcut.py --skip-sign
```

Keep the intermediate unsigned file when signing:

```bash
shortcutpy path/to/shortcut.py --keep-unsigned
```

Choose a signing mode:

```bash
shortcutpy path/to/shortcut.py --mode anyone
```

## Supported Python Subset

Module level:

- only imports from `shortcutpy.dsl`
- one shortcut function per file
- no other top-level statements

Decorator and function shape:

- `@shortcut`
- `@shortcut(...)`
- any function name
- no function parameters
- `name=`, `color=`, `glyph=`, and `input_types=` on the decorator
- if `name=` is omitted, the function name is converted from `snake_case` to spaced capitalized words

Supported statements:

- simple assignment: `x = ...`
- action call as a statement
- `if/else`
- `for item in items`
- `for i in range(<int literal>)`
- `return`

Supported expressions:

- variable references
- literals: `str`, `int`, `float`, `bool`, `None`
- DSL action calls
- list literals
- dict literals, including variable keys like `{key: value}`
- dictionary lookup with literal or variable keys: `mapping["key"]` or `mapping[key]`
- list indexing with non-negative integer literals: `items[0]`
- simple f-strings with name interpolation only

Supported `if` conditions:

- simple comparisons: `==`, `!=`, `>`, `>=`, `<`, `<=`
- boolean name checks: `if flag:`
- negated boolean name checks: `if not flag:`

Not currently supported:

- arithmetic like `a + b`
- boolean `and` / `or`
- chained comparisons
- `while`
- comprehensions
- attribute access like `obj.attr`
- slices like `items[1:3]`
- dynamic list indices like `items[i]`
- method calls
- destructuring assignment
- starred args or `**kwargs`
- aliasing DSL calls to different names

## Examples

See [examples/README.md](examples/README.md) and the files in [examples](examples).

## Current DSL Surface

`shortcutpy.dsl` currently provides the hand-written MVP helpers:

- `shortcut`
- `ask_for_datetime`
- `ask_for_text`
- `choose_from_menu`
- `show_result`
- `get_files`
- `preferred_language`
- `resize_image`
- `save_file`
- `raw_action`
- `shortcut_input`
- `unix_timestamp`

It also exposes a generated catalog of Shortcuts actions sourced from Cherri's action definitions, including wrappers like `alert`, `show_notification`, `toggle_dnd`, `combine_images`, `resize_image_by_percent`, `get_current_weather`, and `save_file_to_path`.

For the exact generated names and typed signatures, see [shortcutpy/dsl.pyi](shortcutpy/dsl.pyi).

`shortcut_input()` references the Shortcut Input variable and flips `WFWorkflowHasShortcutInputVariables` in the emitted payload.
`preferred_language()` emits a small macOS shell-script action that returns the current two-letter `AppleLocale` language code, so using it may trigger Shortcuts' shell-script permission prompt.
`input_types=` on `@shortcut` narrows `WFWorkflowInputContentItemClasses`; for instance `input_types=["text", "date"]`.
`glyph=` accepts a small built-in name map or an integer glyph id. `color=` accepts the standard Shortcuts color names or an integer color value.

## Development

```bash
pip install -e .[dev]
```

For internals, release steps, and the signing/debugging notes, see [DEV.md](DEV.md).
