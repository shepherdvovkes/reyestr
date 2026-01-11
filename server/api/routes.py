"""
API routes for download server
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
import logging
from server.api.models import (
    TaskRequest, TaskResponse, TaskCompleteRequest, TaskCompleteResponse,
    TaskCreateRequest, TaskCreateResponse, TaskStatusResponse,
    ClientRegisterRequest, ClientRegisterResponse,
    ClientHeartbeatRequest, ClientHeartbeatResponse,
    TasksSummaryResponse, ClientsSummaryResponse, ErrorResponse,
    DocumentRegisterRequest, DocumentRegisterResponse,
    DocumentDownloadStartRequest, DocumentDownloadStartResponse
)
from server.database.task_manager import TaskManager, ClientManager, ClientActivityTracker
from server.database.document_manager import DocumentManager
from server.database.cache import (
    cache_get, cache_set, cache_delete, cache_delete_pattern,
    cache_key_task, cache_key_client_statistics, cache_key_document,
    cache_key_tasks_summary
)
from server.api.auth import verify_api_key
from server.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"/api/{config.api_version}", tags=["download"])


@router.post("/tasks/request", response_model=TaskResponse)
async def request_task(
    request: TaskRequest,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Request a pending task to download documents.
    Client will receive task configuration ready for downloader.py
    """
    if not client_id:
        # Allow unauthenticated access if auth is disabled
        client_id = "anonymous"
    
    # Update client heartbeat
    if client_id != "anonymous":
        ClientManager.update_heartbeat(client_id)
    
    # Get pending task
    task = TaskManager.get_pending_task(client_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending tasks available"
        )
    
    # Mark task as started
    TaskManager.start_task(task['id'])
    
    # Invalidate task cache
    cache_delete(cache_key_task(task['id']))
    cache_delete_pattern("cache:tasks_summary:*")
    
    return TaskResponse(
        task_id=task['id'],
        search_params=task['search_params'],
        start_page=task['start_page'],
        max_documents=task['max_documents'],
        status=task['status']
    )


@router.post("/tasks/complete", response_model=TaskCompleteResponse)
async def complete_task(
    request: TaskCompleteRequest,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Mark a task as completed and report results
    """
    if not client_id:
        client_id = "anonymous"
    
    # Update client heartbeat
    if client_id != "anonymous":
        ClientManager.update_heartbeat(client_id)
    
    # Verify task belongs to client (optional check)
    task = TaskManager.get_task(request.task_id)
    if task and task.get('client_id') and task['client_id'] != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task does not belong to this client"
        )
    
    # Complete task
    success = TaskManager.complete_task(
        task_id=request.task_id,
        documents_downloaded=request.documents_downloaded,
        documents_failed=request.documents_failed,
        documents_skipped=request.documents_skipped,
        result_summary=request.result_summary,
        error_message=request.error_message
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete task"
        )
    
    # Invalidate caches
    cache_delete(cache_key_task(request.task_id))
    cache_delete_pattern("cache:tasks_summary:*")
    if client_id and client_id != "anonymous":
        cache_delete(cache_key_client_statistics(client_id))
    
    return TaskCompleteResponse(
        success=True,
        message=f"Task {request.task_id} completed successfully"
    )


@router.post("/tasks/create", response_model=TaskCreateResponse)
async def create_task(
    request: TaskCreateRequest,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Create a new download task
    """
    task_id = TaskManager.create_task(
        search_params=request.search_params,
        start_page=request.start_page,
        max_documents=request.max_documents
    )
    
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )
    
    return TaskCreateResponse(
        task_id=task_id,
        message=f"Task {task_id} created successfully"
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get status of a specific task
    """
    # Try cache first
    cache_key = cache_key_task(task_id)
    cached_task = cache_get(cache_key)
    if cached_task:
        return TaskStatusResponse(**cached_task)
    
    task = TaskManager.get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    task_response = TaskStatusResponse(
        task_id=str(task['id']),
        status=task['status'],
        search_params=task['search_params'],
        start_page=task['start_page'],
        max_documents=task['max_documents'],
        client_id=str(task['client_id']) if task.get('client_id') else None,
        assigned_at=task.get('assigned_at'),
        started_at=task.get('started_at'),
        completed_at=task.get('completed_at'),
        documents_downloaded=task.get('documents_downloaded', 0),
        documents_failed=task.get('documents_failed', 0),
        documents_skipped=task.get('documents_skipped', 0),
        error_message=task.get('error_message')
    )
    
    # Cache task (shorter TTL for in_progress tasks)
    ttl = 5 if task['status'] in ['in_progress', 'assigned'] else config.cache_ttl_tasks
    cache_set(cache_key, task_response.dict(), ttl=ttl)
    
    return task_response


@router.get("/tasks/{task_id}/download-statistics", response_model=dict)
async def get_task_download_statistics(
    task_id: str,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get download statistics for a task including speed and ETA
    """
    # Verify task exists
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    statistics = TaskManager.get_task_download_statistics(task_id)
    
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task download statistics"
        )
    
    return statistics


@router.get("/tasks", response_model=TasksSummaryResponse)
async def get_tasks_summary(
    status_filter: Optional[str] = None,
    limit: int = 100,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get summary of all tasks
    """
    # Try cache first
    cache_key = cache_key_tasks_summary(status_filter)
    cached_summary = cache_get(cache_key)
    if cached_summary:
        return TasksSummaryResponse(**cached_summary)
    
    if status_filter:
        tasks = TaskManager.get_tasks_by_status(status_filter, limit)
    else:
        # Get tasks from all statuses
        all_tasks = []
        for status_val in ['pending', 'assigned', 'in_progress', 'completed', 'failed']:
            all_tasks.extend(TaskManager.get_tasks_by_status(status_val, limit // 5))
        tasks = all_tasks[:limit]
    
    # Count by status
    status_counts = {}
    for status_val in ['pending', 'assigned', 'in_progress', 'completed', 'failed']:
        status_counts[status_val] = len([
            t for t in tasks if t['status'] == status_val
        ])
    
    task_responses = [
        TaskStatusResponse(
            task_id=str(t['id']),
            status=t['status'],
            search_params=t['search_params'],
            start_page=t['start_page'],
            max_documents=t['max_documents'],
            client_id=str(t['client_id']) if t.get('client_id') else None,
            assigned_at=t.get('assigned_at'),
            started_at=t.get('started_at'),
            completed_at=t.get('completed_at'),
            documents_downloaded=t.get('documents_downloaded', 0),
            documents_failed=t.get('documents_failed', 0),
            documents_skipped=t.get('documents_skipped', 0),
            error_message=t.get('error_message')
        )
        for t in tasks
    ]
    
    summary = TasksSummaryResponse(
        total_tasks=len(tasks),
        pending=status_counts.get('pending', 0),
        assigned=status_counts.get('assigned', 0),
        in_progress=status_counts.get('in_progress', 0),
        completed=status_counts.get('completed', 0),
        failed=status_counts.get('failed', 0),
        tasks=task_responses
    )
    
    # Cache summary
    cache_set(cache_key, summary.dict(), ttl=config.cache_ttl_tasks)
    
    return summary


@router.post("/clients/register", response_model=ClientRegisterResponse)
async def register_client(request: ClientRegisterRequest):
    """
    Register a new download client
    """
    client_id = ClientManager.register_client(
        client_name=request.client_name,
        client_host=request.client_host,
        api_key=request.api_key
    )
    
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register client"
        )
    
    return ClientRegisterResponse(
        client_id=client_id,
        message=f"Client {request.client_name} registered successfully"
    )


@router.post("/clients/heartbeat", response_model=ClientHeartbeatResponse)
async def client_heartbeat(
    request: ClientHeartbeatRequest,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Send heartbeat to indicate client is alive
    """
    if not client_id or client_id == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for heartbeat"
        )
    
    success = ClientManager.update_heartbeat(client_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return ClientHeartbeatResponse(
        success=True,
        message="Heartbeat received"
    )


@router.get("/clients", response_model=ClientsSummaryResponse)
async def get_clients_summary(
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get summary of all registered clients
    """
    clients = ClientManager.get_all_clients()
    
    active_count = len([c for c in clients if c['status'] == 'active'])
    
    return ClientsSummaryResponse(
        total_clients=len(clients),
        active_clients=active_count,
        clients=[dict(c) for c in clients]
    )


@router.post("/tasks/reset-stale", response_model=dict)
async def reset_stale_tasks(
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Reset tasks that have timed out (admin function)
    """
    reset_count = TaskManager.reset_stale_tasks()
    
    return {
        "success": True,
        "reset_count": reset_count,
        "message": f"Reset {reset_count} stale tasks"
    }


@router.post("/documents/register", response_model=DocumentRegisterResponse)
async def register_document(
    request: DocumentRegisterRequest,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Register a document with metadata and classification
    
    Server assigns system_id (UUID) and classifies document based on:
    - Search parameters (court_region, instance_type)
    - Extracted metadata (court_name, etc.)
    """
    if not client_id:
        client_id = "anonymous"
    
    # Update client heartbeat
    if client_id != "anonymous":
        ClientManager.update_heartbeat(client_id)
    
    # Convert metadata to dict
    metadata_dict = request.metadata.dict(exclude_none=True)
    
    # Register document
    system_id, classification = DocumentManager.register_document(
        metadata=metadata_dict,
        task_id=request.task_id,
        search_params=request.search_params,
        client_id=client_id if client_id != "anonymous" else None
    )
    
    if not system_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register document"
        )
    
    # Build classification response
    classification_response = None
    if classification.get('court_region') or classification.get('instance_type'):
        classification_response = {
            'court_region': classification.get('court_region'),
            'instance_type': classification.get('instance_type'),
            'source': classification.get('classification_source')
        }
    
    return DocumentRegisterResponse(
        system_id=system_id,
        external_id=metadata_dict.get('external_id') or metadata_dict.get('reg_number'),
        reg_number=metadata_dict.get('reg_number'),
        classified=bool(classification_response),
        classification=classification_response,
        message=f"Document registered with system_id: {system_id}"
    )


@router.get("/documents/{system_id}", response_model=dict)
async def get_document(
    system_id: str,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get document by system_id
    """
    # Try cache first
    cache_key = cache_key_document(system_id)
    cached_doc = cache_get(cache_key)
    if cached_doc:
        return cached_doc
    
    document = DocumentManager.get_document_by_system_id(system_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {system_id} not found"
        )
    
    # Cache document
    cache_set(cache_key, document, ttl=config.cache_ttl_documents)
    
    return document


@router.get("/clients/{client_id}/statistics", response_model=dict)
async def get_client_statistics(
    client_id: str,
    requesting_client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get detailed statistics for a specific client
    
    Clients can only view their own statistics unless they have admin privileges
    """
    # Check if requesting client can view this client's statistics
    if requesting_client_id and requesting_client_id != client_id:
        # In future, add admin check here
        # For now, only allow viewing own statistics
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own statistics"
        )
    
    # Try cache first
    cache_key = cache_key_client_statistics(client_id)
    cached_stats = cache_get(cache_key)
    if cached_stats:
        return cached_stats
    
    statistics = ClientManager.get_client_statistics(client_id)
    
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found"
        )
    
    # Cache statistics
    cache_set(cache_key, statistics, ttl=config.cache_ttl_statistics)
    
    return statistics


@router.get("/clients/me/statistics", response_model=dict)
async def get_my_statistics(
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get statistics for the current client (convenience endpoint)
    """
    if not client_id or client_id == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    statistics = ClientManager.get_client_statistics(client_id)
    
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return statistics


@router.post("/tasks/document-download-start", response_model=DocumentDownloadStartResponse)
async def document_download_start(
    request: DocumentDownloadStartRequest,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Notify server that a document download has started.
    Server will track this to calculate download speed and ETA.
    """
    if not client_id:
        client_id = "anonymous"
    
    # Update client heartbeat
    if client_id != "anonymous":
        ClientManager.update_heartbeat(client_id)
    
    # Verify task exists and belongs to client (optional check)
    task = TaskManager.get_task(request.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {request.task_id} not found"
        )
    
    # Record document download start
    success = TaskManager.record_document_download_start(
        task_id=request.task_id,
        document_id=request.document_id,
        reg_number=request.reg_number,
        client_id=client_id if client_id != "anonymous" else None
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record document download start"
        )
    
    # Get current statistics
    statistics = TaskManager.get_task_download_statistics(request.task_id)
    
    return DocumentDownloadStartResponse(
        success=True,
        message=f"Document {request.document_id} download start recorded",
        statistics=statistics
    )


@router.get("/clients/{client_id}/activity", response_model=dict)
async def get_client_activity(
    client_id: str,
    requesting_client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get real-time activity for a specific client
    """
    from server.database.task_manager import ClientActivityTracker
    
    activity = ClientActivityTracker.get_client_activity(client_id)
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found or no activity"
        )
    
    return activity


@router.get("/tasks/indexes", response_model=list)
async def get_task_indexes(
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get task indexes grouped by court region, instance type, and date range
    """
    indexes = TaskManager.get_task_indexes()
    return indexes


@router.get("/tasks/by-index", response_model=list)
async def get_tasks_by_index(
    court_region: str,
    instance_type: str,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    client_id: Optional[str] = Depends(verify_api_key)
):
    """
    Get tasks filtered by index (court region, instance type, date range)
    """
    tasks = TaskManager.get_tasks_by_index(
        court_region=court_region,
        instance_type=instance_type,
        date_start=date_start,
        date_end=date_end
    )
    
    task_responses = [
        TaskStatusResponse(
            task_id=str(t['id']),
            status=t['status'],
            search_params=t['search_params'],
            start_page=t['start_page'],
            max_documents=t['max_documents'],
            client_id=str(t['client_id']) if t.get('client_id') else None,
            assigned_at=t.get('assigned_at'),
            started_at=t.get('started_at'),
            completed_at=t.get('completed_at'),
            documents_downloaded=t.get('documents_downloaded', 0),
            documents_failed=t.get('documents_failed', 0),
            documents_skipped=t.get('documents_skipped', 0),
            error_message=t.get('error_message')
        )
        for t in tasks
    ]
    
    return task_responses
