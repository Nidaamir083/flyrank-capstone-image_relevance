# AI Image Understanding & Content Matching Engine

FlyRank Backend Track Capstone — a system that reads a library of images, understands
what's really in each one using a vision AI model, and matches the right image to the
right blog post based on meaning, not filenames or keywords.

The key feature is the **mismatch guard**: a safety layer that rejects a bad match
(e.g. suggesting a wolf photo for a fox article) and explains why, instead of
guessing. Good suggestions when confident, safe rejection when not.

> Status: All 4 phases complete. Top-1 precision on the hand-labeled eval set: 7/7 (100%).

## What it does

1. Reads each image with a vision model and produces structured tags (subject,
   category, attributes, caption, confidence)
2. Turns image captions and blog post text into embeddings, and ranks images by how
   closely they match a post's meaning
3. Runs every top match through a mismatch guard before suggesting it — rejecting
   anything that doesn't clear the bar, with a plain-language reason
4. Processes images in the background as a batch job, with retries and cost tracking
5. Exposes a small review API to fetch suggestions, approve/reject them, and inspect
   why each decision was made

See [`DESIGN.md`](./DESIGN.md) for the original design doc — problem statement,
data model, matching strategy, guard rules, and API surface.

## Tech stack

- Python + FastAPI
- Vision model: Gemini (`gemini-3.5-flash-lite`, free tier)
- Embeddings: Gemini (`gemini-embedding-001`, free tier)
- Storage: JSON files (`data/`) — see "Known deviation from the design doc" below

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/Nidaamir083/flyrank-capstone-image_relevance.git
cd flyrank-capstone-image_relevance

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the example env file and add your own free Gemini API key
#    (get one at aistudio.google.com - no credit card required)
cp .env.example .env

# 4. (Optional) Regenerate the tagged data and embeddings from scratch.
#    This is NOT required to try the system - data/image_tags.json and
#    data/embeddings.json are already committed to the repo.
python batch_tag_images.py
python embed_all.py

# 5. Check the guard's real accuracy against the hand-labeled eval set
python measure_precision.py

# 6. Start the review API
uvicorn review_api:app --reload
```

Then open **http://127.0.0.1:8000/docs** in a browser for an interactive page to
try every endpoint — no extra tooling needed. Try `GET /posts/post_1/suggestion`
(a real match) and `GET /posts/post_7/suggestion` (correctly no match).

See [`capstone.yaml`](./capstone.yaml) for the exact commands an evaluator will run.

## Evaluation

Top-1 precision was measured against a hand-labeled eval set of 7 sample blog
posts (one per animal category, plus one post with no matching animal at all,
to test correct rejection).

**Result: 7 of 7 posts correct — 100% top-1 precision.**

This includes correctly:
- Matching each animal post to a genuinely correct image
- Skipping an ambiguous photo (a "giraffe and deer" image) and finding a real
  deer photo instead
- Returning "no confident match" for a post about something unrelated to any
  animal in the dataset

Note: this is a small eval set (7 posts, only one true negative case). A 100%
result here shows the approach works well on this test set — it is not proof
the system is flawless. A larger, more adversarial eval set (more "no match"
cases, more close lookalikes) would be a natural next step to more thoroughly
stress-test the guard. See `data/eval_results.json` for the full per-post
breakdown, and `EVIDENCE.md` for the raw output backing every claim above.

## Architecture

```
images/*.jpg
     |
     v
batch_tag_images.py --(Gemini vision model)--> data/image_tags.json
     |                                          (subject, category, caption,
     |                                           attributes, confidence)
     v
embed_all.py --(Gemini embedding model)--> data/embeddings.json
     |                                     (one embedding per image caption,
     |                                      one embedding per post)
     v
mismatch_guard.py
     |-- rank_images_for_post(): cosine similarity, image embeddings vs. post embedding
     |-- for each candidate, best score first:
     |      1. ambiguous photo? (subject mentions >1 animal) -> skip
     |      2. category mismatch? (subject doesn't match expected keywords) -> reject, explain
     |      3. below similarity threshold (0.75)? -> stop, "no confident match"
     |      4. otherwise -> ACCEPT, with score + reason
     v
review_api.py (FastAPI)
     |-- GET  /posts/{post_id}/suggestion      -> runs the guard, returns the decision
     |-- POST /suggestions/{post_id}/approve   -> human marks it approved
     |-- POST /suggestions/{post_id}/reject    -> human marks it rejected
     |-- GET  /suggestions                     -> lists every decision + reason so far
     v
data/review_decisions.json  (all human review decisions, saved)
```

`measure_precision.py` runs the same guard against every post and checks its
answers against `eval_labels.json` (hand-labeled ground truth), producing the
top-1 precision score reported above.

See [`DESIGN.md`](./DESIGN.md) for the originally planned architecture (including
a database layer) and how it differs from what was actually built — see "Known
deviation" below.

## Known deviation from the design doc

`DESIGN.md` originally planned a PostgreSQL database with tables for images,
posts, embeddings, and suggestions. Given the project's small scope (59 images,
7 posts), the built version uses flat JSON files under `data/` instead
(`image_tags.json`, `embeddings.json`, `eval_results.json`,
`review_decisions.json`). The logic layer (`mismatch_guard.py`) is written
independently of storage, so swapping in a real database later would mean
changing how data is loaded/saved, not how matching or guarding decisions
are made.

## Limitations

- **The vision model is not ground truth, and mistakes propagate.** During manual
  review, a genuine white wolf photo (`wolf_10.jpg`) was tagged "white dog" by the
  vision model with 0.95 confidence. The guard correctly rejects it for wolf-related
  posts, since it only ever sees the tag it was given, not the real photo. In this
  project's dataset, other correctly-tagged wolf photos still allowed a correct match
  to be found, but a system with fewer redundant photos per category would be more
  exposed to this kind of upstream tagging error.
- **Confidence scores reflect certainty about what the model sees, not correctness.**
  The mistagged wolf photo above was scored at 0.95 confidence — high — despite being
  wrong. Confidence alone cannot be relied on to catch every mistake; category and
  ambiguity checks in the guard are what caught the other real error case found
  (`deer_4.jpg`, "giraffe and deer").
- **Stock photo folders are not reliable ground truth either.** Several images
  auto-downloaded into the "deer" folder from a Pexels search for "deer" were
  actually blackbuck, nyala, or springbok (antelope species, not deer). These were
  caught only through manual visual review, not automatically.
- **One image (`wolf_8.jpg`) has an uncertain true label** — it looks like it may be
  a husky or wolfdog rather than a wild wolf, and was excluded from evaluation
  rather than guessed at.
- **No frontend UI.** Review happens through API endpoints and a simple list-style
  table (`GET /suggestions`), by design — see the stated non-goal in `DESIGN.md`.
- **Free-tier rate limits shaped the build.** Google's Gemini free tier enforces
  daily request limits that vary significantly by model (as low as 20/day on some
  models, up to 500/day on lighter models). The batch job includes retries and a
  daily-limit detector to handle this gracefully rather than crashing.
- **File-based storage, not a real database.** See "Known deviation" above.
- **Small dataset.** 59 images across 6 categories (bear, deer, dog, red fox, wolf,
  coyote) plus one deliberately blurry test image. Enough to demonstrate the
  approach; a production system would need a much larger, more diverse library.

## Utility scripts

- `download_images.py` / `download_coyote.py` — download the sample image dataset from Pexels
- `shrink_images.py` — detects and resizes any image over 500 KB (max 1200px on
  the long side). Added after the 5 replacement deer photos (`deer_11.jpg` to
  `deer_15.jpg`) turned out to be full-resolution originals up to 4 MB each —
  large enough to slow down uploads to Gemini and risk violating the capstone's
  "don't commit large datasets" rule. Run once after adding any new image.
- `make_blurry_test.py` — creates a deliberately blurry test image, used to prove
  the low-confidence flagging rule actually works (see `EVIDENCE.md`)

## Project docs

- [`DESIGN.md`](./DESIGN.md) — original design doc
- [`EVIDENCE.md`](./EVIDENCE.md) — proof for every requirement in the capstone brief
- [`BUILDLOG.md`](./BUILDLOG.md) — honest log of where AI helped and what I changed
- [`capstone.yaml`](./capstone.yaml) — evaluator manifest (install/run/seed/test/endpoints)
- `eval_labels.json` — hand-labeled ground truth used for evaluation
- `data/eval_results.json` — full per-post precision results
- `.env.example` — required environment variables with placeholder values
