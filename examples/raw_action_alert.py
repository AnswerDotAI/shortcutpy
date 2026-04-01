from shortcutpy.dsl import *


@shortcut(name="Raw Action Alert", color="orange", glyph="alert")
def main():
    name = ask_for_text("Who should we greet?")
    raw_action("alert", WFAlertActionTitle="shortcutpy", WFAlertActionMessage=f"Hello {name}!")
