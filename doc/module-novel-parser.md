# 模块：小说解析器（Novel Parser）

> 隶属系统：小说 TTS 配音系统
> 运行端：Mac 客户端
> 上游输入：用户上传的小说文件（TXT / EPUB / PDF）
> 下游输出：章节列表 `List[Chapter]` → 交给编剧 Agent 处理
> 关联文档：[`novel-tts-design.md`](novel-tts-design.md)（总纲）、[`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md)（编剧 Agent）

---

## 1. 模块职责

| 职责 | 说明 |
|------|------|
| 文件读取 | 支持 TXT、EPUB、PDF 三种格式的小说文件 |
| 编码检测 | 自动识别文件编码（UTF-8、GBK、GB2312 等），统一转为 UTF-8 |
| 章节分割 | 按章节标记自动拆分全文，输出有序章节列表 |
| 元数据提取 | 提取书名、作者、目录等元数据（EPUB/PDF） |
| 文本清洗 | 去除广告、水印、重复空行、乱码等噪声 |

---

## 2. 代码结构

> 项目路径：`src/xspy/parser/`（完整项目结构见 [`novel-tts-design.md`](novel-tts-design.md) §4）

```
src/xspy/parser/
├── __init__.py          # 公共导出：ParserFactory, ParseResult, Chapter
├── base.py              # BaseParser 抽象基类，定义统一接口
├── txt.py               # TXTParser
├── epub.py              # EPUBParser
├── pdf.py               # PDFParser
├── splitter.py          # ChapterSplitter 章节分割引擎（独立于格式）
├── encoding.py          # EncodingDetector 编码检测
├── cleaner.py           # TextCleaner 文本清洗
└── factory.py           # ParserFactory 工厂函数
```

**导入方式：**

```python
from xspy.parser import ParserFactory, ParseResult
from xspy.parser.txt import TXTParser
from xspy.parser.splitter import ChapterSplitter
```

---

## 3. 数据模型

### 3.1 解析结果

```python
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

@dataclass
class NovelMetadata:
    """小说元数据"""
    title: str
    author: Optional[str] = None
    language: Optional[str] = None
    source_format: str = ""
    source_path: str = ""
    total_chars: int = 0
    encoding: str = "utf-8"

@dataclass
class Chapter:
    """章节数据"""
    chapter_num: int
    title: str
    raw_text: str
    char_count: int = 0
    has_dialogue: bool = False

    def __post_init__(self):
        self.char_count = len(self.raw_text)

@dataclass
class ParseResult:
    """解析结果"""
    metadata: NovelMetadata
    chapters: list[Chapter] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

---

## 4. 抽象基类

```python
from abc import ABC, abstractmethod
from pathlib import Path

class BaseParser(ABC):
    """小说解析器抽象基类"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._validate_file()

    def _validate_file(self):
        if not self.filepath.exists():
            raise FileNotFoundError(f"文件不存在: {self.filepath}")
        if not self.filepath.is_file():
            raise ValueError(f"路径不是文件: {self.filepath}")

    @abstractmethod
    def parse(self) -> ParseResult:
        """解析文件，返回结构化结果"""
        ...

    @abstractmethod
    def get_raw_text(self) -> str:
        """获取全文纯文本"""
        ...
```

---

## 5. TXT 解析器

### 5.1 编码检测

```python
import chardet
from pathlib import Path

class EncodingDetector:
    """文件编码检测"""

    COMMON_ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'utf-16']

    @staticmethod
    def detect(filepath: Path, sample_size: int = 65536) -> str:
        raw = filepath.read_bytes()[:sample_size]
        result = chardet.detect(raw)
        encoding = result.get('encoding', 'utf-8')
        confidence = result.get('confidence', 0)

        if confidence < 0.7:
            for enc in EncodingDetector.COMMON_ENCODINGS:
                try:
                    raw.decode(enc)
                    return enc
                except (UnicodeDecodeError, LookupError):
                    continue

        return encoding or 'utf-8'
```

### 5.2 TXT 解析实现

```python
from pathlib import Path

class TXTParser(BaseParser):

    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self.encoding = EncodingDetector.detect(filepath)
        self.content = filepath.read_text(encoding=self.encoding)

    def get_raw_text(self) -> str:
        return self.content

    def parse(self) -> ParseResult:
        cleaned = TextCleaner.clean(self.content)
        chapters = ChapterSplitter.split(cleaned)

        metadata = NovelMetadata(
            title=self.filepath.stem,
            source_format="txt",
            source_path=str(self.filepath),
            total_chars=len(cleaned),
            encoding=self.encoding
        )

        return ParseResult(metadata=metadata, chapters=chapters)
```

---

## 6. EPUB 解析器

### 6.1 依赖

| 库 | 版本 | 用途 |
|-----|------|------|
| `ebooklib` | >=0.18 | EPUB 文件解析 |
| `beautifulsoup4` | >=4.12 | HTML 内容提取 |
| `lxml` | >=4.9 | XML/HTML 解析器 |

### 6.2 实现要点

```python
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

class EPUBParser(BaseParser):

    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self.book = epub.read_epub(str(filepath))

    def get_raw_text(self) -> str:
        texts = []
        for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'lxml')
            texts.append(soup.get_text(separator='\n'))
        return '\n'.join(texts)

    def _extract_metadata(self) -> NovelMetadata:
        title = self.book.get_metadata('DC', 'title')
        author = self.book.get_metadata('DC', 'creator')
        language = self.book.get_metadata('DC', 'language')

        return NovelMetadata(
            title=title[0][0] if title else self.filepath.stem,
            author=author[0][0] if author else None,
            language=language[0][0] if language else None,
            source_format="epub",
            source_path=str(self.filepath)
        )

    def parse(self) -> ParseResult:
        metadata = self._extract_metadata()
        raw_text = self.get_raw_text()
        cleaned = TextCleaner.clean(raw_text)
        metadata.total_chars = len(cleaned)

        # EPUB 优先使用自带的目录结构分章
        chapters = self._split_by_toc()
        if not chapters:
            chapters = ChapterSplitter.split(cleaned)

        return ParseResult(metadata=metadata, chapters=chapters)

    def _split_by_toc(self) -> list[Chapter]:
        """利用 EPUB 自带目录结构分章"""
        toc = self.book.toc
        if not toc:
            return []

        chapters = []
        for i, item in enumerate(toc):
            if isinstance(item, epub.Link):
                href = item.href.split('#')[0]
                doc = self.book.get_item_with_href(href)
                if doc:
                    soup = BeautifulSoup(doc.get_content(), 'lxml')
                    text = TextCleaner.clean(soup.get_text(separator='\n'))
                    if text.strip():
                        chapters.append(Chapter(
                            chapter_num=i + 1,
                            title=item.title or f"第{i+1}章",
                            raw_text=text
                        ))
        return chapters
```

---

## 7. PDF 解析器

### 7.1 依赖

| 库 | 版本 | 用途 |
|-----|------|------|
| `PyPDF2` | >=3.0 | 基础 PDF 文本提取 |
| `pdfplumber` | >=0.10 | 增强 PDF 解析（表格、布局） |

### 7.2 实现要点

```python
import PyPDF2
from pathlib import Path

class PDFParser(BaseParser):

    def __init__(self, filepath: Path):
        super().__init__(filepath)

    def get_raw_text(self) -> str:
        texts = []
        with open(self.filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
        return '\n'.join(texts)

    def _extract_metadata(self) -> NovelMetadata:
        with open(self.filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            info = reader.metadata
            return NovelMetadata(
                title=info.title if info and info.title else self.filepath.stem,
                author=info.author if info and info.author else None,
                source_format="pdf",
                source_path=str(self.filepath)
            )

    def parse(self) -> ParseResult:
        metadata = self._extract_metadata()
        raw_text = self.get_raw_text()
        cleaned = TextCleaner.clean(raw_text)
        metadata.total_chars = len(cleaned)
        chapters = ChapterSplitter.split(cleaned)
        return ParseResult(metadata=metadata, chapters=chapters)
```

### 7.3 PDF 特殊处理

| 问题 | 解决方案 |
|------|----------|
| 扫描版 PDF（图片） | 后续可集成 OCR（Tesseract / PaddleOCR） |
| 分栏排版 | pdfplumber 按布局提取 |
| 页眉页脚干扰 | 文本清洗阶段过滤重复短文本 |
| 跨页段落 | 合并连续页面文本后再分章 |

---

## 8. 章节分割引擎

### 8.1 支持的章节标记模式

```python
import re
from typing import Optional

class ChapterSplitter:
    """章节分割引擎"""

    PATTERNS = [
        # 中文标准格式
        (r'第[一二三四五六七八九十百千万零〇\d]+[章回节卷集部篇][\s\S]{0,30}', 'zh_standard'),
        # 纯数字格式
        (r'(?:^|\n)\s*(\d{1,4})\s*[\.、]\s*\S+', 'numeric'),
        # 英文格式
        (r'(?i)chapter\s+\d+', 'en_chapter'),
        # 分隔线格式
        (r'={3,}.*={3,}', 'separator'),
        # 卷/册 + 章
        (r'(?:卷|册)\s*[一二三四五六七八九十\d]+', 'volume'),
    ]

    MIN_CHAPTER_LENGTH = 200  # 最少字符数，避免误切
    MAX_CHAPTER_LENGTH = 50000  # 最多字符数，超过强制切分

    @classmethod
    def split(cls, text: str) -> list[Chapter]:
        pattern, pattern_type = cls._detect_pattern(text)
        if pattern is None:
            return cls._split_by_length(text)

        matches = list(re.finditer(pattern, text))
        if len(matches) < 2:
            return cls._split_by_length(text)

        chapters = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chapter_text = text[start:end].strip()

            if len(chapter_text) < cls.MIN_CHAPTER_LENGTH and chapters:
                chapters[-1].raw_text += '\n' + chapter_text
                chapters[-1].char_count = len(chapters[-1].raw_text)
                continue

            chapters.append(Chapter(
                chapter_num=i + 1,
                title=match.group().strip()[:50],
                raw_text=chapter_text
            ))

        # 处理过长章节
        result = []
        for ch in chapters:
            if ch.char_count > cls.MAX_CHAPTER_LENGTH:
                result.extend(cls._split_long_chapter(ch))
            else:
                result.append(ch)

        return result

    @classmethod
    def _detect_pattern(cls, text: str) -> tuple[Optional[str], Optional[str]]:
        """自动检测最匹配的章节模式"""
        best_pattern = None
        best_type = None
        best_count = 0

        for pattern, ptype in cls.PATTERNS:
            count = len(re.findall(pattern, text))
            if count > best_count:
                best_count = count
                best_pattern = pattern
                best_type = ptype

        if best_count >= 2:
            return best_pattern, best_type
        return None, None

    @classmethod
    def _split_by_length(cls, text: str, target_length: int = 5000) -> list[Chapter]:
        """无章节标记时按段落 + 长度切分"""
        paragraphs = text.split('\n\n')
        chapters = []
        current_text = ""
        chapter_num = 1

        for para in paragraphs:
            if len(current_text) + len(para) > target_length and current_text:
                chapters.append(Chapter(
                    chapter_num=chapter_num,
                    title=f"段落 {chapter_num}",
                    raw_text=current_text.strip()
                ))
                chapter_num += 1
                current_text = para
            else:
                current_text += '\n\n' + para

        if current_text.strip():
            chapters.append(Chapter(
                chapter_num=chapter_num,
                title=f"段落 {chapter_num}",
                raw_text=current_text.strip()
            ))

        return chapters

    @classmethod
    def _split_long_chapter(cls, chapter: Chapter) -> list[Chapter]:
        """将过长的章节在段落边界处二次切分"""
        sub_chapters = cls._split_by_length(
            chapter.raw_text,
            target_length=cls.MAX_CHAPTER_LENGTH // 2
        )
        for i, sub in enumerate(sub_chapters):
            sub.title = f"{chapter.title}（{i+1}/{len(sub_chapters)}）"
            sub.chapter_num = chapter.chapter_num
        return sub_chapters
```

### 8.2 章节标记匹配优先级

| 优先级 | 模式 | 说明 |
|--------|------|------|
| 1 | EPUB 自带目录 | 最可靠，直接使用 |
| 2 | 中文标准格式 | "第X章"、"第X回"等 |
| 3 | 英文格式 | "Chapter X" |
| 4 | 纯数字格式 | "1. xxx"、"1、xxx" |
| 5 | 分隔线 | "=====" |
| 6 | 按段落长度切分 | 兜底方案 |

---

## 9. 文本清洗

```python
import re

class TextCleaner:
    """文本清洗工具"""

    AD_PATTERNS = [
        r'(?:本书|本文|本章).*?(?:网|com|cn|org)',
        r'(?:关注|搜索|公众号|微信|QQ群).*',
        r'(?:更新|连载|签约|收藏|推荐|打赏).*?(?:求|请)',
        r'手打.*?(?:小说|文字)',
    ]

    @classmethod
    def clean(cls, text: str) -> str:
        text = cls._normalize_whitespace(text)
        text = cls._remove_ads(text)
        text = cls._fix_punctuation(text)
        text = cls._remove_duplicate_lines(text)
        return text.strip()

    @classmethod
    def _normalize_whitespace(cls, text: str) -> str:
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        return text

    @classmethod
    def _remove_ads(cls, text: str) -> str:
        for pattern in cls.AD_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text

    @classmethod
    def _fix_punctuation(cls, text: str) -> str:
        """修复常见标点问题"""
        text = text.replace('。。。', '……')
        text = text.replace('...', '……')
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r'[''']', "'", text)
        return text

    @classmethod
    def _remove_duplicate_lines(cls, text: str) -> str:
        """去除连续重复行（常见于 PDF 提取的页眉页脚）"""
        lines = text.split('\n')
        result = []
        prev_line = None
        repeat_count = 0
        for line in lines:
            stripped = line.strip()
            if stripped == prev_line and stripped:
                repeat_count += 1
                if repeat_count >= 3:
                    continue
            else:
                repeat_count = 0
            result.append(line)
            prev_line = stripped
        return '\n'.join(result)
```

---

## 10. 工厂函数

```python
from pathlib import Path

class ParserFactory:
    """解析器工厂"""

    PARSERS = {
        '.txt': TXTParser,
        '.epub': EPUBParser,
        '.pdf': PDFParser,
    }

    SUPPORTED_FORMATS = list(PARSERS.keys())

    @classmethod
    def create(cls, filepath: Path) -> BaseParser:
        suffix = filepath.suffix.lower()
        parser_cls = cls.PARSERS.get(suffix)
        if parser_cls is None:
            raise ValueError(
                f"不支持的文件格式: {suffix}，"
                f"支持: {', '.join(cls.SUPPORTED_FORMATS)}"
            )
        return parser_cls(filepath)

    @classmethod
    def parse(cls, filepath: Path) -> ParseResult:
        parser = cls.create(filepath)
        return parser.parse()
```

---

## 11. 依赖清单

```
# novel_parser dependencies
chardet>=5.0
ebooklib>=0.18
beautifulsoup4>=4.12
lxml>=4.9
PyPDF2>=3.0
pdfplumber>=0.10  # optional, for enhanced PDF
```

---

## 12. 测试策略

| 测试类型 | 覆盖范围 |
|----------|----------|
| 编码检测 | UTF-8、GBK、GB2312、BIG5 各一个样本文件 |
| TXT 章节分割 | 标准章节、无章节、混合格式 |
| EPUB 解析 | 有目录、无目录、多层嵌套目录 |
| PDF 解析 | 文本 PDF、分栏 PDF |
| 文本清洗 | 广告文本、重复行、标点混乱 |
| 边界情况 | 空文件、超大文件（>100MB）、二进制文件误传 |

---

## 13. 关联文档

| 文档 | 关系 |
|------|------|
| [`novel-tts-design.md`](novel-tts-design.md) | 总纲 |
| [`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) | 下游消费方（接收 `Chapter` 列表） |
| [`module-task-manager.md`](module-task-manager.md) | 解析任务由任务管理器调度 |
