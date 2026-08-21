import time
import os
from app.agent.gemini import create_gemini_client

# Dummy API key for test
os.environ["GEMINI_API_KEY"] = "dummy_api_key_for_benchmark"

def benchmark():
    start_time = time.perf_counter()
    n = 1000
    for _ in range(n):
        client = create_gemini_client()
    end_time = time.perf_counter()

    total_time = end_time - start_time
    print(f"Total time for {n} calls: {total_time:.4f} seconds")
    print(f"Average time per call: {(total_time/n)*1000:.4f} ms")

if __name__ == "__main__":
    benchmark()
