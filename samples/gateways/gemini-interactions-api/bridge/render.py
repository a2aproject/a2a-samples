# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Render Vertex Interactions stream objects as user-facing markdown."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


_MAX_COMMAND_CHARS = 200
_MAX_COMMAND_LINES = 6
_MAX_OUTPUT_CHARS = 500
_MAX_ERROR_CHARS = 300
_MAX_CITATIONS = 10

_STDOUT_MARKER = '[STDOUT]'
_STDERR_MARKER = '[STDERR]'


def _truncate(text: str, limit: int, suffix: str = '…') -> str:
    return text if len(text) <= limit else text[:limit] + suffix


_PRIMARY_ARG_KEYS = ('CommandLine', 'command', 'code', 'sql', 'query', 'path')


def _primary_arg(args: Mapping[str, Any]) -> str:
    for key in _PRIMARY_ARG_KEYS:
        if isinstance(args.get(key), str):
            return args[key]
    for key, value in args.items():
        if key != 'toolAction' and isinstance(value, str) and value:
            return value
    return ''


def _fence(body: str) -> str:
    lines = body.splitlines()
    if len(lines) > _MAX_COMMAND_LINES:
        lines = [*lines[:_MAX_COMMAND_LINES], '…']
    return '```\n' + '\n'.join(lines) + '\n```'


def function_call(obj: Mapping[str, Any]) -> str:
    """Renders a ``function_call`` content/delta for a working-status update."""
    args = obj.get('arguments') or {}
    label = args.get('toolAction') or obj.get('name') or 'tool'
    cmd = _primary_arg(args)
    if not cmd:
        return f'⏵ {label}'
    if '\n' in cmd:
        return f'⏵ {label}\n{_fence(cmd)}'
    return f'⏵ {label}: `{_truncate(cmd, _MAX_COMMAND_CHARS)}`'


def function_result(obj: Mapping[str, Any]) -> str:
    """Renders a ``function_result`` delta as a fenced code block."""
    result = obj.get('result') or {}
    output = result.get('Output') or ''
    if _STDOUT_MARKER in output:
        _, _, tail = output.partition(_STDOUT_MARKER)
        stdout, _, stderr = tail.partition(_STDERR_MARKER)
        parts = [stream.strip() for stream in (stdout, stderr) if stream.strip()]
        output = '\n'.join(parts)
    output = _truncate(output, _MAX_OUTPUT_CHARS, '\n… (truncated)')
    return f'```\n{output}\n```' if output else ''


def citations(annotations: Sequence[Mapping[str, Any]]) -> str:
    """Renders a deduplicated numbered source list, or '' if empty."""
    seen: set[str] = set()
    lines: list[str] = []
    for annotation in annotations:
        citation = annotation.get('url_citation', annotation)
        url = citation.get('url') or citation.get('uri')
        if not url or url in seen:
            continue
        seen.add(url)
        title = citation.get('title') or url
        lines.append(f'{len(lines) + 1}. [{title}]({url})')
        if len(lines) >= _MAX_CITATIONS:
            break
    return '**Sources**\n' + '\n'.join(lines) if lines else ''


def short_error(message: str) -> str:
    """Returns the first line of *message*, truncated for display."""
    first = message.splitlines()[0] if message else 'unknown error'
    return _truncate(first, _MAX_ERROR_CHARS)
