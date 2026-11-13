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

# ruff: noqa: S101, PLR2004  # pytest-idiomatic

"""Tests for bridge.render."""

from bridge import render


def test_function_call_single_line_is_inline_code() -> None:
    out = render.function_call({'name': 'run', 'arguments': {'CommandLine': 'ls -la'}})
    assert out == '⏵ run: `ls -la`'


def test_function_call_multiline_is_fenced() -> None:
    out = render.function_call({'name': 'run', 'arguments': {'CommandLine': 'a\nb\nc'}})
    assert out == '⏵ run\n```\na\nb\nc\n```'


def test_function_call_multiline_truncates_lines() -> None:
    body = '\n'.join(f'line{i}' for i in range(20))
    out = render.function_call({'name': 'run', 'arguments': {'code': body}})
    assert out.splitlines()[-2] == '…'
    assert 'line0' in out and 'line19' not in out


def test_function_call_picks_mcp_arg() -> None:
    out = render.function_call({'name': 'bigquery.execute_sql', 'arguments': {'sql': 'SELECT 1'}})
    assert out == '⏵ bigquery.execute_sql: `SELECT 1`'


def test_function_call_truncates_long_single_line() -> None:
    out = render.function_call({'name': 'run', 'arguments': {'CommandLine': 'x' * 300}})
    assert out.endswith('…`')
    assert len(out) < 220


def test_function_result_strips_markers() -> None:
    raw = '[STDOUT]\nhello\n[STDERR]\nwarn: thing'
    out = render.function_result({'result': {'Output': raw}})
    assert out == '```\nhello\nwarn: thing\n```'


def test_function_result_passthrough_when_no_markers() -> None:
    out = render.function_result({'result': {'Output': 'plain'}})
    assert out == '```\nplain\n```'


def test_function_result_empty() -> None:
    assert render.function_result({'result': {'Output': ''}}) == ''


def test_citations_dedupe_and_number() -> None:
    anns = [
        {'url_citation': {'url': 'https://a', 'title': 'A'}},
        {'url': 'https://a', 'title': 'dup'},
        {'uri': 'https://b'},
    ]
    out = render.citations(anns)
    assert out.startswith('**Sources**')
    assert out.count('https://a') == 1
    assert '1. [A](https://a)' in out
    assert '2. [https://b](https://b)' in out


def test_short_error() -> None:
    assert render.short_error('boom\ntrace') == 'boom'
    assert render.short_error('') == 'unknown error'
