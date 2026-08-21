# app/agent/gemini.py
import os
import json
import functools

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.agent.tool_schemas import get_tool_schema
from app.models.plan import AnalysisPlan

load_dotenv()


MODEL_NAME = "gemini-3.5-flash-lite"


def create_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    return genai.Client(api_key=api_key)


def make_gemini_parameters(schema: dict) -> dict:
    """
    Convert a Pydantic JSON Schema into the subset
    accepted by Gemini function declarations.
    """

    parameters = {
        "type": schema["type"],
        "properties": {},
    }

    for name, property_schema in schema.get("properties", {}).items():

        converted = {
            key: value
            for key, value in property_schema.items()
            if key
            in {
                "type",
                "description",
                "enum",
                "format",
                "items",
            }
        }

        parameters["properties"][name] = converted

    if "required" in schema:
        parameters["required"] = schema["required"]

    return parameters


@functools.lru_cache(maxsize=None)
def get_gemini_tool_declarations():
    declarations = []

    for tool_name in (
        "ndvi_analysis",
        "landcover_analysis",
    ):
        schema = get_tool_schema(tool_name)

        parameters = make_gemini_parameters(schema["parameters"])

        declarations.append(
            types.FunctionDeclaration(
                name=schema["name"],
                description=schema["description"],
                parameters=parameters,
            )
        )

    return declarations


def extract_function_call(response):
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if part.function_call:
                return part.function_call

    return None


def ask_gemini(
    prompt: str,
):
    client = create_gemini_client()

    declarations = get_gemini_tool_declarations()

    tool = types.Tool(function_declarations=declarations)

    config = types.GenerateContentConfig(
        tools=[tool],
        automatic_function_calling=(types.AutomaticFunctionCallingConfig(disable=True)),
    )

    return client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=config,
    )


def generate_final_response(
    original_prompt: str,
    response,
    tool_result: dict,
):
    client = create_gemini_client()

    function_call = extract_function_call(response)

    if function_call is None:
        return response.text

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=original_prompt)],
        ),
        response.candidates[0].content,
        types.Content(
            role="user",
            parts=[
                types.Part.from_function_response(
                    name=function_call.name,
                    response={"result": tool_result},
                )
            ],
        ),
    ]

    declarations = get_gemini_tool_declarations()

    tool = types.Tool(function_declarations=declarations)

    config = types.GenerateContentConfig(
        tools=[tool],
        automatic_function_calling=(types.AutomaticFunctionCallingConfig(disable=True)),
    )

    final_response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=config,
    )

    return final_response.text


def generate_replan_response(
    original_prompt: str,
    response,
    tool_result: dict,
):
    client = create_gemini_client()

    function_call = extract_function_call(response)

    if function_call is None:
        raise RuntimeError("Cannot re-plan without an original function call.")

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=original_prompt)],
        ),
        response.candidates[0].content,
        types.Content(
            role="user",
            parts=[
                types.Part.from_function_response(
                    name=function_call.name,
                    response={"result": tool_result},
                )
            ],
        ),
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=(
                        "The analysis failed validation. "
                        "Do not provide a final answer yet. "
                        "Inspect the validation issues and "
                        "choose the next appropriate tool action. "
                        "Only use the available tools and their "
                        "declared parameters."
                    )
                )
            ],
        ),
    ]

    declarations = get_gemini_tool_declarations()

    tool = types.Tool(function_declarations=declarations)

    config = types.GenerateContentConfig(
        tools=[tool],
        automatic_function_calling=(types.AutomaticFunctionCallingConfig(disable=True)),
    )

    return client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=config,
    )


def create_analysis_plan(prompt: str) -> AnalysisPlan:
    client = create_gemini_client()

    print("Creating plan....")

    system_instruction = """
                You are the planning component of a geospatial analysis agent.

                Your job is to determine which available analyses
                are necessary to answer the user's question.

                Available analyses:

                1. ndvi_analysis
                Measures vegetation characteristics.

                2. landcover_analysis
                Measures land-cover composition.

                Rules:

                - Only use the analysis names listed above.
                - Do not invent analysis names.
                - Include only analyses that are relevant.
                - If one analysis is sufficient, return one analysis.
                - If multiple analyses are needed, return them in the
                order they should be performed.
                - Do not perform the analysis yourself.
                - Do not invent numerical results.
                """

    user_content = f"""
                User question:

                {prompt}
                """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=AnalysisPlan,
        ),
    )
    # print("")
    return AnalysisPlan.model_validate_json(response.text)


def synthesize_analysis_results(
    prompt: str,
    plan,
    results: list[dict],
):
    client = create_gemini_client()

    evidence = []

    for item in results:
        evidence.append(
            {
                "tool": item["tool"],
                "reason": item["reason"],
                "analysis": item["result"].model_dump(),
                "validation": item["validation"].model_dump(),
            }
        )

    system_instruction = """
                You are the synthesis component of a geospatial
                analysis agent.

                Answer the user's question using ONLY the analysis
                evidence provided below.

                Do not invent measurements, statistics, observations,
                or conclusions that are not supported by the evidence.

                Clearly distinguish between:
                - observed analysis results
                - reasonable interpretation of those results
                - limitations stated by the analyses

                If an analysis failed validation, do not present its
                results as reliable evidence.

                Provide a concise, evidence-backed answer.
                """

    user_content = f"""
                User question:
                {prompt}

                Analysis plan:
                {plan.model_dump_json()}

                Evidence:
                {evidence}
                """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
        ),
    )

    return response.text
