# --- SINGLE-STAGE N5105-SAFE DOCKERFILE ---
FROM python:3.11-slim

# Install build-time and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -----------------------------------------------------------------------------
# CMake args tuned for Intel N5105 (Jasper Lake)
# AVX2, AVX, FMA enabled (fast), AVX512 disabled (avoids SIGILL / exit 132)
# -----------------------------------------------------------------------------
ENV CMAKE_ARGS="-DLLAMA_NATIVE=OFF \
                -DLLAMA_AVX2=ON \
                -DLLAMA_AVX=ON \
                -DLLAMA_FMA=ON \
                -DLLAMA_AVX512=OFF \
                -DLLAMA_F16C=ON \
                -DLLAMA_SSE4=ON"
ENV FORCE_CMAKE=1

# -----------------------------------------------------------------------------
# Step 1: Build llama-cpp-python FIRST from source to lock in correct CPU flags
# -----------------------------------------------------------------------------
RUN pip install --no-cache-dir -v \
    --no-binary=llama-cpp-python \
    llama-cpp-python==0.2.79

# -----------------------------------------------------------------------------
# Step 2: Install the rest of the dependencies (excluding llama-cpp-python wheel)
# -----------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -v \
    --no-binary=llama-cpp-python \
    -r requirements.txt

# -----------------------------------------------------------------------------
# Step 3: Copy application code AND the test script
# -----------------------------------------------------------------------------
COPY ./app ./app

# --- THIS IS THE MISSING LINE ---
# Copy your test script into the container's working directory (/app)
#COPY test_llm.py .
# --- END OF FIX ---

# Create non-root user and set permissions for ALL copied files
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /app/data /app/logs /models \
    && chown -R appuser:appuser /app

USER appuser

# -----------------------------------------------------------------------------
# Step 4: Expose port & set default command
# -----------------------------------------------------------------------------
EXPOSE 8000
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# SET the new command to run our health check script
CMD ["python", "-u", "app/test_llm.py"]
