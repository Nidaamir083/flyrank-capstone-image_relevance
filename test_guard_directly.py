import json
from mismatch_guard import (
    looks_ambiguous,
    matches_expected_subject,
    SIMILARITY_THRESHOLD,
    cosine_similarity,
)

EMBEDDINGS_FILE = "data/embeddings.json"
TAGS_FILE = "data/image_tags.json"
POSTS_FILE = "posts.json"


def check_one_candidate(post_id, image_path, embeddings, image_tags, posts_by_id):
    """Checks ONE specific image against ONE specific post, and explains the result."""
    post = posts_by_id[post_id]
    expected_keywords = post["expected_keywords"]

    post_vector = embeddings["posts"][post_id]
    image_vector = embeddings["images"][image_path]
    score = cosine_similarity(post_vector, image_vector)

    tags = image_tags[image_path]
    subject = tags.get("subject", "unknown")

    print(f"\nPost: {post['title']}")
    print(f"Forced candidate: {image_path} (subject: '{subject}')")
    print(f"Similarity score: {score:.3f}")

    if looks_ambiguous(subject):
        print(f"RESULT: REJECTED - ambiguous photo, more than one animal mentioned.")
        return

    if not matches_expected_subject(subject, expected_keywords):
        expected_text = " / ".join(expected_keywords)
        print(f"RESULT: REJECTED - category mismatch: expected one of "
              f"[{expected_text}], detected '{subject}'.")
        return

    if score < SIMILARITY_THRESHOLD:
        print(f"RESULT: REJECTED - similarity ({score:.3f}) is below the "
              f"threshold ({SIMILARITY_THRESHOLD}).")
        return

    print(f"RESULT: ACCEPTED - subject matches and similarity clears the threshold.")


def main():
    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        embeddings = json.load(f)
    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        image_tags = json.load(f)
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    posts_by_id = {post["id"]: post for post in posts}

    check_one_candidate("post_1", "images/wolf/wolf_3.jpg", embeddings, image_tags, posts_by_id)

    check_one_candidate("post_2", "images/wolf/wolf_10.jpg", embeddings, image_tags, posts_by_id)
    check_one_candidate("post_4", "images/deer/deer_4.jpg", embeddings, image_tags, posts_by_id)
    check_one_candidate("post_1", "images/red_fox/red_fox_3.jpg", embeddings, image_tags, posts_by_id)


if __name__ == "__main__":
    main()
