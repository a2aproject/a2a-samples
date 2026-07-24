# Copyright 2026 The A2A Project Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ruff: noqa: INP001, PLR0912

"""Fail-closed reference matcher for the edge-cloud capability contract."""

from collections.abc import Mapping, Sequence
from typing import Any


EXTENSION_URI = (
    'https://github.com/a2aproject/a2a-samples/extensions/edge-cloud-capability-contract/v1'
)


class ContractMismatchError(ValueError):
    """Raised when no declared execution site satisfies the requirements."""


def _string_set(value: Any, field: str) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ContractMismatchError(f'{field} must be an array of strings')
    result = set(value)
    if not result or not all(isinstance(item, str) and item for item in result):
        raise ContractMismatchError(f'{field} must be a non-empty array of strings')
    return result


def select_execution_site(
    contract: Mapping[str, Any],
    requirements: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Return the lowest-latency compatible site, or fail before execution."""
    if contract.get('version') != '1.0':
        raise ContractMismatchError('unsupported contract version')

    sites = contract.get('executionSites')
    if not isinstance(sites, list) or not sites:
        raise ContractMismatchError('contract must declare executionSites')

    data_classification = requirements.get('dataClassification')
    if not isinstance(data_classification, str) or not data_classification:
        raise ContractMismatchError('dataClassification is required')

    allowed_site_types = _string_set(
        requirements.get('allowedSiteTypes', ['edge', 'cloud']),
        'allowedSiteTypes',
    )
    allowed_regions = requirements.get('allowedRegions')
    if allowed_regions is not None:
        allowed_regions = _string_set(allowed_regions, 'allowedRegions')

    max_latency_ms = requirements.get('maxLatencyMs')
    if not isinstance(max_latency_ms, int) or isinstance(max_latency_ms, bool):
        raise ContractMismatchError('maxLatencyMs must be an integer')
    if max_latency_ms <= 0:
        raise ContractMismatchError('maxLatencyMs must be positive')

    required_attestation = set(requirements.get('requiredAttestation', []))
    required_verification = set(requirements.get('requiredVerification', []))
    supported_attestation = set(contract.get('attestationMethods', []))
    supported_verification = set(contract.get('verificationMethods', []))
    if not required_attestation.issubset(supported_attestation):
        raise ContractMismatchError('required attestation is not supported')
    if not required_verification.issubset(supported_verification):
        raise ContractMismatchError('required result verification is not supported')

    side_effects = contract.get('sideEffects', {})
    if side_effects.get('kind') != 'none':
        if not side_effects.get('supportsIdempotencyKey', False):
            raise ContractMismatchError('side-effecting capability is not replay-safe')
        if not requirements.get('idempotencyKey'):
            raise ContractMismatchError('idempotencyKey is required for side effects')

    network_mode = requirements.get('networkMode', 'connected')
    candidates: list[Mapping[str, Any]] = []
    for site in sites:
        if not isinstance(site, Mapping):
            raise ContractMismatchError('executionSites entries must be objects')
        if site.get('type') not in allowed_site_types:
            continue
        if allowed_regions is not None and site.get('region') not in allowed_regions:
            continue
        if data_classification not in site.get('acceptedDataClassifications', []):
            continue
        latency_ms = site.get('p95LatencyMs')
        if (
            not isinstance(latency_ms, int)
            or isinstance(latency_ms, bool)
            or latency_ms <= 0
            or latency_ms > max_latency_ms
        ):
            continue
        if network_mode == 'offline' and not site.get('offlineCapable', False):
            continue
        candidates.append(site)

    if not candidates:
        raise ContractMismatchError('no execution site satisfies all requirements')
    return min(candidates, key=lambda site: (site['p95LatencyMs'], site['id']))
