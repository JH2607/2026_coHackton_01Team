
from ai_service import get_openrouter_client

client, model = get_openrouter_client()
print("현재 모델:", model)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "안녕하세요라고만 답해"}
        ],
        max_tokens=30,
    )
    print("AI 응답:", response.choices[0].message.content)

except Exception as e:
    print("API 오류:", type(e).__name__)
    print(str(e)[:500])
