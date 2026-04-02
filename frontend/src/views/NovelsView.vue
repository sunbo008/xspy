<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadProps } from 'element-plus'
import { useRouter } from 'vue-router'
import { useNovelsStore } from '../stores/novels'
import { useTasksStore } from '../stores/tasks'

const router = useRouter()
const store = useNovelsStore()
const tasksStore = useTasksStore()
const uploading = ref(false)

onMounted(() => store.fetch())

const handleUpload: UploadProps['beforeUpload'] = (file) => {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['txt', 'epub', 'pdf'].includes(ext || '')) {
    ElMessage.error('仅支持 TXT / EPUB / PDF 格式')
    return false
  }
  uploading.value = true
  store.upload(file).then(() => {
    ElMessage.success('上传成功')
  }).catch(() => {
    ElMessage.error('上传失败')
  }).finally(() => {
    uploading.value = false
  })
  return false
}

async function handleDelete(id: string) {
  await ElMessageBox.confirm('确定要删除这本小说及其所有数据？', '确认删除', { type: 'warning' })
  await store.remove(id)
  ElMessage.success('已删除')
}

async function handleStart(id: string) {
  const task = await tasksStore.start(id)
  ElMessage.success(`任务已启动: ${task.task_id}`)
  router.push('/tasks')
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2>小说管理</h2>
      <el-upload :before-upload="handleUpload" :show-file-list="false" accept=".txt,.epub,.pdf">
        <el-button type="primary" :loading="uploading">
          <el-icon><Upload /></el-icon>上传小说
        </el-button>
      </el-upload>
    </div>

    <el-table :data="store.novels" v-loading="store.loading" stripe style="width: 100%">
      <el-table-column prop="filename" label="文件名" min-width="200" />
      <el-table-column label="大小" width="120">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'uploaded' ? 'info' : 'success'" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button-group>
            <el-button size="small" @click="handleStart(row.id)">
              <el-icon><VideoPlay /></el-icon>开始处理
            </el-button>
            <el-button size="small" @click="router.push(`/novels/${row.id}/characters`)">
              <el-icon><User /></el-icon>角色
            </el-button>
            <el-button size="small" @click="router.push(`/novels/${row.id}/script`)">
              <el-icon><Notebook /></el-icon>剧本
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!store.loading && store.novels.length === 0" description="还没有小说，点击上传按钮开始" />
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 22px;
  color: #303133;
}
</style>
