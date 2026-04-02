import api from './client'
import type { CastEntry, VoiceEntry } from '../types'

export async function getCast(slug: string): Promise<CastEntry[]> {
  const { data } = await api.get<{ characters: CastEntry[] }>(`/characters/${slug}/cast`)
  return data.characters
}

export async function updateCharacter(
  slug: string,
  speakerId: string,
  update: { voice_description?: string }
): Promise<void> {
  await api.put(`/characters/${slug}/cast/${speakerId}`, update)
}

export async function getVoices(slug: string): Promise<Record<string, VoiceEntry>> {
  const { data } = await api.get<{ assignments: Record<string, VoiceEntry> }>(
    `/characters/${slug}/voices`
  )
  return data.assignments
}
