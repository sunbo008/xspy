## ADDED Requirements

### Requirement: Module I/O type definition
The TTSClient module SHALL define the following typed I/O models:

**Input: `TTSRequest`**
- `text: str` — text to synthesize (single utterance)
- `voice_id: str` — reference to voice entry in VoiceBank
- `reference_audio_path: Path | None` — reference audio for voice cloning
- `emotion_params: TTSEmotionParams | None` — emotion-mapped TTS parameters
- `tts_engine: str` — which engine to use ("index-tts" | "qwen3-tts")
- `engine_params: dict` — engine-specific overrides

**Output: `TTSResponse`**
- `audio_bytes: bytes` — synthesized audio (WAV 24kHz 16-bit mono)
- `duration_ms: int` — audio duration in milliseconds
- `sample_rate: int` — always 24000
- `engine_used: str` — actual engine used (may differ from request if fallback)
- `metadata: TTSMetadata` — latency_ms, model_name, request_id
- `_meta: IntermediateMetaHeader`

**Per-utterance persistence:** `data/intermediate/{novel_slug}/tts_results/ch{NNN}/manifest.json` (metadata) + `u{NNNN}.wav` (audio)

#### Scenario: TTSRequest constructed from upstream modules
- **WHEN** the pipeline constructs a `TTSRequest` from `EnrichedScreenplay.utterance[i]` + `VoiceAssignment.assignments[speaker_id]`
- **THEN** all required fields SHALL be populated without any manual mapping

#### Scenario: TTSResponse usable by AudioProcessor
- **WHEN** `TTSResponse.audio_bytes` is loaded
- **THEN** `AudioProcessor` SHALL be able to decode it as WAV 24kHz 16-bit mono without format conversion

### Requirement: Multi-engine TTS client
The TTS Client SHALL support multiple TTS engines (Index-TTS 1.5/2, Qwen3-TTS) via a unified `TTSEngineProtocol`. Each engine SHALL have its own client implementation.

#### Scenario: Index-TTS synthesis
- **WHEN** a `TTSRequest` is sent to the Index-TTS client with text "你好世界" and a reference audio path
- **THEN** the client SHALL POST to the Index-TTS HTTP API and return a `TTSResponse` with the synthesized audio bytes and metadata

#### Scenario: Qwen3-TTS synthesis with emotion
- **WHEN** a `TTSRequest` includes `emotion_detail` with type `JOYFUL`
- **THEN** the Qwen3-TTS client SHALL include the emotion as an instruct prompt and return synthesized audio

### Requirement: Retry and fallback
TTS calls SHALL retry on transient failures (network timeout, 5xx errors) with exponential backoff. After max retries, the system SHALL fall back to an alternative TTS engine if configured.

#### Scenario: Transient failure retry
- **WHEN** Index-TTS returns HTTP 503 on the first attempt
- **THEN** the client SHALL retry up to 3 times with exponential backoff (1s, 2s, 4s) and succeed if the server recovers

#### Scenario: Engine fallback
- **WHEN** Index-TTS is unreachable after all retries
- **THEN** the client SHALL fall back to Qwen3-TTS (if configured) and log a warning with the fallback details

### Requirement: Connection health monitoring
The TTS Client SHALL periodically probe the TTS server health endpoint and report status.

#### Scenario: Health check on startup
- **WHEN** the application starts
- **THEN** the TTS Client SHALL verify connectivity to all configured TTS engines and log their status (reachable/unreachable)

### Requirement: Audio format normalization
Regardless of the TTS engine's native output format, the client SHALL normalize all output to WAV 24kHz 16-bit mono.

#### Scenario: Format conversion
- **WHEN** Qwen3-TTS returns audio in 44.1kHz format
- **THEN** the client SHALL resample to 24kHz 16-bit mono before returning the response
