"""
API client for communicating with download server
"""
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DownloadServerClient:
    """Client for communicating with download server API"""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        client_name: Optional[str] = None,
        client_host: Optional[str] = None
    ):
        """
        Initialize API client
        
        Args:
            base_url: Base URL of the download server (e.g., "https://gate-server.com")
            api_key: Optional API key for authentication
            client_name: Optional client name for registration
            client_host: Optional client hostname
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client_name = client_name or "downloader_client"
        self.client_host = client_host
        self.client_id: Optional[str] = None
        self.api_version = "v1"
        
        # Register client if API key is provided
        if api_key:
            self._register_client()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key if available"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def _register_client(self) -> bool:
        """Register client with server"""
        try:
            response = requests.post(
                f"{self.base_url}/api/{self.api_version}/clients/register",
                json={
                    "client_name": self.client_name,
                    "client_host": self.client_host,
                    "api_key": self.api_key
                },
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            self.client_id = data.get("client_id")
            logger.info(f"Registered client: {self.client_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to register client: {e}")
            return False
    
    def request_task(self) -> Optional[Dict[str, Any]]:
        """
        Request a pending task from the server
        
        Returns:
            Task configuration dict with:
            - task_id: Task ID
            - search_params: Search parameters
            - start_page: Starting page number
            - max_documents: Maximum documents to download
            - status: Task status
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/{self.api_version}/tasks/request",
                json={},
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 404:
                # No pending tasks
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error requesting task: {e}")
            return None
    
    def complete_task(
        self,
        task_id: str,
        documents_downloaded: int = 0,
        documents_failed: int = 0,
        documents_skipped: int = 0,
        result_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Mark task as completed and send results to server
        
        Args:
            task_id: Task ID
            documents_downloaded: Number of successfully downloaded documents
            documents_failed: Number of failed downloads
            documents_skipped: Number of skipped documents
            result_summary: Optional summary dict
            error_message: Optional error message
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/{self.api_version}/tasks/complete",
                json={
                    "task_id": task_id,
                    "documents_downloaded": documents_downloaded,
                    "documents_failed": documents_failed,
                    "documents_skipped": documents_skipped,
                    "result_summary": result_summary,
                    "error_message": error_message
                },
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Task {task_id} completed successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error completing task {task_id}: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to server"""
        try:
            response = requests.post(
                f"{self.base_url}/api/{self.api_version}/clients/heartbeat",
                json={},
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error sending heartbeat: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        try:
            response = requests.get(
                f"{self.base_url}/api/{self.api_version}/tasks/{task_id}",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting task status: {e}")
            return None
    
    def health_check(self) -> bool:
        """Check if server is healthy"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def register_document(
        self,
        metadata: Dict[str, Any],
        task_id: Optional[str] = None,
        search_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Register a document with metadata on the server
        
        Args:
            metadata: Document metadata dictionary
            task_id: Optional task ID that downloaded this document
            search_params: Optional search parameters used
        
        Returns:
            Response dict with system_id and classification, or None on error
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/{self.api_version}/documents/register",
                json={
                    "task_id": task_id,
                    "search_params": search_params,
                    "metadata": metadata
                },
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Document registered: system_id={result.get('system_id')}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error registering document: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error detail: {error_detail}")
                except:
                    logger.error(f"Response: {e.response.text}")
            return None
    
    def get_document_by_system_id(self, system_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by system_id
        
        Args:
            system_id: System UUID of the document
        
        Returns:
            Document dict or None if not found
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/{self.api_version}/documents/{system_id}",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting document {system_id}: {e}")
            return None
    
    def get_client_statistics(self, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a client
        
        Args:
            client_id: Client ID (if None, gets statistics for current client)
        
        Returns:
            Statistics dict or None on error
        """
        try:
            if client_id:
                url = f"{self.base_url}/api/{self.api_version}/clients/{client_id}/statistics"
            else:
                url = f"{self.base_url}/api/{self.api_version}/clients/me/statistics"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting client statistics: {e}")
            return None
    
    def notify_document_download_start(
        self,
        task_id: str,
        document_id: str,
        reg_number: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Notify server that a document download has started
        
        Args:
            task_id: Task ID
            document_id: Document ID being downloaded
            reg_number: Optional registration number
        
        Returns:
            Response dict with statistics, or None on error
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/{self.api_version}/tasks/document-download-start",
                json={
                    "task_id": task_id,
                    "document_id": document_id,
                    "reg_number": reg_number
                },
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Notified server about document {document_id} download start")
            return result
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error notifying document download start: {e}")
            return None
