import json
from openai import OpenAI

client = OpenAI()
resp = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": "Return JSON only."},
        {"role": "user", "content": "For the chemistry topic 'Atomic radius', return an object with fields title, hook, claim, beats (array of four short captions), and closing."},
    ],
    max_completion_tokens=1200,
)
print(json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))
