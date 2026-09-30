import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PEXELS_API_KEY")

if not API_KEY:
    print("No API key found. Did you create a .env file with PEXELS_API_KEY=your_key?")
    exit()

CATEGORIES = ["red fox", "wolf", "dog", "bear", "deer"]
IMAGES_PER_CATEGORY = 10


OUTPUT_FOLDER = "images"


SEARCH_URL = "https://api.pexels.com/v1/search"
HEADERS = {"Authorization": API_KEY}


def download_category(category_name):
    """Downloads images for one category, e.g. 'red fox'."""
    folder_name = category_name.replace(" ", "_")
    folder_path = os.path.join(OUTPUT_FOLDER, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    print(f"\nSearching Pexels for: {category_name}")

    params = {"query": category_name, "per_page": IMAGES_PER_CATEGORY}
    response = requests.get(SEARCH_URL, headers=HEADERS, params=params)

    if response.status_code != 200:
        print(f"  Something went wrong: {response.status_code} - {response.text}")
        return

    data = response.json()
    photos = data.get("photos", [])

    if not photos:
        print(f"  No photos found for '{category_name}'.")
        return


    for index, photo in enumerate(photos, start=1):
        image_url = photo["src"]["medium"]
        file_path = os.path.join(folder_path, f"{folder_name}_{index}.jpg")

        try:
            image_response = requests.get(image_url)
            with open(file_path, "wb") as f:
                f.write(image_response.content)
            print(f"  Saved: {file_path}")
        except Exception as error:
            print(f"  Failed to save image {index}: {error}")


def main():
    print("Starting image download for the capstone dataset...")
    for category in CATEGORIES:
        download_category(category)
    print("\nDone! Check the 'images' folder.")


if __name__ == "__main__":
    main()
