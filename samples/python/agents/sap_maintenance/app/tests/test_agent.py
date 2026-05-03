"""Tests for the SAP Maintenance Order Agent."""

# ruff: noqa: S101, PLR2004

import json

from app.tool_policy import WRITE_TOOLS, ToolPolicyEngine
from app.tools import (
    _resolve_phase_code,
    _resolve_subphase_code,
    get_equipment_details,
    get_maintenance_notification,
    get_maintenance_order,
    get_material_shortages_batch,
    get_material_stock,
    get_missing_confirmations_batch,
    get_work_order_confirmation,
    get_work_order_cost_table,
    reset_orders_teco,
    search_maintenance_orders,
    set_orders_to_teco,
)


# ── Tool Tests (Mock Mode) ──────────────────────────────────────────────────


class TestGetMaintenanceOrder:
    def test_existing_order(self):
        result = json.loads(
            get_maintenance_order.invoke({'order_id': '4000045'})
        )
        assert result['MaintenanceOrder'] == '4000045'
        assert result['PhaseName'] == 'Execution'
        assert result['SubPhaseName'] == 'Main Work Started'
        assert len(result['to_MaintenanceOrderOperation']['results']) == 3
        assert len(result['to_MaintOrderOpComponent']['results']) == 2

    def test_nonexistent_order(self):
        result = json.loads(
            get_maintenance_order.invoke({'order_id': '9999999'})
        )
        assert 'error' in result

    def test_operations_have_subphase(self):
        result = json.loads(
            get_maintenance_order.invoke({'order_id': '4000045'})
        )
        ops = result['to_MaintenanceOrderOperation']['results']
        assert ops[0]['SubPhaseName'] == 'Work Finished'
        assert ops[1]['SubPhaseName'] == 'Work in Execution'
        assert ops[2]['SubPhaseName'] == 'Ready for Execution'


class TestSearchOrders:
    def test_search_by_plant(self):
        result = json.loads(search_maintenance_orders.invoke({'plant': '1010'}))
        assert result['count'] == 2
        assert all(o['plant'] == '1010' for o in result['orders'])

    def test_search_by_priority(self):
        result = json.loads(search_maintenance_orders.invoke({'priority': '1'}))
        assert result['count'] == 1
        assert result['orders'][0]['order_id'] == '4000045'

    def test_search_no_filters(self):
        result = json.loads(search_maintenance_orders.invoke({}))
        assert result['count'] == 3

    def test_search_by_phase_name(self):
        result = json.loads(
            search_maintenance_orders.invoke({'phase': 'EXECUTION'})
        )
        assert result['count'] == 2

    def test_search_by_phase_code(self):
        result = json.loads(search_maintenance_orders.invoke({'phase': '03'}))
        assert result['count'] == 1
        assert result['orders'][0]['order_id'] == '4000047'


class TestConfirmations:
    def test_get_confirmations(self):
        result = json.loads(
            get_work_order_confirmation.invoke({'order_id': '4000045'})
        )
        assert result['order_id'] == '4000045'
        assert len(result['operations']) == 3
        assert result['operations'][0]['progress_pct'] == 100.0
        assert result['operations'][2]['progress_pct'] == 0.0

    def test_missing_confirmations_batch(self):
        result = json.loads(
            get_missing_confirmations_batch.invoke({'order_ids': ['4000045']})
        )
        assert result['results'][0]['missing_confirmations'] == 2


class TestCosts:
    def test_get_costs(self):
        result = json.loads(
            get_work_order_cost_table.invoke({'order_id': '4000045'})
        )
        assert result['total_estimated'] == 8500.0
        assert len(result['categories']) == 3


class TestMaterialStock:
    def test_existing_material(self):
        result = json.loads(get_material_stock.invoke({'material': '100-100'}))
        assert result['Material'] == '100-100'
        assert float(result['MatlWrhsStkQtyInMatlBaseUnit']) == 15.0

    def test_nonexistent_material(self):
        result = json.loads(get_material_stock.invoke({'material': '999-999'}))
        assert 'error' in result


class TestEquipment:
    def test_get_equipment(self):
        result = json.loads(
            get_equipment_details.invoke({'equipment_id': '10000001'})
        )
        assert result['EquipmentName'] == 'Centrifugal Pump P-101'
        assert result['Manufacturer'] == 'Grundfos'


class TestNotification:
    def test_get_notification(self):
        result = json.loads(
            get_maintenance_notification.invoke({'notification_id': '10000001'})
        )
        items = result['to_MaintenanceNotificationItem']['results']
        assert items[0]['MaintNotifDamageCode'] == 'BEAR-FAIL'


class TestShortages:
    def test_shortage_detection(self):
        result = json.loads(
            get_material_shortages_batch.invoke({'order_ids': ['4000045']})
        )
        shortages = result['results'][0]['shortages']
        assert len(shortages) == 1
        assert shortages[0]['material'] == '100-200'
        assert shortages[0]['shortage'] == 1.0


class TestWriteTools:
    def test_teco_mock(self):
        result = json.loads(
            set_orders_to_teco.invoke({'order_ids': ['4000045']})
        )
        assert result['status'] == 'success'

    def test_unteco_mock(self):
        result = json.loads(
            reset_orders_teco.invoke({'order_ids': ['4000045']})
        )
        assert result['status'] == 'success'


# ── Phase/SubPhase Resolution ───────────────────────────────────────────────


class TestPhaseResolution:
    def test_code_passthrough(self):
        assert _resolve_phase_code('07') == '07'

    def test_name_to_code(self):
        assert _resolve_phase_code('EXECUTION') == '07'
        assert _resolve_phase_code('Planning') == '03'

    def test_empty(self):
        assert _resolve_phase_code('') == ''

    def test_subphase_code(self):
        assert _resolve_subphase_code('0065') == '0065'

    def test_subphase_name(self):
        assert _resolve_subphase_code('READY_FOR_EXECUTION') == '0065'


# ── Tool Policy ─────────────────────────────────────────────────────────────


class TestToolPolicy:
    def test_read_always_allowed(self):
        engine = ToolPolicyEngine()
        assert engine.evaluate('get_maintenance_order').allowed

    def test_write_tools_identified(self):
        assert 'set_orders_to_teco' in WRITE_TOOLS
        assert 'reset_orders_teco' in WRITE_TOOLS
        assert 'get_maintenance_order' not in WRITE_TOOLS
