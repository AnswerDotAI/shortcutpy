from shortcutpy.dsl import shortcut, show_result


@shortcut(name="Hello, shortcutpy!", color="yellow", glyph="smileyFace")
def main(): show_result("Hello, shortcutpy!")
