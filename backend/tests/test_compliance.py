import pytest


@pytest.mark.asyncio
async def test_list_ncrs(client):
    """Test NCR listing endpoint."""
    response = await client.get("/api/compliance/ncrs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_specifications(client):
    """Test specification listing endpoint."""
    response = await client.get("/api/compliance/specifications")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
