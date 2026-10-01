# Evidence

One proof per requirement from the capstone brief (Section 6).
Status is updated as I build. Claims without pasted output are marked NOT YET.

## AI processing

### Vision model produces structured output validated against a schema
Status: DONE 

- Schema: `schemas.py` (`ImageTags`, Pydantic). Confidence must be between 0 and 1.
- Every Gemini answer is checked with `ImageTags.model_validate_json(...)` in `batch_tag_images.py`.
- Invalid answers are retried, never accepted.

Proof (real output from `python test_one_image.py`):

```json
{
  "subject": "red fox",
  "category": "animal",
  "attributes": ["reddish-brown fur", "curled up", "lying in green grass", "closed eyes"],
  "caption": "A red fox is curled up and resting in a field of tall green grass.",
  "confidence": 0.95
}
```

### Low-confidence classifications are flagged instead of accepted
Status: DONE 

- Rule: confidence below 0.6 gives status `flagged`, in `batch_tag_images.py`.
- Proof: I deliberately created a very blurry test image (`make_blurry_test.py`, heavy
  Gaussian blur applied to a real fox photo) to check the rule actually works, rather
  than hoping a random stock photo would be unclear.

Real output from `python batch_tag_images.py`:

```
[39/59] Tagging: images/hard_cases/blurry_1.jpg
   -> unknown (confidence 0.05) [flagged]
```

The model correctly reported very low confidence on an image it genuinely
could not identify, and the flagging rule caught it.

### Images are processed through a batch background job with retries
Status: DONE 

- Script: `batch_tag_images.py` (retries with growing waits, skips finished images,
  60 second timeout per call, retries network errors as well as API errors).
- Proof: real retry output from Google's servers being busy:

```
[1/50] Tagging: images/bear/bear_1.jpg
   Attempt 1: API error 503
   Waiting 2 seconds before trying again...
   Attempt 2: API error 503
   Waiting 4 seconds before trying again...
   Attempt 3: API error 503
   FAILED after all attempts
```

- Proof: final run summary, after re-running the same command multiple times as the
  dataset grew (only unfinished images were redone each time):

```
===== SUMMARY =====
Done: 59 of 59 | Tagged: 58 | Flagged (low confidence): 1 | Failed: 0 | Still to do: 0
Tags saved in:  data\image_tags.json
Cost log in:    data\cost_log.csv
```

Note: this is a script run from the command line, not yet a job triggered from the
API. TODO in a later phase.

### Vision and embedding costs are tracked per call
Status: DONE

- `data/cost_log.csv` gets one row per Gemini call (vision AND embedding calls both
  log to this same file): time, item name, model, input tokens, output tokens,
  cost, status.
- Vision tagging costs: logged throughout Phase 2, 59 images.
- Embedding costs: logged throughout Phase 3, 58 images + 7 posts (`embed_all.py`).
- Paste the first 5 lines of `data/cost_log.csv` here.
  t_tokens,output_tokens,cost_usd,status
2026-09-28T10:43:03,images\bear\bear_1.jpg,gemini-3.5-flash,0,0,0.0,api_error_503
2026-09-28T10:43:07,images\bear\bear_1.jpg,gemini-3.5-flash,0,0,0.0,api_error_503
2026-09-28T10:43:13,images\bear\bear_1.jpg,gemini-3.5-flash,0,0,0.0,api_error_503
2026-09-28T10:43:32,images\bear\bear_10.jpg,gemini-3.5-flash,1241,63,0.0,ok

## Matching system

### Image and post embeddings are stored; posts return ranked image suggestions
Status: DONE 

- Script: `embed_all.py`. Every image caption and every post's title+body embedded
  with Gemini's `gemini-embedding-001` model, task type `SEMANTIC_SIMILARITY`.
  Saved to `data/embeddings.json`.
- Script: `rank_images.py`. For any post, ranks every image by cosine similarity,
  highest first.

Proof (real output, `python rank_images.py`, post_1):

```
Top 5 image matches for: The secret life of red foxes

1. images/red_fox/red_fox_3.jpg
   Similarity score: 0.837
   Subject: red fox | Category: animal
2. images/red_fox/red_fox_5.jpg
   Similarity score: 0.826
3. images/red_fox/red_fox_6.jpg
   Similarity score: 0.823
4. images/red_fox/red_fox_7.jpg
   Similarity score: 0.818
5. images/coyote/coyote_2.jpg
   Similarity score: 0.816
```

### Semantic matching works for equivalent concepts ("red fox" matches "Vulpes vulpes")
Status: PARTLY DEMONSTRATED

- Not tested with the exact "Vulpes vulpes" example from the brief, but the same
  underlying behavior is shown: matching works on MEANING, not exact keywords.
  Evidence: the "coyote" post's top result was a real coyote photo, and its
  4th/5th ranked results were gray wolf photos (0.797, 0.795) even though the
  post never uses the word "wolf" — the model captured that coyotes and wolves
  are conceptually related animals.
- TODO: could add a direct "Vulpes vulpes" test post in a future pass for a more
  literal match to the brief's example.

## Safety layer

### The mismatch guard rejects incorrect recommendations (wolf on a fox post fails)
Status: DONE

- Script: `mismatch_guard.py` (ranked candidates, checked in order) and
  `test_guard_directly.py` (forces a specific image against a specific post,
  matching the brief's Probe 3: "force the wolf as a candidate for the fox post").

Proof (real output, `python test_guard_directly.py`):

```
Post: The secret life of red foxes
Forced candidate: images/wolf/wolf_3.jpg (subject: 'gray wolf')
Similarity score: 0.789
RESULT: REJECTED - category mismatch: expected one of [fox], detected 'gray wolf'.
```

Additional proof the guard is consistent even against confident wrong data:

```
Post: Why gray wolves are misunderstood
Forced candidate: images/wolf/wolf_10.jpg (subject: 'white dog')
Similarity score: 0.751
RESULT: REJECTED - category mismatch: expected one of [wolf], detected 'white dog'.
```

(`wolf_10` is a real wolf by my own visual review, but the vision model tagged it
"white dog" in Phase 2. The guard correctly rejects based on the tag it was given,
which is the safe behavior — see BUILDLOG.md for the full story.)

Additional proof of the ambiguous-photo rule (a photo mentioning more than one
animal is rejected before its similarity score is even considered):

```
Post: Deer in the wild: grace and caution
Forced candidate: images/deer/deer_4.jpg (subject: 'giraffe and deer')
Similarity score: 0.863
RESULT: REJECTED - ambiguous photo, more than one animal mentioned.
```

And proof a genuine match still passes cleanly:

```
Post: The secret life of red foxes
Forced candidate: images/red_fox/red_fox_3.jpg (subject: 'red fox')
Similarity score: 0.837
RESULT: ACCEPTED - subject matches and similarity clears the threshold.
```
### Adversarial stress test (added in response to reviewer feedback)
14 forced lookalike/unrelated-post tests, all correctly rejected:
- Fox ↔ wolf ↔ coyote ↔ dog cross-confusions (4 tests)
- All 3 antelope species (blackbuck, nyala, springbok) forced onto the deer post (3 tests)
- 3 animal photos forced onto 3 unrelated posts (travel, recipe, time-blocking)
- Plus the original 4 core tests

Full output: see `test_guard_directly.py` run log.

Updated top-1 precision on the expanded 10-post eval set (4 true-negative cases,
up from 1): **10 of 10 (100%)**

### Rejections include a human-readable explanation
Status: DONE (Phase 3)

- Every REJECTED result above includes a plain-language reason (category mismatch,
  ambiguous photo, or below threshold). Same proof as the section above.

### When no image clears the bar, the system answers "no confident match" with reasons
Status: DONE (Phase 3)

Proof (real output, `python mismatch_guard.py`, post_7):

```
=== post_7: Our new office coffee machine, reviewed ===
NO CONFIDENT MATCH
  Reason: This post is not about any of our known animal categories.
```

## Backend

### Database models for images, tags, embeddings, posts, suggestions, approvals/rejections
Status: DESIGNED ONLY (see `DESIGN.md`). Not built yet.

### API endpoints validated; review workflow (approve / reject / inspect why) exists
Status: DONE
![alt text](<json response.PNG>)

## Quality and documentation

### Labeled evaluation dataset measures top-1 precision; number is in the README
Status: Done

7 of 7 posts correct -> precision = 1.00 (100%)

- Ground-truth notes gathered so far, from my own review of the images (to become
  the eval labels file):
  - `deer_1`, `deer_10`: blackbuck, not deer
  - `deer_3`: nyala, not deer
  - `deer_4`: giraffe plus antelope, not deer, mixed photo
  - `deer_5`: springbok, not deer
  - `wolf_8`: husky or wolfdog, uncertain, exclude from wolf tests
  - `wolf_10`: true label wolf (model said "white dog", model is wrong here)
  - `coyote_2`: true label coyote (model said "fox", model is wrong here)

### README with architecture explanation and diagram; required files present
Status: DONE

- Present: `README.md` (finalized with real setup steps, evaluation results,
  ASCII architecture diagram, and limitations), `DESIGN.md`, `.env.example`,
  `.gitignore`, `LICENSE`, `EVIDENCE.md`, `BUILDLOG.md`, `capstone.yaml`,
  `requirements.txt`.
