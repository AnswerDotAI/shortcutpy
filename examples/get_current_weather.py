from shortcutpy.dsl import *


@shortcut(name="Current Weather", color="blue")
def main():
    weather = get_current_weather()
    show_result(weather)
