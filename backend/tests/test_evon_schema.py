"""Tests for the Evon 30B schema validation, endpoint resolution, and demo fallback result."""

from app.gnani.evon import DEMO_RESULT, EvonReasoningClient
from app.schemas import EvonAnalysisResult


def test_demo_result_validates_against_schema():
    """The built-in demo result must validate as a full EvonAnalysisResult."""
    result = EvonAnalysisResult(**DEMO_RESULT)
    assert result.severity in {"GREEN", "YELLOW", "RED"}
    assert len(result.next_steps) == 3
    assert result.spoken_summary_regional


def test_evon_next_steps_must_be_exactly_three():
    base = dict(DEMO_RESULT)
    base["next_steps"] = ["one", "two"]
    try:
        EvonAnalysisResult(**base)
    except Exception:
        pass
    else:
        raise AssertionError("next_steps with 2 items should fail validation")


def test_client_instantiates_without_credentials():
    client = EvonReasoningClient()
    client.endpoint = ""
    client.model_id = ""
    client.api_token = ""
    assert client.endpoint == ""
    assert client.api_token == ""
    assert client.get_target_url() is None


def test_target_url_resolution():
    client = EvonReasoningClient()

    # Dedicated endpoint URL
    client.endpoint = "https://my-endpoint.endpoints.huggingface.cloud"
    assert client.get_target_url() == "https://my-endpoint.endpoints.huggingface.cloud"

    # Model ID as endpoint
    client.endpoint = "gnani-ai/evon-30b"
    assert client.get_target_url() == "https://router.huggingface.co/hf-inference/models/gnani-ai/evon-30b"

    # Model ID via model_id setting
    client.endpoint = ""
    client.model_id = "GnaniAI/Evon-30B"
    assert client.get_target_url() == "https://router.huggingface.co/hf-inference/models/GnaniAI/Evon-30B"
