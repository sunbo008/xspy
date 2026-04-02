## ADDED Requirements

### Requirement: Declarative DI container
The system SHALL use `dependency-injector` to define a top-level `ApplicationContainer` in `src/xspy/core/container.py`. All module implementations SHALL be registered as providers (Singleton or Factory).

#### Scenario: Container wiring
- **WHEN** the application starts via `xspy.main:create_app()`
- **THEN** all module dependencies SHALL be resolved from the container and no module SHALL instantiate its own dependencies via `import` + direct construction

#### Scenario: Test override
- **WHEN** a test calls `container.tts_engine.override(MockTTSEngine)`
- **THEN** all code paths using `TTSEngineProtocol` SHALL receive the mock implementation for the duration of that test

### Requirement: Configuration provider
The container SHALL include a `Configuration` provider loaded from `config.yaml` (with `.env` overrides). All module settings SHALL be injected from this provider.

#### Scenario: Environment variable override
- **WHEN** environment variable `XSPY_TTS__BASE_URL` is set
- **THEN** it SHALL override the `tts.base_url` value from `config.yaml`

#### Scenario: Missing required config
- **WHEN** a required configuration key is absent from all sources
- **THEN** application startup SHALL fail with a descriptive error message listing the missing key
