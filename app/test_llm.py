import sys
import os
import platform
import llama_cpp
import llama_cpp.llama_cpp as llama_cpp_internal

def run_health_check():
    """
    Performs a basic health check on a MODERN (>=0.2.80) llama_cpp installation.
    This script should run without errors if the library was compiled correctly.
    """
    print("--- Modern Llama CPP Python Health Check ---")
    
    try:
        # 1. Print library and system information
        print(f"Python Version: {sys.version}")
        print(f"Platform: {platform.platform()}")
        print(f"llama_cpp version: {llama_cpp.__version__}")
        
        # 2. In modern versions, the shared library path is found differently
        shared_lib_path = llama_cpp_internal.Llama.metadata.get("compiled_with_new_cmake")
        if shared_lib_path:
            print("Status: [SUCCESS] Library compiled with modern CMake build system.")
        else:
            print("Status: [NOTE] Library compiled with legacy build system.")

        # 3. Accessing llama_cpp functions proves the library can be loaded.
        print("\nAttempting to access library functions...")
        llama_cpp.llama_backend_init(numa=False)
        print("Successfully called 'llama_backend_init'.")
        
        system_info = llama_cpp.llama_print_system_info()
        print("\n--- System Info from llama.cpp ---")
        # The output from llama_print_system_info is bytes, so we decode it
        info_str = system_info.decode('utf-8')
        print(info_str)
        print("------------------------------------")
        
        # Check that the system info confirms the build flags
        if "AVX = 1" in info_str and "AVX2 = 1" in info_str:
            print("Status: [SUCCESS] Build flags (AVX=1, AVX2=1) correctly detected in system info.")
        else:
            print("Status: [WARNING] Expected build flags not detected in system info.")

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
