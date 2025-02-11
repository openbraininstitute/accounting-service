"""Constants used for tests."""

import dataclasses
from uuid import UUID


@dataclasses.dataclass(frozen=True)
class _UUIDS:
    SYS: UUID
    VLAB: list[UUID]
    PROJ: list[UUID]
    USER: list[UUID]
    RSV: list[UUID]
    JOB: list[UUID]
    GROUP: list[UUID]


UUIDS = _UUIDS(
    SYS=UUID("00000000-0000-0000-0000-000000000001"),
    VLAB=[
        UUID("1b3bd3f4-3441-41b0-8fae-83a30c133dc2"),
    ],
    PROJ=[
        UUID("2cb0ea5a-0e6f-4080-a43c-25a4f0dd0ea2"),
        UUID("cccb843e-0b5e-4aed-88b0-6f218a27b6ae"),
    ],
    USER=[
        UUID("76693c58-8f5d-45b8-bb41-dbc3599402f5"),
        UUID("b2807649-3621-4865-b156-456c5a4ec376"),
    ],
    RSV=[
        UUID("58835fd6-b62d-40bb-97b1-7e071fc35c94"),
        UUID("cd2ea830-1288-482f-b69b-73da9e5da227"),
    ],
    JOB=[
        UUID("923cc386-ae77-44f1-88cd-0cc85cea60b9"),
        UUID("3dade995-fe19-4386-a71a-e24dacf0f0e1"),
        UUID("d2304a0d-f19e-404b-b327-211de0d515b7"),
    ],
    GROUP=[
        UUID("9f9ec707-5ad6-4b19-804b-f85220756b2c"),
        UUID("fa2499af-f678-429f-ab2e-6653a0fc4b2e"),
    ],
)

SYS_ID = str(UUIDS.SYS)
VLAB_ID = str(UUIDS.VLAB[0])
PROJ_ID = str(UUIDS.PROJ[0])
USER_ID = str(UUIDS.USER[0])
USER_ID_2 = str(UUIDS.USER[1])
RSV_ID = str(UUIDS.RSV[0])
PROJ_ID_2 = str(UUIDS.PROJ[1])
RSV_ID_2 = str(UUIDS.RSV[1])
GROUP_ID = str(UUIDS.GROUP[0])
GROUP_ID_2 = str(UUIDS.GROUP[1])

KB = 1024
MB = 1024**2
GB = 1024**3
