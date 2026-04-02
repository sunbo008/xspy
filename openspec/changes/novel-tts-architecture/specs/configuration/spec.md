## ADDED Requirements

### Requirement: Pydantic Settings for configuration
All application configuration SHALL be defined as `pydantic_settings.BaseSettings` subclasses in `src/xspy/core/config.py`. Settings SHALL support loading from `config.yaml`, `.env` files, and environment variables (in that priority order, env vars highest).

#### Scenario: Default configuration
- **WHEN** the application starts with no `.env` file and no environment variables
- **THEN** it SHALL use defaults from `config.yaml` and all required fields SHALL have sensible defaults

#### Scenario: Nested settings access
- **WHEN** code accesses `settings.tts.index_tts.base_url`
- **THEN** it SHALL resolve to the configured URL, merged from all configuration sources

### Requirement: Per-novel configuration overrides
Each novel MAY have a `config.yaml` override in `data/novels/{novel_slug}/config.yaml` that overrides global settings for that specific novel (e.g., different TTS engine, silence duration).

#### Scenario: Novel-specific TTS engine
- **WHEN** novel "shengyu-zhanzun" has a local config specifying `tts.preferred_engine: "qwen3-tts"`
- **THEN** processing that novel SHALL use Qwen3-TTS instead of the global default

### Requirement: Configuration validation at startup
All configuration SHALL be validated at startup. Missing required values or invalid types SHALL prevent the application from starting.

#### Scenario: Invalid TTS URL format
- **WHEN** `config.yaml` contains `tts.index_tts.base_url: "not-a-url"`
- **THEN** startup SHALL fail with a validation error: "tts.index_tts.base_url: invalid URL format"

### Requirement: Multi-model LLM configuration
LLM models SHALL be configured via a JSON file (`config/llm_models.json`). Each model entry SHALL specify: `id`, `name`, `base_url`, `api_key`, `model`, `max_tokens`, `temperature`, `capabilities` (list of task types), and `priority` (integer, lower = preferred). All models SHALL conform to the OpenAI SDK `ChatCompletion` protocol.

#### Scenario: Local model registration
- **WHEN** `llm_models.json` contains a model with `base_url: "http://localhost:8000/v1"` and `model: "qwen3.5-35b-a3b"`
- **THEN** the system SHALL create an OpenAI-compatible client for that model and make it available for tasks listed in its `capabilities`

#### Scenario: Add new cloud model without code change
- **WHEN** a user adds a new entry in `llm_models.json` with `base_url` pointing to a DeepSeek/Qwen/OpenAI-compatible API
- **THEN** the system SHALL load the model on next startup and route tasks to it based on `task_routing` configuration, requiring zero code changes

#### Scenario: API key from environment variable
- **WHEN** a model's `api_key` is set to `"${DEEPSEEK_API_KEY}"`
- **THEN** the system SHALL resolve it from the environment variable `DEEPSEEK_API_KEY` at startup, and fail with a clear error if the variable is not set

### Requirement: Task-to-model routing
A `task_routing` mapping SHALL define which model handles each task type (e.g., `screenwriter`, `character-analysis`, `emotion-inference`). If the assigned model is unavailable, the system SHALL fall back to the next model by `priority` that has the matching `capability`.

#### Scenario: Task routing resolution
- **WHEN** task type `screenwriter` is mapped to model `qwen3.5-local` in `task_routing`
- **THEN** all screenwriter LLM calls SHALL use the `qwen3.5-local` model

#### Scenario: Automatic fallback on model failure
- **WHEN** model `qwen3.5-local` (priority 1) is unreachable for a `screenwriter` task
- **THEN** the system SHALL fall back to the next model with `screenwriter` in its `capabilities`, ordered by `priority`

### Requirement: Configuration documentation
Each settings class SHALL generate a JSON Schema that documents all available configuration options with types, defaults, and descriptions.

#### Scenario: Config schema export
- **WHEN** running `python -m xspy.core.config --schema`
- **THEN** it SHALL output a JSON Schema document describing all configuration options
