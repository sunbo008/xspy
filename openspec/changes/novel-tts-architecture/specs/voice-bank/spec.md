## ADDED Requirements

### Requirement: Module I/O type definition
The VoiceBank module SHALL define the following typed I/O models:

**Input: `VoiceBankInput`**
- `cast_registry: CastRegistry` — character profiles with gender, age, voice_description
- `existing_assignments: VoiceAssignment | None` — previous assignments to preserve (None for fresh)

**Output: `VoiceAssignment`**
- `assignments: dict[str, VoiceEntry]` — maps speaker_id → voice configuration (voice_id, tts_engine, reference_audio_path, engine_params)
- `unassigned: list[str]` — speaker_ids that could not be assigned (for manual review)
- `_meta: IntermediateMetaHeader`

**Intermediate persistence:** `data/intermediate/{novel_slug}/voice_assignment.json`

#### Scenario: VoiceAssignment consumed by TTSClient
- **WHEN** `VoiceAssignment` is loaded from JSON and a `TTSRequest` is constructed for speaker "ye-feng"
- **THEN** the request SHALL include `voice_id`, `reference_audio_path`, and `engine_params` from `assignments["ye-feng"]`

#### Scenario: VoiceBank run from intermediate cast_registry
- **WHEN** `VoiceBank.process(VoiceBankInput(cast_registry=<loaded from cast_registry.json>))` is called
- **THEN** it SHALL produce `VoiceAssignment` with entries for every speaker in the registry

### Requirement: Voice entry registry
The Voice Bank SHALL maintain a registry of voice entries, each containing: `voice_id`, `speaker_id`, `display_name`, `gender`, `age_range`, `voice_description`, `reference_audio_path`, `tts_engine`, `engine_params`.

#### Scenario: Voice entry creation from profile
- **WHEN** the Character Engine produces a profile for "叶枫" (male, 20s, confident warrior)
- **THEN** the Voice Bank SHALL auto-generate a voice entry with appropriate `voice_description` and attempt to synthesize a reference audio sample

#### Scenario: Manual voice assignment
- **WHEN** a user assigns a specific reference audio to a character via the Web UI
- **THEN** the Voice Bank SHALL update the entry and invalidate any cached TTS for that character

### Requirement: Template voice pool for minor characters
Minor characters (appearing ≤ 3 times) SHALL be assigned voices from a pre-built template pool, grouped by gender and age range.

#### Scenario: Template voice assignment
- **WHEN** a minor male elder character needs a voice
- **THEN** the Voice Bank SHALL select from the `male-elder` template pool, preferring voices not already assigned to other active characters in the same chapter

### Requirement: Voice distinctiveness checking
When assigning voices, the system SHALL verify that no two simultaneously-present characters share overly similar voices.

#### Scenario: Voice similarity conflict
- **WHEN** two characters in the same scene are assigned voices with cosine similarity > 0.85
- **THEN** the system SHALL log a warning and suggest an alternative voice assignment

### Requirement: Voice persistence
Voice assignments SHALL persist in `data/voice_bank/` as JSON. Re-processing a novel SHALL reuse existing voice assignments unless explicitly reset.

#### Scenario: Voice bank reload
- **WHEN** a novel is re-processed after initial completion
- **THEN** all previously assigned voices SHALL be loaded from the persisted voice bank, maintaining consistency
