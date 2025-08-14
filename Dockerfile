# Stage 1: Builder
# This stage compiles dependencies, including llama-cpp-python from source.
# It is designed to be discarded after the build.
FROM python:3.11-slim as builder

# Install build-time dependencies required for compiling wheels.
# build-essential & cmake are for llama-cpp-python.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -----------------------------------------------------------------------------
# CRITICAL: Set CMake arguments to disable modern CPU instruction sets.
# This prevents "Illegal Instruction" (Exit Code 132) errors on older or
# low-power CPUs like the Intel N5105 that do not support AVX/AVX2.
# -----------------------------------------------------------------------------
ENV CMAKE_ARGS="-DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_AVX512=OFF -DGGML_FMA=OFF"
ENV FORCE_CMAKE=1

# Copy the requirements file and build all dependencies into wheels.
# This pre-compiles everything in the builder stage.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt


# -----------------------------------------------------------------------------
# Stage 2: Final Production Image
# This stage is the lean final image that will be deployed.
# It only contains the necessary runtime libraries and application code.
# -----------------------------------------------------------------------------
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install the essential runtime library for llama.cpp.
# libgomp1 is the GNU OpenMP library, required for multi-threaded CPU inference.
# Without this, the app will fail to load the llama_cpp library.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group for security.
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories and set their ownership to the non-root user.
# The container process will run as this user and needs write access.
RUN mkdir -p /app/data /app/logs /models && \
    chown -R appuser:appuser /app/data /app/logs /models

# Copy the pre-built wheels from the builder stage.
COPY --from=builder /wheels /wheels

# Install the Python dependencies from the pre-built wheels.
# This is much faster and doesn't require build tools in the final image.
# The '*.whl' pattern correctly installs all wheels in the directory.
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl && \
    rm -rf /wheels

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
