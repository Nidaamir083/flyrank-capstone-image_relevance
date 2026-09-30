import os
from PIL import Image, ImageFilter

# Pick any real photo you already have as the starting point
SOURCE_IMAGE = os.path.join("images", "red_fox", "red_fox_1.jpg")
OUTPUT_FOLDER = os.path.join("images", "hard_cases")
OUTPUT_PATH = os.path.join(OUTPUT_FOLDER, "blurry_1.jpg")

BLUR_STRENGTH = 25  # higher = blurrier


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    with Image.open(SOURCE_IMAGE) as img:
        blurred = img.filter(ImageFilter.GaussianBlur(radius=BLUR_STRENGTH))
        blurred.save(OUTPUT_PATH, "JPEG", quality=85)

    print(f"Created a deliberately blurry test image: {OUTPUT_PATH}")
    print("Run batch_tag_images.py next to see how the AI handles it.")


if __name__ == "__main__":
    main()
