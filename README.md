# Chat bot for fun

Chat bot with some functionality:

- answer on commands
- reacts on some keywords in text
- support for eki game

# Code validations
### Lint
`make lint`

### Tests
`make tests`

# Build image
`make build`

# Run created container
docker run --env-file .env --rm -d --name <cont_name> skraynev/chat_bot 