## ADDED Requirements

### Requirement: Module I/O type definition
The EmotionSystem module SHALL define the following typed I/O models:

**Input: `EmotionInput`**
- `screenplay: Screenplay` — raw screenplay with basic emotion_type from screenwriter
- `cast_registry: CastRegistry` — character profiles with emotional baselines
- `chapter_index: int | None` — specific chapter to process (None = all)

**Output: `EnrichedScreenplay`**
- `chapters: list[ChapterScreenplay]` — same structure as input but with `emotion_detail` fully populated for every utterance (type, VAD vector, intensity, tts_params per engine)
- `_meta: IntermediateMetaHeader`

**Per-chapter persistence:** `data/intermediate/{novel_slug}/enriched_screenplay/ch{NNN}.json`

#### Scenario: EmotionSystem run from intermediate screenplay
- **WHEN** `EmotionSystem.process(EmotionInput(screenplay=<loaded from ch001.json>, cast_registry=<loaded>))` is called
- **THEN** every utterance in the output SHALL have `emotion_detail.vad` and `emotion_detail.tts_params` populated

#### Scenario: Output directly consumable by TTSClient
- **WHEN** `EnrichedScreenplay` is loaded from JSON
- **THEN** each utterance's `emotion_detail.tts_params["index-tts"]` SHALL be a valid `TTSEmotionParams` dict ready to pass to the TTS client

### Requirement: 20-category emotion taxonomy
The emotion system SHALL support 20 emotion types defined as `EmotionType` enum. Each type SHALL have a default VAD (Valence-Arousal-Dominance) vector.

#### Scenario: Emotion type resolution
- **WHEN** the screenwriter agent assigns `emotion_type="furious"` to an utterance
- **THEN** the emotion system SHALL resolve it to `EmotionType.FURIOUS` with VAD defaults `(0.1, 0.9, 0.7)`

### Requirement: Multi-layer emotion analysis
Emotion inference SHALL operate at three layers: chapter arc (overall mood trajectory), scene context (local emotional atmosphere), and utterance level (per-line emotion).

#### Scenario: Chapter arc influence
- **WHEN** a chapter's arc is classified as "rising tension" and an utterance has neutral text "他走了进去"
- **THEN** the utterance-level emotion SHALL be biased toward `tense` rather than pure `neutral`

### Requirement: Emotion-to-TTS parameter mapping
Each TTS engine SHALL have an adapter that converts `EmotionDetail` (type + VAD + intensity) into engine-specific parameters (pitch shift, speed, energy, style tags).

#### Scenario: Index-TTS emotion mapping
- **WHEN** emotion is `JOYFUL` with intensity 0.8
- **THEN** the Index-TTS adapter SHALL map to `speed=1.05, pitch_shift=+2, energy=1.1`

#### Scenario: Qwen3-TTS emotion mapping
- **WHEN** emotion is `SORROWFUL` with intensity 0.6
- **THEN** the Qwen3-TTS adapter SHALL map to `style="sad"` with appropriate instruct prompt

### Requirement: Narration cue rule engine
Common narration cues (e.g., "冷笑道", "叹了口气说") SHALL be mapped to emotion types via a configurable rule table, reducing LLM calls for obvious cases.

#### Scenario: Rule-based emotion override
- **WHEN** text contains "他冷笑道：'你以为你赢了？'"
- **THEN** the rule engine SHALL set emotion to `CONTEMPTUOUS` without calling LLM

### Requirement: Emotion smoothing
Consecutive utterances from the same speaker SHALL have their emotions smoothed to avoid jarring transitions.

#### Scenario: Emotion transition smoothing
- **WHEN** speaker "ye-feng" has utterances with emotions `[JOYFUL, FURIOUS, JOYFUL]` in 3 consecutive lines
- **THEN** the smoother SHALL flag the middle transition as suspicious and log a warning for review
