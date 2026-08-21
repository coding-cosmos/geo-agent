# tests/test_gemini.py
from unittest.mock import MagicMock, patch
from google.genai import types

from app.agent.gemini import (
    get_gemini_tool_declarations,
    make_gemini_parameters,
    ask_gemini,
    MODEL_NAME
)
from app.agent.tool_schemas import get_tool_schema


def test_gemini_parameters_remove_unsupported_fields():
    schema = get_tool_schema("ndvi_analysis")

    parameters = make_gemini_parameters(schema["parameters"])

    scale = parameters["properties"]["scale"]

    assert scale["type"] == "integer"
    assert "exclusiveMinimum" not in scale


def test_gemini_tool_declarations():
    declarations = get_gemini_tool_declarations()

    names = {declaration.name for declaration in declarations}

    assert names == {
        "ndvi_analysis",
        "landcover_analysis",
    }


@patch("app.agent.gemini.create_gemini_client")
@patch("app.agent.gemini.get_gemini_tool_declarations")
def test_ask_gemini_calls_generate_content(mock_get_declarations, mock_create_client):
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    mock_declarations = [types.FunctionDeclaration(name="dummy", description="dummy")]
    mock_get_declarations.return_value = mock_declarations

    mock_response = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    prompt = "What is the NDVI of this area?"

    result = ask_gemini(prompt)

    assert result == mock_response
    mock_create_client.assert_called_once()
    mock_get_declarations.assert_called_once()

    mock_client.models.generate_content.assert_called_once()

    call_args, call_kwargs = mock_client.models.generate_content.call_args
    assert call_kwargs["model"] == MODEL_NAME
    assert call_kwargs["contents"] == prompt
    assert isinstance(call_kwargs["config"], types.GenerateContentConfig)
    assert call_kwargs["config"].automatic_function_calling.disable is True
    assert len(call_kwargs["config"].tools) == 1
    assert call_kwargs["config"].tools[0].function_declarations == mock_declarations
