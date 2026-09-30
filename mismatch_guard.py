import json
import math

EMBEDDINGS_FILE = "data/embeddings.json"
TAGS_FILE = "data/image_tags.json"
POSTS_FILE = "posts.json"

SIMILARITY_THRESHOLD = 0.75
CANDIDATES_TO_CHECK = 10  


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

    if not expected_keywords:
        return {
            "post_id": post_id,
            "result": "no_confident_match",
            "reason": "This post is not about any of our known animal categories.",
        }

    ranked = rank_images_for_post(post_id, embeddings)

    for image_path, score in ranked[:CANDIDATES_TO_CHECK]:
        if score < SIMILARITY_THRESHOLD:
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
