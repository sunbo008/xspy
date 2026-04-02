import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TaskStatus } from '../types'
import { listTasks, startTask, getTaskStatus, connectProgress } from '../api/tasks'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<TaskStatus[]>([])
  const activeWs = ref<WebSocket | null>(null)

  async function fetch() {
    tasks.value = await listTasks()
  }

  async function start(novelId: string) {
    const task = await startTask(novelId)
    tasks.value.unshift(task)
    watchProgress(task.task_id)
    return task
  }

  function watchProgress(taskId: string) {
    if (activeWs.value) activeWs.value.close()
    activeWs.value = connectProgress(taskId, (data) => {
      const idx = tasks.value.findIndex((t) => t.task_id === taskId)
      if (idx >= 0) tasks.value[idx] = data
    })
  }

  return { tasks, fetch, start, watchProgress }
})
