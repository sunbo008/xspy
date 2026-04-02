<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { ChapterInfo, Utterance } from '../types'
import { listChapters, getChapter, updateUtterance } from '../api/scripts'

const route = useRoute()
const slug = route.params.slug as string
const chapters = ref<ChapterInfo[]>([])
const activeChapter = ref<number | null>(null)
const utterances = ref<Utterance[]>([])
const chapterTitle = ref('')
const loading = ref(true)
const editingUtt = ref<string | null>(null)

const emotionColors: Record<string, string> = {
  neutral: '#909399', joyful: '#67c23a', sorrowful: '#409eff',
  furious: '#f56c6c', fearful: '#e6a23c', surprised: '#b37feb',
  tender: '#f5a0c0', proud: '#ffd666', contemptuous: '#8c8c8c',
  anxious: '#fa8c16', curious: '#36cfc9', playful: '#ff85c0',
}

onMounted(async () => {
  try {
    chapters.value = await listChapters(slug)
    if (chapters.value.length > 0) {
      await loadChapter(chapters.value[0].chapter_index)
    }
  } catch {
    ElMessage.warning('剧本数据未就绪')
  } finally {
    loading.value = false
  }
})

async function loadChapter(index: number) {
  activeChapter.value = index
  const data = await getChapter(slug, index)
  utterances.value = data.utterances
  chapterTitle.value = data.chapter_title
}

async function saveUtterance(utt: Utterance) {
  if (activeChapter.value === null) return
  await updateUtterance(slug, activeChapter.value, utt.id, {
    speaker_id: utt.speaker_id,
    text: utt.text,
    emotion_type: utt.emotion_type,
  })
  editingUtt.value = null
  ElMessage.success('已保存')
}

const speakerColors = computed(() => {
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#b37feb', '#36cfc9', '#ff85c0']
  const map: Record<string, string> = {}
  const speakers = [...new Set(utterances.value.map(u => u.speaker_id))]
  speakers.forEach((s, i) => { map[s] = colors[i % colors.length] })
  return map
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2>剧本审阅 — {{ slug }}</h2>
      <router-link to="/novels"><el-button>返回</el-button></router-link>
    </div>

    <el-row :gutter="20" v-loading="loading">
      <el-col :span="5">
        <el-card shadow="never" class="chapter-list">
          <template #header><strong>章节列表</strong></template>
          <el-menu :default-active="String(activeChapter)">
            <el-menu-item
              v-for="ch in chapters"
              :key="ch.chapter_index"
              :index="String(ch.chapter_index)"
              @click="loadChapter(ch.chapter_index)"
            >
              <span class="ch-title">{{ ch.chapter_title || `第${ch.chapter_index + 1}章` }}</span>
              <el-badge :value="ch.utterance_count" type="info" class="ch-badge" />
            </el-menu-item>
          </el-menu>
        </el-card>
      </el-col>

      <el-col :span="19">
        <el-card shadow="never">
          <template #header>
            <strong>{{ chapterTitle || '选择章节' }}</strong>
          </template>
          <div class="utterance-list">
            <div
              v-for="utt in utterances"
              :key="utt.id"
              class="utt-row"
              :class="{ dialogue: utt.is_dialogue, narration: !utt.is_dialogue }"
            >
              <div class="utt-meta">
                <el-tag
                  size="small"
                  :color="speakerColors[utt.speaker_id]"
                  effect="dark"
                  class="speaker-tag"
                >
                  {{ utt.speaker_id }}
                </el-tag>
                <el-tag
                  size="small"
                  :style="{ color: emotionColors[utt.emotion_type] || '#909399' }"
                  effect="plain"
                >
                  {{ utt.emotion_type }}
                </el-tag>
                <span v-for="p in utt.paraverbals" :key="p.type" class="paraverbal">
                  {{ p.type === 'sigh' ? '😮‍💨' : p.type === 'laughter' ? '😄' : p.type === 'sob' ? '😢' : '🎭' }}
                </span>
              </div>

              <div v-if="editingUtt === utt.id" class="utt-edit">
                <el-input v-model="utt.text" type="textarea" :rows="2" />
                <div class="edit-row">
                  <el-input v-model="utt.speaker_id" placeholder="说话人" style="width: 120px" size="small" />
                  <el-select v-model="utt.emotion_type" placeholder="情感" size="small" style="width: 140px">
                    <el-option v-for="e in ['neutral','joyful','sorrowful','furious','fearful','surprised','tender','proud','contemptuous','anxious','curious','playful','irritated','serene','pained','amused']"
                      :key="e" :label="e" :value="e" />
                  </el-select>
                  <el-button size="small" type="primary" @click="saveUtterance(utt)">保存</el-button>
                  <el-button size="small" @click="editingUtt = null">取消</el-button>
                </div>
              </div>
              <div v-else class="utt-text" @click="editingUtt = utt.id">
                <span v-if="utt.is_dialogue">"{{ utt.text }}"</span>
                <span v-else class="narration-text">{{ utt.text }}</span>
              </div>
            </div>
          </div>
          <el-empty v-if="utterances.length === 0" description="选择左侧章节查看剧本" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 22px; }
.chapter-list .el-menu { border-right: none; }
.ch-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.ch-badge { margin-left: 8px; }
.utterance-list { max-height: 70vh; overflow-y: auto; }
.utt-row { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; transition: background 0.15s; }
.utt-row:hover { background: #fafafa; }
.utt-row.narration { background: #fafcff; }
.utt-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.speaker-tag { border: none; font-size: 12px; }
.paraverbal { font-size: 14px; }
.utt-text { font-size: 15px; line-height: 1.6; color: #303133; }
.narration-text { color: #909399; font-style: italic; }
.utt-edit { margin-top: 8px; }
.edit-row { display: flex; gap: 8px; margin-top: 8px; align-items: center; }
</style>
