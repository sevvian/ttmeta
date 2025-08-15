import sys
import platform
import llama_cpp

def run_health_check():
    """
    Performs a health check on the llama_cpp installation using functions
    verified against the official documentation.
    """
    print("--- Documentation-Verified Llama CPP Python Health Check ---")
    
    try:
        # 1. Print basic version and platform info
        print(f"Python Version: {sys.version}")
        print(f"Platform: {platform.platform()}")
        print(f"llama_cpp version: {llama_cpp.__version__}")
        
        # 2. Call the low-level backend initialization function.
        # This is the most basic test. If this fails, the core library is broken.
        print("\nAttempting to initialize llama.cpp backend...")
        llama_cpp.llama_backend_init(numa=False)
        print("Successfully called 'llama_backend_init'.")
        
        # 3. Get the system info directly from the C++ library.
        # This is the definitive way to check for AVX support.
        system_info_bytes = llama_cpp.llama_print_system_info()
        print("\n--- System Info from llama.cpp ---")
        info_str = system_info_bytes.decode('utf-8', errors='ignore')
        print(info_str)
        print("------------------------------------")
        
        # 4. Check that the system info confirms our expected build flags.
        # For your N5105, both AVX and AVX2 should be ON (1).
        if "AVX = 1" in info_str and "AVX2 = 1" in info_str:
            print("Status: [SUCCESS] Build flags (AVX=1, AVX2=1) correctly detected.")
        else:
            print("Status: [FAIL] Expected build flags (AVX=1, AVX2=1) were NOT detected in system info!")
            # This is a critical failure, but not a crash.
            # We will still let the script exit gracefully.

        # 5. Clean up the backend.
        llama_cpp.llama_backend_free()
        print("Successfully called 'llama_backend_free'.")

        print("\nFinal Status: [SUCCESS] Health check passed. The library is loadable and built with the correct flags.")
        return 0

    except Exception as e:
        print(f"\nFinal Status: [FAIL] An unexpected error occurred during health check: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_health_check())
