lint:
	uv run black .
	uv run flake8 chat_bot/*

test:
	uv run pytest tests/*

build:
	docker build -f docker/Dockerfile -t skraynev/chat_bot .
