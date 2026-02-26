import os
from dotenv import load_dotenv

# NEW SDK (google-genai)
from google import genai

# Load .env
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ Error: GOOGLE_API_KEY not found.")
    raise SystemExit(1)

print(f"🔑 Key found: {api_key[:5]}...{api_key[-3:]}")

client = genai.Client(api_key=api_key)

print("\n📡 Connecting to Google API...")
print("-" * 80)
print(f"{'MODEL NAME':<55} | {'SUPPORTED'}")
print("-" * 80)

def _supported_methods(model_obj) -> str:
    """
    google-genai model objects vary a bit by version; try common fields.
    """
    for attr in (
        "supported_generation_methods",  # legacy-ish naming
        "supported_methods",
        "supported_actions",
        "capabilities",
    ):
        v = getattr(model_obj, attr, None)
        if v:
            return str(v)
    return ""

try:
    count = 0

    # google-genai: list models via client.models.list()
    # This returns an iterable/pager.
    for m in client.models.list():
        name = getattr(m, "name", None) or getattr(m, "model", None) or str(m)

        supported = _supported_methods(m)
        # Best-effort filter: keep models that look like they can generate content
        if supported:
            s = supported.lower()
            if "generate" not in s and "content" not in s:
                continue

        print(f"{name:<55} | {supported}")
        count += 1

    print("-" * 80)
    if count == 0:
        print("⚠️  No models listed as supporting generation. Check API key permissions/region.")
    else:
        print(f"✅ Found {count} candidate models.")

except Exception as e:
    print(f"\n❌ API Error: {e}")