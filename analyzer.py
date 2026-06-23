import anthropic
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS
from prompts import SYSTEM_PROMPT

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def analyze_code(code: str, language: str = "otomatik tespit") -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Dil: {language}\n\nKod:\n```\n{code}\n```"
            }
        ]
    )
    return message.content[0].text

def analyze_multi(files: list) -> str:
    parts = [f"### {f['path']}\n```\n{f['code']}\n```" for f in files]
    content = "Aşağıdaki dosyalar birbiriyle ilişkili, birlikte analiz et:\n\n" + "\n\n".join(parts)
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )
    return message.content[0].text