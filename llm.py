import httpx

text = """Cb0fAaF0 QDQl a6YU6Iu WFsgp NqYV5F9  
50 3hOWMW0O4"""

response = httpx.post(
    "https://api.openai.com/v1/chat/completions",
    headers={
        "Authorization": "Bearer dummy-api-key",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Analyze the sentiment of the following text and classify it as GOOD, BAD, or NEUTRAL.",
            },
            {"role": "user", "content": text},
        ],
    },
)
response.raise_for_status()
print(response.json()["choices"][0]["message"]["content"])
