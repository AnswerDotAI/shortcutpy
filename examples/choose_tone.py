from shortcutpy.dsl import ask_for_text, choose_from_menu, shortcut


@shortcut(name="Choose Tone", color="green", glyph="chatBubble")
def main():
    name = ask_for_text("What is your name?")
    tone = choose_from_menu("Tone", ["formal", "casual"])
    if tone == "formal": return f"Good day, {name}."
    return f"Hey {name}!"
