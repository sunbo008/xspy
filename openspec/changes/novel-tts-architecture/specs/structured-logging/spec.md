## ADDED Requirements

### Requirement: Structured logging with structlog
All modules SHALL use `structlog` for logging. Log entries SHALL be structured (key-value pairs) and include at minimum: `timestamp`, `level`, `module`, `event`.

#### Scenario: Log output format in development
- **WHEN** the application runs with `XSPY_ENV=development`
- **THEN** logs SHALL be rendered in colored human-readable console format via `ConsoleRenderer`

#### Scenario: Log output format in production
- **WHEN** the application runs with `XSPY_ENV=production`
- **THEN** logs SHALL be rendered in JSON format with one JSON object per line

### Requirement: Context-bound logging
Each processing unit (novel, chapter, utterance) SHALL bind contextual fields to the logger. Downstream log entries SHALL automatically include these fields without explicit passing.

#### Scenario: Chapter processing context
- **WHEN** chapter 5 of novel "圣域战尊" is being processed
- **THEN** every log entry within that processing scope SHALL contain `novel_slug="shengyu-zhanzun"` and `chapter_num=5`

#### Scenario: Utterance-level tracing
- **WHEN** a TTS request fails for utterance ID "ch5-u042"
- **THEN** the error log SHALL contain `utterance_id="ch5-u042"`, `speaker_id`, `emotion_type`, and the TTS engine name

### Requirement: Trace ID propagation
Each top-level pipeline run SHALL generate a unique `trace_id`. This ID SHALL propagate through all module calls and appear in every log entry.

#### Scenario: Cross-module trace correlation
- **WHEN** an error occurs in the audio processor for a specific utterance
- **THEN** searching logs by `trace_id` SHALL return the complete processing chain from parsing → agent → TTS → audio for that utterance

### Requirement: Performance logging
Key operations SHALL emit timing metrics as structured log fields.

#### Scenario: TTS call duration logging
- **WHEN** a TTS API call completes (success or failure)
- **THEN** a log entry SHALL include `duration_ms`, `audio_length_ms`, `tts_engine`, and `status`
