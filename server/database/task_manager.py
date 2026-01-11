"""
Task management for distributed downloads
"""
import uuid
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from server.database.connection import get_db_connection, return_db_connection
from server.config import config

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages download tasks in the database"""
    
    @staticmethod
    def create_task(
        search_params: Dict,
        start_page: int,
        max_documents: int
    ) -> Optional[str]:
        """Create a new download task"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            task_id = str(uuid.uuid4())
            
            cur.execute("""
                INSERT INTO download_tasks (
                    id, search_params, start_page, max_documents, status
                )
                VALUES (%s, %s, %s, %s, 'pending')
                RETURNING id
            """, (
                task_id,
                json.dumps(search_params),
                start_page,
                max_documents
            ))
            
            result = cur.fetchone()
            conn.commit()
            cur.close()
            
            if result:
                logger.info(f"Created task {task_id}: page {start_page}, max {max_documents} docs")
                return task_id
            return None
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_pending_task(client_id: str) -> Optional[Dict]:
        """Get a pending task and assign it to a client"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Find oldest pending task
            cur.execute("""
                SELECT id, search_params, start_page, max_documents
                FROM download_tasks
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)
            
            task = cur.fetchone()
            
            if not task:
                return None
            
            task_id = task['id']
            
            # Assign task to client
            cur.execute("""
                UPDATE download_tasks
                SET 
                    client_id = %s,
                    status = 'assigned',
                    assigned_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, search_params, start_page, max_documents, status
            """, (client_id, task_id))
            
            assigned_task = cur.fetchone()
            conn.commit()
            cur.close()
            
            if assigned_task:
                return {
                    'id': str(assigned_task['id']),
                    'search_params': assigned_task['search_params'],
                    'start_page': assigned_task['start_page'],
                    'max_documents': assigned_task['max_documents'],
                    'status': assigned_task['status']
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting pending task: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def start_task(task_id: str) -> bool:
        """Mark task as in progress"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE download_tasks
                SET 
                    status = 'in_progress',
                    started_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (task_id,))
            
            conn.commit()
            cur.close()
            return True
            
        except Exception as e:
            logger.error(f"Error starting task {task_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def complete_task(
        task_id: str,
        documents_downloaded: int = 0,
        documents_failed: int = 0,
        documents_skipped: int = 0,
        result_summary: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Mark task as completed"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            status = 'failed' if error_message else 'completed'
            
            cur.execute("""
                UPDATE download_tasks
                SET 
                    status = %s,
                    completed_at = CURRENT_TIMESTAMP,
                    documents_downloaded = %s,
                    documents_failed = %s,
                    documents_skipped = %s,
                    result_summary = %s,
                    error_message = %s
                WHERE id = %s
            """, (
                status,
                documents_downloaded,
                documents_failed,
                documents_skipped,
                json.dumps(result_summary) if result_summary else None,
                error_message,
                task_id
            ))
            
            # Update client statistics
            cur.execute("""
                UPDATE download_clients
                SET 
                    total_tasks_completed = total_tasks_completed + 1,
                    total_documents_downloaded = total_documents_downloaded + %s
                WHERE id = (SELECT client_id FROM download_tasks WHERE id = %s)
            """, (documents_downloaded, task_id))
            
            # Get client info before closing connection
            cur.execute("""
                SELECT client_id FROM download_tasks WHERE id = %s
            """, (task_id,))
            task_row = cur.fetchone()
            client_id_value = task_row['client_id'] if task_row else None
            
            client_name = None
            if client_id_value:
                cur.execute("""
                    SELECT client_name FROM download_clients WHERE id = %s
                """, (client_id_value,))
                client = cur.fetchone()
                client_name = client['client_name'] if client else None
            
            conn.commit()
            cur.close()
            logger.info(f"Task {task_id} completed: {documents_downloaded} downloaded, {documents_failed} failed")
            
            # Send Telegram notification for critical errors (after connection is closed)
            if error_message:
                try:
                    from server.api.telegram import telegram_notifier
                    
                    # Get users with Telegram chat IDs
                    conn2 = get_db_connection()
                    cur2 = conn2.cursor()
                    cur2.execute("""
                        SELECT telegram_chat_id FROM users WHERE telegram_chat_id IS NOT NULL
                    """)
                    users = cur2.fetchall()
                    cur2.close()
                    return_db_connection(conn2)
                    
                    # Send notifications
                    for user in users:
                        telegram_notifier.send_critical_error(
                            chat_id=user['telegram_chat_id'],
                            error_message=error_message,
                            task_id=task_id,
                            client_id=client_name or str(client_id_value) if client_id_value else None
                        )
                except Exception as e:
                    logger.error(f"Failed to send Telegram notification: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error completing task {task_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_task(task_id: str) -> Optional[Dict]:
        """Get task by ID"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    id, client_id, search_params, start_page, max_documents,
                    status, assigned_at, started_at, completed_at,
                    documents_downloaded, documents_failed, documents_skipped,
                    error_message, result_summary, created_at, updated_at
                FROM download_tasks
                WHERE id = %s
            """, (task_id,))
            
            task = cur.fetchone()
            cur.close()
            
            if task:
                return dict(task)
            return None
            
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_tasks_by_status(status: str, limit: int = 100) -> List[Dict]:
        """Get tasks by status"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    id, client_id, search_params, start_page, max_documents,
                    status, assigned_at, started_at, completed_at,
                    documents_downloaded, documents_failed, documents_skipped,
                    created_at
                FROM download_tasks
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (status, limit))
            
            tasks = [dict(row) for row in cur.fetchall()]
            cur.close()
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks by status {status}: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def reset_stale_tasks() -> int:
        """Reset tasks that have been in progress too long (timeout)"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            timeout_threshold = datetime.utcnow() - timedelta(seconds=config.task_timeout_seconds)
            
            cur.execute("""
                UPDATE download_tasks
                SET 
                    status = 'pending',
                    client_id = NULL,
                    assigned_at = NULL,
                    started_at = NULL
                WHERE status = 'in_progress'
                AND started_at < %s
            """, (timeout_threshold,))
            
            reset_count = cur.rowcount
            conn.commit()
            cur.close()
            
            if reset_count > 0:
                logger.warning(f"Reset {reset_count} stale tasks")
            
            return reset_count
            
        except Exception as e:
            logger.error(f"Error resetting stale tasks: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def record_document_download_start(
        task_id: str,
        document_id: str,
        reg_number: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> bool:
        """Record when a document download starts"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO document_download_progress (
                    task_id, document_id, reg_number, client_id, status, started_at
                )
                VALUES (%s, %s, %s, %s, 'in_progress', CURRENT_TIMESTAMP)
                ON CONFLICT (task_id, document_id) 
                DO UPDATE SET 
                    started_at = EXCLUDED.started_at,
                    status = 'in_progress'
            """, (task_id, document_id, reg_number, client_id))
            
            conn.commit()
            cur.close()
            logger.debug(f"Recorded download start for document {document_id} in task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording document download start: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_task_download_statistics(task_id: str) -> Optional[Dict]:
        """
        Get download statistics for a task to calculate speed and ETA
        
        Returns:
            Dict with:
            - total_documents: Total documents in task
            - started_count: Number of documents that started downloading
            - completed_count: Number of completed downloads
            - failed_count: Number of failed downloads
            - avg_download_time_seconds: Average time per document
            - estimated_time_remaining_seconds: Estimated time to complete
            - download_speed_docs_per_second: Current download speed
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get task info
            cur.execute("""
                SELECT max_documents, documents_downloaded, documents_failed, documents_skipped
                FROM download_tasks
                WHERE id = %s
            """, (task_id,))
            
            task = cur.fetchone()
            if not task:
                return None
            
            max_documents = task['max_documents']
            completed_count = task['documents_downloaded'] or 0
            failed_count = task['documents_failed'] or 0
            skipped_count = task['documents_skipped'] or 0
            
            # Get download progress stats
            cur.execute("""
                SELECT 
                    COUNT(*) AS started_count,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_in_progress,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed_in_progress,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) AS avg_download_time_seconds
                FROM document_download_progress
                WHERE task_id = %s
            """, (task_id,))
            
            progress_stats = cur.fetchone()
            
            # Get recent completed downloads for speed calculation (last 10)
            cur.execute("""
                SELECT 
                    EXTRACT(EPOCH FROM (completed_at - started_at)) AS download_time_seconds
                FROM document_download_progress
                WHERE task_id = %s 
                AND status = 'completed'
                AND completed_at IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT 10
            """, (task_id,))
            
            recent_times = [row['download_time_seconds'] for row in cur.fetchall()]
            
            cur.close()
            
            started_count = progress_stats['started_count'] or 0
            avg_download_time = progress_stats['avg_download_time_seconds']
            
            # Calculate download speed (documents per second)
            download_speed = None
            if recent_times and len(recent_times) > 0:
                avg_recent_time = sum(recent_times) / len(recent_times)
                if avg_recent_time > 0:
                    download_speed = 1.0 / avg_recent_time
            
            # Calculate estimated time remaining
            estimated_time_remaining = None
            if download_speed and download_speed > 0:
                remaining_docs = max_documents - completed_count - failed_count - skipped_count
                if remaining_docs > 0:
                    estimated_time_remaining = remaining_docs / download_speed
            
            return {
                'total_documents': max_documents,
                'started_count': started_count,
                'completed_count': completed_count,
                'failed_count': failed_count,
                'skipped_count': skipped_count,
                'avg_download_time_seconds': float(avg_download_time) if avg_download_time else None,
                'estimated_time_remaining_seconds': float(estimated_time_remaining) if estimated_time_remaining else None,
                'download_speed_docs_per_second': float(download_speed) if download_speed else None
            }
            
        except Exception as e:
            logger.error(f"Error getting task download statistics: {e}")
            return None
        finally:
            if conn:
                return_db_connection(conn)


class ClientManager:
    """Manages download clients"""
    
    @staticmethod
    def register_client(client_name: str, client_host: Optional[str] = None, api_key: Optional[str] = None) -> Optional[str]:
        """Register a new client or get existing client ID"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if client with this API key exists
            if api_key:
                cur.execute("""
                    SELECT id FROM download_clients
                    WHERE api_key = %s
                """, (api_key,))
                existing = cur.fetchone()
                if existing:
                    # Update heartbeat
                    cur.execute("""
                        UPDATE download_clients
                        SET 
                            last_heartbeat = CURRENT_TIMESTAMP,
                            status = 'active'
                        WHERE id = %s
                        RETURNING id
                    """, (existing['id'],))
                    result = cur.fetchone()
                    conn.commit()
                    cur.close()
                    return str(result['id'])
            
            # Create new client
            client_id = str(uuid.uuid4())
            
            cur.execute("""
                INSERT INTO download_clients (
                    id, client_name, client_host, api_key, status
                )
                VALUES (%s, %s, %s, %s, 'active')
                RETURNING id
            """, (client_id, client_name, client_host, api_key))
            
            result = cur.fetchone()
            conn.commit()
            cur.close()
            
            if result:
                logger.info(f"Registered client {client_name} ({client_id})")
                return client_id
            return None
            
        except Exception as e:
            logger.error(f"Error registering client: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def update_heartbeat(client_id: str) -> bool:
        """Update client heartbeat"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE download_clients
                SET 
                    last_heartbeat = CURRENT_TIMESTAMP,
                    status = 'active'
                WHERE id = %s
            """, (client_id,))
            
            conn.commit()
            cur.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating heartbeat for client {client_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_client_by_api_key(api_key: str) -> Optional[Dict]:
        """Get client by API key"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, client_name, client_host, status, last_heartbeat,
                       total_tasks_completed, total_documents_downloaded
                FROM download_clients
                WHERE api_key = %s
            """, (api_key,))
            
            client = cur.fetchone()
            cur.close()
            
            if client:
                return dict(client)
            return None
            
        except Exception as e:
            logger.error(f"Error getting client by API key: {e}")
            return None
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_all_clients() -> List[Dict]:
        """Get all clients"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    id, client_name, client_host, status, last_heartbeat,
                    total_tasks_completed, total_documents_downloaded, created_at
                FROM download_clients
                ORDER BY last_heartbeat DESC
            """)
            
            clients = [dict(row) for row in cur.fetchall()]
            cur.close()
            
            return clients
            
        except Exception as e:
            logger.error(f"Error getting all clients: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_client_statistics(client_id: str) -> Optional[Dict]:
        """Get detailed statistics for a client"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get client basic info
            cur.execute("""
                SELECT 
                    id, client_name, client_host, status, last_heartbeat,
                    total_tasks_completed, total_documents_downloaded, created_at, updated_at
                FROM download_clients
                WHERE id = %s
            """, (client_id,))
            
            client = cur.fetchone()
            if not client:
                return None
            
            client_dict = dict(client)
            
            # Get task statistics
            cur.execute("""
                SELECT 
                    COUNT(*) AS total_tasks,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_tasks,
                    COUNT(CASE WHEN status = 'in_progress' THEN 1 END) AS in_progress_tasks,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed_tasks,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending_tasks,
                    SUM(documents_downloaded) AS total_docs_from_tasks,
                    SUM(documents_failed) AS total_docs_failed,
                    SUM(documents_skipped) AS total_docs_skipped,
                    MIN(created_at) AS first_task_date,
                    MAX(completed_at) AS last_task_date
                FROM download_tasks
                WHERE client_id = %s
            """, (client_id,))
            
            task_stats = cur.fetchone()
            if task_stats:
                client_dict['task_statistics'] = dict(task_stats)
            else:
                client_dict['task_statistics'] = {
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'in_progress_tasks': 0,
                    'failed_tasks': 0,
                    'pending_tasks': 0,
                    'total_docs_from_tasks': 0,
                    'total_docs_failed': 0,
                    'total_docs_skipped': 0
                }
            
            # Get document statistics
            cur.execute("""
                SELECT 
                    COUNT(*) AS total_documents,
                    COUNT(DISTINCT court_region) AS unique_regions,
                    COUNT(DISTINCT instance_type) AS unique_instance_types,
                    COUNT(DISTINCT case_type) AS unique_case_types,
                    COUNT(CASE WHEN classification_date IS NOT NULL THEN 1 END) AS classified_documents,
                    MIN(created_at) AS first_document_date,
                    MAX(created_at) AS last_document_date
                FROM documents
                WHERE client_id = %s
            """, (client_id,))
            
            doc_stats = cur.fetchone()
            if doc_stats:
                client_dict['document_statistics'] = dict(doc_stats)
            else:
                client_dict['document_statistics'] = {
                    'total_documents': 0,
                    'unique_regions': 0,
                    'unique_instance_types': 0,
                    'unique_case_types': 0,
                    'classified_documents': 0
                }
            
            cur.close()
            return client_dict
            
        except Exception as e:
            logger.error(f"Error getting client statistics: {e}")
            return None
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_task_indexes() -> List[Dict]:
        """Get task indexes grouped by court region, instance type, and date range"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    search_params->>'CourtRegion' AS court_region,
                    search_params->>'INSType' AS instance_type,
                    MIN(created_at) AS date_start,
                    MAX(created_at) AS date_end,
                    COUNT(*) AS total_tasks,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_tasks,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending_tasks,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed_tasks
                FROM download_tasks
                WHERE search_params->>'CourtRegion' IS NOT NULL
                  AND search_params->>'INSType' IS NOT NULL
                GROUP BY search_params->>'CourtRegion', search_params->>'INSType'
                ORDER BY court_region, instance_type
            """)
            
            indexes = []
            for row in cur.fetchall():
                indexes.append({
                    'court_region': row['court_region'],
                    'instance_type': row['instance_type'],
                    'date_range': {
                        'start': row['date_start'].isoformat() if row['date_start'] else '',
                        'end': row['date_end'].isoformat() if row['date_end'] else ''
                    },
                    'total_tasks': row['total_tasks'],
                    'completed_tasks': row['completed_tasks'],
                    'pending_tasks': row['pending_tasks'],
                    'failed_tasks': row['failed_tasks'],
                    'tasks': []  # Will be loaded separately
                })
            
            cur.close()
            return indexes
            
        except Exception as e:
            logger.error(f"Error getting task indexes: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_tasks_by_index(
        court_region: str,
        instance_type: str,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None
    ) -> List[Dict]:
        """Get tasks filtered by index"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            query = """
                SELECT 
                    id, client_id, search_params, start_page, max_documents,
                    status, assigned_at, started_at, completed_at,
                    documents_downloaded, documents_failed, documents_skipped,
                    error_message, created_at
                FROM download_tasks
                WHERE search_params->>'CourtRegion' = %s
                  AND search_params->>'INSType' = %s
            """
            params = [court_region, instance_type]
            
            if date_start:
                query += " AND created_at >= %s"
                params.append(date_start)
            
            if date_end:
                query += " AND created_at <= %s"
                params.append(date_end)
            
            query += " ORDER BY created_at DESC"
            
            cur.execute(query, params)
            tasks = [dict(row) for row in cur.fetchall()]
            cur.close()
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks by index: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)


class ClientActivityTracker:
    """Tracks real-time client activity"""
    
    # In-memory storage for activity (use Redis in production)
    _activity: Dict[str, Dict] = {}
    
    @staticmethod
    def get_client_activity(client_id: str) -> Optional[Dict]:
        """Get current activity for a client"""
        from datetime import datetime, timedelta
        
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get current active task
            cur.execute("""
                SELECT 
                    id, search_params, start_page, max_documents, status,
                    started_at, documents_downloaded, documents_failed
                FROM download_tasks
                WHERE client_id = %s
                  AND status IN ('in_progress', 'assigned')
                ORDER BY started_at DESC
                LIMIT 1
            """, (client_id,))
            
            current_task_row = cur.fetchone()
            current_task = None
            
            if current_task_row:
                # Calculate speed (simplified - in production, track document timestamps)
                started_at = current_task_row['started_at']
                if started_at:
                    elapsed_minutes = (datetime.utcnow() - started_at).total_seconds() / 60
                    if elapsed_minutes > 0:
                        speed = current_task_row['documents_downloaded'] / elapsed_minutes
                    else:
                        speed = 0
                else:
                    speed = 0
                
                current_task = {
                    'task_id': str(current_task_row['id']),
                    'search_params': current_task_row['search_params'],
                    'start_page': current_task_row['start_page'],
                    'max_documents': current_task_row['max_documents'],
                    'status': current_task_row['status'],
                    'started_at': current_task_row['started_at'].isoformat() if current_task_row['started_at'] else None,
                    'documents_downloaded': current_task_row['documents_downloaded'],
                    'documents_failed': current_task_row['documents_failed'],
                    'speed_docs_per_minute': speed
                }
            
            # Get session stats (tasks started in last 24 hours)
            session_start = datetime.utcnow() - timedelta(hours=24)
            cur.execute("""
                SELECT 
                    COUNT(*) AS tasks_completed,
                    SUM(documents_downloaded) AS documents_downloaded
                FROM download_tasks
                WHERE client_id = %s
                  AND started_at >= %s
            """, (client_id, session_start))
            
            session_stats_row = cur.fetchone()
            session_stats = {
                'documents_downloaded': session_stats_row['documents_downloaded'] or 0,
                'tasks_completed': session_stats_row['tasks_completed'] or 0,
                'start_time': session_start.isoformat()
            }
            
            # Get lifetime stats
            cur.execute("""
                SELECT 
                    total_tasks_completed AS total_tasks,
                    total_documents_downloaded AS total_documents
                FROM download_clients
                WHERE id = %s
            """, (client_id,))
            
            lifetime_row = cur.fetchone()
            lifetime_stats = {
                'total_documents': lifetime_row['total_documents'] or 0 if lifetime_row else 0,
                'total_tasks': lifetime_row['total_tasks'] or 0 if lifetime_row else 0
            }
            
            # Get recent errors
            cur.execute("""
                SELECT 
                    id, error_message, completed_at, id AS task_id
                FROM download_tasks
                WHERE client_id = %s
                  AND error_message IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT 10
            """, (client_id,))
            
            errors = [
                {
                    'id': str(row['id']),
                    'error_message': row['error_message'],
                    'timestamp': row['completed_at'].isoformat() if row['completed_at'] else None,
                    'task_id': str(row['task_id'])
                }
                for row in cur.fetchall()
            ]
            
            cur.close()
            
            return {
                'client_id': client_id,
                'current_task': current_task,
                'session_stats': session_stats,
                'lifetime_stats': lifetime_stats,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error getting client activity: {e}")
            return None
        finally:
            if conn:
                return_db_connection(conn)
