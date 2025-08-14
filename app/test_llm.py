import sys
import os
import platform
import llama_cpp

def run_health_check():
    """
    Performs a basic health check on the llama_cpp installation.
    This script should run without errors if the library was compiled correctly.
    It deliberately does NOT load a model file to isolate the library itself.
    """
    print("--- Llama CPP Python Health Check ---")
    
    try:
        # 1. Print library and system information
        print(f"Python Version: {sys.version}")
        print(f"Platform: {platform.platform()}")
        print(f"llama_cpp module location: {llama_cpp.__file__}")
        
        # 2. Check for the compiled shared library (.so file)
        lib_path = llama_cpp.llama_cpp._lib_path
        if lib_path and os.path.exists(lib_path):
            print(f"Found shared library: {lib_path}")
            print("Status: [SUCCESS] Shared library file exists.")
        else:
            print("Status: [FAIL] Shared library file not found!")
            return 1

        # 3. Accessing llama_cpp functions proves the library can be loaded.
        # This will call a function inside the .so file. If it works, the
        # core library is not causing the SIGILL on its own.
        print("\nAttempting to access library functions...")
        llama_cpp.llama_backend_init(numa=False)
        print("Successfully called 'llama_backend_init'.")
        
        system_info = llama_cpp.llama_print_system_info()
        print("\n--- System Info from llama.cpp ---")
        # The output from llama_print_system_info is bytes, so we decode it
        print(system_info.decode('utf-8'))
        print("------------------------------------")
        
        llama_cpp.llama_backend_free()
        print("Successfully called 'llama_backend_free'.")

        print("\nStatus: [SUCCESS] Health check passed. The llama_cpp library is correctly compiled and loadable.")
        return 0

    except Exception as e:
        print(f"\nStatus: [FAIL] An unexpected error occurred during health check: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_health_check())
