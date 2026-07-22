import pytest


@pytest.mark.asyncio
async def test_list_tasks(client):
    """Test schedule tasks endpoint."""
    response = await client.get("/api/schedule/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_gantt_data(client):
    """Test Gantt chart data endpoint."""
    response = await client.get("/api/schedule/gantt")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data


@pytest.mark.asyncio
async def test_list_shipments(client):
    """Test shipments endpoint."""
    response = await client.get("/api/supply-chain/shipments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_vendors(client):
    """Test vendors endpoint."""
    response = await client.get("/api/supply-chain/vendors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
