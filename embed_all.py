"""
embed_all.py

What this script does, in plain words:
1. Reads the tags we already made for every image (data/image_tags.json)
2. Reads our sample blog posts (posts.json)
3. Sends each image's CAPTION, and each post's title+body, to Gemini's embedding
   model, which turns the text into a list of numbers (an embedding)
4. Saves everything to data/embeddings.json
5. Skips anything already embedded, so it is safe to run again
6. Logs every call in data/cost_log.csv, same as the vision tagging did

Why we embed the CAPTION and not the image itself:
Our vision step already turned each image into words (the caption). Comparing
two pieces of text (a caption and a post) is exactly what an embedding model
is good at. This is simpler and cheaper than image embeddings, and it is
enough for what the capstone asks for.

Run it with:
    python embed_all.py
"""

import os
import csv
import json
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

# ---------- Settings ----------
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# task_type SEMANTIC_SIMILARITY only works with this model, per Google's docs.
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

TAGS_FILE = os.path.join("data", "image_tags.json")
POSTS_FILE = "posts.json"
OUTPUT_FILE = os.path.join("data", "embeddings.json")
COST_FILE = os.path.join("data", "cost_log.csv")

MAX_ATTEMPTS = 4
PAUSE_BETWEEN_CALLS = 3   # seconds; embeddings are usually allowed faster than vision calls
TEMPORARY_ERROR_CODES = (429, 500, 503, 504)

if not API_KEY:
    print("No API key found. Add GEMINI_API_KEY=your_key to your .env file.")
    exit()

client = genai.Client(api_key=API_KEY, http_options=types.HttpOptions(timeout=60000))


# ---------- Small helper functions ----------
def load_existing():
    """Loads embeddings already saved from an earlier run."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"images": {}, "posts": {}}


def save_results(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)  # no indent: embeddings are long, keep the file smaller


def log_cost(item_name, token_count, status):
    """Adds one line to the SAME cost log used by the vision tagging step."""
    file_is_new = not os.path.exists(COST_FILE)
    with open(COST_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if file_is_new:
            writer.writerow(["time", "image", "model", "input_tokens",
                              "output_tokens", "cost_usd", "status"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), item_name,
                          EMBED_MODEL, token_count, 0, 0.0, status])


def embed_text(text):
    """Sends ONE piece of text to Gemini and returns (embedding, token_count)."""
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
    )
    embedding = response.embeddings[0].values
    stats = response.embeddings[0].statistics
    token_count = int(stats.token_count) if stats and stats.token_count else 0
    return embedding, token_count


def embed_with_retries(name, text):
    """Tries up to MAX_ATTEMPTS times. Returns an embedding list, or None if it failed."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            embedding, tokens = embed_text(text)
            log_cost(name, tokens, "ok")
            return embedding

        except errors.APIError as error:
            log_cost(name, 0, f"api_error_{error.code}")
            print(f"   Attempt {attempt}: API error {error.code}")
            if error.code not in TEMPORARY_ERROR_CODES:
                break

        except httpx.HTTPError as error:
            log_cost(name, 0, "network_error")
            print(f"   Attempt {attempt}: network problem ({type(error).__name__})")

        if attempt < MAX_ATTEMPTS:
            wait = 10 * attempt
            print(f"   Waiting {wait} seconds before trying again...")
            time.sleep(wait)

    return None


# ---------- The main job ----------
def main():
    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        image_tags = json.load(f)

    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    results = load_existing()

    # --- Embed every image caption ---
    print(f"Embedding {len(image_tags)} image captions...\n")
    for image_path, tags in image_tags.items():
        if image_path in results["images"]:
            continue  # already done in an earlier run

        # Skip images that failed tagging or were flagged as "unknown"
        if tags.get("status") == "failed" or tags.get("subject") == "unknown":
            print(f"Skipping (no usable caption): {image_path}")
            continue

        caption = tags["caption"]
        print(f"Embedding image: {image_path}")
        embedding = embed_with_retries(image_path, caption)
        if embedding is not None:
            results["images"][image_path] = embedding
            save_results(results)
        else:
            print("   FAILED after all attempts")
        time.sleep(PAUSE_BETWEEN_CALLS)

    # --- Embed every post ---
    print(f"\nEmbedding {len(posts)} posts...\n")
    for post in posts:
        post_id = post["id"]
        if post_id in results["posts"]:
            continue

        text = post["title"] + ". " + post["body"]
        print(f"Embedding post: {post_id} ({post['title']})")
        embedding = embed_with_retries(post_id, text)
        if embedding is not None:
            results["posts"][post_id] = embedding
            save_results(results)
        else:
            print("   FAILED after all attempts")
        time.sleep(PAUSE_BETWEEN_CALLS)

    print("\n===== SUMMARY =====")
    print(f"Images embedded: {len(results['images'])} of {len(image_tags)}")
    print(f"Posts embedded:  {len(results['posts'])} of {len(posts)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
