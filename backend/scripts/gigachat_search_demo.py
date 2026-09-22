import asyncio
import json
import sys

from app.clients.gigachat import GigaChatClient
from app.clients.searxng import search
from app.function_schema import WEB_SEARCH_FUNCTION


SYSTEM_PROMPT = (
    "Отвечай только на основе результатов web_search. "
    "Если функция не дала полезных данных — честно скажи, "
    "что не можешь ответить."
)


async def run(question: str) -> None:
    client = GigaChatClient()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    try:
        response = await client.complete_with_tools(
            messages,
            functions=[WEB_SEARCH_FUNCTION],
        )

        msg = response["choices"][0]["message"]

        if msg.get("function_call"):
            call = msg["function_call"]

            arguments = call["arguments"]

            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            query = arguments["query"]

            print(f"Поисковый запрос: {query}")

            results = await search(query)

            if not results:
                print("Поиск не дал результатов. Честный отказ.")
                return

            messages.append(msg)

            messages.append(
                {
                    "role": "function",
                    "name": "web_search",
                    "content": json.dumps(
                        results,
                        ensure_ascii=False,
                    ),
                }
            )

            response2 = await client.complete_with_tools(
                messages,
                functions=[WEB_SEARCH_FUNCTION],
            )

            final = response2["choices"][0]["message"].get(
                "content",
                "",
            )

        else:
            final = msg.get("content", "")

        print("\nОтвет:")
        print(final)

        if msg.get("function_call"):
            print("\nИсточники:")

            for result in results:
                print(
                    f"- {result['title']}: {result['url']}"
                )

    finally:
        await client.aclose()


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])

    if not question:
        question = "курс USD ЦБ сегодня"

    asyncio.run(run(question))