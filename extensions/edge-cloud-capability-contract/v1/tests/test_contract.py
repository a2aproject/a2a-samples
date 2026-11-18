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

# ruff: noqa: INP001, S101

import importlib.util

from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / 'contract.py'
SPEC = importlib.util.spec_from_file_location('edge_cloud_contract', MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
contract_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract_module)

ContractMismatchError = contract_module.ContractMismatchError
select_execution_site = contract_module.select_execution_site


@pytest.fixture
def contract():
    return {
        'version': '1.0',
        'executionSites': [
            {
                'id': 'device',
                'type': 'edge',
                'region': 'customer-premises',
                'p95LatencyMs': 20,
                'offlineCapable': True,
                'acceptedDataClassifications': ['public', 'restricted'],
            },
            {
                'id': 'cloud-cn-hangzhou',
                'type': 'cloud',
                'region': 'cn-hangzhou',
                'p95LatencyMs': 80,
                'offlineCapable': False,
                'acceptedDataClassifications': ['public'],
            },
        ],
        'sideEffects': {
            'kind': 'external_write',
            'supportsIdempotencyKey': True,
        },
        'attestationMethods': ['tpm-quote'],
        'verificationMethods': ['sha256-result'],
    }


def test_selects_lowest_latency_compatible_site(contract):
    selected = select_execution_site(
        contract,
        {
            'dataClassification': 'public',
            'allowedSiteTypes': ['edge', 'cloud'],
            'maxLatencyMs': 100,
            'idempotencyKey': 'task-42',
        },
    )
    assert selected['id'] == 'device'


def test_offline_and_residency_constraints_keep_task_at_edge(contract):
    selected = select_execution_site(
        contract,
        {
            'dataClassification': 'restricted',
            'allowedSiteTypes': ['edge'],
            'allowedRegions': ['customer-premises'],
            'maxLatencyMs': 30,
            'networkMode': 'offline',
            'idempotencyKey': 'task-42',
            'requiredAttestation': ['tpm-quote'],
            'requiredVerification': ['sha256-result'],
        },
    )
    assert selected['id'] == 'device'


@pytest.mark.parametrize(
    'overrides, match',
    [
        ({'allowedRegions': ['eu-west'], 'idempotencyKey': 'task-42'}, 'no execution'),
        ({'maxLatencyMs': 10, 'idempotencyKey': 'task-42'}, 'no execution'),
        ({'requiredAttestation': ['sgx-quote'], 'idempotencyKey': 'task-42'}, 'attestation'),
        ({'requiredVerification': ['human-review'], 'idempotencyKey': 'task-42'}, 'verification'),
        ({}, 'idempotencyKey'),
    ],
)
def test_rejects_before_execution_when_constraints_cannot_be_met(
    contract,
    overrides,
    match,
):
    requirements = {
        'dataClassification': 'public',
        'maxLatencyMs': 100,
        **overrides,
    }
    with pytest.raises(ContractMismatchError, match=match):
        select_execution_site(contract, requirements)
