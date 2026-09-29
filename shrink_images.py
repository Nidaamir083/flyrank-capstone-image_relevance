"""
shrink_images.py

What this script does, in plain words:
- Looks at every .jpg inside the images/ folder
- If a photo is bigger than 500 KB, it makes it smaller (max 1200 pixels on the long side)
- Saves it back under the SAME name, so your saved tags still match the file

Run it with:
    python shrink_images.py

Note: this replaces the big original. If you ever need the original again,
you can download it again from Pexels.
"""

import os
import glob

from PIL import Image, ImageOps

IMAGES_FOLDER = "images"
MAX_SIDE = 1200          # longest side in pixels
BIG_FILE_KB = 500        # only touch files bigger than this


def shrink(path):
    size_before = os.path.getsize(path) / 1024

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)   # keep the photo the right way up
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))   # shrinks, never stretches
        img.save(path, "JPEG", quality=85, optimize=True)

    size_after = os.path.getsize(path) / 1024
    print(f"{path}: {size_before:.0f} KB -> {size_after:.0f} KB")


def main():
    paths = sorted(glob.glob(os.path.join(IMAGES_FOLDER, "*", "*.jpg")))
    count = 0
    for path in paths:
        if os.path.getsize(path) / 1024 > BIG_FILE_KB:
            shrink(path)
            count += 1
    print(f"\nDone. Shrunk {count} image(s). The others were already small enough.")


if __name__ == "__main__":
    main()