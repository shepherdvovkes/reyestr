"""
Document management for server-side document registration and classification
"""
import uuid
import json
import logging
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from server.database.connection import get_db_connection, return_db_connection

logger = logging.getLogger(__name__)


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string in DD.MM.YYYY format"""
    if not date_str:
        return None
    try:
        # Try DD.MM.YYYY format
        parts = date_str.replace('/', '.').replace('-', '.').split('.')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year < 100:
                year += 2000
            return datetime(year, month, day)
    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
    return None


def classify_document(
    metadata: Dict[str, Any],
    search_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Classify document based on metadata and search parameters
    
    Returns:
        Dictionary with classification data:
        - court_region: Court region ID
        - instance_type: Instance type (1, 2, 3)
        - classification_source: Source of classification
    """
    classification = {
        'court_region': None,
        'instance_type': None,
        'classification_source': None
    }
    
    # First, try to get from search_params (most reliable)
    if search_params:
        if search_params.get('CourtRegion'):
            classification['court_region'] = str(search_params['CourtRegion'])
            classification['classification_source'] = 'search_params'
        
        if search_params.get('INSType'):
            classification['instance_type'] = str(search_params['INSType'])
            if not classification['classification_source']:
                classification['classification_source'] = 'search_params'
    
    # If not from search_params, try to extract from court_name
    if not classification['court_region'] and metadata.get('court_name'):
        court_name = metadata['court_name']
        
        # Try to extract region from court name patterns
        # Examples: "Київський районний суд" -> region 11 (Київська область)
        region_patterns = {
            r'Київ': '11',
            r'Львів': '14',
            r'Одес': '15',
            r'Харків': '19',
            r'Дніпро': '12',
            r'Запоріжж': '13',
            r'Вінниц': '05',
            r'Луцьк': '07',
            r'Донецьк': '14',
            r'Житомир': '18',
            r'Ужгород': '21',
            r'Івано-Франківськ': '06',
            r'Кропивницьк': '09',
            r'Полтав': '17',
            r'Рівне': '18',
            r'Суми': '20',
            r'Тернопіль': '22',
            r'Херсон': '23',
            r'Хмельницьк': '24',
            r'Черкас': '25',
            r'Чернівці': '26',
            r'Чернігів': '27',
        }
        
        for pattern, region_id in region_patterns.items():
            if re.search(pattern, court_name, re.IGNORECASE):
                classification['court_region'] = region_id
                classification['classification_source'] = 'extracted_from_court_name'
                break
    
    # Try to extract instance type from court name
    if not classification['instance_type'] and metadata.get('court_name'):
        court_name = metadata['court_name'].lower()
        
        if 'апеляційн' in court_name or 'апел' in court_name:
            classification['instance_type'] = '2'
            if not classification['classification_source']:
                classification['classification_source'] = 'extracted_from_court_name'
        elif 'касаційн' in court_name or 'касац' in court_name:
            classification['instance_type'] = '3'
            if not classification['classification_source']:
                classification['classification_source'] = 'extracted_from_court_name'
        elif 'районн' in court_name or 'міськ' in court_name or 'окружн' in court_name:
            classification['instance_type'] = '1'
            if not classification['classification_source']:
                classification['classification_source'] = 'extracted_from_court_name'
    
    return classification


class DocumentManager:
    """Manages document registration and classification"""
    
    @staticmethod
    def register_document(
        metadata: Dict[str, Any],
        task_id: Optional[str] = None,
        search_params: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Register a document and return system_id and classification
        
        Args:
            metadata: Document metadata
            task_id: Optional task ID that downloaded this document
            search_params: Optional search parameters used
            client_id: Optional client ID that registered this document
        
        Returns:
            Tuple of (system_id, classification_dict)
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Classify document
            classification = classify_document(metadata, search_params)
            
            # Get external_id (from metadata or use reg_number)
            external_id = metadata.get('external_id') or metadata.get('reg_number')
            if not external_id:
                # Generate a temporary ID if none provided
                external_id = f"temp_{uuid.uuid4().hex[:12]}"
            
            # Check if document already exists
            cur.execute("""
                SELECT system_id, id FROM documents
                WHERE id = %s OR reg_number = %s
                LIMIT 1
            """, (external_id, metadata.get('reg_number', '')))
            
            existing = cur.fetchone()
            
            if existing:
                # Document exists, update it
                system_id = str(existing[0])
                existing_external_id = existing[1]
                
                # Check if document already has a client_id
                cur.execute("""
                    SELECT client_id FROM documents WHERE system_id = %s
                """, (system_id,))
                existing_client_row = cur.fetchone()
                existing_client_id = existing_client_row[0] if existing_client_row else None
                is_new_client_document = client_id and client_id != existing_client_id
                
                # Update metadata and classification
                update_fields = []
                update_values = []
                
                if metadata.get('url'):
                    update_fields.append("url = %s")
                    update_values.append(metadata['url'])
                
                if metadata.get('reg_number'):
                    update_fields.append("reg_number = %s")
                    update_values.append(metadata['reg_number'])
                
                if metadata.get('court_name'):
                    update_fields.append("court_name = %s")
                    update_values.append(metadata['court_name'])
                
                if metadata.get('judge_name'):
                    update_fields.append("judge_name = %s")
                    update_values.append(metadata['judge_name'])
                
                if metadata.get('decision_type'):
                    update_fields.append("decision_type = %s")
                    update_values.append(metadata['decision_type'])
                
                if metadata.get('decision_date'):
                    decision_date = parse_date(metadata['decision_date'])
                    if decision_date:
                        update_fields.append("decision_date = %s")
                        update_values.append(decision_date)
                
                if metadata.get('law_date'):
                    law_date = parse_date(metadata['law_date'])
                    if law_date:
                        update_fields.append("law_date = %s")
                        update_values.append(law_date)
                
                if metadata.get('case_type'):
                    update_fields.append("case_type = %s")
                    update_values.append(metadata['case_type'])
                
                if metadata.get('case_number'):
                    update_fields.append("case_number = %s")
                    update_values.append(metadata['case_number'])
                
                # Update classification fields
                if classification.get('court_region'):
                    update_fields.append("court_region = %s")
                    update_values.append(classification['court_region'])
                
                if classification.get('instance_type'):
                    update_fields.append("instance_type = %s")
                    update_values.append(classification['instance_type'])
                
                if classification.get('classification_source'):
                    update_fields.append("classification_source = %s")
                    update_values.append(classification['classification_source'])
                    update_fields.append("classification_date = CURRENT_TIMESTAMP")
                
                if task_id:
                    update_fields.append("download_task_id = %s")
                    update_values.append(task_id)
                
                # Update client_id if provided and not already set
                if client_id and not existing_client_id:
                    update_fields.append("client_id = %s")
                    update_values.append(client_id)
                
                if update_fields:
                    update_values.append(system_id)
                    cur.execute(f"""
                        UPDATE documents
                        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE system_id = %s
                    """, update_values)
                
                # Update client statistics if this is a new document for this client
                if is_new_client_document:
                    cur.execute("""
                        UPDATE download_clients
                        SET total_documents_downloaded = total_documents_downloaded + 1
                        WHERE id = %s
                    """, (client_id,))
                
                conn.commit()
                cur.close()
                logger.info(f"Updated document {system_id} (external: {existing_external_id})")
                return system_id, classification
            
            else:
                # New document, create it
                system_id = str(uuid.uuid4())
                
                # Get or create default search session
                cur.execute("""
                    SELECT id FROM search_sessions 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                session_row = cur.fetchone()
                session_id = session_row[0] if session_row else None
                
                if not session_id:
                    cur.execute("""
                        INSERT INTO search_sessions (search_date, total_extracted)
                        VALUES (CURRENT_DATE, 0)
                        RETURNING id
                    """)
                    session_id = cur.fetchone()[0]
                
                # Insert new document
                cur.execute("""
                    INSERT INTO documents (
                        system_id, id, search_session_id, url, reg_number,
                        decision_type, decision_date, law_date, case_type,
                        case_number, court_name, judge_name,
                        court_region, instance_type, classification_source,
                        classification_date, download_task_id, client_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    system_id,
                    external_id,
                    session_id,
                    metadata.get('url', ''),
                    metadata.get('reg_number', external_id),
                    metadata.get('decision_type'),
                    parse_date(metadata.get('decision_date')),
                    parse_date(metadata.get('law_date')),
                    metadata.get('case_type'),
                    metadata.get('case_number'),
                    metadata.get('court_name'),
                    metadata.get('judge_name'),
                    classification.get('court_region'),
                    classification.get('instance_type'),
                    classification.get('classification_source'),
                    datetime.utcnow() if classification.get('classification_source') else None,
                    task_id,
                    client_id
                ))
                
                # Update client statistics
                if client_id:
                    cur.execute("""
                        UPDATE download_clients
                        SET total_documents_downloaded = total_documents_downloaded + 1
                        WHERE id = %s
                    """, (client_id,))
                
                conn.commit()
                cur.close()
                logger.info(f"Registered new document {system_id} (external: {external_id}) for client {client_id}")
                return system_id, classification
                
        except Exception as e:
            logger.error(f"Error registering document: {e}")
            if conn:
                conn.rollback()
            return None, {}
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_document_by_system_id(system_id: str) -> Optional[Dict]:
        """Get document by system_id"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    system_id, id, reg_number, url, court_name, judge_name,
                    decision_type, decision_date, law_date, case_type,
                    case_number, court_region, instance_type,
                    classification_source, classification_date,
                    download_task_id, client_id, created_at, updated_at
                FROM documents
                WHERE system_id = %s
            """, (system_id,))
            
            doc = cur.fetchone()
            cur.close()
            
            if doc:
                return dict(doc)
            return None
            
        except Exception as e:
            logger.error(f"Error getting document {system_id}: {e}")
            return None
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_document_by_external_id(external_id: str) -> Optional[Dict]:
        """Get document by external_id (id or reg_number)"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    system_id, id, reg_number, url, court_name, judge_name,
                    decision_type, decision_date, law_date, case_type,
                    case_number, court_region, instance_type,
                    classification_source, classification_date,
                    download_task_id, client_id, created_at, updated_at
                FROM documents
                WHERE id = %s OR reg_number = %s
                LIMIT 1
            """, (external_id, external_id))
            
            doc = cur.fetchone()
            cur.close()
            
            if doc:
                return dict(doc)
            return None
            
        except Exception as e:
            logger.error(f"Error getting document by external_id {external_id}: {e}")
            return None
        finally:
            if conn:
                return_db_connection(conn)
