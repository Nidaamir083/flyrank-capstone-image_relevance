# AI Image Understanding & Content Matching Engine

FlyRank Backend Track Capstone — a system that reads a library of images, understands
what's really in each one using a vision AI model, and matches the right image to the
right blog post based on meaning, not filenames or keywords.

The key feature is the **mismatch guard**: a safety layer that rejects a bad match
(e.g. suggesting a wolf photo for a fox article) and explains why, instead of
guessing. Good suggestions when confident, safe rejection when not.

> Status: In progress — currently in the Design phase. This README will be filled in
> as each part gets built.

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
- PostgreSQL (via Docker)
- Vision model: Gemini Flash (free tier) or Ollama (local)
- Embeddings: Gemini embeddings (free tier) or Ollama

## Setup

> Placeholder — will be filled in once the pipeline is built (Phase 2 onward).

```bash
# 1. Clone the repo
git clone https://github.com/YOUR-USERNAME/flyrank-capstone-imagerelevance.git
cd flyrank-capstone-imagerelevance

# 2. Copy the example env file and fill in your own API key
cp .env.example .env

# 3. Start the app (exact command TBD once Docker setup is added)
docker compose up

# 4. Seed demo data (TBD)
```

## Evaluation

A small labeled evaluation set will be used to measure top-1 precision — how often
the system's first suggested image is the correct one. The result will be reported
here once Phase 4 is complete.

## Limitations

> Placeholder — an honest note on what this project does *not* do will go here
> (e.g. no frontend UI — review happens via API only).

## Project docs

- [`DESIGN.md`](./DESIGN.md) — design doc
- `capstone.yaml` — evaluator manifest (added in Phase 4)
- `EVIDENCE.md` — proof for each requirement (added as I build)
- `BUILDLOG.md` — honest log of where AI helped and what I changed (added as I build)
- `.env.example` — required environment variables with placeholder values
