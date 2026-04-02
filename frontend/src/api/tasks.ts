import api from './client'
import type { TaskStatus } from '../types'

export async function startTask(
  novelId: string,
  chapterIndices?: number[]
): Promise<TaskStatus> {
  const { data } = await api.post<TaskStatus>('/tasks/start', {
    novel_id: novelId,
    chapter_indices: chapterIndices,
  })
  return data
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const { data } = await api.get<TaskStatus>(`/tasks/${taskId}/status`)
  return data
}

export async function listTasks(): Promise<TaskStatus[]> {
  const { data } = await api.get<TaskStatus[]>('/tasks/')
  return data
}

export function connectProgress(taskId: string, onMessage: (data: TaskStatus) => void): WebSocket {
  const ws = new WebSocket(`ws://localhost:8080/ws/progress/${taskId}`)
  ws.onmessage = (event) => {
    onMessage(JSON.parse(event.data))
  }
  return ws
}
