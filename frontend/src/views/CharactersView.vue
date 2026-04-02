<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { CastEntry, VoiceEntry } from '../types'
import { getCast, updateCharacter, getVoices } from '../api/characters'

const route = useRoute()
const slug = route.params.slug as string
const cast = ref<CastEntry[]>([])
const voices = ref<Record<string, VoiceEntry>>({})
const loading = ref(true)
const editingId = ref('')
const editDesc = ref('')

onMounted(async () => {
  try {
    ;[cast.value, voices.value] = await Promise.all([getCast(slug), getVoices(slug)])
  } catch {
    ElMessage.warning('数据未就绪，请先运行角色分析')
  } finally {
    loading.value = false
  }
})

function startEdit(char: CastEntry) {
  editingId.value = char.speaker_id
  editDesc.value = char.voice_description
}

async function saveEdit(char: CastEntry) {
  await updateCharacter(slug, char.speaker_id, { voice_description: editDesc.value })
  char.voice_description = editDesc.value
  editingId.value = ''
  ElMessage.success('已保存')
}

const roleTags: Record<string, string> = {
  protagonist: 'danger',
  supporting: 'warning',
  minor: 'info',
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2>角色管理 — {{ slug }}</h2>
      <router-link to="/novels"><el-button>返回</el-button></router-link>
    </div>

    <el-row :gutter="16" v-loading="loading">
      <el-col :span="8" v-for="char in cast" :key="char.speaker_id">
        <el-card shadow="hover" class="char-card">
          <template #header>
            <div class="card-header">
              <span class="char-name">{{ char.name }}</span>
              <el-tag :type="(roleTags[char.role_level] as any) || 'info'" size="small">
                {{ char.role_level }}
              </el-tag>
            </div>
          </template>

          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="性别">{{ char.profile.gender || '—' }}</el-descriptions-item>
            <el-descriptions-item label="年龄">{{ char.profile.age_range || '—' }}</el-descriptions-item>
            <el-descriptions-item label="身份">{{ char.profile.profession || '—' }}</el-descriptions-item>
            <el-descriptions-item label="性格">{{ char.profile.personality || '—' }}</el-descriptions-item>
            <el-descriptions-item label="语风">{{ char.profile.speech_style || '—' }}</el-descriptions-item>
          </el-descriptions>

          <div class="voice-section">
            <div class="voice-label">
              <el-icon><Microphone /></el-icon> 音色描述
            </div>
            <div v-if="editingId === char.speaker_id">
              <el-input v-model="editDesc" type="textarea" :rows="2" />
              <div class="edit-actions">
                <el-button size="small" type="primary" @click="saveEdit(char)">保存</el-button>
                <el-button size="small" @click="editingId = ''">取消</el-button>
              </div>
            </div>
            <div v-else class="voice-text" @click="startEdit(char)">
              {{ char.voice_description || '点击编辑音色描述...' }}
            </div>
          </div>

          <div v-if="voices[char.speaker_id]" class="voice-id">
            音色 ID: <code>{{ voices[char.speaker_id].voice_id }}</code>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && cast.length === 0" description="暂无角色数据" />
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; font-size: 22px; }
.char-card { margin-bottom: 16px; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.char-name { font-weight: 600; font-size: 16px; }
.voice-section { margin-top: 12px; }
.voice-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.voice-text {
  color: #606266;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 4px;
  background: #f5f7fa;
  font-size: 13px;
  min-height: 32px;
}
.voice-text:hover { background: #ecf5ff; }
.edit-actions { margin-top: 8px; display: flex; gap: 8px; }
.voice-id { margin-top: 8px; font-size: 12px; color: #c0c4cc; }
.voice-id code { background: #f5f7fa; padding: 2px 6px; border-radius: 3px; }
</style>
