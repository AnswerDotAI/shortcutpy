from shortcutpy.dsl import get_current_weather, shortcut, show_result


@shortcut(name="Current Weather", color="blue")
def main():
    weather = get_current_weather()
    show_result(weather)
