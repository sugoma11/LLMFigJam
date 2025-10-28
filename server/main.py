import uuid
import traceback
from enum import Enum
from collections import deque
from datetime import datetime
from langchain_openai import ChatOpenAI
from typing import Any, List, Optional, Dict, Type
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, create_model, Field
from fastapi import FastAPI, HTTPException, BackgroundTasks

from core.loaders import get_pdf_plumber_message
from runners.company_research.runner import CompanyResearchRunner

app = FastAPI()

# Enable CORS for Figma plugin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory queue for /poll, /push, /peek
message_queue = deque(maxlen=1000)

# In-memory storage for jobs
jobs: Dict[str, Dict[str, Any]] = {}


runners_facade = {
    'company_research': CompanyResearchRunner,
}

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Message(BaseModel):
    type: str
    topicTitle: str

    content: Optional[Any] = None
    color: Optional[Any] = None
    width: Optional[int] = None
    height: Optional[int] = None
    center: Optional[List[float]] = None
    font: Optional[str] = None
    size: Optional[int] = None
    spacing: Optional[int] = None


class JobRequest(BaseModel):
    """Request model for submitting a new job"""
    schema: Dict[str, Any]  # The schema definition from FigJam plugin
    pdf_path: Optional[str] = None
    prompt: Optional[str] = None
    runner: Optional[str] = None
    pipeline_vars: Optional[Dict[str, str]] = None
    llm_config: Dict[str, str]


class JobResponse(BaseModel):
    """Response model for job submission"""
    job_id: str
    status: JobStatus
    message: str


class JobResultResponse(BaseModel):
    """Response model for job results"""
    job_id: str
    status: JobStatus
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# ============================================================================
# EXISTING ENDPOINTS (unchanged)
# ============================================================================

@app.post("/push")
async def push_message(message: Message):
    """Your app pushes messages here"""
    message_queue.append(message.model_dump())
    return {"status": "ok", "queue_size": len(message_queue)}


@app.get("/poll")
async def poll_messages(limit: int = 50) -> List[dict]:
    """Figma plugin polls messages here"""
    messages = []
    for _ in range(min(limit, len(message_queue))):
        if message_queue:
            messages.append(message_queue.popleft())
    return messages


@app.get("/peek")
async def peek_queue(limit: int = 10) -> List[dict]:
    """Check queue without removing messages"""
    return list(message_queue)[:limit]


@app.get("/status")
async def get_status():
    """Check queue status"""
    return {
        "queue_size": len(message_queue),
        "max_size": message_queue.maxlen,
        "active_jobs": len(jobs),
        "pending_jobs": len([j for j in jobs.values() if j["status"] == JobStatus.PENDING]),
        "processing_jobs": len([j for j in jobs.values() if j["status"] == JobStatus.PROCESSING]),
    }


@app.delete("/clear")
async def clear_queue():
    """Clear all messages"""
    message_queue.clear()
    return {"status": "cleared"}


# ============================================================================
# NEW JOB MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/send_job", response_model=JobResponse)
async def send_job(job_request: JobRequest, background_tasks: BackgroundTasks):
    """
    Submit a new job for processing.
    Returns job_id immediately and processes in background.
    """
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "request": job_request.model_dump(),
        "results": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    # Schedule background processing
    background_tasks.add_task(process_job, job_id)

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Job submitted successfully"
    )


@app.get("/get_results/{job_id}", response_model=JobResultResponse)
async def get_results(job_id: str):
    """
    Poll for job results by job_id.
    Returns pending status if not complete, or results when done.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    return JobResultResponse(
        job_id=job["job_id"],
        status=job["status"],
        results=job["results"],
        error=job["error"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
    )


@app.get("/list_jobs")
async def list_jobs(status: Optional[JobStatus] = None, limit: int = 50):
    """List all jobs, optionally filtered by status"""
    job_list = list(jobs.values())

    if status:
        job_list = [j for j in job_list if j["status"] == status]

    # Sort by creation time, newest first
    job_list.sort(key=lambda x: x["created_at"], reverse=True)

    return job_list[:limit]


@app.delete("/delete_job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from the system"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    del jobs[job_id]
    return {"status": "deleted", "job_id": job_id}


@app.delete("/clear_jobs")
async def clear_jobs(status: Optional[JobStatus] = None):
    """Clear jobs, optionally filtered by status"""
    if status:
        jobs_to_delete = [job_id for job_id, job in jobs.items() if job["status"] == status]
        for job_id in jobs_to_delete:
            del jobs[job_id]
        return {"status": "cleared", "deleted_count": len(jobs_to_delete)}
    else:
        count = len(jobs)
        jobs.clear()
        return {"status": "cleared", "deleted_count": count}


# ============================================================================
# JOB PROCESSING LOGIC
# ============================================================================

def restore_pydantic_schema(
    schema_dict: Dict[str, Any],
    model_name: str = "ResponseSchema",
    additional_fields: Optional[Dict[str, Any]] = None
) -> Type[BaseModel]:
    """
    Compose a Pydantic model from a dictionary schema.

    Args:
        schema_dict: Dictionary containing the schema definition
        model_name: Name for the created model
        additional_fields: Optional additional fields to add to the model

    Returns:
        A dynamically created Pydantic model class

    Example schema_dict:
        {
            'Values': {
                'type': 'Sticker',
                'description': 'Find values of xAI'
            },
            'General': {
                'type': 'Table',
                'reference_field': 'Company',
                'reference_items': ['xAI', 'Anthropic', 'OpenAI'],
                'columns': {
                    'USP': 'Find USP',
                    'Values': 'Find Values',
                    'Revenue': 'Find Revenue'
                }
            }
        }
    """

    type_mapping = {
        'Sticker': str,
        'Stickers Column': List[str],
    }

    fields = {}

    for field_name, field_info in schema_dict.items():
        field_type = field_info.get('type')

        if field_type == 'Table':
            inner_model_name = f"{field_info['reference_field']}"
            inner_fields = {
                col_name: (str, ...)
                for col_name in field_info['columns'].keys()
            }
            inner_model = create_model(inner_model_name, **inner_fields)

            column_descriptions = [desc.format(**{field_info['reference_field']: field_info['reference_items']}) for desc in field_info['columns'].values()]
            combined_description = '\n'.join(column_descriptions)

            fields[field_name] = (
                Optional[Dict[str, inner_model]],
                Field(None, description=combined_description)
            )

        else:
            python_type = type_mapping.get(field_type, str)
            description = field_info.get('description', '')
            fields[field_name] = (
                Optional[python_type],
                Field(None, description=description)
            )

    if additional_fields:
        fields.update(additional_fields)

    return create_model(model_name, **fields)



def process_job(job_id: str):
    """
    Background task to process a job.
    This is where the model inference happens.
    """
    try:
        jobs[job_id]["status"] = JobStatus.PROCESSING
        request_data = jobs[job_id]["request"]

        llm_config = request_data.get("llm_config", {})
        model = ChatOpenAI(
            model=llm_config["model_name"],
            openai_api_key=llm_config["api_key"],
            openai_api_base=llm_config["model_provider_url"],
            temperature=llm_config["temperature"],
        )

        response_schema = request_data["schema"]
        response_schema = restore_pydantic_schema(response_schema)

        prompts = request_data["prompt"]
        pdf_path = request_data["pdf_path"]
        pipeline_vars = request_data["pipeline_vars"] if request_data["pipeline_vars"] else {}

        runner = runners_facade[request_data['runner']]

        runner = runner(
            model,
            response_schema,
            prompts,
            get_pdf_plumber_message,
            pipeline_vars,
            pdf_path
        )

        messages = runner.run()

        jobs[job_id]["results"] = messages
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

        print('\n\n\n COMPLETED')

    except Exception as e:

        error_traceback = traceback.format_exc()
        print(f"Full traceback for job {job_id}:")
        print(error_traceback)

        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["error"] = error_traceback  # Store full traceback instead of just str(e)
        jobs[job_id]["completed_at"] = datetime.now().isoformat()


def start_server(host="0.0.0.0", port=8000, messages=[]):
    """Start FastAPI server in background thread"""
    import uvicorn
    import threading
    global message_queue
    message_queue = deque(messages, maxlen=1000)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


if __name__ == "__main__":
    import json
    import uvicorn

    try:
        message_queue = deque(
            json.load(open('to-figma-messages-2025-10-13-08-14-22.json', 'r')),
            maxlen=1000
        )
    except FileNotFoundError:
        message_queue = deque(maxlen=1000)

    uvicorn.run(app, host="0.0.0.0", port=8080)