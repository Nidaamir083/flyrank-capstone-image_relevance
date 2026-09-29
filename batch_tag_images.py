"""
batch_tag_images.py

What this script does, in plain words:
1. Finds every image inside the images/ folder
2. Sends each one to Gemini and gets validated tags back
3. If Gemini is busy or the answer is invalid, it WAITS and RETRIES (up to 3 times)
4. Saves the tags to data/image_tags.json
5. Writes one line per AI call to data/cost_log.csv (tokens used)
6. Skips images that are already done, so you can safely run it again

Run it with:
    python batch_tag_images.py
"""

import os
import csv
import json
import time
import glob
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types, errors
import httpx
from pydantic import ValidationError

from schemas import ImageTags

# ---------- Settings ----------
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

IMAGES_FOLDER = "images"
DATA_FOLDER = "data"
TAGS_FILE = os.path.join(DATA_FOLDER, "image_tags.json")
COST_FILE = os.path.join(DATA_FOLDER, "cost_log.csv")

MAX_ATTEMPTS = 4            # how many times we try one image before giving up
PAUSE_BETWEEN_IMAGES = 10   # seconds to wait between images (free tier has speed limits)
LOW_CONFIDENCE = 0.6        # below this, an image is flagged for human review

# Error codes that usually mean "try again later" (busy server, too many requests)
TEMPORARY_ERROR_CODES = (429, 500, 503, 504)


class DailyQuotaReached(Exception):
    """Raised when the free daily limit is used up. Retrying is pointless, so we stop."""

PROMPT = """Look at this image and describe it.
- subject: the main thing in the image, as specific as possible (e.g. "red fox", "gray wolf")
- category: one broad word (e.g. "animal", "food", "landscape")
- attributes: 3 to 5 short visual details
- caption: one short sentence describing the image
- confidence: a number from 0 to 1 showing how sure you are about the subject.
  Use a LOW number if the image is blurry, unclear, or you are not sure what it shows.
Be honest about confidence. Do not guess."""

if not API_KEY:
    print("No API key found. Add GEMINI_API_KEY=your_key to your .env file.")
    exit()

client = genai.Client(api_key=API_KEY, http_options=types.HttpOptions(timeout=60000))


# ---------- Small helper functions ----------
def load_saved_results():
    """Loads results from earlier runs, so we don't redo finished images."""
    if os.path.exists(TAGS_FILE):
        with open(TAGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_results(results):
    """Saves all results to the JSON file."""
    with open(TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def log_cost(image_path, input_tokens, output_tokens, status):
    """Adds one line to the cost log for every AI call we make."""
    file_is_new = not os.path.exists(COST_FILE)
    with open(COST_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if file_is_new:
            writer.writerow(["time", "image", "model", "input_tokens",
                             "output_tokens", "cost_usd", "status"])
        # Free tier = 0 dollars. We still record tokens so the habit is in place.
        writer.writerow([datetime.now().isoformat(timespec="seconds"), image_path,
                         MODEL_NAME, input_tokens, output_tokens, 0.0, status])


def ask_gemini(image_path):
    """Sends ONE image to Gemini. Returns (validated tags, input tokens, output tokens)."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ImageTags,
        ),
    )
    usage = response.usage_metadata
    # Never trust the answer blindly. If it doesn't fit the template, this raises an error.
    tags = ImageTags.model_validate_json(response.text)
    return tags, usage.prompt_token_count, usage.candidates_token_count


def tag_with_retries(image_path):
    """Tries up to MAX_ATTEMPTS times. Returns a result dictionary for this image."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            tags, in_tokens, out_tokens = ask_gemini(image_path)
            log_cost(image_path, in_tokens, out_tokens, "ok")

            status = "flagged" if tags.confidence < LOW_CONFIDENCE else "tagged"
            result = tags.model_dump()
            result["status"] = status
            return result

        except ValidationError:
            # The AI's answer didn't fit our template.
            log_cost(image_path, 0, 0, "invalid_answer")
            print(f"   Attempt {attempt}: invalid answer from AI")

        except errors.APIError as error:
            log_cost(image_path, 0, 0, f"api_error_{error.code}")
            print(f"   Attempt {attempt}: API error {error.code}")
            # A "PerDay" quota error means today's free allowance is finished.
            if error.code == 429 and "PerDay" in str(error):
                raise DailyQuotaReached()
            if error.code not in TEMPORARY_ERROR_CODES:
                break  # a permanent error (like a wrong key): retrying won't help

        except httpx.HTTPError as error:
            # The internet connection dropped or timed out. Treat it like a busy server.
            log_cost(image_path, 0, 0, "network_error")
            print(f"   Attempt {attempt}: network problem ({type(error).__name__})")

        # Wait longer after each failure: 2s, then 4s, then 8s
        if attempt < MAX_ATTEMPTS:
            wait = 20 * attempt
            print(f"   Waiting {wait} seconds before trying again...")
            time.sleep(wait)

    return {"status": "failed"}


# ---------- The main batch job ----------
def main():
    os.makedirs(DATA_FOLDER, exist_ok=True)

    # Find every .jpg inside images/<category>/
    image_paths = sorted(glob.glob(os.path.join(IMAGES_FOLDER, "*", "*.jpg")))
    results = load_saved_results()

    print(f"Found {len(image_paths)} images. Using model: {MODEL_NAME}\n")

    for number, path in enumerate(image_paths, start=1):
        key = path.replace("\\", "/")  # same style on Windows and Mac

        # Skip images that were already tagged successfully in an earlier run
        if key in results and results[key]["status"] in ("tagged", "flagged"):
            print(f"[{number}/{len(image_paths)}] Skipping (already done): {key}")
            continue

        print(f"[{number}/{len(image_paths)}] Tagging: {key}")
        try:
            results[key] = tag_with_retries(path)
        except DailyQuotaReached:
            print("\nSTOPPED: the free daily limit for this model is used up.")
            print("Run this script again tomorrow, or switch GEMINI_MODEL in .env.")
            break
        save_results(results)  # save after every image, so a crash loses nothing

        info = results[key]
        if info["status"] == "failed":
            print("   FAILED after all attempts")
        else:
            print(f"   -> {info['subject']} (confidence {info['confidence']}) [{info['status']}]")

        time.sleep(PAUSE_BETWEEN_IMAGES)

    # ---------- Summary ----------
    total = len(results)
    tagged = sum(1 for r in results.values() if r["status"] == "tagged")
    flagged = sum(1 for r in results.values() if r["status"] == "flagged")
    failed = sum(1 for r in results.values() if r["status"] == "failed")
    print("\n===== SUMMARY =====")
    remaining = len(image_paths) - tagged - flagged
    print(f"Done: {tagged + flagged} of {len(image_paths)} | Tagged: {tagged} | "
          f"Flagged (low confidence): {flagged} | Failed: {failed} | Still to do: {remaining}")
    print(f"Tags saved in:  {TAGS_FILE}")
    print(f"Cost log in:    {COST_FILE}")
    if failed:
        print("Some images failed. Run the script again and it will retry only those.")


if __name__ == "__main__":
    main()