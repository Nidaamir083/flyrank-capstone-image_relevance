# Design Doc — AI Image Understanding & Content Matching Engine

## 1. Problem

We have a library of images and a set of blog posts. Right now there is no automatic
way to pick the right image for a post — filenames and keywords don't tell us what an
image actually shows. This system will:

- Look at each image and understand what's really in it (using a vision AI model)
- Understand what each blog post is about
- Suggest the best-matching image for a post, based on *meaning*, not keywords
- Refuse to suggest an image when nothing is a confident enough match, and explain why

**The core problem this solves:** avoiding a wrong match matters more than finding *a*
match. A wolf photo must never be suggested for a fox article, even if it's the closest
thing available.

## 2. Non-goal (what we will NOT build)

We will **not** build a full frontend UI. Reviewing and approving image suggestions
will happen through API endpoints and/or a simple admin table — not a polished web app.

## 3. Image metadata schema

Every image, after being processed by the vision model, produces this shape:

```json
{
  "subject": "red fox",
  "category": "animal",
  "attributes": ["orange fur", "wild", "forest"],
  "caption": "A red fox standing in a forest",
  "confidence": 0.94
}
```

Rules:
- This JSON is checked against a schema before we trust it (using Pydantic in Python).
- If the response doesn't match the schema, it is **retried**, never accepted as-is.
- If `confidence` is below a set number (to be tuned in Phase 3), the image is
  **flagged for manual review** instead of being used automatically.

## 4. Matching strategy

1. Turn each image's `caption` into an embedding (a list of numbers representing meaning).
2. Turn each blog post's text into an embedding the same way.
3. For a given post, compare its embedding against every image embedding using
   **cosine similarity** — a score of how close two embeddings are.
4. Rank images by similarity score, highest first.
5. Pass the top candidate through the **mismatch guard** before suggesting it.

This lets the system match concepts, not exact words — e.g. "red fox" and "Vulpes vulpes"
should be recognized as related even though the words are completely different.

## 5. Mismatch guard rules

The guard decides whether the top-ranked image is actually good enough to suggest.
It rejects a candidate if **any** of these are true:

- The image's `category` doesn't match the post's expected category
  (e.g. post expects "animal: fox", image is tagged "animal: wolf")
- The similarity score is below the tuned threshold (exact number set during Phase 3,
  using the labeled eval set)
- The image's `confidence` score was too low to trust in the first place

When rejected, the guard returns a plain-language reason, e.g.:
> "Animal category mismatch: expected fox, detected wolf"

When *no* image clears the bar for a post, the system returns:
> "No confident match — reason: similarity below threshold" (or category mismatch)

## 6. Database design (initial sketch)

**images**
| column | type | notes |
|---|---|---|
| id | UUID (primary key) | |
| file_path / URL | text | |
| subject | text | from vision model |
| category | text | from vision model |
| attributes | text[] | from vision model |
| caption | text | from vision model |
| confidence | float | from vision model |
| status | text | e.g. `pending`, `tagged`, `flagged` |
| created_at | timestamp | |

**image_vectors**
| column | type | notes |
|---|---|---|
| id | UUID (primary key) | |
| image_id | UUID (foreign key → images) | |
| embedding | array/vector | |

**posts**
| column | type | notes |
|---|---|---|
| id | UUID (primary key) | |
| title | text | |
| body | text | |
| category | text | expected image category, if known |

**post_vectors**
| column | type | notes |
|---|---|---|
| id | UUID (primary key) | |
| post_id | UUID (foreign key → posts) | |
| embedding | array/vector | |

**suggestions**
| column | type | notes |
|---|---|---|
| id | UUID (primary key) | |
| post_id | UUID (foreign key → posts) | |
| image_id | UUID (foreign key → images, nullable) | null if no match |
| similarity_score | float | |
| guard_result | text | `accepted` / `rejected` |
| reason | text | human-readable explanation |
| review_status | text | `pending`, `approved`, `rejected` |
| created_at | timestamp | |

Indexes: `image_id` and `post_id` foreign keys, plus an index on `suggestions.review_status`
for quick lookups in the review API.

## 7. API surface (planned endpoints)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/images/ingest` | Kick off the batch job to tag a new batch of images |
| GET | `/images/{id}` | View a single image's tags/status |
| POST | `/posts` | Add a new blog post |
| GET | `/posts/{id}/images` | Get ranked image suggestions for a post |
| POST | `/suggestions/{id}/approve` | Approve a suggested image |
| POST | `/suggestions/{id}/reject` | Reject a suggested image |
| GET | `/costs` | View per-call AI cost log |

## 8. Layer sketch (architecture)

```
Images --(batch job)--> Vision Model --> {tags, caption, confidence} --> images table
   |
   embed(caption) --------------------------------------------------> image_vectors

Posts ----------------------> embed(post text) ---------------------> post_vectors

GET /posts/:id/images
   --> Similarity Ranking (image_vectors x post_vector)
   --> Mismatch Guard (category + threshold + confidence)
      --> Suggested image (ranked, explained)
      --> "No good match" + explanation
   --> Review API: approve / reject
```

Layers: **HTTP layer** (API endpoints) → **logic layer** (matching, guard rules) →
**data layer** (database models, vector storage). Kept separate so each part can be
tested and changed independently.

## 9. Initial image dataset plan

Target: **50 images across 5 categories** (10 each) — animals, to keep scope small
and match the PDF's fox/wolf/dog example:

- Red fox
- Wolf
- Dog
- Bear
- Deer

Source: Unsplash or Pexels (free license, no card required). Images will be downloaded
into an `/images` folder in the repo, or fetched via a small download script if the
folder gets too large to commit directly.
