"""Api schema."""

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """QueryRequest."""

    input_text: str


class QueryResponse(BaseModel):
    """QueryResponse."""

    input_text: str
    output_text: str
