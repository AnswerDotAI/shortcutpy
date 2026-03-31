def _runtime_only(name: str):
    raise RuntimeError(f"`{name}` is only for shortcutpy source files; compile the file instead of running it")


def shortcut(*, name: str, color: str | int | None = None, glyph: str | int | None = None):
    def dec(fn): return fn
    return dec


def ask_for_text(prompt: str, /, *, default: str | None = None): _runtime_only("ask_for_text")
def choose_from_menu(prompt: str, options, /): _runtime_only("choose_from_menu")
def show_result(value, /): _runtime_only("show_result")
def get_files(*, prompt: str | None = None): _runtime_only("get_files")
def resize_image(image, /, *, width: int, height: int | None = None): _runtime_only("resize_image")
def save_file(value, /, *, ask_where: bool = True): _runtime_only("save_file")
def raw_action(action_id: str, /, **params): _runtime_only("raw_action")
