"""
measure_precision.py

What this script does, in plain words:
1. Runs the mismatch guard on EVERY post, exactly as it would run for real
2. Compares each answer against eval_labels.json (what YOU determined is
   actually true, by looking at the photos yourself)
3. Marks each post CORRECT or INCORRECT
4. Calculates top-1 precision: the percentage of posts where the system's
   top suggestion was actually the right answer

Important: the guard itself never sees eval_labels.json. It only ever sees
the vision model's tags, exactly like it would in the real system. The
labels file is used ONLY here, afterwards, to check the guard's homework.

A post counts as CORRECT if:
- The post expects an animal, the guard ACCEPTED an image, and that image's
  TRUE subject (from our own review) matches what the post expects, AND
  that image isn't one we flagged as too ambiguous/uncertain to count.
- OR the post expects no animal at all (like the coffee machine post), and
  the guard correctly said "no confident match".

Run it with:
    python measure_precision.py
"""

import json

from mismatch_guard import check_post

EMBEDDINGS_FILE = "data/embeddings.json"
TAGS_FILE = "data/image_tags.json"
POSTS_FILE = "posts.json"
LABELS_FILE = "eval_labels.json"
RESULTS_FILE = "data/eval_results.json"


def get_true_subject(image_path, image_tags, labels):
    """Returns the TRUE subject for an image: our own correction if we made
    one, otherwise whatever the vision model originally tagged."""
    if image_path in labels and "true_subject" in labels[image_path]:
        return labels[image_path]["true_subject"]
    return image_tags.get(image_path, {}).get("subject", "unknown")


def is_excluded(image_path, labels):
    """True if we marked this image as too ambiguous/uncertain to count fairly."""
    return labels.get(image_path, {}).get("exclude_reason") is not None


def score_post(post_id, guard_result, expected, image_tags, labels):
    """Compares the guard's real answer to the ground truth. Returns (is_correct, explanation)."""
    expected_keywords = expected["correct_subject_keywords"]

    if not expected_keywords:
        # This post should never get a match (e.g. the coffee machine post).
        if guard_result["result"] == "no_confident_match":
            return True, "Correct: no real match exists, and the guard correctly found none."
        else:
            return False, (f"WRONG: guard accepted '{guard_result['image']}', but this post "
                            f"has no correct answer at all.")

    if guard_result["result"] != "accepted":
        return False, (f"WRONG: guard said no confident match, but a valid image "
                        f"exists for this post ({', '.join(expected_keywords)}).")

    image_path = guard_result["image"]
    if is_excluded(image_path, labels):
        return False, (f"WRONG: guard accepted '{image_path}', but this image is "
                        f"too ambiguous/uncertain to count as a real answer.")

    true_subject = get_true_subject(image_path, image_tags, labels)
    matches = any(keyword.lower() in true_subject.lower() for keyword in expected_keywords)

    if matches:
        return True, f"Correct: '{image_path}' (true subject: '{true_subject}') matches what was expected."
    else:
        return False, (f"WRONG: guard accepted '{image_path}', but its TRUE subject "
                        f"is '{true_subject}', not one of [{', '.join(expected_keywords)}].")


def main():
    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        embeddings = json.load(f)
    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        image_tags = json.load(f)
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)
    with open(LABELS_FILE, "r", encoding="utf-8") as f:
        labels_data = json.load(f)

    posts_by_id = {post["id"]: post for post in posts}
    image_labels = {k: v for k, v in labels_data.items() if not k.startswith("_")}
    expected_matches = labels_data["_expected_match_per_post"]

    results = []
    correct_count = 0

    print("===== Running the guard against every post =====\n")
    for post in posts:
        post_id = post["id"]
        guard_result = check_post(post_id, embeddings, image_tags, posts_by_id)
        expected = expected_matches[post_id]

        is_correct, explanation = score_post(post_id, guard_result, expected, image_tags, image_labels)
        if is_correct:
            correct_count += 1

        status = "CORRECT" if is_correct else "INCORRECT"
        print(f"{post_id} ({post['title']}): {status}")
        print(f"   Guard said: {guard_result['result']}"
              + (f" -> {guard_result.get('image', '')}" if guard_result["result"] == "accepted" else ""))
        print(f"   {explanation}\n")

        results.append({
            "post_id": post_id,
            "title": post["title"],
            "guard_result": guard_result,
            "correct": is_correct,
            "explanation": explanation,
        })

    total = len(posts)
    precision = correct_count / total

    print("===== TOP-1 PRECISION =====")
    print(f"{correct_count} of {total} posts correct -> precision = {precision:.2f} ({precision * 100:.0f}%)")

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "correct_count": correct_count,
            "total_posts": total,
            "precision": precision,
            "results": results,
        }, f, indent=2)
    print(f"\nFull results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
