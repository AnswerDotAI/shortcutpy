from shortcutpy.dsl import shortcut, show_result


@shortcut(name="Repeat Demo", color="blue", glyph="textBubble")
def main():
    people = ["Ada", "Grace", "Linus"]
    for person in people: show_result(f"Hello {person}")
    for i in range(3): show_result(f"Round {i}")
