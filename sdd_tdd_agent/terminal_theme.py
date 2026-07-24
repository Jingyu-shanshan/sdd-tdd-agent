import re
from dataclasses import dataclass


INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")


@dataclass(frozen=True)
class InteractiveTheme:
    """Small ANSI theme for readable interactive terminal output."""

    enabled: bool

    def accent(self, value: str) -> str:
        return self._paint("38;5;45", value)

    def secondary(self, value: str) -> str:
        return self._paint("38;5;75", value)

    def success(self, value: str) -> str:
        return self._paint("38;5;114", value)

    def error(self, value: str) -> str:
        return self._paint("38;5;203", value)

    def warning(self, value: str) -> str:
        return self._paint("38;5;220", value)

    def muted(self, value: str) -> str:
        return self._paint("38;5;244", value)

    def text(self, value: str) -> str:
        return self._paint("38;5;252", value)

    def markdown(self, value: str) -> str:
        """Color headings, inline code, fenced code, and unified diffs."""
        if not self.enabled:
            return value
        rendered = []
        fenced = False
        diff = False
        for line in value.splitlines():
            if line.startswith("```"):
                fenced = not fenced
                diff = fenced and line[3:].strip().casefold() == "diff"
                rendered.append(self.muted(line))
            elif fenced and diff:
                rendered.append(self._diff_line(line))
            elif fenced:
                rendered.append(self._paint("38;5;159", line))
            elif line.startswith("#"):
                rendered.append(self.warning(line))
            else:
                rendered.append(
                    INLINE_CODE_PATTERN.sub(
                        lambda match: self._paint(
                            "38;5;159",
                            match.group(1),
                        ),
                        self.text(line),
                    )
                )
        return "\n".join(rendered)

    def diff(self, value: str) -> str:
        """Color one standalone unified diff."""
        if not self.enabled:
            return value
        return "\n".join(self._diff_line(line) for line in value.splitlines())

    def _diff_line(self, line: str) -> str:
        if line.startswith("+") and not line.startswith("+++"):
            return self.success(line)
        if line.startswith("-") and not line.startswith("---"):
            return self.error(line)
        if line.startswith("@@"):
            return self.accent(line)
        return self.muted(line)

    def _paint(self, code: str, value: str) -> str:
        if not self.enabled or not value:
            return value
        return f"\x1b[{code}m{value}\x1b[0m"
