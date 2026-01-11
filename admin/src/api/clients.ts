import { apiClient } from './client'

export interface Client {
  id: string
  client_name: string
  client_host: string | null
  status: 'active' | 'inactive' | 'error'
  last_heartbeat: string | null
  total_tasks_completed: number
  total_documents_downloaded: number
  created_at: string
}

export interface ClientStatistics {
  id: string
  client_name: string
  client_host: string | null
  status: string
  last_heartbeat: string | null
  total_tasks_completed: number
  total_documents_downloaded: number
  created_at: string
  updated_at: string
  task_statistics: {
    total_tasks: number
    completed_tasks: number
    in_progress_tasks: number
    failed_tasks: number
    pending_tasks: number
    total_docs_from_tasks: number
    total_docs_failed: number
    total_docs_skipped: number
    first_task_date: string | null
    last_task_date: string | null
  }
  document_statistics: {
    total_documents: number
    unique_regions: number
    unique_instance_types: number
    unique_case_types: number
    classified_documents: number
    first_document_date: string | null
    last_document_date: string | null
  }
}

export interface ClientActivity {
  client_id: string
  current_task: {
    task_id: string
    search_params: Record<string, any>
    start_page: number
    max_documents: number
    status: string
    started_at: string
    documents_downloaded: number
    documents_failed: number
    speed_docs_per_minute: number
  } | null
  session_stats: {
    documents_downloaded: number
    tasks_completed: number
    start_time: string
  }
  lifetime_stats: {
    total_documents: number
    total_tasks: number
  }
  errors: Array<{
    id: string
    error_message: string
    timestamp: string
    task_id: string | null
  }>
}

export const clientsApi = {
  async getAll(): Promise<Client[]> {
    const response = await apiClient.get<{ clients: Client[] }>('/clients')
    return response.data.clients
  },

  async getStatistics(clientId: string): Promise<ClientStatistics> {
    const response = await apiClient.get<ClientStatistics>(`/clients/${clientId}/statistics`)
    return response.data
  },

  async getActivity(clientId: string): Promise<ClientActivity> {
    const response = await apiClient.get<ClientActivity>(`/clients/${clientId}/activity`)
    return response.data
  },
}
