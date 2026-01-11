import { apiClient } from './client'

export interface Task {
  task_id: string
  status: 'pending' | 'assigned' | 'in_progress' | 'completed' | 'failed'
  search_params: {
    CourtRegion?: string
    INSType?: string
    ChairmenName?: string
    SearchExpression?: string
    RegDateBegin?: string
    RegDateEnd?: string
    DateFrom?: string
    DateTo?: string
  }
  start_page: number
  max_documents: number
  client_id: string | null
  assigned_at: string | null
  started_at: string | null
  completed_at: string | null
  documents_downloaded: number
  documents_failed: number
  documents_skipped: number
  error_message: string | null
}

export interface TasksSummary {
  total_tasks: number
  pending: number
  assigned: number
  in_progress: number
  completed: number
  failed: number
  tasks: Task[]
}

export interface TaskIndex {
  court_region: string
  instance_type: string
  date_range: {
    start: string
    end: string
  }
  total_tasks: number
  completed_tasks: number
  pending_tasks: number
  failed_tasks: number
  tasks: Task[]
}

export const tasksApi = {
  async getSummary(statusFilter?: string, limit = 100): Promise<TasksSummary> {
    const params = new URLSearchParams()
    if (statusFilter) params.append('status_filter', statusFilter)
    params.append('limit', limit.toString())
    const response = await apiClient.get<TasksSummary>(`/tasks?${params.toString()}`)
    return response.data
  },

  async getById(taskId: string): Promise<Task> {
    const response = await apiClient.get<Task>(`/tasks/${taskId}`)
    return response.data
  },

  async getIndexes(): Promise<TaskIndex[]> {
    const response = await apiClient.get<TaskIndex[]>('/tasks/indexes')
    return response.data
  },

  async getByIndex(
    courtRegion: string,
    instanceType: string,
    dateStart?: string,
    dateEnd?: string
  ): Promise<Task[]> {
    const params = new URLSearchParams({
      court_region: courtRegion,
      instance_type: instanceType,
    })
    if (dateStart) params.append('date_start', dateStart)
    if (dateEnd) params.append('date_end', dateEnd)
    const response = await apiClient.get<Task[]>(`/tasks/by-index?${params.toString()}`)
    return response.data
  },
}
