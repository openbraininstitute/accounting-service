from tests.constants import PROJ_ID, SYS_ID, VLAB_ID


async def test_post_account(api_client):
    response = await api_client.post(
        "/account/system",
        json={"id": SYS_ID, "name": ""},
    )

    assert response.json()["data"] == {"id": SYS_ID, "name": ""}
    assert response.status_code == 201

    response = await api_client.post(
        "/account/virtual-lab",
        json={"id": VLAB_ID, "name": "vlab-01"},
    )

    assert response.json()["data"] == {"id": VLAB_ID, "name": "vlab-01"}
    assert response.status_code == 201

    response = await api_client.post(
        "/account/project",
        json={"id": PROJ_ID, "name": "vlab-01/proj-01", "vlab_id": VLAB_ID},
    )

    assert response.json()["data"] == {"id": PROJ_ID, "name": "vlab-01/proj-01"}
    assert response.status_code == 201
