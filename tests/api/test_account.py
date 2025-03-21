from tests.constants import PROJ_ID, SYS_ID, VLAB_ID, VLAB_ID_2, VLAB_ID_3


async def test_post_account(api_client):
    # System account
    response = await api_client.post(
        "/account/system",
        json={"id": SYS_ID, "name": ""},
    )

    assert response.json()["data"] == {"id": SYS_ID, "name": ""}
    assert response.status_code == 201

    # Virtual lab account
    response = await api_client.post(
        "/account/virtual-lab",
        json={"id": VLAB_ID, "name": "vlab-01"},
    )

    assert response.json()["data"] == {"id": VLAB_ID, "name": "vlab-01", "balance": "0"}
    assert response.status_code == 201

    # Virtual lab account with initial balance as string
    response = await api_client.post(
        "/account/virtual-lab",
        json={"id": VLAB_ID_2, "name": "vlab-02", "balance": "1000.0"},
    )

    assert response.json()["data"] == {"id": VLAB_ID_2, "name": "vlab-02", "balance": "1000.0"}
    assert response.status_code == 201

    # Virtual lab account with initial balance as float
    response = await api_client.post(
        "/account/virtual-lab",
        json={"id": VLAB_ID_3, "name": "vlab-03", "balance": 2000.0},
    )

    assert response.json()["data"] == {"id": VLAB_ID_3, "name": "vlab-03", "balance": "2000.0"}
    assert response.status_code == 201

    # Project account
    response = await api_client.post(
        "/account/project",
        json={"id": PROJ_ID, "name": "vlab-01/proj-01", "vlab_id": VLAB_ID},
    )

    assert response.json()["data"] == {"id": PROJ_ID, "name": "vlab-01/proj-01"}
    assert response.status_code == 201
