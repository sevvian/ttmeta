.PHONY: all build up down logs shell test clean

# Default command
all: up

# Build the Docker image
build:
	docker compose build

# Start the services in detached mode
up:
	docker compose up -d --build

# Stop and remove the services
down:
	docker compose down

# View logs from the app service
logs:
	docker compose logs -f app

# Access a shell inside the running app container
shell:
	docker compose exec app /bin/bash

# Run pytest tests inside a temporary container
test:
	docker compose run --rm app pytest

# Clean up Docker resources
clean: down
	docker compose rm -f
	docker volume prune -f
