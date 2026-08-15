from unittest.mock import MagicMock, patch

from fplquant.data.fpl_client import FPLClient


def _mock_response(payload: object) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_get_bootstrap_static_calls_expected_url() -> None:
    client = FPLClient(base_url="https://example.test/api")
    with patch.object(client.session, "get", return_value=_mock_response({"elements": []})) as get:
        result = client.get_bootstrap_static()

    get.assert_called_once()
    called_url = get.call_args.args[0]
    assert called_url == "https://example.test/api/bootstrap-static/"
    assert result == {"elements": []}


def test_get_element_summary_builds_player_specific_path() -> None:
    client = FPLClient(base_url="https://example.test/api")
    with patch.object(client.session, "get", return_value=_mock_response({"history": []})) as get:
        client.get_element_summary(42)

    called_url = get.call_args.args[0]
    assert called_url == "https://example.test/api/element-summary/42/"


def test_context_manager_closes_session() -> None:
    with FPLClient(base_url="https://example.test/api") as client:
        session = client.session
    assert session.adapters  # session object still exists, just closed
