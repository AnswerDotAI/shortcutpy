from .action_catalog import ACTION_SPECS


def _runtime_only(name: str):
    raise RuntimeError(f"`{name}` is only for shortcutpy source files; compile the file instead of running it")


def shortcut(fn=None, /, *, name: str | None = None, color: str | int | None = None, glyph: str | int | None = None, input_types=None):
    def dec(fn): return fn
    return dec(fn) if fn is not None else dec


def ask_for_datetime(prompt, /, *, default=None): _runtime_only("ask_for_datetime")
def ask_for_text(prompt: str, /, *, default: str | None = None): _runtime_only("ask_for_text")
def choose_from_menu(prompt: str, options, /): _runtime_only("choose_from_menu")
def show_result(value, /): _runtime_only("show_result")
def get_files(*, prompt: str | None = None): _runtime_only("get_files")
def preferred_language(): _runtime_only("preferred_language")
def resize_image(image, /, *, width: int, height: int | None = None): _runtime_only("resize_image")
def save_file(value, /, *, ask_where: bool = True): _runtime_only("save_file")
def raw_action(action_id: str, /, **params): _runtime_only("raw_action")
def shortcut_input(): _runtime_only("shortcut_input")
def unix_timestamp(date, /): _runtime_only("unix_timestamp")


def _make_stub(name: str, doc: str):
    def stub(*args, **kwargs): _runtime_only(name)
    stub.__name__,stub.__doc__ = name,doc
    return stub


__all__ = ["shortcut", "ask_for_datetime", "ask_for_text", "choose_from_menu", "show_result", "get_files", "preferred_language",
    "resize_image", "save_file", "raw_action", "shortcut_input", "unix_timestamp"]
for name,spec in ACTION_SPECS.items():
    globals()[name] = _make_stub(name, spec["doc"])
    __all__.append(name)
