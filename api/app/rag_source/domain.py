from dataclasses import dataclass
from enum import StrEnum


class RagSourceType(StrEnum):
    TAX_CODE = "tax_code"
    DOCTRINE = "doctrine"
    INTERNAL_PROCEDURE = "internal_procedure"
    RATE_REFERENCE = "rate_reference"
    BUSINESS_NOTE = "business_note"
    POLICY = "policy"
    KNOWLEDGE_BASE = "knowledge_base"
    REPORT = "report"
    CONTRACT = "contract"


class RagSourceOrigin(StrEnum):
    ANONYMIZED_REFERENCE = "anonymized_reference"
    USER_UPLOAD = "user_upload"


class RagSourceStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class RagTextBlockType(StrEnum):
    ARTICLE = "article"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    PAGE = "page"
    NOTE = "note"


@dataclass(frozen=True)
class RagSourceMetadata:
    source_type: RagSourceType
    title: str
    version: str
    language: str
    origin: RagSourceOrigin
    source_path: str
    themes: tuple[str, ...]
    domain: str = "fiscal"
    country: str | None = None
    article_or_section: str | None = None
    owner_reference: str | None = None

    def __post_init__(self) -> None:
        domain = self.domain.strip().lower()
        country = self.country.strip().upper() if self.country is not None else None
        title = self.title.strip()
        version = self.version.strip()
        language = self.language.strip().lower()
        source_path = self.source_path.strip()
        themes = tuple(theme.strip() for theme in self.themes if theme.strip())
        article_or_section = _strip_optional(self.article_or_section)
        owner_reference = _strip_optional(self.owner_reference)

        _require_non_empty("domain", domain)
        _require_non_empty("title", title)
        _require_non_empty("version", version)
        _require_non_empty("language", language)
        _require_non_empty("source_path", source_path)
        if not themes:
            raise ValueError("themes must contain at least one value")
        if self.origin == RagSourceOrigin.USER_UPLOAD and owner_reference is None:
            raise ValueError("owner_reference is required for user uploads")

        object.__setattr__(self, "domain", domain)
        object.__setattr__(self, "country", country)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "language", language)
        object.__setattr__(self, "source_path", source_path)
        object.__setattr__(self, "themes", themes)
        object.__setattr__(self, "article_or_section", article_or_section)
        object.__setattr__(self, "owner_reference", owner_reference)


@dataclass(frozen=True)
class RagSourceDocument:
    metadata: RagSourceMetadata
    text_sha256: str
    status: RagSourceStatus

    def __post_init__(self) -> None:
        text_sha256 = self.text_sha256.strip()
        _require_non_empty("text_sha256", text_sha256)
        object.__setattr__(self, "text_sha256", text_sha256)

    @property
    def can_be_indexed(self) -> bool:
        return self.status == RagSourceStatus.ACTIVE


@dataclass(frozen=True)
class RagTextBlock:
    block_type: RagTextBlockType
    reference: str
    heading: str | None
    text: str

    def __post_init__(self) -> None:
        reference = self.reference.strip()
        heading = _strip_optional(self.heading)
        text = self.text.strip()

        _require_non_empty("reference", reference)
        _require_non_empty("text", text)

        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "heading", heading)
        object.__setattr__(self, "text", text)

    @property
    def searchable_text(self) -> str:
        if self.heading is None:
            return self.text
        return f"{self.heading}\n{self.text}"


@dataclass(frozen=True)
class RagChunk:
    sequence: int
    chunk_reference: str
    text: str
    section_reference: str
    block_type: RagTextBlockType
    source_metadata: RagSourceMetadata
    source_text_sha256: str

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("sequence must be positive")
        chunk_reference = self.chunk_reference.strip()
        text = self.text.strip()
        section_reference = self.section_reference.strip()
        source_text_sha256 = self.source_text_sha256.strip()

        _require_non_empty("chunk_reference", chunk_reference)
        _require_non_empty("text", text)
        _require_non_empty("section_reference", section_reference)
        _require_non_empty("source_text_sha256", source_text_sha256)

        object.__setattr__(self, "chunk_reference", chunk_reference)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "section_reference", section_reference)
        object.__setattr__(self, "source_text_sha256", source_text_sha256)


def _require_non_empty(field_name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{field_name} is required")


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


FiscalSourceType = RagSourceType
FiscalSourceOrigin = RagSourceOrigin
FiscalSourceStatus = RagSourceStatus
FiscalTextBlockType = RagTextBlockType
FiscalSourceMetadata = RagSourceMetadata
FiscalSourceDocument = RagSourceDocument
FiscalTextBlock = RagTextBlock
FiscalChunk = RagChunk
