## ADDED Requirements

### Requirement: Module I/O type definition
The AudioProcessor module SHALL define the following typed I/O models:

**Input: `AudioInput`**
- `segments: list[AudioSegment]` — ordered utterance audio files (path + duration_ms + utterance_id)
- `screenplay: ChapterScreenplay` — screenplay for paraverbal positions and silence gap rules
- `voice_assignment: VoiceAssignment` — for speaker-aware processing
- `config: AudioProcessingConfig` — silence gaps, normalization target, fade settings

**Output: `ChapterAudio`**
- `file_path: Path` — path to assembled chapter WAV
- `duration_ms: int` — total duration
- `chapter_index: int`
- `chapter_title: str`
- `utterance_markers: list[UtteranceMarker]` — start_ms, end_ms, utterance_id for each segment
- `_meta: IntermediateMetaHeader`

**Audiobook Output: `AudioBook`**
- `file_path: Path` — path to M4B file
- `chapters: list[ChapterMarker]` — chapter title + start_ms for M4B markers
- `total_duration_ms: int`
- `metadata: AudioBookMetadata` — title, author, cover_image_path

**Intermediate persistence:** `data/output/{novel_slug}/ch{NNN}/{novel_slug}_ch{NNN}.wav` + `data/output/{novel_slug}/{novel_slug}.m4b`

#### Scenario: AudioProcessor run from intermediate TTS results
- **WHEN** `AudioProcessor.process(AudioInput(segments=<loaded from tts_results/ch001/>, screenplay=<loaded>))` is called
- **THEN** it SHALL produce `ChapterAudio` without needing any upstream module to re-run

#### Scenario: UtteranceMarker enables waveform UI
- **WHEN** the Web UI loads `ChapterAudio.utterance_markers`
- **THEN** it SHALL render clickable utterance boundaries on the WaveSurfer.js waveform

### Requirement: Chapter audio assembly
The Audio Processor SHALL concatenate utterance audio clips into complete chapter audio files, inserting configurable silence gaps between utterances.

#### Scenario: Standard chapter assembly
- **WHEN** chapter 5 has 120 utterance audio clips
- **THEN** the processor SHALL concatenate them in order with 300ms silence between dialogue utterances and 500ms between narration segments, producing a single chapter WAV file

### Requirement: Paraverbal sound effect injection
The processor SHALL inject sound effect clips (sigh, laughter, gasp, etc.) at positions specified by the screenplay's `paraverbals` field.

#### Scenario: Sigh injection before dialogue
- **WHEN** an utterance has `paraverbals: [{type: "sigh", position: "before"}]`
- **THEN** the processor SHALL insert the sigh sound effect clip before the utterance audio with a 100ms crossfade

### Requirement: Audio post-processing pipeline
Each chapter audio SHALL pass through: volume normalization (target -16 LUFS), optional noise reduction, fade-in (first chapter, 1s), fade-out (last chapter, 2s).

#### Scenario: Volume normalization
- **WHEN** a chapter audio has average loudness of -20 LUFS
- **THEN** the post-processor SHALL normalize to -16 LUFS without clipping

### Requirement: M4B audiobook assembly
The processor SHALL combine all chapter audio files into an M4B audiobook with chapter markers and metadata (title, author, cover image).

#### Scenario: M4B with chapter markers
- **WHEN** a novel with 100 chapters is fully synthesized
- **THEN** the M4B output SHALL contain 100 chapter markers, each with the correct chapter title and start time

### Requirement: Audio file naming convention
All audio files SHALL follow the naming convention: `{novel_slug}/ch{NNN}/{novel_slug}_ch{NNN}_u{NNNN}.wav` for utterances and `{novel_slug}/ch{NNN}/{novel_slug}_ch{NNN}.wav` for chapters.

#### Scenario: Utterance file path
- **WHEN** utterance 42 of chapter 5 of novel "shengyu-zhanzun" is synthesized
- **THEN** the file SHALL be saved to `data/output/shengyu-zhanzun/ch005/shengyu-zhanzun_ch005_u0042.wav`
