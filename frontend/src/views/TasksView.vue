<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useTasksStore } from '../stores/tasks'
import type { TaskStatus } from '../types'

const store = useTasksStore()
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  store.fetch()
  pollTimer = setInterval(() => store.fetch(), 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

function statusType(status: string) {
  switch (status) {
    case 'completed': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'primary'
    case 'queued': return 'warning'
    default: return 'info'
  }
}

function progressStatus(task: TaskStatus) {
  if (task.status === 'failed') return 'exception'
  if (task.status === 'completed') return 'success'
  return undefined
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2>任务监控</h2>
      <el-button @click="store.fetch()" :icon="Refresh">刷新</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="24" v-for="task in store.tasks" :key="task.task_id">
        <el-card shadow="hover" class="task-card">
          <div class="task-header">
            <div>
              <span class="task-id">{{ task.task_id }}</span>
              <el-tag :type="statusType(task.status)" size="small" class="status-tag">
                {{ task.status }}
              </el-tag>
            </div>
            <span class="task-novel">小说 ID: {{ task.novel_id }}</span>
          </div>

          <el-progress
            :percentage="task.progress"
            :status="progressStatus(task)"
            :stroke-width="20"
            :text-inside="true"
            class="task-progress"
          />

          <div class="task-message">{{ task.message }}</div>

          <div v-if="task.status === 'running'" class="task-actions">
            <el-button size="small" @click="store.watchProgress(task.task_id)">
              <el-icon><Connection /></el-icon>实时监控
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="store.tasks.length === 0" description="暂无任务，去小说管理页面启动处理" />
  </div>
</template>

<script lang="ts">
import { Refresh } from '@element-plus/icons-vue'
export default { components: { Refresh } }
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 22px; }
.task-card { margin-bottom: 16px; }
.task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.task-id { font-weight: 600; font-family: monospace; font-size: 15px; }
.status-tag { margin-left: 10px; }
.task-novel { color: #909399; font-size: 13px; }
.task-progress { margin-bottom: 10px; }
.task-message { font-size: 13px; color: #606266; }
.task-actions { margin-top: 10px; }
</style>
