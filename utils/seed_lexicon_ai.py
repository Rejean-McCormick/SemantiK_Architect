import os
import sys
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load API Key
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("❌ Error: GOOGLE_API_KEY not found in .env")
    print("   Please add GOOGLE_API_KEY to your .env file.")
    sys.exit(1)

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# The prompt enforces the exact JSON schema your app needs
SYSTEM_PROMPT = """You are a computational linguist building a lexicon for an Abstract Wikipedia project.
Your task is to generate a JSON lexicon for a specific target language.

Output Format:
Return ONLY valid JSON. The structure must match this schema:
{
  "meta": {
    "language": "<ISO_CODE>",
    "schema_version": 1
  },
  "lemmas": {
    "<lemma_string>": {
      "pos": "NOUN" | "ADJ" | "VERB",
      "gender": "m" | "f" | "n" | "common" (optional),
      "human": true | false (optional),
      "nationality": true (optional, for adjectives like 'French')
    }
  }
}

Task:
Generate 30-50 common words used in biographical texts (professions, nationalities, basic verbs).
Include:
- Professions: physicist, writer, teacher, politician, doctor, chemist, actor, etc.
- Nationalities: American, French, German, Chinese, etc.
- Verbs: be, have, born, die, study, win.

Ensure the 'lemma' keys are in the Target Language (not English).
"""

def seed_lexicon(lang_code, lang_name):
    print(f"🌱 Seeding Lexicon for {lang_name} ({lang_code})...")
    print("   Asking Gemini to generate vocabulary...")

    try:
        response = model.generate_content(f"{SYSTEM_PROMPT}\nTarget Language: {lang_name} ({lang_code})")
        
        # Clean up potential markdown blocks
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        
        # Save to file
        output_path = os.path.join("data", "lexicon", f"{lang_code}_lexicon.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Success! Wrote {len(data['lemmas'])} words to {output_path}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python utils/seed_lexicon_ai.py <iso_code> <LangName>")
        print("Example: python utils/seed_lexicon_ai.py fra French")
        sys.exit(1)
        
    seed_lexicon(sys.argv[1], sys.argv[2])
