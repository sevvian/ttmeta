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
# CRITICAL: Set CMake arguments to disable modern CPU instruction sets.
# This is our primary defense against Exit Code 132.
# -----------------------------------------------------------------------------
ENV CMAKE_ARGS="-DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_AVX512=OFF -DGGML_FMA=OFF"
ENV FORCE_CMAKE=1

# Copy requirements file first for layer caching
COPY requirements.txt .

# -----------------------------------------------------------------------------
# Install dependencies with maximum control and verbosity.
# --no-cache-dir: Prevents pip from using its own cache.
# --no-binary: Forces pip to build from source for these specific packages.
#              This is KEY to ensuring uvicorn/uvloop and llama-cpp-python
#              are compiled without illegal instructions.
# -v: Verbose flag to see detailed build output.
# -----------------------------------------------------------------------------
RUN pip install --no-cache-dir -v \
    --no-binary uvicorn \
    --no-binary llama-cpp-python \
    -r requirements.txt

# --- The rest of the Dockerfile is for setting up the runtime environment ---

# Create a non-root user and group for security.
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories and set their ownership.
# This time we do it *after* pip install to avoid permission issues during build.
RUN mkdir -p /app/data /app/logs /models && \
    chown -R appuser:appuser /app/data /app/logs /models

# Copy the application code into the image.
COPY ./app ./app

# Set ownership of the application code to the non-root user.
RUN chown -R appuser:appuser /app

# Switch to the non-root user for running the application.
USER appuser

# Expose the port the application will run on.
EXPOSE 8000

# Define the command to run the application.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
