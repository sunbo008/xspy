## ADDED Requirements

### Requirement: Module I/O type definition
The ScreenwriterAgent module SHALL define the following typed I/O models:

**Input: `ScreenwriterInput`**
- `parse_result: ParseResult` — full novel parse result (or single chapter for per-chapter mode)
- `cast_registry: CastRegistry | None` — existing character registry from previous chapters (None for first chapter)
- `chapter_indices: list[int] | None` — specific chapters to process (None = all)

**Output: `ScreenwriterOutput`**
- `screenplay: Screenplay` — contains `chapters: list[ChapterScreenplay]`, each with `utterances: list[Utterance]`
- `cast_registry: CastRegistry` — updated registry with any newly discovered characters
- `_meta: IntermediateMetaHeader`

**Per-chapter persistence:** `data/intermediate/{novel_slug}/screenplay/ch{NNN}.json`
**Registry persistence:** `data/intermediate/{novel_slug}/cast_registry.json` (shared with CharacterEngine)

#### Scenario: Screenwriter run from intermediate ParseResult
- **WHEN** `ScreenwriterAgent.process(ScreenwriterInput(parse_result=<loaded from parse_result.json>))` is called
- **THEN** it SHALL produce a valid `ScreenwriterOutput` without requiring the original novel file

#### Scenario: Incremental chapter processing
- **WHEN** `ScreenwriterInput` specifies `chapter_indices=[5, 6, 7]` and provides `cast_registry` from chapters 1–4
- **THEN** only chapters 5–7 SHALL be processed, and the output `cast_registry` SHALL include characters from all 7 chapters

### Requirement: LLM-driven screenplay generation
The Screenwriter Agent SHALL convert raw chapter text into a structured screenplay JSON. Each chapter SHALL produce a list of `Utterance` objects with fields: `id`, `speaker_id`, `text`, `is_dialogue`, `emotion_type`, `emotion_detail`, `paraverbals`.

#### Scenario: Dialogue extraction
- **WHEN** chapter text contains `"你怎么来了？"叶枫惊讶道。`
- **THEN** the agent SHALL produce an utterance with `speaker_id="ye-feng"`, `text="你怎么来了？"`, `is_dialogue=true`, `emotion_type="surprised"`

#### Scenario: Narration splitting
- **WHEN** chapter text contains a 200-character narration paragraph
- **THEN** the agent SHALL split it into multiple utterances of appropriate length (50–100 chars each) with `is_dialogue=false`

### Requirement: Cast registry per novel
The agent SHALL maintain a `cast_registry` mapping `speaker_id` → character metadata (name, aliases, role_level, profile, voice_description). This registry SHALL persist across chapters and be updated as new characters appear.

#### Scenario: New character discovery
- **WHEN** chapter 3 introduces a character "萧炎" not in the existing registry
- **THEN** the agent SHALL add an entry with auto-inferred profile and log the discovery

#### Scenario: Character alias resolution
- **WHEN** text refers to "叶少" and "叶枫" as the same person
- **THEN** the agent SHALL map both to the same `speaker_id` in the registry

### Requirement: Structured output validation
Every LLM response SHALL be validated against a predefined JSON Schema. Invalid responses SHALL trigger up to 3 retries with adjusted prompts.

#### Scenario: LLM returns invalid JSON
- **WHEN** the LLM outputs malformed JSON for a chapter
- **THEN** the agent SHALL log the error, retry with a stricter prompt, and succeed within 3 attempts or mark the chapter as failed

#### Scenario: Missing required fields
- **WHEN** the LLM output lacks the `emotion_type` field for an utterance
- **THEN** validation SHALL reject the output and the retry prompt SHALL explicitly request the missing field

### Requirement: Prompt template management
All LLM prompts SHALL be stored as Jinja2 templates in `resources/prompts/`. Templates SHALL accept typed context variables.

#### Scenario: Prompt versioning
- **WHEN** the screenwriter prompt is updated from v2 to v3
- **THEN** both versions SHALL coexist in `resources/prompts/` and the active version SHALL be configurable
