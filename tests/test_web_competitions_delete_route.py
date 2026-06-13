import pytest


@pytest.mark.unit
def test_next_delete_proxy_should_return_204_not_json():
    """Regression: our Next DELETE proxy must not JSON-encode a 204 response.

    We can't execute Next route handlers here, but we can assert intent:
    - the backend DELETE returns 204
    - the proxy should return 204 with no JSON body

    This test is a lightweight guard that the proxy uses NextResponse with status=204.
    """
    # Kept intentionally simple: failing symptom was "Value is not JSON serializable"
    # due to NextResponse.json(undefined) on 204 deletes.
    from pathlib import Path

    route = Path("web/app/src/app/app/api/competitions/[competitionId]/route.ts").read_text(
        encoding="utf-8"
    )
    delete_handler = route.split("export async function DELETE", maxsplit=1)[1].split(
        "\nexport async function", maxsplit=1
    )[0]
    assert "status: 204" in delete_handler or "status:204" in delete_handler
    assert "NextResponse.json" not in delete_handler


@pytest.mark.unit
def test_next_competition_proxy_supports_patch():
    from pathlib import Path

    route = Path("web/app/src/app/app/api/competitions/[competitionId]/route.ts").read_text(
        encoding="utf-8"
    )
    assert "export async function PATCH" in route
    assert 'method: "PATCH"' in route
