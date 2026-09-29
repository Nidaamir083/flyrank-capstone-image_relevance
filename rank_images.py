"""
rank_images.py

What this script does, in plain words:
1. Loads all the saved embeddings (images and posts)
2. For ONE chosen post, compares its embedding against every image's embedding
3. Sorts all images by how close they are in meaning (highest score first)
4. Prints the top 5, along with each image's subject and category

The comparison uses COSINE SIMILARITY: a score between -1 and 1.
- 1 means "identical in meaning"
- 0 means "unrelated"
- Negative means "opposite in meaning" (rare in practice here)

Note: this script does NOT reject bad matches yet. It just ranks everything,
even for a post with no good match, like our coffee machine post. That's on
purpose — the ranking step is "find the best options." The GUARD (next step)
is what decides whether the best option is actually good enough.

Run it with:
    python rank_images.py
Then follow the on-screen prompt to choose which post to test.
"""

import json
import math

EMBEDDINGS_FILE = "data/embeddings.json"
TAGS_FILE = "data/image_tags.json"
POSTS_FILE = "posts.json"

TOP_N = 5  # how many results to show


def cosine_similarity(vec_a, vec_b):
    """Measures how similar two embeddings are, from -1 (opposite) to 1 (identical)."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    size_a = math.sqrt(sum(a * a for a in vec_a))
    size_b = math.sqrt(sum(b * b for b in vec_b))
    if size_a == 0 or size_b == 0:
        return 0.0
    return dot_product / (size_a * size_b)


def rank_images_for_post(post_id, embeddings, image_tags):
    """Returns a list of (image_path, score) sorted best-match-first."""
    post_vector = embeddings["posts"][post_id]

    scores = []
    for image_path, image_vector in embeddings["images"].items():
        score = cosine_similarity(post_vector, image_vector)
        scores.append((image_path, score))

    scores.sort(key=lambda item: item[1], reverse=True)
    return scores


def main():
    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        embeddings = json.load(f)
    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        image_tags = json.load(f)
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    # Show the list of posts so it's easy to pick one
    print("Available posts:")
    for post in posts:
        print(f"  {post['id']}: {post['title']}")

    chosen_id = input("\nType a post id to rank images for (e.g. post_1): ").strip()

    if chosen_id not in embeddings["posts"]:
        print(f"'{chosen_id}' was not found in the embeddings. Check the spelling.")
        return

    ranked = rank_images_for_post(chosen_id, embeddings, image_tags)

    post_title = next(p["title"] for p in posts if p["id"] == chosen_id)
    print(f"\nTop {TOP_N} image matches for: {post_title}\n")

    for rank, (image_path, score) in enumerate(ranked[:TOP_N], start=1):
        tags = image_tags.get(image_path, {})
        subject = tags.get("subject", "unknown")
        category = tags.get("category", "unknown")
        print(f"{rank}. {image_path}")
        print(f"   Similarity score: {score:.3f}")
        print(f"   Subject: {subject} | Category: {category}\n")


if __name__ == "__main__":
    main()
