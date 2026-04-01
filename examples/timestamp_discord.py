from shortcutpy.dsl import *


# In examples we use `import *` on purpose: the file reads like a shortcut, not like import bookkeeping.
# `@shortcut` marks the single function that should become the Shortcut.
# `color=` and `glyph=` become icon metadata, and `input_types=` narrows `WFWorkflowInputContentItemClasses`.
# The first statement in the body uses `comment()`, which compiles to one native Shortcuts Comment action.
@shortcut(color="pink", glyph="chatBubble", input_types=["text", "date"])
def timestamp_discord():
    comment("Generate a Discord timestamp code and copy it to the clipboard.")

    # The original shortcut localized itself.
    # This tutorial keeps one language so it stays permission-free: there is no native Shortcuts action here for the current macOS locale,
    # so auto-detecting language would require `preferred_language()`, which emits Run Shell Script.
    # A Python dict literal becomes one Shortcuts Dictionary action, and `dict[key]` compiles to Get Value from Dictionary.
    # chkstyle: off
    text = {"select-date-time": "Select the date and time for your code",
        "select-style": "Select a style for your code",
        "long-date-time-name": "Long date and time",
        "short-date-time-name": "Short date and time",
        "long-date-name": "Long date",
        "short-date-name": "Short date",
        "long-time-name": "Long time",
        "short-time-name": "Short time",
        "relative-time-name": "Relative time",
        "copied-to-clipboard": "%s copied to clipboard",
    }
    # chkstyle: on
    select_date_time = text["select-date-time"]
    select_style = text["select-style"]
    long_date_time_name = text["long-date-time-name"]
    short_date_time_name = text["short-date-time-name"]
    long_date_name = text["long-date-name"]
    short_date_name = text["short-date-name"]
    long_time_name = text["long-time-name"]
    short_time_name = text["short-time-name"]
    relative_time_name = text["relative-time-name"]
    copied_to_clipboard = text["copied-to-clipboard"]

    # `shortcut_input()` is special: it does not emit an action, it references the Shortcut Input variable directly.
    # `get_clipboard()` and `current_date()` are normal action wrappers.
    # The f-string becomes a Text action with variable attachments, which is how `shortcutpy` represents interpolation.
    shared = shortcut_input()
    clipboard = get_clipboard()
    now = current_date()
    source = f"{shared}\n{clipboard}\n{now}"

    # `get_dates()` returns a list output, and `list[0]` now maps to Shortcuts' Get Item from List action.
    # The indexing syntax stays Pythonic, but `shortcutpy` translates the zero-based index to Shortcuts' one-based indexing.
    # `ask_for_datetime()` is another hand-written helper; it emits the Ask action in Date and Time mode.
    dates = get_dates(source)
    selected = now
    if count(dates) > 0: selected = dates[0]
    picked = ask_for_datetime(select_date_time, default=selected)

    # Each formatting call below becomes one Shortcuts action whose output we can keep reusing.
    # The generated wrappers such as `format_timestamp()`, `replace_text()`, and `match_text()` all come from Cherri metadata.
    # This is a good example of the `shortcutpy` model: write expressions naturally, let the compiler build the action graph.
    weekday = format_timestamp(picked, custom_date_format="EEEE")
    long_date = format_timestamp(picked, date_format="Long")

    # Nested calls are allowed, so this line lowers to a small pipeline of formatting, regex replace, and regex match actions.
    # We use that pipeline to normalize the short date preview before showing it in the style menu.
    short_date = match_text("^.{6}", replace_text("(?m)(^|/)(\\d)(?=/)", "$10$2", format_timestamp(picked, date_format="Short"), reg_exp=True))
    year = format_timestamp(picked, custom_date_format="yyyy")
    long_time = format_timestamp(picked, time_format="Medium")
    short_time = format_timestamp(picked, time_format="Short")
    relative_time = format_timestamp(picked, date_format="Relative")

    long_date_time_option = f"{long_date_time_name}  {weekday}, {long_date} {short_time}"
    short_date_time_option = f"{short_date_time_name}  {long_date} {short_time}"
    long_date_option = f"{long_date_name}  {long_date}"
    short_date_option = f"{short_date_name}  {short_date}{year}"
    long_time_option = f"{long_time_name}  {long_time}"
    short_time_option = f"{short_time_name}  {short_time}"
    relative_time_option = f"{relative_time_name}  {relative_time}"

    # A Python list literal lowers to a Shortcuts List action.
    # `choose_from_menu()` then wraps Choose from List, and its return value is just another variable in the program.
    options = [long_date_time_option, short_date_time_option, long_date_option, short_date_option, long_time_option,
        short_time_option, relative_time_option]
    style = choose_from_menu(select_style, options)

    # Dictionary literals can use earlier values as keys, and `dict[key]` works with variable keys too.
    # That lets a lookup table replace an `if` / `elif` ladder while still compiling to native Dictionary actions.
    # chkstyle: off
    style_codes = {long_date_time_option: "F",
        short_date_time_option: "f",
        long_date_option: "D",
        short_date_option: "d",
        long_time_option: "T",
        short_time_option: "t",
        relative_time_option: "R"}
    # chkstyle: on
    code = style_codes[style]

    # `unix_timestamp()` emits Get Time Between Dates with the Unix epoch as the fixed start date.
    # The final f-string again becomes a Text action with attachments rather than eager Python string formatting.
    # `set_clipboard()` and `show_notification()` are generated wrappers over the native Shortcuts actions.
    ts = unix_timestamp(picked)
    discord_code = f"<t:{ts}:{code}>"
    set_clipboard(discord_code)
    show_notification(replace_text("%s", discord_code, copied_to_clipboard), play_sound=False)
