export interface Novel {
  id: string
  filename: string
  file_size: number
  status: string
}

export interface CharacterProfile {
  gender: string
  age_range: string
  profession: string
  personality: string
  speech_style: string
  emotional_baseline: string
}

export interface CastEntry {
  speaker_id: string
  name: string
  aliases: string[]
  role_level: string
  profile: CharacterProfile
  voice_description: string
}

export interface VoiceEntry {
  voice_id: string
  speaker_id: string
  display_name: string
  tts_engine: string
  reference_audio_path: string
}

export interface Utterance {
  id: string
  speaker_id: string
  text: string
  is_dialogue: boolean
  emotion_type: string
  paraverbals: { type: string; position: string }[]
}

export interface ChapterInfo {
  file: string
  chapter_index: number
  chapter_title: string
  utterance_count: number
  enriched: boolean
}

export interface TaskStatus {
  task_id: string
  novel_id: string
  status: string
  progress: number
  message: string
}
