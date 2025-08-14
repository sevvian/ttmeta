# Stage 1: Builder
# This stage compiles dependencies, including llama-cpp-python from source
# for CPUs without AVX/AVX2 support (like Intel N5105).
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set CMAKE_ARGS to compile for a baseline CPU without AVX support.
# This ensures compatibility with older/low-power CPUs.
# For modern CPUs with AVX2, you can remove this ENV line.
ENV CMAKE_ARGS="-DGGML_CPU_F16=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_AVX512=OFF -DGGML_FMA=OFF"
ENV FORCE_CMAKE=1

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# Stage 2: Final Image
# This stage uses the pre-built wheels for a lean final image.
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create directories for data, logs, and models and set permissions
RUN mkdir -p /app/data /app/logs /models && \
    chown -R appuser:appuser /app/data /app/logs /models

# Copy pre-built wheels from the builder stage
COPY --from=builder /wheels /wheels

# Install the wheels
# --no-index prevents pip from accessing PyPI
# --find-links tells pip to look in the /wheels directory
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /wheels/requirements.txt && \
    rm -rf /wheels

# Copy the application code
COPY ./app ./app

# Set ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

EXPOSE 8000

# Set entrypoint to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
