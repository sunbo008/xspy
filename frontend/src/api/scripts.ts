import api from './client'
import type { ChapterInfo, Utterance } from '../types'

export async function listChapters(slug: string): Promise<ChapterInfo[]> {
  const { data } = await api.get<{ chapters: ChapterInfo[] }>(`/scripts/${slug}/chapters`)
  return data.chapters
}

export async function getChapter(slug: string, index: number): Promise<{
  chapter_index: number
  chapter_title: string
  utterances: Utterance[]
}> {
  const { data } = await api.get(`/scripts/${slug}/chapters/${index}`)
  return data
}

export async function updateUtterance(
  slug: string,
  chapterIndex: number,
  utteranceId: string,
  update: { speaker_id?: string; text?: string; emotion_type?: string }
): Promise<void> {
  await api.put(`/scripts/${slug}/chapters/${chapterIndex}/utterances/${utteranceId}`, update)
}
