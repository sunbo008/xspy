import api from './client'
import type { Novel } from '../types'

export async function uploadNovel(file: File): Promise<Novel> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<Novel>('/novels/upload', form)
  return data
}

export async function listNovels(): Promise<Novel[]> {
  const { data } = await api.get<{ novels: Novel[] }>('/novels/')
  return data.novels
}

export async function deleteNovel(id: string): Promise<void> {
  await api.delete(`/novels/${id}`)
}
