# shortcutpy

Compile a small Python-shaped DSL into Apple Shortcuts on macOS.

Shoutout to Cherri for inspiration and ideas.

## Status

This is the MVP compiler:

- one file = one shortcut
- one `@shortcut(...)`-decorated `main()`
- assignments, action calls, `if/else`, `for item in items`, `for _ in range(n)`, and `return`
- literals, f-strings, list literals, and dict literals
- native signing via `shortcuts sign`

## Example

```python
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
```

## Usage

Install in editable mode:

```bash
pip install -e .[dev]
```

Compile and sign:

```bash
shortcutpy path/to/shortcut.py
```

Compile, sign, and open the result in Shortcuts.app:

```bash
shortcutpy -o path/to/shortcut.py
```

Write an unsigned shortcut file instead:

```bash
shortcutpy path/to/shortcut.py --skip-sign
```

## Examples

See [examples/README.md](/Users/jhoward/git/shortcutpy/examples/README.md) and the files in [examples](/Users/jhoward/git/shortcutpy/examples).

## Current DSL Surface

`shortcutpy.dsl` currently provides:

- `shortcut`
- `ask_for_text`
- `choose_from_menu`
- `show_result`
- `get_files`
- `resize_image`
- `save_file`
- `raw_action`

`glyph=` accepts a small built-in name map or an integer glyph id. `color=` accepts the standard Shortcuts color names or an integer color value.

## Development

```bash
pip install -e .[dev]
```

For internals, release steps, and the signing/debugging notes, see [DEV.md](/Users/jhoward/git/shortcutpy/DEV.md).
