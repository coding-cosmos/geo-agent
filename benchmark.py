import timeit
from app.agent.gemini import get_gemini_tool_declarations

def run_benchmark():
    # Run the function 10000 times
    time_taken = timeit.timeit(
        "get_gemini_tool_declarations()",
        setup="from app.agent.gemini import get_gemini_tool_declarations",
        number=10000
    )
    print(f"Time taken for 10000 calls: {time_taken:.4f} seconds")

if __name__ == "__main__":
    run_benchmark()
