# Build Log: AI Usage

Honest log of where AI helped, where it was wrong, and what I changed.
I use Claude as a coding helper and explainer. I must be able to explain any line of my own code.

## Session 1: Phase 1 and Phase 2

### Where AI helped
- Explained the capstone brief in simple steps and suggested a daily pace.
- Drafted `DESIGN.md` (problem, schema, matching strategy, guard rules, database tables, API list, non-goal) and the starter `README.md`.
- Wrote `download_images.py` (Pexels download, 10 images for each of 5 animals).
- Wrote `schemas.py`, `test_one_image.py` and `batch_tag_images.py` (Gemini vision tagging, schema validation, retries, cost log).

### Where AI was wrong or needed fixing
1. **Rate limit misdiagnosis.** Gemini returned error 429 for almost every image. The AI first suggested I was sending requests too fast and told me to slow the script down. The real error message said the limit was **20 requests per day** for `gemini-3.5-flash`, and I had used it up. Slowing down could not fix that.
   - What I changed: I checked the rate-limit page in Google AI Studio, saw that `gemini-3.5-flash-lite` allows 500 requests per day, and switched the model in `.env`. The script now also stops right away when it sees a daily-limit error instead of retrying.
2. **Retry code missed network errors.** The script crashed with a dropped internet connection (`WinError 10053`). The first retry code only handled Google error codes (503, 429).
   - What I changed: added a catch for network errors (`httpx.HTTPError`) and a 60 second timeout per call. This same crash happened a second time later because I had only applied the timeout line by hand and missed the actual network-error fix; had to compare line numbers in the traceback to notice the fix wasn't actually installed.
3. **Model names.** The AI was not sure which Gemini model names were current or free. I made the model name a setting in `.env` (`GEMINI_MODEL`) so I can change it without editing code.
4. **A frozen terminal.** The script hung once and Ctrl+C did not work. I closed the terminal and re-ran it. Finished images were safe because the script saves after every image.

### Where the vision model was wrong (found by my own review)
- `wolf_10.jpg` is a white wolf (my own check), but the model called it "white dog" with confidence 0.95. Shows the model can be very confident and still wrong.
- `wolf_8.jpg` was called "Siberian husky". It is probably a husky or wolfdog, so the folder label is what is wrong, not necessarily the model.
- Several images in the `deer` folder were tagged blackbuck, nyala, springbok or giraffe. The Pexels search "deer" returned other animals. Replaced with 5 confirmed real deer photos (`deer_11` to `deer_15`).
- `coyote_2.jpg` was tagged "fox" with confidence 0.85. A genuine mismatch case, useful for testing the guard later.
- Lesson: folder names and model confidence are not ground truth. The eval set must be labeled by me looking at each image.

### Deliberate test cases I added (not from the Pexels search results)
- `images/coyote/` (3 photos): coyotes are a real lookalike for fox/wolf/dog, a harder test than any of the animals originally in scope.
- `images/hard_cases/blurry_1.jpg`: a real fox photo I deliberately blurred heavily with `make_blurry_test.py`, specifically to check whether the "flag low confidence" rule actually works, rather than hoping a random stock photo would happen to be unclear. It worked: confidence 0.05, correctly flagged.

### A problem I noticed myself: oversized images
When I manually added 5 replacement deer photos (`deer_11.jpg` to `deer_15.jpg`,
after finding several original "deer" photos were actually antelope species), I
checked their file sizes before committing out of caution and found they ranged
from 1.3 MB to 4.2 MB each — full-resolution originals, much larger than the
Pexels "medium" downloads the rest of the dataset used. This mattered for two
reasons: the capstone brief says not to commit large datasets, and large uploads
to Gemini may have been contributing to the dropped-connection errors I was
seeing around the same time. I wrote `shrink_images.py` to resize any image over
500 KB down to a max of 1200px on the long side, and ran it before committing.
Lesson: check file sizes before committing new images, not just their content.

### Things I need to be able to explain (fill in my own words)
- What `ImageTags.model_validate_json` does and why the schema check matters:
- Why the script waits longer after each failed attempt:
- Why the script skips images that are already tagged:
- Why `.env` is in `.gitignore`:
- Why a blurred fox image was a better test than searching for a random blurry stock photo:
