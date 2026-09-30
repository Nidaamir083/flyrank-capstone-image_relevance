import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

from schemas import ImageTags

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

if not API_KEY:
    print("No API key found. Add GEMINI_API_KEY=your_key to your .env file.")
    exit()


IMAGE_PATH = os.path.join("images", "red_fox", "red_fox_1.jpg")


PROMPT = """Look at this image and describe it.
- subject: the main thing in the image, as specific as possible (e.g. "red fox", "gray wolf")
- category: one broad word (e.g. "animal", "food", "landscape")
- attributes: 3 to 5 short visual details
- caption: one short sentence describing the image
- confidence: a number from 0 to 1 showing how sure you are about the subject.
  Use a LOW number if the image is blurry, unclear, or you are not sure what it shows.
Be honest about confidence. Do not guess."""


def tag_image(image_path):
    """Sends one image to Gemini and returns validated tags (or None if invalid)."""

    
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=API_KEY)

   
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ImageTags,
        ),
    )

    usage = response.usage_metadata
    print(f"Tokens used -> input: {usage.prompt_token_count}, output: {usage.candidates_token_count}")

    try:
        tags = ImageTags.model_validate_json(response.text)
        return tags
    except ValidationError as error:
        print("The AI's answer did NOT match our template:")
        print(error)
        print("Raw answer was:", response.text)
        return None


def main():
    print(f"Testing one image: {IMAGE_PATH}")
    print(f"Using model: {MODEL_NAME}\n")

    tags = tag_image(IMAGE_PATH)

    if tags is None:
        print("\nResult: INVALID answer (in the real pipeline we would retry this).")
        return

    print("\nResult: VALID answer")
    print(tags.model_dump_json(indent=2))

    
    if tags.confidence < 0.6:
        print("\nFLAGGED: confidence is low, a human should review this image.")


if __name__ == "__main__":
    main()

# NOTE: If you see an error like "model not found" or "404":
# Google renames and retires model names often. Open aistudio.google.com,
# look at the model list, pick a current Flash model that says it is free,
# and put its name in your .env file like this:
#     GEMINI_MODEL=the-model-name-here