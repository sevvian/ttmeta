# --- SINGLE-STAGE DEBUGGING DOCKERFILE ---
FROM python:3.11-slim

# Install build-time AND runtime dependencies together.
# build-essential & cmake are for compiling from source.
# libgomp1 is the runtime dependency for llama.cpp.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -----------------------------------------------------------------------------
# CRITICAL: Set CMake arguments for Intel N5105 (Jasper Lake)
# This enables AVX2/AVX/FMA (which your CPU supports) and disables AVX512 (unsupported).
# -----------------------------------------------------------------------------
ENV CMAKE_ARGS="-DLLAMA_NATIVE=OFF \
                -DLLAMA_AVX2=ON \
                -DLLAMA_AVX=ON \
                -DLLAMA_FMA=ON \
                -DLLAMA_AVX512=OFF \
                -DLLAMA_F16C=ON \
                -DLLAMA_SSE4=ON"
ENV FORCE_CMAKE=1

# Copy requirements file first for layer caching
COPY requirements.txt .

# -----------------------------------------------------------------------------
# Install dependencies with controlled build flags.
# We force llama-cpp-python to build from source with the CPU-safe CMake flags.
# -----------------------------------------------------------------------------
RUN pip install --no-cache-dir -v \
    --no-binary llama-cpp-python \
    --no-binary uvicorn \
    -r requirements.txt

# --- The rest of the Dockerfile is for setting up the runtime environment ---

# Create a non-root user and group for security.
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories and set their ownership.
RUN mkdir -p /app/data /app/logs /models && \
    chown -R appuser:appuser /app/data /app/logs /models

# Copy the application code into the image.
COPY ./app ./app
RUN chown -R appuser:appuser /app

# Switch to the non-root user for running the application.
USER appuser

# Expose the port the application will run on.
EXPOSE 8000

# Default command to run the application.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
