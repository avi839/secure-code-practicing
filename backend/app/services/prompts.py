"""
Prompt templates. This module is the ONLY place prompt text lives.
"""

from typing import Iterable

# Reflection prompt derived from arXiv 2511.03898 ("Secure Code Generation at Scale with Reflexion");
# verify wording against the paper PDF (not in this workspace). This is NOT claimed to be verbatim.
SYSTEM_PROMPT = "You are a senior software engineer who writes secure, production-quality code."

GENERATION_PROMPT_TEMPLATE = (
    "Write {language} code for the following task. Return only the complete code in a single code block.\n\n"
    "Task:\n{task}"
)

REFLECTION_PROMPT_TEMPLATE = """You were previously asked to write {language} code for the following task:
{task}

Here is your most recent solution ({prev_version}):
```{language}
{previous_code}
```

Static security analysis of that solution reported these findings:
{findings_block}

Reflect on each finding and identify the unsafe practice behind it. Then revise the code to fix every reported
vulnerability while preserving the intended functionality. Do not break existing behaviour, do not introduce new
security issues, and prefer minimal, targeted changes that use safer APIs.

Return only the complete updated {language} code in a single code block, with no explanations."""


def _get(item, name: str):
    return item.get(name) if isinstance(item, dict) else getattr(item, name, None)


def format_findings(findings: Iterable) -> str:
    lines = []
    for finding in findings:
        lines.append(
            f"- [{_get(finding, 'severity')}] {_get(finding, 'cwe_id')} {_get(finding, 'cwe_name')} "
            f"(line {_get(finding, 'start_line')}): {_get(finding, 'description')}"
        )
    return "\n".join(lines) if lines else "- No findings were reported."


def build_generation_prompt(task: str, language: str) -> str:
    return GENERATION_PROMPT_TEMPLATE.format(language=language, task=task)


def build_reflection_prompt(task: str, language: str, prev_version: str, previous_code: str, findings) -> str:
    return REFLECTION_PROMPT_TEMPLATE.format(
        language=language,
        task=task,
        prev_version=prev_version,
        previous_code=previous_code,
        findings_block=format_findings(findings),
    )
