from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List

import google.generativeai as genai
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_contact_numbers(
    image_path: str,
    api_key: str,
    model_name: str = "gemini-1.5-pro",
) -> List[str]:
    """
    Extract phone numbers from an image using Google's Gemini model.

    Args:
        image_path: Path to image.
        api_key: Google AI Studio API Key.
        model_name: Gemini model name.

    Returns:
        List[str]: List of unique phone numbers.
    """

    image_file = Path(image_path)

    if not image_file.exists():
        raise FileNotFoundError(f"Image not found: {image_file}")

    if image_file.suffix.lower() not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    }:
        raise ValueError("Unsupported image format.")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={
            "temperature": 0,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 200,
        },
    )

    prompt = """
You are an OCR assistant.

Read the image carefully.

Extract ONLY phone/contact numbers.

Rules:
- Return one number per line.
- Remove spaces and hyphens.
- Preserve country codes.
- Ignore usernames, IDs, dates and OTPs.
- If no phone number exists, return exactly:
NO_CONTACT_FOUND
"""

    try:
        with Image.open(image_file) as image:

            response = model.generate_content(
                [prompt, image],
                request_options={"timeout": 60},
            )

        if not response.text:
            return []

        text = response.text.strip()

        if text == "NO_CONTACT_FOUND":
            return []

        phone_pattern = re.compile(
            r"(?:\+?\d{1,3}[- ]?)?(?:\d[- ]?){8,15}"
        )

        numbers = phone_pattern.findall(text)

        cleaned = sorted(
            {
                re.sub(r"[^\d+]", "", number)
                for number in numbers
            }
        )

        logger.info("Found %d phone numbers", len(cleaned))

        return cleaned

    except Exception:
        logger.exception("Gemini request failed")
        raise


if __name__ == "__main__":

    API_KEY = "YOUR_API_KEY"

    IMAGE_PATH = "screenshot.jpg"

    try:
        contacts = extract_contact_numbers(
            IMAGE_PATH,
            API_KEY,
        )

        if contacts:
            print("\nExtracted Numbers:")
            for number in contacts:
                print(number)
        else:
            print("No contact numbers found.")

    except Exception as exc:
        print(f"Error: {exc}")
