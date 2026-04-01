from shortcutpy.dsl import *


@shortcut
def coffee_or_tea():
    drink = ask_for_text("Coffee or tea?")
    if drink == "coffee": show_result("Grinding beans")
    else: show_result("Boiling the kettle")
