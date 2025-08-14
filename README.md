# Torrent Title Parser API

This project provides a robust, containerized application to parse torrent titles into structured JSON metadata. It uses a hybrid approach, combining fast, deterministic regex parsing with a lightweight GGUF language model (`unsloth/Qwen3-0.6B-GGUF`) for refinement and title extraction.

The entire application runs on the CPU and is optimized for low-power hardware, including non-AVX CPUs like the Intel N5105.

## Features

- **Hybrid Parsing:** Fast regex-first approach, with LLM for ambiguity resolution.
- **FastAPI Backend:** Exposes a clean, documented API.
- **Minimal Frontend:** A simple HTMX/Tailwind UI for easy interaction.
- **Dockerized:** Thin, reproducible image via a multi-stage Docker build.
- **CPU-Only:** Runs `llama-cpp-python` without a GPU.
- **Auditing:** Logs all requests/responses to a file and persists results to an SQLite database.
- **Configurable:** Settings managed via an `.env` file (API key, CORS, etc.).

---

## 1. Setup and Installation

### Prerequisites

-   [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
-   `git` to clone the repository.
-   `huggingface-cli` for easy model download (optional, but recommended).

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd <repo-name>
