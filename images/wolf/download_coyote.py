"""
download_coyote.py

What this script does, in plain words:
- Downloads 3 coyote photos from Pexels into images/coyote/
- A coyote looks a bit like a fox, a bit like a wolf, and a bit like a dog,
  so it is a good hard test for the mismatch guard later.

Run it with:
    python download_coyote.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PEXELS_API_KEY")

if not API_KEY:
    print("No API key found. Did you create a .env file with PEXELS_API_KEY=your_key?")
    exit()

QUERY = "coyote"
COUNT = 3
FOLDER = os.path.join("images", "coyote")
SEARCH_URL = "https://api.pexels.com/v1/search"
HEADERS = {"Authorization": API_KEY}


def main():
    os.makedirs(FOLDER, exist_ok=True)
    print(f"Searching Pexels for: {QUERY}")

    params = {"query": QUERY, "per_page": COUNT}
    response = requests.get(SEARCH_URL, headers=HEADERS, params=params)

    if response.status_code != 200:
        print(f"Something went wrong: {response.status_code} - {response.text}")
        return

    photos = response.json().get("photos", [])
    if not photos:
        print("No photos found.")
        return

    for index, photo in enumerate(photos, start=1):
        image_url = photo["src"]["medium"]
        file_path = os.path.join(FOLDER, f"coyote_{index}.jpg")
        image_response = requests.get(image_url)
        with open(file_path, "wb") as f:
            f.write(image_response.content)
        print(f"Saved: {file_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()