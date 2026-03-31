from shortcutpy.dsl import get_files, resize_image, save_file, shortcut


@shortcut(name="Resize Images", color="lightblue", glyph="image")
def main():
    files = get_files()
    for image in files:
        resized = resize_image(image, width=1200)
        save_file(resized)
