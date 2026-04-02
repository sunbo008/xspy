## ADDED Requirements

### Requirement: Three-layer test architecture — function / module / project
The project SHALL maintain a three-layer test architecture organized in `tests/unit/`, `tests/module/`, and `tests/project/`. Each layer SHALL have distinct scope, speed expectations, and dependency rules.

#### Scenario: Test directory structure enforcement
- **WHEN** a developer creates a new test file
- **THEN** it SHALL be placed in `tests/unit/`, `tests/module/`, or `tests/project/` based on its scope — files outside these directories SHALL trigger a CI warning

### Requirement: Layer 1 — Function-level unit tests (tests/unit/)
Function-level tests SHALL test individual pure functions and class methods in complete isolation. They SHALL have NO external dependencies (no filesystem, no network, no LLM, no database). All inputs SHALL be constructed programmatically.

#### Scenario: Text cleaner function test
- **WHEN** `test_text_cleaner.py` calls `clean_text("本书来自XXX网\n正文内容")`
- **THEN** it SHALL assert the output is `"正文内容"` with zero I/O operations

#### Scenario: Chapter splitter function test
- **WHEN** `test_chapter_splitter.py` calls `split_chapters(text, pattern="第.*?章")` with a 3-chapter text
- **THEN** it SHALL return exactly 3 `Chapter` objects with correct boundaries

#### Scenario: Emotion VAD mapper function test
- **WHEN** `test_emotion_mapper.py` calls `map_emotion_to_tts_params(EmotionDetail(type=JOYFUL, intensity=0.8))` for Index-TTS
- **THEN** it SHALL return `TTSEmotionParams(speed=1.05, pitch_shift=2, energy=1.1)` with no external calls

#### Scenario: Unit test speed requirement
- **WHEN** the entire `tests/unit/` suite runs
- **THEN** it SHALL complete in under 10 seconds with no network or disk I/O beyond reading test source files

### Requirement: Layer 2 — Module-level intermediate data tests (tests/module/)
Module-level tests SHALL test each module's `process()` method by feeding it real intermediate data JSON fixtures from `tests/fixtures/intermediate/`. LLM calls SHALL use cache replay. TTS calls SHALL use mock implementations.

#### Scenario: Parser module test with real novel excerpt
- **WHEN** `test_novel_parser.py` feeds `tests/fixtures/novels/test_3chapters.txt` to `NovelParser.process()`
- **THEN** the output `ParseResult` SHALL have 3 chapters, correct word counts, and pass validation against the Pydantic schema

#### Scenario: Screenwriter module test from intermediate data
- **WHEN** `test_screenwriter.py` loads `tests/fixtures/intermediate/parse_result.json` and feeds it to `ScreenwriterAgent.process()`
- **THEN** the output `Screenplay` SHALL contain valid utterances with `speaker_id`, `emotion_type`, and `text` fields, using LLM cache replay for all LLM calls

#### Scenario: Emotion system module test from intermediate data
- **WHEN** `test_emotion_system.py` loads `tests/fixtures/intermediate/screenplay_ch001.json` and `cast_registry.json`
- **THEN** the output `EnrichedScreenplay` SHALL have `emotion_detail` populated for every utterance

#### Scenario: Voice bank module test from intermediate data
- **WHEN** `test_voice_bank.py` loads `tests/fixtures/intermediate/cast_registry.json`
- **THEN** the output `VoiceAssignment` SHALL map every `speaker_id` to a `voice_id` with no two same-scene characters sharing identical voice params

#### Scenario: Audio processor module test from intermediate data
- **WHEN** `test_audio_processor.py` loads pre-generated WAV segments and `enriched_screenplay_ch001.json`
- **THEN** the output `ChapterAudio` SHALL have correct total duration equal to sum of segments plus expected silence gaps

#### Scenario: Module test I/O snapshot comparison
- **WHEN** a module test produces output
- **THEN** it MAY optionally compare against a golden snapshot in `tests/fixtures/intermediate/` and fail if structural differences exceed the configured threshold

### Requirement: Layer 3 — Project-level end-to-end tests (tests/project/)
Project-level tests SHALL exercise the full pipeline from novel file input to audiobook output. They SHALL use LLM cache replay and TTS mock, but execute all modules in their real dependency order via the PipelineOrchestrator.

#### Scenario: Full pipeline smoke test
- **WHEN** `test_full_pipeline.py` runs with `tests/fixtures/novels/test_3chapters.txt`
- **THEN** it SHALL produce a chapter audio file for each chapter and an M4B audiobook, completing in under 60 seconds

#### Scenario: Pipeline resume after interruption
- **WHEN** `test_resume_pipeline.py` simulates a crash after chapter 2 screenplay generation
- **THEN** on resume it SHALL skip chapters 1–2 screenplay, re-run chapter 2 TTS (if incomplete), and continue from chapter 3

#### Scenario: Selective re-processing
- **WHEN** `test_full_pipeline.py` modifies `screenplay/ch002.json` and re-runs the pipeline
- **THEN** only chapter 2's downstream tasks (emotion enrichment, TTS, audio assembly) SHALL re-execute; chapters 1 and 3 SHALL be skipped

### Requirement: Intermediate data fixture generation
The project SHALL provide a `scripts/generate_test_fixtures.py` script that runs the full pipeline on a small novel excerpt and persists all intermediate data to `tests/fixtures/intermediate/`. This script SHALL be run manually to refresh fixtures when models or prompts change.

#### Scenario: Fixture generation script
- **WHEN** a developer runs `python scripts/generate_test_fixtures.py --novel tests/fixtures/novels/test_3chapters.txt`
- **THEN** it SHALL produce all intermediate JSON files in `tests/fixtures/intermediate/` with `_meta` headers, and update the LLM cache in `tests/fixtures/llm_cache/`

### Requirement: LLM cache replay for module and project tests
LLM calls in module-level and project-level tests SHALL use a record-replay mechanism. First run records responses to `tests/fixtures/llm_cache/` (keyed by prompt hash + model_id). Subsequent runs replay from cache.

#### Scenario: CI without LLM access
- **WHEN** CI runs tests without LLM access
- **THEN** all LLM-dependent tests SHALL pass using cached responses, with zero network calls

#### Scenario: Cache miss handling
- **WHEN** a test makes an LLM call not found in cache and `XSPY_LLM_ALLOW_LIVE=false`
- **THEN** the test SHALL fail with a clear message: "LLM cache miss for prompt hash {hash}, model {model_id}. Run with XSPY_LLM_ALLOW_LIVE=true to record."

### Requirement: TTS mock for testing
Module-level and project-level tests SHALL use a `MockTTSEngine` that returns deterministic audio (sine wave or silence) of appropriate duration, without calling real TTS servers.

#### Scenario: Mock TTS deterministic output
- **WHEN** `MockTTSEngine.process(TTSRequest(text="你好世界"))` is called
- **THEN** it SHALL return a `TTSResponse` with a 1-second silence WAV and `duration_ms=1000`, computed from text length

### Requirement: Snapshot testing for audio output
Audio output tests SHALL use snapshot comparison. Reference audio files SHALL be stored in `tests/fixtures/audio_snapshots/`.

#### Scenario: Audio regression detection
- **WHEN** a code change causes a chapter's assembled audio to differ from the snapshot beyond a configurable threshold (default: PESQ > 0.5 difference)
- **THEN** the snapshot test SHALL fail and output a diff report with the affected utterance IDs

### Requirement: Pre-commit quality gates
The project SHALL use pre-commit hooks enforcing: `ruff check`, `ruff format`, `pyright --strict`, and minimum test coverage thresholds per layer (unit: 90%, module: 80%, project: 70%).

#### Scenario: Pre-commit failure on type error
- **WHEN** a developer commits code with a type error
- **THEN** the pre-commit hook SHALL block the commit with the pyright error message

#### Scenario: Coverage threshold enforcement
- **WHEN** unit test coverage drops below 90%
- **THEN** CI SHALL fail with a report listing uncovered lines per module

### Requirement: Test fixtures with real novel excerpts
Integration tests SHALL use real novel excerpts (≤ 5 chapters) stored in `tests/fixtures/novels/`.

#### Scenario: End-to-end data integrity
- **WHEN** the project-level test runs with `test_3chapters.txt`
- **THEN** the final M4B SHALL contain exactly 3 chapter markers with titles matching the parsed chapter titles
