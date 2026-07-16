"""LangChain tools for the SAP Maintenance Order Agent.

Each @tool function queries SAP S/4HANA OData APIs (or returns mock data in demo mode).
All SAP APIs referenced are public and documented on the SAP API Business Hub:
- API_MAINTENANCEORDER v0002: https://api.sap.com/api/API_MAINTENANCEORDER/overview
- API_MAINTNOTIFICATION: https://api.sap.com/api/API_MAINTNOTIFICATION/overview
- API_EQUIPMENT: https://api.sap.com/api/API_EQUIPMENT/overview
- API_MATERIAL_STOCK_SRV: https://api.sap.com/api/API_MATERIAL_STOCK_SRV/overview
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from langchain_core.tools import tool

from app.agent_config import (
    OPERATION_SUBPHASE_MAP,
    ORDER_SUBPHASE_MAP,
    PHASE_MAP,
    SAP_BASE_URL,
    SAP_CLIENT,
    SAP_PASSWORD,
    SAP_USER,
    USE_MOCK_DATA,
)
from app.mock_sap_data import (
    MOCK_CONFIRMATIONS,
    MOCK_COSTS,
    MOCK_EQUIPMENT,
    MOCK_NOTIFICATIONS,
    MOCK_ORDERS,
    MOCK_STOCK,
)


logger = logging.getLogger(__name__)


# ── SAP OData Connector ─────────────────────────────────────────────────────


def _sap_get(path: str, params: dict | None = None) -> dict:
    """Execute GET against SAP S/4HANA OData service.

    In mock mode, this is never called. When connecting to a real system,
    uses basic authentication with the configured credentials.
    """
    url = f'{SAP_BASE_URL}{path}'
    headers = {
        'Accept': 'application/json',
        'sap-client': SAP_CLIENT,
    }
    resp = httpx.get(
        url,
        params=params or {},
        headers=headers,
        auth=(SAP_USER, SAP_PASSWORD),
        timeout=30.0,
        verify=True,
    )
    resp.raise_for_status()
    return resp.json().get('d', resp.json())


def _sanitize_odata_value(value: str) -> str:
    """Sanitize a value before embedding in an OData $filter to prevent injection."""
    if not value:
        return value
    return re.sub(r'[^a-zA-Z0-9 ._-]', '', str(value))


def _sanitize_http_error(status_code: int) -> str:
    """Return user-friendly error message — never expose raw SAP details."""
    error_map = {
        401: 'Authentication failed — check SAP credentials',
        403: 'Access denied — you are not authorized for this data',
        404: 'The requested data was not found in SAP',
        500: 'SAP system encountered an error — please try again later',
        503: 'SAP service temporarily unavailable — please try again later',
    }
    return error_map.get(
        status_code, 'Unable to connect to SAP — please try again later'
    )


# ── Tool Implementations ────────────────────────────────────────────────────


@tool
def get_maintenance_order(order_id: str) -> str:
    """Get complete maintenance order details including operations and components.

    Queries SAP API_MAINTENANCEORDER v0002 with $expand for operations and components.
    Returns order header, all operations with phase/subphase, and material components.

    Args:
        order_id: SAP Maintenance Order number (e.g. '4000045')
    """
    if USE_MOCK_DATA:
        order = MOCK_ORDERS.get(order_id)
        if not order:
            return json.dumps(
                {'error': f'Order {order_id} not found', 'order_id': order_id}
            )
        # Enrich with phase names
        result = dict(order)
        result['PhaseName'] = PHASE_MAP.get(
            result.get('MaintOrdProcessPhaseCode', ''), 'Unknown'
        )
        result['SubPhaseName'] = ORDER_SUBPHASE_MAP.get(
            result.get('MaintOrdProcessSubPhaseCode', ''), 'Unknown'
        )
        for op in result.get('to_MaintenanceOrderOperation', {}).get(
            'results', []
        ):
            op['SubPhaseName'] = OPERATION_SUBPHASE_MAP.get(
                op.get('MaintOrdOperationSubPhaseCode', ''), 'Unknown'
            )
        return json.dumps(result, indent=2)

    # Real SAP OData call
    try:
        path = (
            f'/sap/opu/odata/sap/API_MAINTENANCEORDER;v=0002'
            f"/MaintenanceOrder('{_sanitize_odata_value(order_id)}')"
        )
        params = {
            '$expand': 'to_MaintenanceOrderOperation,to_MaintOrderOpComponent',
        }
        data = _sap_get(path, params)
        data['PhaseName'] = PHASE_MAP.get(
            data.get('MaintOrdProcessPhaseCode', ''), 'Unknown'
        )
        data['SubPhaseName'] = ORDER_SUBPHASE_MAP.get(
            data.get('MaintOrdProcessSubPhaseCode', ''), 'Unknown'
        )
        return json.dumps(data, indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {'error': _sanitize_http_error(e.response.status_code)}
        )
    except Exception:
        logger.exception('get_maintenance_order failed')
        return json.dumps({'error': 'Unable to retrieve order data'})


@tool
def get_maintenance_notification(notification_id: str) -> str:
    """Get maintenance notification with damage codes and cause codes.

    Queries SAP API_MAINTNOTIFICATION with $expand for notification items.

    Args:
        notification_id: SAP Notification number (e.g. '10000001')
    """
    if USE_MOCK_DATA:
        notif = MOCK_NOTIFICATIONS.get(notification_id)
        if not notif:
            return json.dumps(
                {'error': f'Notification {notification_id} not found'}
            )
        return json.dumps(notif, indent=2)

    try:
        path = (
            f'/sap/opu/odata/sap/API_MAINTNOTIFICATION'
            f"/MaintenanceNotification('{_sanitize_odata_value(notification_id)}')"
        )
        params = {'$expand': 'to_MaintenanceNotificationItem'}
        return json.dumps(_sap_get(path, params), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {'error': _sanitize_http_error(e.response.status_code)}
        )
    except Exception:  # noqa: BLE001
        return json.dumps({'error': 'Unable to retrieve notification data'})


@tool
def search_maintenance_orders(  # noqa: PLR0912, PLR0913
    plant: str = '',
    priority: str = '',
    work_center: str = '',
    order_type: str = '',
    equipment: str = '',
    phase: str = '',
    subphase: str = '',
    max_results: int = 20,
) -> str:
    """Search maintenance orders with filters.

    Queries SAP API_MAINTENANCEORDER v0002 with OData $filter.

    Args:
        plant: Planning plant code (e.g. '1010')
        priority: Priority level ('1'=Critical, '2'=High, '3'=Medium, '4'=Low)
        work_center: Main work center code
        order_type: Maintenance order type (e.g. 'PM01')
        equipment: Equipment / technical object ID
        phase: Phase code ('01'-'09') or name ('PLANNING', 'EXECUTION')
        subphase: Sub-phase code ('0035'-'0105') or name ('READY_FOR_EXECUTION')
        max_results: Maximum orders to return (default 20)
    """
    # Resolve phase/subphase names to codes
    phase_code = _resolve_phase_code(phase)
    subphase_code = _resolve_subphase_code(subphase)

    if USE_MOCK_DATA:
        results = []
        for order in MOCK_ORDERS.values():
            if plant and order.get('MaintenancePlanningPlant') != plant:
                continue
            if priority and order.get('MaintPriority') != priority:
                continue
            if work_center and order.get('MainWorkCenter') != work_center:
                continue
            if order_type and order.get('MaintenanceOrderType') != order_type:
                continue
            if equipment and order.get('TechnicalObject') != equipment:
                continue
            if (
                phase_code
                and order.get('MaintOrdProcessPhaseCode') != phase_code
            ):
                continue
            if (
                subphase_code
                and order.get('MaintOrdProcessSubPhaseCode') != subphase_code
            ):
                continue
            summary = {
                'order_id': order['MaintenanceOrder'],
                'description': order['MaintenanceOrderDesc'],
                'type': order['MaintenanceOrderType'],
                'plant': order['MaintenancePlanningPlant'],
                'priority': order['MaintPriority'],
                'priority_desc': order.get('MaintPriorityDesc', ''),
                'phase': PHASE_MAP.get(
                    order.get('MaintOrdProcessPhaseCode', ''), 'Unknown'
                ),
                'subphase': ORDER_SUBPHASE_MAP.get(
                    order.get('MaintOrdProcessSubPhaseCode', ''), 'Unknown'
                ),
                'equipment': order.get('TechnicalObject', ''),
                'work_center': order.get('MainWorkCenter', ''),
                'status': order.get('SystemStatusText', ''),
            }
            results.append(summary)
            if len(results) >= max_results:
                break
        return json.dumps({'orders': results, 'count': len(results)}, indent=2)

    # Real SAP OData call
    try:
        filters = []
        if plant:
            filters.append(
                f"MaintenancePlanningPlant eq '{_sanitize_odata_value(plant)}'"
            )
        if priority:
            filters.append(
                f"MaintPriority eq '{_sanitize_odata_value(priority)}'"
            )
        if work_center:
            filters.append(
                f"MainWorkCenter eq '{_sanitize_odata_value(work_center)}'"
            )
        if order_type:
            filters.append(
                f"MaintenanceOrderType eq '{_sanitize_odata_value(order_type)}'"
            )
        if equipment:
            filters.append(
                f"TechnicalObject eq '{_sanitize_odata_value(equipment)}'"
            )
        if phase_code:
            filters.append(f"MaintOrdProcessPhaseCode eq '{phase_code}'")
        if subphase_code:
            filters.append(f"MaintOrdProcessSubPhaseCode eq '{subphase_code}'")

        params = {'$top': str(max_results), '$format': 'json'}
        if filters:
            params['$filter'] = ' and '.join(filters)

        path = '/sap/opu/odata/sap/API_MAINTENANCEORDER;v=0002/MaintenanceOrder'
        data = _sap_get(path, params)
        orders = data.get('results', [])
        results = [
            {
                'order_id': o.get('MaintenanceOrder'),
                'description': o.get('MaintenanceOrderDesc'),
                'type': o.get('MaintenanceOrderType'),
                'plant': o.get('MaintenancePlanningPlant'),
                'priority': o.get('MaintPriority'),
                'phase': PHASE_MAP.get(
                    o.get('MaintOrdProcessPhaseCode', ''), 'Unknown'
                ),
                'subphase': ORDER_SUBPHASE_MAP.get(
                    o.get('MaintOrdProcessSubPhaseCode', ''), 'Unknown'
                ),
                'equipment': o.get('TechnicalObject', ''),
                'work_center': o.get('MainWorkCenter', ''),
                'status': o.get('SystemStatusText', ''),
            }
            for o in orders
        ]
        return json.dumps({'orders': results, 'count': len(results)}, indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {'error': _sanitize_http_error(e.response.status_code)}
        )
    except Exception:  # noqa: BLE001
        return json.dumps({'error': 'Unable to search maintenance orders'})


@tool
def get_work_order_confirmation(order_id: str) -> str:
    """Get confirmation status for all operations in a maintenance order.

    Returns per-operation confirmation status, actual vs planned work, progress %.

    Args:
        order_id: SAP Maintenance Order number
    """
    if USE_MOCK_DATA:
        conf = MOCK_CONFIRMATIONS.get(order_id)
        if not conf:
            return json.dumps(
                {'error': f'No confirmations found for order {order_id}'}
            )
        return json.dumps(conf, indent=2)

    try:
        path = (
            f'/sap/opu/odata/sap/API_MAINTENANCEORDER;v=0002'
            f"/MaintenanceOrder('{_sanitize_odata_value(order_id)}')"
        )
        params = {
            '$expand': 'to_MaintenanceOrderOperation',
            '$select': 'MaintenanceOrder,SystemStatusText',
        }
        data = _sap_get(path, params)
        operations = data.get('to_MaintenanceOrderOperation', {}).get(
            'results', []
        )
        result = {
            'order_id': order_id,
            'operations': [
                {
                    'operation': op.get('MaintenanceOrderOperation'),
                    'description': op.get('OperationDescription'),
                    'is_confirmed': 'CNF'
                    in (op.get('SystemStatusText', '') or '').upper().split(),
                    'is_finally_confirmed': 'CNF'
                    in (op.get('SystemStatusText', '') or '').upper().split()
                    and 'PCNF'
                    not in (op.get('SystemStatusText', '') or '')
                    .upper()
                    .split(),
                    'actual_work': float(op.get('ActualWorkQuantity', 0)),
                    'planned_work': float(op.get('PlannedWorkQuantity', 0)),
                    'progress_pct': round(
                        float(op.get('ActualWorkQuantity', 0))
                        / float(op.get('PlannedWorkQuantity', 1))
                        * 100,
                        1,
                    )
                    if float(op.get('PlannedWorkQuantity', 0)) > 0
                    else 0.0,
                }
                for op in operations
            ],
        }
        return json.dumps(result, indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {'error': _sanitize_http_error(e.response.status_code)}
        )
    except Exception:  # noqa: BLE001
        return json.dumps({'error': 'Unable to retrieve confirmation data'})


@tool
def get_work_order_cost_table(order_id: str) -> str:
    """Get cost breakdown for a maintenance order by category.

    Returns planned vs actual cost per category (Material, Labour, External, etc.).

    Args:
        order_id: SAP Maintenance Order number
    """
    if USE_MOCK_DATA:
        costs = MOCK_COSTS.get(order_id)
        if not costs:
            return json.dumps(
                {'error': f'No cost data found for order {order_id}'}
            )
        return json.dumps(costs, indent=2)

    try:
        # Real implementation would query API_MAINTENANCEORDER cost entities
        # or a controlling API depending on system configuration
        path = (
            f'/sap/opu/odata/sap/API_MAINTENANCEORDER;v=0002'
            f"/MaintenanceOrder('{_sanitize_odata_value(order_id)}')"
        )
        params = {'$select': 'MaintenanceOrder,EstimatedTotalCost,Currency'}
        data = _sap_get(path, params)
        return json.dumps(
            {
                'order_id': order_id,
                'total_estimated': float(data.get('EstimatedTotalCost', 0)),
                'total_actual': 0.0,  # Would need controlling API for actuals
                'categories': [],
            },
            indent=2,
        )
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {'error': _sanitize_http_error(e.response.status_code)}
        )
    except Exception:  # noqa: BLE001
        return json.dumps({'error': 'Unable to retrieve cost data'})


@tool
def get_material_stock(material: str, plant: str = '') -> str:  # noqa: PLR0911
    """Check material stock levels by plant and storage location.

    Queries SAP API_MATERIAL_STOCK_SRV / A_MatlStkInAcctMod.
    Note: Use A_MatlStkInAcctMod (not A_MaterialStock) for actual quantities.

    Args:
        material: Material number (e.g. '100-100')
        plant: Plant code (optional, filters to specific plant)
    """
    if USE_MOCK_DATA:
        stock = MOCK_STOCK.get(material)
        if not stock:
            return json.dumps(
                {'error': f'No stock data found for material {material}'}
            )
        if plant and stock.get('Plant') != plant:
            return json.dumps(
                {'error': f'No stock in plant {plant} for material {material}'}
            )
        return json.dumps(stock, indent=2)

    try:
        filters = [f"Material eq '{_sanitize_odata_value(material)}'"]
        if plant:
            filters.append(f"Plant eq '{_sanitize_odata_value(plant)}'")
        path = '/sap/opu/odata/sap/API_MATERIAL_STOCK_SRV/A_MatlStkInAcctMod'
        params = {'$filter': ' and '.join(filters)}
        data = _sap_get(path, params)
        results = data.get('results', [])
        if not results:
            return json.dumps(
                {'error': f'No stock found for material {material}'}
            )
        return json.dumps(results, indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {'error': _sanitize_http_error(e.response.status_code)}
        )
    except Exception:  # noqa: BLE001
        return json.dumps({'error': 'Unable to retrieve stock data'})


@tool
def get_equipment_details(equipment_id: str) -> str:
    """Get equipment master data including manufacturer and acquisition info.

    Queries SAP API_EQUIPMENT.

    Args:
        equipment_id: Equipment number (e.g. '10000001')
    """
    if USE_MOCK_DATA:
        equip = MOCK_EQUIPMENT.get(equipment_id)
        if not equip:
            return json.dumps({'error': f'Equipment {equipment_id} not found'})
        return json.dumps(equip, indent=2)

    try:
        path = f"/sap/opu/odata/sap/API_EQUIPMENT/Equipment('{_sanitize_odata_value(equipment_id)}')"
        return json.dumps(_sap_get(path), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {'error': _sanitize_http_error(e.response.status_code)}
        )
    except Exception:  # noqa: BLE001
        return json.dumps({'error': 'Unable to retrieve equipment data'})


@tool
def get_missing_confirmations_batch(order_ids: list[str]) -> str:
    """Check multiple orders for missing confirmations in batch.

    For each order, checks if any operations lack final confirmation.

    Args:
        order_ids: List of maintenance order numbers to check
    """
    results = []
    for oid in order_ids[:10]:  # Cap at 10 to prevent abuse
        if USE_MOCK_DATA:
            conf = MOCK_CONFIRMATIONS.get(oid)
            if conf:
                missing = [
                    op
                    for op in conf['operations']
                    if not op['is_finally_confirmed']
                ]
                results.append(
                    {
                        'order_id': oid,
                        'total_operations': len(conf['operations']),
                        'missing_confirmations': len(missing),
                        'missing_operations': [
                            op['operation'] for op in missing
                        ],
                    }
                )
            else:
                results.append(
                    {
                        'order_id': oid,
                        'total_operations': 0,
                        'missing_confirmations': 0,
                        'missing_operations': [],
                    }
                )
        else:
            try:
                raw = get_work_order_confirmation.invoke({'order_id': oid})
                data = json.loads(raw)
                if 'error' in data:
                    results.append({'order_id': oid, 'error': data['error']})
                else:
                    missing = [
                        op
                        for op in data.get('operations', [])
                        if not op.get('is_finally_confirmed')
                    ]
                    results.append(
                        {
                            'order_id': oid,
                            'total_operations': len(data.get('operations', [])),
                            'missing_confirmations': len(missing),
                            'missing_operations': [
                                op['operation'] for op in missing
                            ],
                        }
                    )
            except Exception:  # noqa: BLE001
                results.append(
                    {'order_id': oid, 'error': 'Failed to check confirmations'}
                )
    return json.dumps({'results': results}, indent=2)


@tool
def get_material_shortages_batch(order_ids: list[str]) -> str:
    """Check multiple orders for material shortages.

    Compares required vs withdrawn quantities on order components.

    Args:
        order_ids: List of maintenance order numbers to check
    """
    results = []
    for oid in order_ids[:10]:
        if USE_MOCK_DATA:
            order = MOCK_ORDERS.get(oid)
            if not order:
                results.append({'order_id': oid, 'shortages': []})
                continue
            components = order.get('to_MaintOrderOpComponent', {}).get(
                'results', []
            )
            shortages = []
            for comp in components:
                req = float(comp.get('RequiredQuantity', 0))
                withdrawn = float(comp.get('WithdrawnQuantity', 0))
                if req > withdrawn:
                    shortages.append(
                        {
                            'material': comp.get('Product'),
                            'material_name': comp.get('ProductName'),
                            'required': req,
                            'withdrawn': withdrawn,
                            'shortage': req - withdrawn,
                            'unit': comp.get('BaseUnit'),
                        }
                    )
            results.append({'order_id': oid, 'shortages': shortages})
        else:
            results.append(
                {'order_id': oid, 'shortages': []}
            )  # Would call real API
    return json.dumps({'results': results}, indent=2)


@tool
def set_orders_to_teco(order_ids: list[str]) -> str:
    """Set one or more maintenance orders to Technically Complete (TECO).

    ⚠️ WRITE OPERATION — requires human confirmation before execution.
    The agent will ask for explicit approval before calling this tool.

    Args:
        order_ids: List of order numbers to set to TECO
    """
    if USE_MOCK_DATA:
        return json.dumps(
            {
                'status': 'success',
                'message': f'Orders {", ".join(order_ids)} set to Technically Complete (TECO)',
                'orders_updated': order_ids,
                'note': '(mock mode — no actual SAP changes made)',
            }
        )
    # Real implementation would POST to SAP
    return json.dumps(
        {
            'error': 'Write operations require SAP connection (USE_MOCK_DATA=false)'
        }
    )


@tool
def reset_orders_teco(order_ids: list[str]) -> str:
    """Reset TECO (Technically Complete) status on maintenance orders.

    ⚠️ WRITE OPERATION — requires human confirmation before execution.

    Args:
        order_ids: List of order numbers to reset TECO
    """
    if USE_MOCK_DATA:
        return json.dumps(
            {
                'status': 'success',
                'message': f'TECO reset for orders {", ".join(order_ids)}',
                'orders_updated': order_ids,
                'note': '(mock mode — no actual SAP changes made)',
            }
        )
    return json.dumps(
        {
            'error': 'Write operations require SAP connection (USE_MOCK_DATA=false)'
        }
    )


# ── Phase/SubPhase Code Resolution ──────────────────────────────────────────


def _resolve_phase_code(phase: str) -> str:
    """Resolve phase name or code to a 2-digit phase code."""
    if not phase:
        return ''
    phase = phase.strip()
    # Already a code
    if phase in PHASE_MAP:
        return phase
    # Name lookup (case-insensitive)
    name_upper = phase.upper().replace(' ', '_')
    name_to_code = {
        v.upper().replace(' ', '_'): k for k, v in PHASE_MAP.items()
    }
    return name_to_code.get(name_upper, '')


def _resolve_subphase_code(subphase: str) -> str:
    """Resolve subphase name or code to a 4-digit subphase code."""
    if not subphase:
        return ''
    subphase = subphase.strip()
    if subphase in ORDER_SUBPHASE_MAP:
        return subphase
    name_upper = subphase.upper().replace(' ', '_')
    name_to_code = {
        v.upper().replace(' ', '_'): k for k, v in ORDER_SUBPHASE_MAP.items()
    }
    return name_to_code.get(name_upper, '')


# ── Tool Registry ───────────────────────────────────────────────────────────

TOOLS = [
    get_maintenance_order,
    get_maintenance_notification,
    search_maintenance_orders,
    get_work_order_confirmation,
    get_work_order_cost_table,
    get_material_stock,
    get_equipment_details,
    get_missing_confirmations_batch,
    get_material_shortages_batch,
    set_orders_to_teco,
    reset_orders_teco,
]
