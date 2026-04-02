## ADDED Requirements

### Requirement: Module I/O type definition
The PipelineOrchestrator module SHALL define the following typed I/O models:

**Input: `PipelineInput`**
- `novel_file: Path` — path to the novel file
- `config_overrides: dict | None` — per-novel config overrides
- `resume_from_checkpoint: bool` — whether to resume from existing intermediate data (default: True)
- `chapter_indices: list[int] | None` — specific chapters to process (None = all)
- `force_stages: list[str] | None` — force re-run specific stages even if intermediate data exists (e.g., ["emotion", "tts"])

**Output: `PipelineResult`**
- `novel_slug: str`
- `audiobook: AudioBook | None` — final M4B if complete
- `chapter_results: list[ChapterResult]` — per-chapter status (completed/failed/skipped + paths to all intermediate files)
- `stats: PipelineStats` — total_duration_ms, chapters_processed, tts_calls_made, llm_calls_made, cache_hit_rate
- `_meta: IntermediateMetaHeader`

**Checkpoint persistence:** `data/checkpoints/{novel_slug}/pipeline_state.json`

#### Scenario: PipelineResult provides complete audit trail
- **WHEN** a pipeline run completes
- **THEN** `PipelineResult.chapter_results[i]` SHALL contain paths to every intermediate file (parse_result, screenplay, enriched_screenplay, voice_assignment, tts_manifest, chapter_audio)

#### Scenario: Selective stage re-run via force_stages
- **WHEN** `PipelineInput(force_stages=["emotion", "tts"])` is provided with `resume_from_checkpoint=True`
- **THEN** the orchestrator SHALL reuse existing parse_result and screenplay but re-run emotion enrichment and TTS for all chapters

### Requirement: DAG-based task scheduling
The Pipeline Orchestrator SHALL model the processing pipeline as a DAG (Directed Acyclic Graph). Tasks SHALL execute in dependency order with configurable concurrency limits.

#### Scenario: Parallel chapter processing
- **WHEN** chapters 1–10 all have their screenplays ready and no inter-chapter dependencies
- **THEN** the orchestrator SHALL dispatch TTS tasks for all 10 chapters concurrently (up to the configured concurrency limit)

#### Scenario: Dependency enforcement
- **WHEN** the TTS task for chapter 5 depends on the screenplay being complete
- **THEN** the orchestrator SHALL NOT start the TTS task until the screenplay task reports `completed`

### Requirement: Checkpoint and resume
The orchestrator SHALL persist task state to `data/checkpoints/`. Processing SHALL be resumable from the last checkpoint after interruption.

#### Scenario: Resume after crash
- **WHEN** processing crashes at chapter 50 of 100
- **THEN** on restart, the orchestrator SHALL detect the checkpoint, skip chapters 1–49, and resume from chapter 50

#### Scenario: Selective re-processing
- **WHEN** a user marks chapters 10–15 for re-processing via the Web UI
- **THEN** the orchestrator SHALL invalidate checkpoints for those chapters only and re-run their full pipeline

### Requirement: Progress reporting
The orchestrator SHALL emit real-time progress events (via WebSocket) with: overall percentage, current phase, active tasks, estimated time remaining.

#### Scenario: Progress event format
- **WHEN** the orchestrator completes chapter 25 of 100
- **THEN** it SHALL emit a progress event: `{percent: 25, phase: "tts", active_tasks: 3, eta_seconds: 5400}`

### Requirement: Graceful shutdown
On SIGTERM/SIGINT, the orchestrator SHALL complete in-progress tasks, persist checkpoints, and exit cleanly.

#### Scenario: Interrupt during TTS
- **WHEN** SIGINT is received while 5 TTS tasks are in progress
- **THEN** the orchestrator SHALL wait for those 5 tasks to complete (up to 60s timeout), save checkpoints, and exit with code 0
