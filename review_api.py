"""
review_api.py

What this does, in plain words:
A small web API with 3 endpoints:

1. GET  /posts/{post_id}/suggestion
   Runs the guard for one post and returns its answer: an accepted image
   with a reason, or "no confident match" with a reason.

2. POST /suggestions/{post_id}/approve
   Records that a human approved the suggestion for this post.

3. POST /suggestions/{post_id}/reject
   Records that a human rejected the suggestion for this post.

There is also:
4. GET  /suggestions
   Lists every suggestion made so far, with its approve/reject status —
   this is the "simple review table" the capstone brief allows instead of
   a full frontend.

Decisions are saved to data/review_decisions.json so they survive a restart.

Run it with:
    uvicorn review_api:app --reload
Then open http://127.0.0.1:8000/docs in a browser - FastAPI gives you a
free, clickable page to try every endpoint without writing any code.
"""

import json
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException

from mismatch_guard import check_post

EMBEDDINGS_FILE = "data/embeddings.json"
TAGS_FILE = "data/image_tags.json"
POSTS_FILE = "posts.json"
DECISIONS_FILE = "data/review_decisions.json"

app = FastAPI(title="AI Image Matching Engine - Review API")


# ---------- Small helpers to load and save data ----------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_decisions():
    if os.path.exists(DECISIONS_FILE):
        return load_json(DECISIONS_FILE)
    return {}


def save_decisions(decisions):
    os.makedirs(os.path.dirname(DECISIONS_FILE), exist_ok=True)
    with open(DECISIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2)


def get_post_or_404(post_id, posts_by_id):
    if post_id not in posts_by_id:
        raise HTTPException(status_code=404, detail=f"Post '{post_id}' not found.")
    return posts_by_id[post_id]


# ---------- Endpoints ----------
@app.get("/posts/{post_id}/suggestion")
def get_suggestion(post_id: str):
    """Runs the guard for one post and returns its decision, with the reason why."""
    embeddings = load_json(EMBEDDINGS_FILE)
    image_tags = load_json(TAGS_FILE)
    posts = load_json(POSTS_FILE)
    posts_by_id = {post["id"]: post for post in posts}

    get_post_or_404(post_id, posts_by_id)

    result = check_post(post_id, embeddings, image_tags, posts_by_id)

    # Save this suggestion so it shows up in the review list, defaulting to "pending"
    decisions = load_decisions()
    if post_id not in decisions:
        decisions[post_id] = {
            "post_id": post_id,
            "post_title": posts_by_id[post_id]["title"],
            "suggestion": result,
            "review_status": "pending",
            "decided_at": None,
        }
        save_decisions(decisions)

    return result


@app.post("/suggestions/{post_id}/approve")
def approve_suggestion(post_id: str):
    """Marks the current suggestion for this post as approved by a human reviewer."""
    decisions = load_decisions()
    if post_id not in decisions:
        raise HTTPException(status_code=404,
                             detail=f"No suggestion exists yet for '{post_id}'. "
                                    f"Call GET /posts/{post_id}/suggestion first.")

    decisions[post_id]["review_status"] = "approved"
    decisions[post_id]["decided_at"] = datetime.now().isoformat(timespec="seconds")
    save_decisions(decisions)
    return decisions[post_id]


@app.post("/suggestions/{post_id}/reject")
def reject_suggestion(post_id: str):
    """Marks the current suggestion for this post as rejected by a human reviewer."""
    decisions = load_decisions()
    if post_id not in decisions:
        raise HTTPException(status_code=404,
                             detail=f"No suggestion exists yet for '{post_id}'. "
                                    f"Call GET /posts/{post_id}/suggestion first.")

    decisions[post_id]["review_status"] = "rejected"
    decisions[post_id]["decided_at"] = datetime.now().isoformat(timespec="seconds")
    save_decisions(decisions)
    return decisions[post_id]


@app.get("/suggestions")
def list_suggestions():
    """Returns every suggestion made so far, with its review status. The 'simple
    review table' the capstone allows instead of a full frontend."""
    return list(load_decisions().values())
