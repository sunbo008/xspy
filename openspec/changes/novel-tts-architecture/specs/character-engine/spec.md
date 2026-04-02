## ADDED Requirements

### Requirement: Module I/O type definition
The CharacterEngine module SHALL define the following typed I/O models:

**Input: `CharacterInput`**
- `parse_result: ParseResult` — full novel text for evidence extraction
- `cast_registry: CastRegistry | None` — existing registry from screenwriter (None for fresh analysis)

**Output: `CharacterOutput`**
- `cast_registry: CastRegistry` — enriched registry with profiles (gender, age, profession, personality, speech style, emotional baseline, confidence scores)
- `relation_graph: RelationGraph` — nodes (characters) + edges (relationships with types)
- `_meta: IntermediateMetaHeader`

**Intermediate persistence:**
- `data/intermediate/{novel_slug}/cast_registry.json`
- `data/intermediate/{novel_slug}/relation_graph.json`

#### Scenario: CharacterEngine run from intermediate data
- **WHEN** `CharacterEngine.process(CharacterInput(parse_result=<loaded>, cast_registry=<loaded>))` is called
- **THEN** it SHALL produce a valid `CharacterOutput` that enriches the existing registry with profiles

#### Scenario: Output usable by VoiceBank and EmotionSystem
- **WHEN** `CharacterOutput.cast_registry` is saved to JSON and loaded by VoiceBank
- **THEN** VoiceBank SHALL be able to use `profile.gender`, `profile.age_range`, and `voice_description` to assign voices

### Requirement: Automatic character profiling
The Character Engine SHALL analyze novel text to infer character attributes: gender, age_range, profession, personality traits, speech style, emotional baseline. Profiling SHALL use LLM with structured output.

#### Scenario: Protagonist profiling
- **WHEN** the engine processes a novel with protagonist "叶枫" appearing in 50+ chapters
- **THEN** it SHALL produce a profile with all required fields populated and a confidence score ≥ 0.8

#### Scenario: Minor character minimal profile
- **WHEN** a character appears in only 1–2 lines of dialogue
- **THEN** the engine SHALL produce a minimal profile (gender + age_range) with confidence score reflecting limited evidence

### Requirement: Character relationship graph
The engine SHALL build a relationship graph tracking connections between characters (family, friendship, rivalry, romance, etc.).

#### Scenario: Relationship discovery
- **WHEN** text contains "叶枫对父亲叶天说"
- **THEN** the engine SHALL add a `parent-child` edge between "ye-tian" and "ye-feng" in the relationship graph

#### Scenario: Graph export
- **WHEN** the relationship graph is requested via API
- **THEN** it SHALL be returned as a JSON structure with `nodes` (characters) and `edges` (relationships with type labels)

### Requirement: Cross-chapter consistency validation
Character profiles SHALL be validated for consistency across chapters. Contradictions SHALL be flagged and logged.

#### Scenario: Gender inconsistency detection
- **WHEN** chapter 1 infers "赵灵儿" as female but chapter 10 uses male pronouns
- **THEN** the engine SHALL flag this as a conflict, log the evidence from both chapters, and prefer the majority inference

### Requirement: Character merging
When multiple references likely refer to the same character, the engine SHALL merge them into a single entry.

#### Scenario: Name variant merging
- **WHEN** "萧炎", "萧大哥", and "斗帝萧炎" are detected
- **THEN** the engine SHALL merge them under one `speaker_id` with all variants listed as `aliases`
