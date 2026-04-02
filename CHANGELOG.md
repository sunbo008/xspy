# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-30

### Added

#### Core Infrastructure (M0)
- Python project scaffolding with `src-layout`, hatchling build
- Pydantic data models: 35 models covering all pipeline stages
- Protocol-based interfaces for all core services
- Unified exception hierarchy (`XspyError` → module-specific errors)
- Structured logging via `structlog` (console + JSON modes)
- Configuration system: `config.yaml` + `llm_models.json` + environment variables
- Dependency Injection container (`dependency-injector`)
- Pre-commit hooks: ruff lint, ruff format, pyright type check
- `.editorconfig` for consistent formatting

#### LLM Layer (M1)
- `OpenAICompatibleClient`: generic client for any OpenAI SDK-compatible LLM
- `ModelRouter`: task-based model routing with priority + fallback
- `LLMCache`: disk-based JSON cache for LLM responses (supports replay-only mode)
- `PromptManager`: Jinja2 template-based prompt management
- `validate_json_output`: robust JSON extraction from LLM responses

#### Novel Parser (M1)
- TXT parser with `chardet` encoding auto-detection
- EPUB parser using `ebooklib` with HTML stripping
- PDF parser using `pdfplumber`
- Regex-based chapter splitter with customizable patterns
- CLI: `python -m xspy.parser`

#### Screenwriter Agent (M2)
- LLM-driven dialogue/narration extraction
- Speaker ID assignment with `CastRegistry` tracking
- CLI: `python -m xspy.agent`

#### Character Engine (M2)
- LLM-driven character attribute inference (gender, age, profession, personality)
- Relationship graph generation
- CLI: `python -m xspy.character`

#### Emotion System (M3)
- LLM-based emotion classification (16 emotion types)
- Rule-based fallback detection from narration cues
- Paraverbal detection (sighs, laughter, sobs, etc.)
- Emotion transition smoothing via VAD distance
- TTS parameter adapter with engine-specific mapping
- CLI: `python -m xspy.emotion`

#### Voice Bank (M3)
- Voice catalog management with character-to-voice assignment
- Automatic narrator voice allocation
- CLI: `python -m xspy.voice`

#### TTS Integration (M4)
- `IndexTTSClient`: HTTP client for Index-TTS 1.5/2
- `Qwen3TTSClient`: HTTP client for Qwen3-TTS
- `TTSHealthChecker`: server availability monitoring
- Audio normalization (sample rate, channels, bit depth)
- `MockTTSEngine`: deterministic silent audio for testing
- CLI: `python -m xspy.tts`

#### Audio Processor (M4)
- Chapter audio assembly from utterance segments
- Loudness normalization, fade in/out, silence insertion
- M4B audiobook assembly with chapter markers via ffmpeg
- CLI: `python -m xspy.audio`

#### Pipeline Orchestrator (M4)
- Full novel-to-audiobook pipeline coordination
- Intermediate data persistence (JSON with meta headers)
- Checkpoint/resume from failure
- Real-time progress tracking with phase estimates
- Graceful shutdown on SIGTERM/SIGINT
- CLI: `python -m xspy.pipeline`

#### Web Backend (M5)
- FastAPI application with CORS support
- REST API: novel upload/list/delete, character/voice management, screenplay editing
- Pipeline task management (start, status, list)
- WebSocket endpoint for real-time progress streaming

#### Frontend (M5)
- Vue 3 + TypeScript + Vite + Element Plus
- Novel management page (upload, list, delete, start processing)
- Character/voice editing page with inline editing
- Screenplay review page with emotion tagging and speaker colors
- Task monitoring page with progress bars and WebSocket updates
- Pinia state management, Vue Router navigation

#### Testing (M6)
- 104 unit tests covering all core modules
- Integration smoke tests for parser, pipeline, web app
- Test fixtures with sample novel and intermediate data
- Three-layer test architecture: function → module → project

#### CI/CD (M6)
- GitHub Actions workflow: lint → type check → unit tests → integration tests
- Frontend CI: vue-tsc type check → vite build
- Python 3.12 + 3.13 matrix testing
