"""
Helper module for registering documents on server after download
"""
import logging
from typing import Optional, Dict, Any
from client.api_client import DownloadServerClient

logger = logging.getLogger(__name__)

# Global API client (set by downloader_client.py when processing tasks from server)
_global_api_client: Optional[DownloadServerClient] = None
_global_task_id: Optional[str] = None
_global_search_params: Optional[Dict[str, Any]] = None
_global_client_id: Optional[str] = None


def set_server_context(
    api_client: Optional[DownloadServerClient] = None,
    task_id: Optional[str] = None,
    search_params: Optional[Dict[str, Any]] = None,
    client_id: Optional[str] = None
):
    """
    Set server context for document registration
    
    Args:
        api_client: API client instance
        task_id: Current task ID
        search_params: Search parameters used
        client_id: Client ID (will be extracted from api_client if not provided)
    """
    global _global_api_client, _global_task_id, _global_search_params, _global_client_id
    _global_api_client = api_client
    _global_task_id = task_id
    _global_search_params = search_params
    # Extract client_id from api_client if available
    if not client_id and api_client and hasattr(api_client, 'client_id'):
        _global_client_id = api_client.client_id
    else:
        _global_client_id = client_id


def register_document_on_server(
    metadata: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Register document on server if server context is available
    
    Args:
        metadata: Document metadata dictionary with fields:
            - external_id or reg_number: Document ID
            - reg_number: Registration number
            - url: Document URL
            - court_name: Court name
            - judge_name: Judge name
            - decision_type: Decision type
            - decision_date: Decision date (DD.MM.YYYY)
            - law_date: Law date (DD.MM.YYYY)
            - case_type: Case type
            - case_number: Case number
    
    Returns:
        Response dict with system_id and classification, or None if not registered
    """
    global _global_api_client, _global_task_id, _global_search_params, _global_client_id
    
    if not _global_api_client:
        # Not in server mode, skip registration
        return None
    
    try:
        # Prepare metadata for API
        api_metadata = {
            'external_id': metadata.get('external_id') or metadata.get('reg_number') or metadata.get('document_id'),
            'reg_number': metadata.get('reg_number'),
            'url': metadata.get('url'),
            'court_name': metadata.get('court_name'),
            'judge_name': metadata.get('judge_name'),
            'decision_type': metadata.get('decision_type'),
            'decision_date': metadata.get('decision_date'),
            'law_date': metadata.get('law_date'),
            'case_type': metadata.get('case_type'),
            'case_number': metadata.get('case_number')
        }
        
        # Remove None values
        api_metadata = {k: v for k, v in api_metadata.items() if v is not None}
        
        result = _global_api_client.register_document(
            metadata=api_metadata,
            task_id=_global_task_id,
            search_params=_global_search_params
        )
        
        if result:
            logger.info(f"Document registered on server: system_id={result.get('system_id')}, client_id={_global_client_id}")
            return result
        else:
            logger.warning("Failed to register document on server")
            return None
            
    except Exception as e:
        logger.error(f"Error registering document on server: {e}", exc_info=True)
        return None


def notify_document_download_start(
    document_id: str,
    reg_number: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Notify server that a document download has started.
    Server will track this to calculate download speed and ETA.
    
    Args:
        document_id: Document ID being downloaded
        reg_number: Optional registration number
    
    Returns:
        Response dict with statistics, or None on error
    """
    global _global_api_client, _global_task_id
    
    if not _global_api_client or not _global_task_id:
        # Not in distributed mode, skip notification
        return None
    
    try:
        result = _global_api_client.notify_document_download_start(
            task_id=_global_task_id,
            document_id=document_id,
            reg_number=reg_number
        )
        
        if result and result.get('statistics'):
            stats = result['statistics']
            logger.debug(
                f"Document {document_id} download start notified. "
                f"Speed: {stats.get('download_speed_docs_per_second', 'N/A'):.2f} docs/s, "
                f"ETA: {stats.get('estimated_time_remaining_seconds', 'N/A'):.0f}s"
            )
        
        return result
    except Exception as e:
        logger.warning(f"Error notifying document download start: {e}")
        return None
