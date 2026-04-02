import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Novel } from '../types'
import { listNovels, uploadNovel, deleteNovel } from '../api/novels'

export const useNovelsStore = defineStore('novels', () => {
  const novels = ref<Novel[]>([])
  const loading = ref(false)

  async function fetch() {
    loading.value = true
    try {
      novels.value = await listNovels()
    } finally {
      loading.value = false
    }
  }

  async function upload(file: File) {
    const novel = await uploadNovel(file)
    novels.value.unshift(novel)
    return novel
  }

  async function remove(id: string) {
    await deleteNovel(id)
    novels.value = novels.value.filter((n) => n.id !== id)
  }

  return { novels, loading, fetch, upload, remove }
})
