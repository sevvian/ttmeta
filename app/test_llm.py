import sys
import os
import llama_cpp

MODEL_PATH = "/models/qwen3.gguf"

def run_load_test():
    """
    Attempts to load the specified GGUF model file.
    This is the final test to confirm if the model itself is the source
    of the SIGILL (Exit Code 132) crash.
    """
    print("--- Llama CPP Model Load Test ---")
    
    # Check if the model file actually exists inside the container
    if not os.path.exists(MODEL_PATH):
        print(f"Status: [FAIL] Model file not found at '{MODEL_PATH}' inside the container.")
        print("Please ensure your volume mount is correct and the file is present.")
        return 1
    
    print(f"Found model file at: {MODEL_PATH}")
    print("Attempting to initialize Llama class...")
    
    try:
        # This is the line that will crash if the model is incompatible.
        llm = llama_cpp.Llama(
            model_path=MODEL_PATH,
            n_ctx=512,      # Small context for a quick test
            n_threads=2,   # Use 2 threads for the test
            n_gpu_layers=0 # CPU only
        )
        
        # If the script reaches this line, the model loaded successfully.
        print("\n--- MODEL LOADED SUCCESSFULLY! ---")
        print(f"Model Details: {llm}")
        print("\nFinal Status: [SUCCESS] The model is compatible with your CPU and llama_cpp build.")
        return 0

    except Exception as e:
        # This will likely not be reached if it's a SIGILL crash,
        # but it's good practice to have it.
        print(f"\nFinal Status: [FAIL] An error occurred during model loading: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_load_test())
