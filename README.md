# AI Image Understanding & Content Matching Engine

FlyRank Backend Track Capstone — a system that reads a library of images, understands
what's really in each one using a vision AI model, and matches the right image to the
right blog post based on meaning, not filenames or keywords.

The key feature is the **mismatch guard**: a safety layer that rejects a bad match
(e.g. suggesting a wolf photo for a fox article) and explains why, instead of
guessing. Good suggestions when confident, safe rejection when not.

> Status: Phases 1–3 complete (design, vision tagging, embeddings + matching + guard).
> Phase 4 in progress (review API, final polish).

## What it does

1. Reads each image with a vision model and produces structured tags (subject,
   category, attributes, caption, confidence)
2. Turns image captions and blog post text into embeddings, and ranks images by how
   closely they match a post's meaning
3. Runs every top match through a mismatch guard before suggesting it — rejecting
   anything that doesn't clear the bar, with a plain-language reason
4. Processes images in the background as batch jobs, with retries and cost tracking
5. Exposes a small review API to approve/reject suggested image-post pairings

See [`DESIGN.md`](./DESIGN.md) for the full design doc — problem statement, data
model, matching strategy, guard rules, and API surface.

## Tech stack

- Python + FastAPI
- PostgreSQL (via Docker) — planned for Phase 4
- Vision model: Gemini (gemini-3.5-flash-lite, free tier)
- Embeddings: Gemini (gemini-embedding-001, free tier)

## Setup

> Placeholder — will be finalized once the review API (Phase 4) is built.

```bash
# 1. Clone the repo
git clone https://github.com/Nidaamir083/flyrank-capstone-image_relevance.git
cd flyrank-capstone-image_relevance

# 2. Copy the example env file and fill in your own API key
cp .env.example .env

# 3. Install dependencies
pip install -r requirements.txt   # TODO: add this file

# 4. Run the pipeline
python batch_tag_images.py   # tags all images
python embed_all.py          # embeds images and posts
python measure_precision.py  # runs the guard and reports precision

# 5. Start the review API (TODO, Phase 4)
```

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
breakdown, and `EVIDENCE.md` for the raw output.

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
- **No frontend UI.** Review happens through API endpoints and/or a simple table,
  by design (this is a stated non-goal — see `DESIGN.md`).
- **Free-tier rate limits shaped the build.** Google's Gemini free tier enforces
  daily request limits that vary significantly by model (as low as 20/day on some
  models, up to 500/day on lighter models). The batch job includes retries and a
  daily-limit detector to handle this gracefully rather than crashing.
- **Small dataset.** 59 images across 6 categories (bear, deer, dog, red fox, wolf,
  coyote) plus one deliberately blurry test image. Enough to demonstrate the
  approach; a production system would need a much larger, more diverse library.

## Project docs

- [`DESIGN.md`](./DESIGN.md) — design doc
- [`EVIDENCE.md`](./EVIDENCE.md) — proof for each requirement
- [`BUILDLOG.md`](./BUILDLOG.md) — honest log of where AI helped and what I changed
- `eval_labels.json` — hand-labeled ground truth used for evaluation
- `data/eval_results.json` — full per-post precision results
- `capstone.yaml` — evaluator manifest (TODO, Phase 4)
- `.env.example` — required environment variables with placeholder values
