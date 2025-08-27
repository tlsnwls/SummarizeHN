from google import genai
# from google.genai import types
from google.genai.errors import ServerError
import time
import json
import re

# Environment variable: GEMINI_API_KEY or GOOGLE_API_KEY
client = genai.Client()

INTEREST_CATEGORIES = [
    "Cloud Computing",
    "Software Engineering",
    "Startups & Venture Captial",
    "Cybersecurity",
    "New Technology",
    "Artificial Intelligence",
    "Linux & Operating System"
]

def extract_json(text:str):
    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def get_article_category(titles: str, max_retries: int = 3):
    prompt = f"""
    You are a tech news curator specializing in software engineering, development, and startup trends.
    For each of the following article titles, do the following:

    1. Classify the title into one of these categories:
    {', '.join(INTEREST_CATEGORIES)}.

    2. Assign two priority scores from 1 to 5:
    - "EngineerPriority": How relevant or interesting this article is for a software engineer or developer
        5 = extremely relevant/interesting
        1 = not relevant
    - "StartupPotential": How useful or inspiring this article could be for a startup or business idea
        5 = very high potential
        1 = no potential

    3. Respond strictly in JSON format as:
    {{
    "title1": {{"category": "Software Engineering", "EngineerPriority": 5, "StartupPotential": 3}},
    "title2": {{"category": "Other", "EngineerPriority": 1, "StartupPotential": 1}},
    ...
    }}

    If a title does not fit any of the categories, use "Other" and assign both priorities as 1.

    Titles: {json.dumps(titles, ensure_ascii=False, indent=2)}
    """
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            raw_text = response.text.strip()
            text = extract_json(raw_text)
            try:
                categories = json.loads(text)
                return categories
            except json.JSONDecodeError:
                print("Model did not return valid JSON. Raw output:")
                print(text)
                return {title:"ParseError" for title in titles}
        except ServerError as e:
            print(f"[Retry {attempt+1}/{max_retries}] Gemini 500 error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return {title:"API Error" for title in titles}
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {title:"API Error" for title in titles}

