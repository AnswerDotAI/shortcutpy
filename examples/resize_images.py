from shortcutpy.dsl import *


@shortcut(name="Resize Images", color="lightblue", glyph="image")
def main():
    files = get_files()
    for image in files:
        resized = resize_image(image, width=1200)
        save_file(resized)
