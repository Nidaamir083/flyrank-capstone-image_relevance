import os
import glob

from PIL import Image, ImageOps

IMAGES_FOLDER = "images"
MAX_SIDE = 1200          
BIG_FILE_KB = 500       


def shrink(path):
    size_before = os.path.getsize(path) / 1024

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)   
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))  
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