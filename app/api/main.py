from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import graph_runner, mock_loader
from app.api.schemas import (
    MockEmailSummary,
    StartRunRequest,
    SubmitApprovalRequest,
)

app = FastAPI(title="Hotel AI Manager Approval API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/mock-emails", response_model=list[MockEmailSummary])
def list_mock_emails() -> list[MockEmailSummary]:
    return [MockEmailSummary(**row) for row in mock_loader.load_mock_emails()]


@app.post("/runs")
def start_run(body: StartRunRequest) -> dict:
    sample = mock_loader.get_mock_email_by_id(body.email_id)
    if sample is None:
        raise HTTPException(status_code=404, detail=f"Unknown email_id: {body.email_id}")

    initial_state = mock_loader.build_initial_state_from_mock(sample)
    try:
        return graph_runner.start_run(body.email_id, initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/runs/{thread_id}")
def get_run(thread_id: str) -> dict:
    run = graph_runner.get_run(thread_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown thread_id: {thread_id}")
    return run


@app.post("/runs/{thread_id}/submit")
def submit_run(thread_id: str, body: SubmitApprovalRequest) -> dict:
    try:
        return graph_runner.submit_run(
            thread_id=thread_id,
            email_data=body.email_data.model_dump() if body.email_data else None,
            classification=body.classification.model_dump()
            if body.classification
            else None,
            extract_data=body.extract_data.model_dump() if body.extract_data else None,
            draft_response=body.draft_response,
            action_sqlite=body.action_sqlite.model_dump(),
            manager_comment=body.manager_comment,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
