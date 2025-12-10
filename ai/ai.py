from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from config.settings import settings


class GigaChatt:
    def __init__(self):
        self.client = GigaChat(
            credentials=settings.GIGACHAT_KEY,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False
        )

    def ask(self, prompt: str) -> str:
        messages = [
            Messages(
                role=MessagesRole.USER,
                content=prompt
            )
        ]

        response = self.client.chat(
            Chat(
                messages=messages,
                max_tokens=800
            )
        )

        return response.choices[0].message.content