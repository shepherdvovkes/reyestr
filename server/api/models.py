"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class TaskRequest(BaseModel):
    """Request to get a task"""
    pass


class TaskResponse(BaseModel):
    """Response with task configuration"""
    task_id: str
    search_params: Dict[str, Any]
    start_page: int
    max_documents: int
    status: str


class TaskCompleteRequest(BaseModel):
    """Request to complete a task"""
    task_id: str
    documents_downloaded: int = 0
    documents_failed: int = 0
    documents_skipped: int = 0
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TaskCompleteResponse(BaseModel):
    """Response after completing a task"""
    success: bool
    message: str


class TaskCreateRequest(BaseModel):
    """Request to create a new task"""
    search_params: Dict[str, Any] = Field(..., description="Search parameters")
    start_page: int = Field(..., ge=1, description="Starting page number")
    max_documents: int = Field(..., ge=1, le=1000, description="Maximum documents to download")


class TaskCreateResponse(BaseModel):
    """Response after creating a task"""
    task_id: str
    message: str


class TaskStatusResponse(BaseModel):
    """Task status information"""
    task_id: str
    status: str
    search_params: Dict[str, Any]
    start_page: int
    max_documents: int
    client_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    documents_downloaded: int = 0
    documents_failed: int = 0
    documents_skipped: int = 0
    error_message: Optional[str] = None


class ClientRegisterRequest(BaseModel):
    """Request to register a client"""
    client_name: str
    client_host: Optional[str] = None
    api_key: Optional[str] = None


class ClientRegisterResponse(BaseModel):
    """Response after registering a client"""
    client_id: str
    message: str


class ClientHeartbeatRequest(BaseModel):
    """Client heartbeat request"""
    pass


class ClientHeartbeatResponse(BaseModel):
    """Client heartbeat response"""
    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None


class TasksSummaryResponse(BaseModel):
    """Summary of all tasks"""
    total_tasks: int
    pending: int
    assigned: int
    in_progress: int
    completed: int
    failed: int
    tasks: list[TaskStatusResponse]


class ClientsSummaryResponse(BaseModel):
    """Summary of all clients"""
    total_clients: int
    active_clients: int
    clients: list[Dict[str, Any]]


class DocumentMetadata(BaseModel):
    """Document metadata for registration"""
    external_id: Optional[str] = Field(None, description="External document ID (from registry)")
    reg_number: Optional[str] = Field(None, description="Registration number")
    url: Optional[str] = Field(None, description="Document URL")
    court_name: Optional[str] = Field(None, description="Court name")
    judge_name: Optional[str] = Field(None, description="Judge name")
    decision_type: Optional[str] = Field(None, description="Decision type")
    decision_date: Optional[str] = Field(None, description="Decision date (DD.MM.YYYY)")
    law_date: Optional[str] = Field(None, description="Law date (DD.MM.YYYY)")
    case_type: Optional[str] = Field(None, description="Case type")
    case_number: Optional[str] = Field(None, description="Case number")


class DocumentRegisterRequest(BaseModel):
    """Request to register a document"""
    task_id: Optional[str] = Field(None, description="Task ID that downloaded this document")
    search_params: Optional[Dict[str, Any]] = Field(None, description="Search parameters used")
    metadata: DocumentMetadata = Field(..., description="Document metadata")


class DocumentRegisterResponse(BaseModel):
    """Response after registering a document"""
    system_id: str
    external_id: Optional[str] = None
    reg_number: Optional[str] = None
    classified: bool = Field(..., description="Whether document was classified")
    classification: Optional[Dict[str, Any]] = Field(None, description="Classification data")
    message: str


class DocumentDownloadStartRequest(BaseModel):
    """Request to notify server about document download start"""
    task_id: str = Field(..., description="Task ID")
    document_id: str = Field(..., description="Document ID being downloaded")
    reg_number: Optional[str] = Field(None, description="Registration number")


class DocumentDownloadStartResponse(BaseModel):
    """Response after recording document download start"""
    success: bool
    message: str
    statistics: Optional[Dict[str, Any]] = Field(None, description="Current task download statistics")
