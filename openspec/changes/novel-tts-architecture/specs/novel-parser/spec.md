## ADDED Requirements

### Requirement: Module I/O type definition
The NovelParser module SHALL define the following typed I/O models:

**Input: `ParseInput`**
- `file_path: Path` — path to the novel file (TXT/EPUB/PDF)
- `encoding_override: str | None` — force encoding (optional, auto-detect if None)
- `chapter_pattern_override: str | None` — custom regex for chapter splitting (optional)

**Output: `ParseResult`**
- `metadata: NovelMetadata` — title, author, total_word_count, source_format, file_hash
- `chapters: list[Chapter]` — ordered list of chapters
- `_meta: IntermediateMetaHeader` — module name, version, timestamp, trace_id

**Intermediate persistence:** `data/intermediate/{novel_slug}/parse_result.json`

#### Scenario: ParseResult used as downstream fixture
- **WHEN** a developer saves `ParseResult` to `parse_result.json` from a real parsing run
- **THEN** `ScreenwriterAgent` and `CharacterEngine` SHALL be able to load this JSON and run independently without the original novel file

#### Scenario: ParseInput validation
- **WHEN** `ParseInput(file_path="nonexistent.txt")` is constructed
- **THEN** Pydantic validation SHALL raise a `ValidationError` with message "file_path does not exist"

### Requirement: Multi-format novel parsing
The parser SHALL support TXT, EPUB, and PDF formats. Each format SHALL have its own implementation class conforming to `NovelParserProtocol`.

#### Scenario: TXT file with unknown encoding
- **WHEN** a TXT file encoded in GBK is provided
- **THEN** the parser SHALL auto-detect encoding via `chardet`, decode correctly, and return UTF-8 text

#### Scenario: EPUB with nested chapters
- **WHEN** an EPUB file with nested chapter structure (parts → chapters) is provided
- **THEN** the parser SHALL flatten into a linear chapter list preserving reading order

#### Scenario: PDF with mixed layout
- **WHEN** a PDF with both single-column and two-column pages is provided
- **THEN** the parser SHALL extract text in correct reading order

### Requirement: Chapter splitting
The parser SHALL split raw text into chapters using configurable patterns. At least 6 splitting patterns SHALL be provided as defaults (e.g., `第X章`, `Chapter N`, number-only headings).

#### Scenario: Novel with "第X章" format
- **WHEN** text contains lines matching `第一章 xxx` pattern
- **THEN** each matched line SHALL become a chapter boundary, with the matched line as the chapter title

#### Scenario: No recognizable chapter markers
- **WHEN** text has no recognizable chapter markers
- **THEN** the parser SHALL fall back to splitting by line count (configurable, default 3000 chars) and log a warning

### Requirement: Text cleaning pipeline
After parsing, text SHALL pass through a cleaning pipeline: remove duplicate blank lines, normalize whitespace, strip ad/watermark patterns.

#### Scenario: Watermark text removal
- **WHEN** text contains repeated promotional lines like "本书来自XXX网"
- **THEN** the cleaning pipeline SHALL detect and remove these lines, logging each removal

### Requirement: Parse result with metadata
The parser SHALL return a `ParseResult` containing `NovelMetadata` (title, author, word count, format) and a list of `Chapter` objects (index, title, raw text, word count).

#### Scenario: Parse result completeness
- **WHEN** a novel file is successfully parsed
- **THEN** `ParseResult.metadata.total_word_count` SHALL equal the sum of all `chapter.word_count` values
