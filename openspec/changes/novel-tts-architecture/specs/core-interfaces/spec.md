## ADDED Requirements

### Requirement: Protocol-based module contracts
All inter-module communication SHALL be defined through `typing.Protocol` classes. Each Protocol SHALL reside in `src/xspy/core/protocols.py` and be importable from `xspy.core`.

#### Scenario: TTS engine replacement
- **WHEN** a new TTS engine class implements `TTSEngineProtocol` methods
- **THEN** it SHALL be usable as a drop-in replacement without modifying any consuming module

#### Scenario: Protocol type checking
- **WHEN** `pyright --strict` runs against the codebase
- **THEN** all Protocol conformance errors SHALL be reported and the CI check SHALL fail if any exist

### Requirement: Shared data models via Pydantic
All cross-module data structures SHALL be defined as `pydantic.BaseModel` subclasses in `src/xspy/core/models.py`. Models SHALL include field-level docstrings and `model_config` with `json_schema_extra` examples.

#### Scenario: Novel parse result serialization
- **WHEN** a `ParseResult` model is serialized to JSON and deserialized back
- **THEN** the round-trip result SHALL be identical to the original

#### Scenario: Invalid data rejection
- **WHEN** a `TTSRequest` is constructed with a negative `speed` value
- **THEN** Pydantic validation SHALL raise a `ValidationError` before the request reaches any downstream module

### Requirement: OpenAI-compatible LLM client protocol
The system SHALL define an `LLMClientProtocol` based on the OpenAI SDK `ChatCompletion` interface. All LLM backends (local mlx_lm, vLLM, Ollama, cloud APIs) SHALL be accessed through a single `OpenAICompatibleClient` implementation that accepts `base_url`, `api_key`, and `model` parameters.

#### Scenario: Local model via OpenAI-compatible API
- **WHEN** a local mlx_lm server exposes an OpenAI-compatible endpoint at `http://localhost:8000/v1`
- **THEN** the `OpenAICompatibleClient` SHALL communicate with it using the standard `openai.ChatCompletion.create()` interface

#### Scenario: Cloud model via same client
- **WHEN** a cloud model (DeepSeek, Qwen-Plus, etc.) provides an OpenAI-compatible endpoint
- **THEN** the same `OpenAICompatibleClient` class SHALL work with only `base_url` and `api_key` changed, no code modification needed

#### Scenario: Model router task dispatch
- **WHEN** a `screenwriter` task requests LLM inference
- **THEN** `ModelRouter` SHALL look up `task_routing["screenwriter"]` and dispatch to the configured model's client instance

### Requirement: Module I/O contract via typed process methods
Every core module SHALL expose a `process()` method with Pydantic-typed input and output. The signature SHALL follow the pattern `def process(self, input: ModuleInput) -> ModuleOutput` where both `ModuleInput` and `ModuleOutput` are Pydantic BaseModel subclasses defined in `src/xspy/core/models.py`.

#### Scenario: Parser I/O contract
- **WHEN** `NovelParser.process(ParseInput(file_path=...))` is called
- **THEN** it SHALL return a `ParseResult` containing `metadata: NovelMetadata` and `chapters: list[Chapter]`

#### Scenario: Screenwriter I/O contract
- **WHEN** `ScreenwriterAgent.process(ScreenwriterInput(parse_result=..., cast_registry=...))` is called
- **THEN** it SHALL return a `ScreenwriterOutput` containing `screenplay: Screenplay` and `cast_registry: CastRegistry`

#### Scenario: CharacterEngine I/O contract
- **WHEN** `CharacterEngine.process(CharacterInput(parse_result=..., cast_registry=...))` is called
- **THEN** it SHALL return a `CharacterOutput` containing `cast_registry: CastRegistry` and `relation_graph: RelationGraph`

#### Scenario: EmotionSystem I/O contract
- **WHEN** `EmotionSystem.process(EmotionInput(screenplay=..., cast_registry=...))` is called
- **THEN** it SHALL return an `EnrichedScreenplay` with every utterance's `emotion_detail` populated

#### Scenario: VoiceBank I/O contract
- **WHEN** `VoiceBank.process(VoiceBankInput(cast_registry=...))` is called
- **THEN** it SHALL return a `VoiceAssignment` mapping each `speaker_id` to voice parameters

#### Scenario: TTSClient I/O contract
- **WHEN** `TTSClient.process(TTSRequest(text=..., voice_id=..., emotion_params=...))` is called
- **THEN** it SHALL return a `TTSResponse` containing `audio_bytes`, `duration_ms`, and `metadata`

#### Scenario: AudioProcessor I/O contract
- **WHEN** `AudioProcessor.process(AudioInput(segments=..., screenplay=..., config=...))` is called
- **THEN** it SHALL return a `ChapterAudio` with the assembled audio file path and chapter markers

### Requirement: Intermediate data persistence format
All module outputs SHALL be serializable to JSON (except raw audio which uses WAV). Intermediate data SHALL be persisted to `data/intermediate/{novel_slug}/` following a defined directory structure. Each JSON file SHALL include a `_meta` header with `module_name`, `version`, `timestamp`, and `trace_id`.

#### Scenario: Intermediate JSON metadata
- **WHEN** the ScreenwriterAgent writes `screenplay/ch001.json`
- **THEN** the file SHALL contain a `_meta` field: `{"module": "screenwriter", "version": "1.0", "timestamp": "...", "trace_id": "..."}`

#### Scenario: Standalone module execution from intermediate data
- **WHEN** a developer has `data/intermediate/shengyu-zhanzun/parse_result.json` from a previous run
- **THEN** they SHALL be able to run `python -m xspy.agent.screenwriter --input data/intermediate/shengyu-zhanzun/parse_result.json` to produce screenplay output without running the parser

#### Scenario: Intermediate data round-trip fidelity
- **WHEN** a `ParseResult` is serialized to `parse_result.json` and loaded back
- **THEN** the deserialized object SHALL pass `assert original == loaded` with full field equality

### Requirement: Module CLI for standalone execution
Each module SHALL expose a CLI entry point (`python -m xspy.<module> --input <file> --output <file>`) for standalone execution using intermediate data files, enabling isolated testing and debugging.

#### Scenario: Parser standalone run
- **WHEN** running `python -m xspy.parser --input novel.txt --output parse_result.json`
- **THEN** it SHALL parse the novel and write the `ParseResult` JSON to the specified output path

#### Scenario: Emotion system standalone run
- **WHEN** running `python -m xspy.emotion --input screenplay_ch001.json --cast-registry cast_registry.json --output enriched_ch001.json`
- **THEN** it SHALL enrich the screenplay with emotions and write the result, without needing the full pipeline

### Requirement: Enumeration types with metadata
Emotion types, speaker roles, and task states SHALL be defined as `StrEnum` classes with attached metadata (display name, description, VAD defaults).

#### Scenario: EmotionType enum completeness
- **WHEN** code references `EmotionType.JOYFUL`
- **THEN** it SHALL resolve to a string value `"joyful"` and expose `.vad_default` returning a `(valence, arousal, dominance)` tuple
