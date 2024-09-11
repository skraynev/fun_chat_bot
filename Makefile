lint:
	black .
	flake8 .

test:
	pytest tests/*

build:
	docker build -f docker/Dockerfile -t skraynev/chat_bot .
