from ai.ai import GigaChatt

ai_client = GigaChatt()


async def generate_text(prompt: str) -> str:
    return ai_client.ask(prompt)


async def check_essay(text: str) -> str:
    prompt = f"""Проверь сочинение на ошибки и дай рекомендации:

    1. Орфографические ошибки
    2. Пунктуационные ошибки  
    3. Стилистические ошибки
    4. Логические несоответствия
    5. Рекомендации по улучшению

    Сочинение для проверки:
    {text}

    Ответ предоставь в структурированном виде."""

    return await generate_text(prompt)