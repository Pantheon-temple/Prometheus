import enum
from pathlib import Path


class FileType(enum.StrEnum):
    """Enum of all tree-sitter supported file types"""

    # Supported programming languages
    BASH = "bash"
    C = "c"
    CSHARP = "csharp"
    CPP = "cpp"
    GO = "go"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    KOTLIN = "kotlin"
    PHP = "php"
    PYTHON = "python"
    SQL = "sql"
    RUST = "rust"
    RUBY = "ruby"
    TYPESCRIPT = "typescript"
    # configuration files
    YAML = "yaml"
    # Unknown file type
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_path(cls, path: Path):
        match path.suffix:
            case ".sh" | ".bash":
                return cls.BASH
            case ".c":
                return cls.C
            case ".cs":
                return cls.CSHARP
            case ".cpp" | ".cc" | ".cxx":
                return cls.CPP
            case ".go":
                return cls.GO
            case ".java":
                return cls.JAVA
            case ".js":
                return cls.JAVASCRIPT
            case ".kt":
                return cls.KOTLIN
            case ".php":
                return cls.PHP
            case ".py":
                return cls.PYTHON
            case ".sql":
                return cls.SQL
            case ".rs":
                return cls.RUST
            case ".rb":
                return cls.RUBY
            case ".ts":
                return cls.TYPESCRIPT
            # configuration files
            case ".yaml" | ".yml":
                return cls.YAML
            # If the file type is not recognized, return UNKNOWN
            case _:
                return cls.UNKNOWN
