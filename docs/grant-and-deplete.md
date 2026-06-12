# Grant and Deplete

## Use case: Education plan

Institutions buy seats. Each seat entitles the holder to 200 credits, granted directly to their project. If a student drops out, their project is depleted. At end of semester, the entire vlab is depleted.

## Endpoints

`POST /budget/grant` — Credits a project directly (`SYS → VLAB → PROJ` atomically). Body: `{proj_id, amount}`.

`POST /budget/deplete/project` — Wipes a single project balance to SYS. Body: `{proj_id}`.

`POST /budget/deplete/vlab` — Wipes all projects + vlab balance to SYS. Body: `{vlab_id}`.

## Transaction type

New `DEPLETE` type added (requires migration `20260612_103000_add_deplete_transaction_type.py`). Grant reuses existing `TOP_UP` + `ASSIGN_BUDGET`.

