## 1. Foundation (M0 基础设施)

- [ ] 1.1 Create project skeleton: pyproject.toml with all dependencies, src/xspy/ package, __init__.py with __version__
- [ ] 1.2 Create .editorconfig, ruff.toml, .gitignore (data/, *.wav, *.m4b, __pycache__)
- [ ] 1.3 Implement core/exceptions.py: XspyError base class, module-level exception hierarchy
- [ ] 1.4 Implement core/models.py: IntermediateMetaHeader, NovelMetadata, Chapter, ParseResult, Utterance, Screenplay, CastRegistry, EmotionType enum (20 types with VAD defaults), EmotionDetail, TTSRequest, TTSResponse, VoiceEntry, VoiceAssignment, ChapterAudio, AudioBook, PipelineInput, PipelineResult
- [ ] 1.5 Implement core/protocols.py: NovelParserProtocol, ScreenwriterProtocol, CharacterProtocol, EmotionProtocol, VoiceBankProtocol, TTSEngineProtocol, AudioProcessorProtocol, PipelineProtocol
- [ ] 1.6 Implement core/config.py: XspySettings (Pydantic Settings) with nested TTS/LLM/Audio/Pipeline config, config.yaml loader, env var override, per-novel override support
- [ ] 1.7 Implement core/container.py: ApplicationContainer with dependency-injector, all Protocol providers as Singleton
- [ ] 1.8 Implement core/logging.py: structlog setup, ConsoleRenderer (dev) / JSONRenderer (prod), trace_id processor, context binding helpers
- [ ] 1.9 Create config/config.yaml with sensible defaults and config/llm_models.json with local model template (port 8000)
- [ ] 1.10 Create src/xspy/__main__.py: CLI entry point with --version, --validate-config, --dump-config
- [ ] 1.11 Setup .pre-commit-config.yaml: ruff check, ruff format, pyright strict
- [ ] 1.12 Create doc/glossary.md: 30+ domain term definitions (utterance, screenplay, cast_registry, etc.)
- [ ] 1.13 Add capacity planning section to design.md (LLM call estimates, TTS time, disk space for 100-chapter novel)
- [ ] 1.14 Add async strategy decision to design.md (sync process() + async FastAPI + httpx.AsyncClient for TTS)
- [ ] 1.15 Fix design.md Decision numbering conflict (two Decision 6 → renumber to 7)
- [ ] 1.16 Write tests/unit/ for models.py (serialization roundtrip, validation errors, enum metadata)
- [ ] 1.17 Write tests/unit/ for config.py (default loading, env override, validation failure)
- [ ] 1.18 Verify: python -m xspy --version prints version, pyright --strict src/xspy/ zero errors

## 2. Novel Parser + LLM Layer (M1 解析 + LLM)

- [ ] 2.1 Implement parser/service.py: TXTParser with encoding detection (chardet), chapter splitting (6 patterns), text cleaning pipeline
- [ ] 2.2 Implement parser/models.py: ParseInput, ParseResult with _meta header
- [ ] 2.3 Implement parser/__main__.py: CLI entry point --input novel.txt --output parse_result.json
- [ ] 2.4 Implement core/llm/protocol.py: LLMClientProtocol based on OpenAI ChatCompletion interface
- [ ] 2.5 Implement core/llm/client.py: OpenAICompatibleClient using openai SDK, accepts base_url/api_key/model
- [ ] 2.6 Implement core/llm/router.py: ModelRouter with task_routing config lookup and priority-based fallback
- [ ] 2.7 Implement core/llm/cache.py: disk-based JSON cache keyed by prompt_hash + model_id, record/replay modes
- [ ] 2.8 Implement core/llm/validator.py: JSON Schema validation of LLM output with retry logic (max 3 retries)
- [ ] 2.9 Implement core/llm/prompts.py: Jinja2 template loader from resources/prompts/, typed context variable validation
- [ ] 2.10 Create resources/prompts/_shared/base_system.jinja2 and initial screenwriter/v1.jinja2 template
- [ ] 2.11 Register LLM and Parser providers in core/container.py
- [ ] 2.12 Write tests/unit/ for chapter_splitter, text_cleaner, encoding_detector pure functions
- [ ] 2.13 Write tests/module/test_novel_parser.py: parse real 3-chapter fixture, assert ParseResult schema
- [ ] 2.14 Write tests/module/test_llm_client.py: cache record/replay, router fallback, validator retry
- [ ] 2.15 Create tests/fixtures/novels/test_3chapters.txt: real novel excerpt for testing
- [ ] 2.16 Verify: python -m xspy.parser --input test_3chapters.txt --output parse_result.json succeeds

## 3. Screenwriter Agent + Character Engine (M2 编剧 + 角色)

- [ ] 3.1 Implement agent/service.py: ScreenwriterAgent with LLM-driven dialogue extraction, narration splitting, speaker binding
- [ ] 3.2 Implement agent/models.py: ScreenwriterInput, ScreenwriterOutput, ChapterScreenplay
- [ ] 3.3 Implement agent/__main__.py: CLI --input parse_result.json --output screenplay/
- [ ] 3.4 Create resources/prompts/screenwriter/v1.jinja2: chapter text → structured screenplay JSON prompt
- [ ] 3.5 Implement character/service.py: CharacterEngine with LLM-driven profiling, alias merging, relationship discovery
- [ ] 3.6 Implement character/models.py: CharacterInput, CharacterOutput, CharacterProfile, RelationGraph
- [ ] 3.7 Implement character/__main__.py: CLI --input parse_result.json --output cast_registry.json
- [ ] 3.8 Create resources/prompts/character_analysis/v1.jinja2: text → character profile JSON prompt
- [ ] 3.9 Implement intermediate data persistence: auto-save to data/intermediate/{novel_slug}/ with _meta headers
- [ ] 3.10 Register Agent and Character providers in container.py
- [ ] 3.11 Write tests/unit/ for dialogue regex patterns, narration split logic, alias similarity detection
- [ ] 3.12 Write tests/module/test_screenwriter.py: load parse_result fixture, LLM cache replay, assert Screenplay schema
- [ ] 3.13 Write tests/module/test_character_engine.py: load parse_result fixture, assert CastRegistry + RelationGraph
- [ ] 3.14 Generate and commit tests/fixtures/intermediate/parse_result.json from step 2.16
- [ ] 3.15 Verify: parse_result.json → screenplay/*.json + cast_registry.json pipeline works end-to-end

## 4. Emotion System + Voice Bank (M3 情感 + 音色)

- [ ] 4.1 Implement emotion/service.py: EmotionSystem with multi-layer analysis (chapter arc, scene context, utterance level)
- [ ] 4.2 Implement emotion/rule_engine.py: narration cue → emotion mapping table (configurable YAML)
- [ ] 4.3 Implement emotion/smoother.py: emotion transition smoothing, jump detection
- [ ] 4.4 Implement emotion/tts_adapter.py: EmotionDetail → TTS engine-specific params (Index-TTS, Qwen3-TTS adapters)
- [ ] 4.5 Implement emotion/models.py: EmotionInput, EnrichedScreenplay
- [ ] 4.6 Implement emotion/__main__.py: CLI --input screenplay_ch001.json --cast-registry cast_registry.json --output enriched/
- [ ] 4.7 Create config/emotion_tts_mapping.yaml: emotion type → TTS params per engine (externalized config)
- [ ] 4.8 Create resources/prompts/emotion_inference/v1.jinja2: context + utterance → emotion inference prompt
- [ ] 4.9 Implement voice/service.py: VoiceBank with profile-to-voice matching, template pool, distinctiveness check
- [ ] 4.10 Implement voice/models.py: VoiceBankInput, VoiceAssignment
- [ ] 4.11 Implement voice/__main__.py: CLI --input cast_registry.json --output voice_assignment.json
- [ ] 4.12 Register Emotion and Voice providers in container.py
- [ ] 4.13 Write tests/unit/ for emotion_mapper, emotion_smoother, vad_calculator, voice_similarity pure functions
- [ ] 4.14 Write tests/module/test_emotion_system.py: load screenplay fixture, assert EnrichedScreenplay with emotion_detail
- [ ] 4.15 Write tests/module/test_voice_bank.py: load cast_registry fixture, assert VoiceAssignment completeness
- [ ] 4.16 Verify: screenplay + cast_registry → enriched_screenplay + voice_assignment pipeline works

## 5. TTS Client + Audio Processor (M4 TTS + 音频)

- [ ] 5.1 Implement tts/service.py: TTSClient with multi-engine support (Index-TTS, Qwen3-TTS), retry with exponential backoff, engine fallback
- [ ] 5.2 Implement tts/index_tts.py: Index-TTS HTTP client implementation
- [ ] 5.3 Implement tts/qwen3_tts.py: Qwen3-TTS HTTP client implementation
- [ ] 5.4 Implement tts/health.py: periodic health check for TTS servers
- [ ] 5.5 Implement tts/normalizer.py: audio format normalization to WAV 24kHz 16-bit mono
- [ ] 5.6 Implement tts/models.py: TTSRequest, TTSResponse with per-utterance persistence to manifest.json
- [ ] 5.7 Implement tts/__main__.py: CLI --input tts_request.json --output audio.wav
- [ ] 5.8 Implement audio/service.py: AudioProcessor with chapter assembly, silence gap insertion, paraverbal injection
- [ ] 5.9 Implement audio/postprocess.py: volume normalization (-16 LUFS), fade in/out, optional noise reduction
- [ ] 5.10 Implement audio/m4b.py: M4B audiobook assembly with chapter markers and metadata
- [ ] 5.11 Implement audio/models.py: AudioInput, ChapterAudio, AudioBook, UtteranceMarker
- [ ] 5.12 Implement audio/__main__.py: CLI --input tts_results/ch001/ --screenplay enriched_ch001.json --output chapter.wav
- [ ] 5.13 Register TTS and Audio providers in container.py
- [ ] 5.14 Implement MockTTSEngine for testing: returns deterministic silence WAV based on text length
- [ ] 5.15 Write tests/unit/ for audio_normalizer, silence_generator, m4b_marker_builder pure functions
- [ ] 5.16 Write tests/module/test_tts_client.py: MockTTSEngine, retry logic, fallback behavior
- [ ] 5.17 Write tests/module/test_audio_processor.py: load WAV segments + screenplay, assert ChapterAudio duration
- [ ] 5.18 Verify: enriched_screenplay + voice_assignment → utterance WAVs → chapter WAV → M4B pipeline works

## 6. Pipeline Orchestrator + Web UI (M5 Pipeline + Web UI)

- [ ] 6.1 Implement pipeline/service.py: PipelineOrchestrator with DAG-based task scheduling, dependency enforcement
- [ ] 6.2 Implement pipeline/checkpoint.py: checkpoint persistence to data/checkpoints/, resume logic
- [ ] 6.3 Implement pipeline/progress.py: real-time progress events (percent, phase, active_tasks, eta)
- [ ] 6.4 Implement pipeline/shutdown.py: graceful SIGTERM/SIGINT handling, complete in-progress tasks
- [ ] 6.5 Implement pipeline/models.py: PipelineInput, PipelineResult, PipelineStats, ChapterResult
- [ ] 6.6 Implement pipeline/__main__.py: CLI --input novel.txt --output audiobook.m4b (full pipeline)
- [ ] 6.7 Register Pipeline provider in container.py
- [ ] 6.8 Implement web/app.py: FastAPI application factory with DI container wiring
- [ ] 6.9 Implement web/routes/novels.py: POST /api/novels/upload, GET /api/novels/, DELETE /api/novels/{id}
- [ ] 6.10 Implement web/routes/characters.py: GET/PUT character profiles and voice assignments
- [ ] 6.11 Implement web/routes/scripts.py: GET/PUT screenplay editor endpoints
- [ ] 6.12 Implement web/routes/tasks.py: POST /api/tasks/start, GET /api/tasks/{id}/status
- [ ] 6.13 Implement web/ws.py: WebSocket /ws/progress/{novel_id} for real-time progress streaming
- [ ] 6.14 Scaffold frontend/: Vue 3 + TypeScript + Vite + Element Plus + Pinia project
- [ ] 6.15 Implement frontend novel management page (upload, list, delete, status)
- [ ] 6.16 Implement frontend character/voice editor page with preview playback
- [ ] 6.17 Implement frontend script review/edit page with emotion override
- [ ] 6.18 Implement frontend task monitor page with WaveSurfer.js waveform and progress bar
- [ ] 6.19 Write tests/project/test_full_pipeline.py: 3-chapter novel → M4B with LLM cache + TTS mock
- [ ] 6.20 Write tests/project/test_resume_pipeline.py: simulate crash, verify checkpoint resume
- [ ] 6.21 Write tests/project/test_selective_reprocess.py: modify intermediate JSON, verify partial re-run
- [ ] 6.22 Create scripts/generate_test_fixtures.py: run pipeline on test novel, persist all intermediate data
- [ ] 6.23 Verify: Web UI upload novel → full pipeline → download M4B audiobook

## 7. Review Agents + Polish (M6 评审 + 打磨)

- [ ] 7.1 Implement review agents as Python modules: ScriptReview, CharacterReview, EmotionReview, VoiceReview, AudioQuality, Coherence
- [ ] 7.2 Integrate review agents into pipeline: auto-run after each module, configurable quality thresholds
- [ ] 7.3 Implement review result persistence to data/intermediate/{novel_slug}/reviews/
- [ ] 7.4 Add review results display to Web UI (per-chapter scores, issue list, fix suggestions)
- [ ] 7.5 Create specs/security/spec.md: file upload validation, path traversal prevention, API key management
- [ ] 7.6 Implement security measures: file type/size validation, path sanitization, API key env-only storage
- [ ] 7.7 Performance optimization: LLM batch call merging, TTS concurrent requests tuning, cache hit rate monitoring
- [ ] 7.8 Setup GitHub Actions CI: lint → unit test → module test → project test → coverage report
- [ ] 7.9 Write CHANGELOG.md with initial release notes
- [ ] 7.10 Final architecture review with xspy-architect-review skill, target overall score > 4.5/5
- [ ] 7.11 Verify: full book processing quality score > 0.8 across all 6 review dimensions
