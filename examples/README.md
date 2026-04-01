# Examples

Small, focused examples inspired by Cherri's tiny test shortcuts.

Compile one without signing:

```bash
shortcutpy examples/hello_world.py --skip-sign
```

Compile and sign:

```bash
shortcutpy examples/hello_world.py
```

Files here:

- `conditionals.py`: focused `if/else` example using bare `@shortcut`
- `hello_world.py`: smallest useful shortcut
- `choose_tone.py`: input, menu, `if`, and `return`
- `get_current_weather.py`: generated action wrapper for the current weather
- `repeats.py`: `for item in items` and `for _ in range(n)`
- `resize_images.py`: file selection, image resize, save
- `raw_action_alert.py`: drop down to a raw Shortcuts action
