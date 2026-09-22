WEB_SEARCH_FUNCTION = {
    "name": "web_search",
    "description": "Поиск актуальной информации в интернете",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Поисковый запрос",
            }
        },
        "required": ["query"],
    },
}