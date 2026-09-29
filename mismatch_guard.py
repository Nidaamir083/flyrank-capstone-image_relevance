"""
mismatch_guard.py

What this script does, in plain words:
For a chosen post, it looks at the ranked images (best match first) and
decides, one at a time, whether each one is actually good enough to suggest.
It rejects a candidate for any of these reasons:

  1. AMBIGUOUS PHOTO - the caption mentions more than one animal
     (e.g. "giraffe and deer"). We can't be sure which animal the photo is
     really about, so we skip it rather than guess.
  2. CATEGORY MISMATCH - the image's subject doesn't contain any of the
     words we expect for this post (e.g. post expects "fox", image says
     "wolf").
  3. BELOW THRESHOLD - the similarity score is too low. Once we reach a
     candidate below the threshold, there is no point checking further
     down the list, since everything after it scores even lower.

The first candidate that passes ALL checks is ACCEPTED, with an explanation.
If nothing passes, the result is "no confident match", with the reason why.

This threshold (0.75) was not guessed. It came from real numbers: every
correct animal match scored between 0.78 and 0.86 in our tests, and the
one post with no matching image (the coffee machine post) scored only
0.717 at best. 0.75 sits cleanly between those two groups.

Run it with:
    python mismatch_guard.py
Then follow the on-screen prompt to choose which post to test.
"""

import json
import math

EMBEDDINGS_FILE = "data/embeddings.json"
TAGS_FILE = "data/image_tags.json"
POSTS_FILE = "posts.json"

SIMILARITY_THRESHOLD = 0.75
CANDIDATES_TO_CHECK = 10  # how far down the ranked list we're willing to look


def cosine_similarity(vec_a, vec_b):
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    size_a = math.sqrt(sum(a * a for a in vec_a))
    size_b = math.sqrt(sum(b * b for b in vec_b))
    if size_a == 0 or size_b == 0:
        return 0.0
    return dot_product / (size_a * size_b)


def rank_images_for_post(post_id, embeddings):
    post_vector = embeddings["posts"][post_id]
    scores = []
    for image_path, image_vector in embeddings["images"].items():
        score = cosine_similarity(post_vector, image_vector)
        scores.append((image_path, score))
    scores.sort(key=lambda item: item[1], reverse=True)
    return scores


def looks_ambiguous(subject):
    """True if the caption's subject mentions more than one animal, e.g. 'giraffe and deer'."""
    return " and " in subject.lower()


def matches_expected_subject(subject, expected_keywords):
    """True if any expected keyword appears inside the subject text."""
    subject_lower = subject.lower()
    return any(keyword.lower() in subject_lower for keyword in expected_keywords)


def check_post(post_id, embeddings, image_tags, posts_by_id):
    """Runs the guard for one post. Returns a result dictionary."""
    post = posts_by_id[post_id]
    expected_keywords = post["expected_keywords"]

    # A post with no expected animal at all can never get a real match.
    if not expected_keywords:
        return {
            "post_id": post_id,
            "result": "no_confident_match",
            "reason": "This post is not about any of our known animal categories.",
        }

    ranked = rank_images_for_post(post_id, embeddings)

    for image_path, score in ranked[:CANDIDATES_TO_CHECK]:
        if score < SIMILARITY_THRESHOLD:
            # Everything after this point scores even lower. Stop looking.
            return {
                "post_id": post_id,
                "result": "no_confident_match",
                "reason": f"Best remaining similarity ({score:.3f}) is below "
                          f"the threshold ({SIMILARITY_THRESHOLD}).",
            }

        tags = image_tags.get(image_path, {})
        subject = tags.get("subject", "unknown")

        if looks_ambiguous(subject):
            print(f"   Skipping {image_path} (subject '{subject}'): ambiguous, "
                  f"more than one animal mentioned.")
            continue

        if not matches_expected_subject(subject, expected_keywords):
            expected_text = " / ".join(expected_keywords)
            print(f"   Rejecting {image_path} (subject '{subject}'): "
                  f"category mismatch, expected one of [{expected_text}].")
            continue

        # Passed every check.
        return {
            "post_id": post_id,
            "result": "accepted",
            "image": image_path,
            "score": score,
            "subject": subject,
            "reason": f"Subject '{subject}' matches the expected category, "
                      f"and similarity ({score:.3f}) is above the threshold.",
        }

    return {
        "post_id": post_id,
        "result": "no_confident_match",
        "reason": "No image both matched the expected category and cleared the threshold.",
    }


def main():
    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        embeddings = json.load(f)
    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        image_tags = json.load(f)
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    posts_by_id = {post["id"]: post for post in posts}

    print("Available posts:")
    for post in posts:
        print(f"  {post['id']}: {post['title']}")

    chosen_id = input("\nType a post id to check (e.g. post_1), "
                       "or 'all' to check every post: ").strip()

    ids_to_check = list(posts_by_id.keys()) if chosen_id == "all" else [chosen_id]

    for post_id in ids_to_check:
        if post_id not in posts_by_id:
            print(f"'{post_id}' was not found. Check the spelling.")
            continue

        title = posts_by_id[post_id]["title"]
        print(f"\n=== {post_id}: {title} ===")
        result = check_post(post_id, embeddings, image_tags, posts_by_id)

        if result["result"] == "accepted":
            print(f"ACCEPTED: {result['image']}")
            print(f"  Subject: {result['subject']} | Score: {result['score']:.3f}")
            print(f"  Reason: {result['reason']}")
        else:
            print("NO CONFIDENT MATCH")
            print(f"  Reason: {result['reason']}")


if __name__ == "__main__":
    main()
