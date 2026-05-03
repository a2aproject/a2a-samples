"""Mock SAP OData responses for demo/testing without a real S/4HANA system.

All data uses public field names from the SAP API Business Hub:
- API_MAINTENANCEORDER v0002
- API_MAINTNOTIFICATION
- API_EQUIPMENT
- API_MATERIAL_STOCK_SRV
- API_PURCHASEORDER_PROCESS_SRV

No real system data or credentials are used.
"""

from __future__ import annotations

# ── Maintenance Orders ───────────────────────────────────────────────────────

MOCK_ORDERS = {
    "4000045": {
        "MaintenanceOrder": "4000045",
        "MaintenanceOrderDesc": "Pump bearing replacement — Unit P-101",
        "MaintenanceOrderType": "PM01",
        "MaintenancePlanningPlant": "1010",
        "MainWorkCenter": "MECH_WC",
        "MaintPriority": "1",
        "MaintPriorityDesc": "Critical",
        "MaintOrdProcessPhaseCode": "07",
        "MaintOrdProcessSubPhaseCode": "0070",
        "TechnicalObject": "10000001",
        "TechnicalObjectLabel": "Centrifugal Pump P-101",
        "FunctionalLocation": "FN-1010-PP-001",
        "MaintOrdBasicStartDate": "2026-04-20",
        "MaintOrdBasicEndDate": "2026-04-28",
        "SystemStatusText": "REL MANC PCNF",
        "MaintOrderCreationDateTime": "/Date(1745107200000)/",
        "EstimatedTotalCost": "8500.00",
        "Currency": "USD",
        "to_MaintenanceOrderOperation": {
            "results": [
                {
                    "MaintenanceOrder": "4000045",
                    "MaintenanceOrderOperation": "0010",
                    "OperationDescription": "Isolate pump and lock-out/tag-out",
                    "OperationControlKey": "PM01",
                    "PlannedWorkQuantity": "2.0",
                    "ActualWorkQuantity": "2.0",
                    "WorkCenter": "MECH_WC",
                    "MaintOrdOperationSubPhaseCode": "0140",
                    "SystemStatusText": "REL CNF",
                },
                {
                    "MaintenanceOrder": "4000045",
                    "MaintenanceOrderOperation": "0020",
                    "OperationDescription": "Remove and replace bearing assembly",
                    "OperationControlKey": "PM01",
                    "PlannedWorkQuantity": "6.0",
                    "ActualWorkQuantity": "4.5",
                    "WorkCenter": "MECH_WC",
                    "MaintOrdOperationSubPhaseCode": "0130",
                    "SystemStatusText": "REL PCNF",
                },
                {
                    "MaintenanceOrder": "4000045",
                    "MaintenanceOrderOperation": "0030",
                    "OperationDescription": "Alignment check and test run",
                    "OperationControlKey": "PM01",
                    "PlannedWorkQuantity": "3.0",
                    "ActualWorkQuantity": "0.0",
                    "WorkCenter": "MECH_WC",
                    "MaintOrdOperationSubPhaseCode": "0125",
                    "SystemStatusText": "REL",
                },
            ]
        },
        "to_MaintOrderOpComponent": {
            "results": [
                {
                    "Product": "100-100",
                    "ProductName": "Ball Bearing 6205-2RS",
                    "RequiredQuantity": "2.000",
                    "WithdrawnQuantity": "2.000",
                    "BaseUnit": "EA",
                },
                {
                    "Product": "100-200",
                    "ProductName": "Mechanical Seal Kit",
                    "RequiredQuantity": "1.000",
                    "WithdrawnQuantity": "0.000",
                    "BaseUnit": "EA",
                },
            ]
        },
    },
    "4000046": {
        "MaintenanceOrder": "4000046",
        "MaintenanceOrderDesc": "Conveyor belt tensioner adjustment — Line C3",
        "MaintenanceOrderType": "PM02",
        "MaintenancePlanningPlant": "1010",
        "MainWorkCenter": "MECH_WC",
        "MaintPriority": "2",
        "MaintPriorityDesc": "High",
        "MaintOrdProcessPhaseCode": "07",
        "MaintOrdProcessSubPhaseCode": "0075",
        "TechnicalObject": "10000002",
        "TechnicalObjectLabel": "Belt Conveyor C3-200",
        "FunctionalLocation": "FN-1010-PP-002",
        "MaintOrdBasicStartDate": "2026-04-22",
        "MaintOrdBasicEndDate": "2026-04-25",
        "SystemStatusText": "REL MANC CNF",
        "MaintOrderCreationDateTime": "/Date(1745280000000)/",
        "EstimatedTotalCost": "3200.00",
        "Currency": "USD",
        "to_MaintenanceOrderOperation": {
            "results": [
                {
                    "MaintenanceOrder": "4000046",
                    "MaintenanceOrderOperation": "0010",
                    "OperationDescription": "Inspect tensioner and idler rollers",
                    "OperationControlKey": "PM01",
                    "PlannedWorkQuantity": "1.5",
                    "ActualWorkQuantity": "1.5",
                    "WorkCenter": "MECH_WC",
                    "MaintOrdOperationSubPhaseCode": "0140",
                    "SystemStatusText": "REL CNF",
                },
                {
                    "MaintenanceOrder": "4000046",
                    "MaintenanceOrderOperation": "0020",
                    "OperationDescription": "Adjust belt tension to spec",
                    "OperationControlKey": "PM01",
                    "PlannedWorkQuantity": "2.0",
                    "ActualWorkQuantity": "2.0",
                    "WorkCenter": "MECH_WC",
                    "MaintOrdOperationSubPhaseCode": "0140",
                    "SystemStatusText": "REL CNF",
                },
            ]
        },
        "to_MaintOrderOpComponent": {"results": []},
    },
    "4000047": {
        "MaintenanceOrder": "4000047",
        "MaintenanceOrderDesc": "HVAC chiller annual maintenance — Building A",
        "MaintenanceOrderType": "PM03",
        "MaintenancePlanningPlant": "1020",
        "MainWorkCenter": "ELEC_WC",
        "MaintPriority": "3",
        "MaintPriorityDesc": "Medium",
        "MaintOrdProcessPhaseCode": "03",
        "MaintOrdProcessSubPhaseCode": "0035",
        "TechnicalObject": "10000003",
        "TechnicalObjectLabel": "Chiller Unit CH-A01",
        "FunctionalLocation": "FN-1020-BL-A",
        "MaintOrdBasicStartDate": "2026-05-01",
        "MaintOrdBasicEndDate": "2026-05-10",
        "SystemStatusText": "CRTD",
        "MaintOrderCreationDateTime": "/Date(1745884800000)/",
        "EstimatedTotalCost": "12000.00",
        "Currency": "USD",
        "to_MaintenanceOrderOperation": {
            "results": [
                {
                    "MaintenanceOrder": "4000047",
                    "MaintenanceOrderOperation": "0010",
                    "OperationDescription": "Refrigerant pressure check",
                    "OperationControlKey": "PM01",
                    "PlannedWorkQuantity": "4.0",
                    "ActualWorkQuantity": "0.0",
                    "WorkCenter": "ELEC_WC",
                    "MaintOrdOperationSubPhaseCode": "0110",
                    "SystemStatusText": "CRTD",
                },
            ]
        },
        "to_MaintOrderOpComponent": {
            "results": [
                {
                    "Product": "100-300",
                    "ProductName": "R-410A Refrigerant",
                    "RequiredQuantity": "5.000",
                    "WithdrawnQuantity": "0.000",
                    "BaseUnit": "KG",
                },
            ]
        },
    },
}

# ── Notifications ────────────────────────────────────────────────────────────

MOCK_NOTIFICATIONS = {
    "10000001": {
        "MaintenanceNotification": "10000001",
        "NotificationType": "M2",
        "NotificationText": "Excessive vibration detected on pump P-101",
        "TechnicalObject": "10000001",
        "FunctionalLocation": "FN-1010-PP-001",
        "MaintenanceOrder": "4000045",
        "to_MaintenanceNotificationItem": {
            "results": [
                {
                    "MaintNotifItemText": "Bearing failure — inner race spalling",
                    "MaintNotifDamageCodeGroup": "PM-PUMP",
                    "MaintNotifDamageCode": "BEAR-FAIL",
                    "MaintNotifCauseCodeGroup": "PM-WEAR",
                    "MaintNotifCauseCode": "FATIGUE",
                    "MaintNotifObjPartCodeGroup": "PM-PUMP",
                    "MaintNotifObjPartCode": "BEARING",
                }
            ]
        },
    },
}

# ── Equipment ────────────────────────────────────────────────────────────────

MOCK_EQUIPMENT = {
    "10000001": {
        "Equipment": "10000001",
        "EquipmentName": "Centrifugal Pump P-101",
        "EquipmentCategory": "M",
        "TechnicalObjectType": "PUMP",
        "MaintenancePlant": "1010",
        "FunctionalLocation": "FN-1010-PP-001",
        "Manufacturer": "Grundfos",
        "ManufacturerCountry": "DK",
        "ConstructionYear": "2019",
        "AcquisitionDate": "2019-03-15",
        "AcquisitionValue": "45000.00",
        "Currency": "USD",
    },
    "10000002": {
        "Equipment": "10000002",
        "EquipmentName": "Belt Conveyor C3-200",
        "EquipmentCategory": "M",
        "TechnicalObjectType": "CONV",
        "MaintenancePlant": "1010",
        "FunctionalLocation": "FN-1010-PP-002",
        "Manufacturer": "Siemens",
        "ManufacturerCountry": "DE",
        "ConstructionYear": "2020",
        "AcquisitionDate": "2020-06-01",
        "AcquisitionValue": "120000.00",
        "Currency": "USD",
    },
}

# ── Material Stock ───────────────────────────────────────────────────────────

MOCK_STOCK = {
    "100-100": {
        "Material": "100-100",
        "MaterialName": "Ball Bearing 6205-2RS",
        "Plant": "1010",
        "StorageLocation": "WH01",
        "MatlWrhsStkQtyInMatlBaseUnit": "15.000",
        "MaterialBaseUnit": "EA",
    },
    "100-200": {
        "Material": "100-200",
        "MaterialName": "Mechanical Seal Kit",
        "Plant": "1010",
        "StorageLocation": "WH01",
        "MatlWrhsStkQtyInMatlBaseUnit": "3.000",
        "MaterialBaseUnit": "EA",
    },
    "100-300": {
        "Material": "100-300",
        "MaterialName": "R-410A Refrigerant",
        "Plant": "1020",
        "StorageLocation": "WH02",
        "MatlWrhsStkQtyInMatlBaseUnit": "25.000",
        "MaterialBaseUnit": "KG",
    },
}

# ── Cost Data ────────────────────────────────────────────────────────────────

MOCK_COSTS = {
    "4000045": {
        "order_id": "4000045",
        "total_estimated": 8500.00,
        "total_actual": 5200.00,
        "categories": [
            {"CostElement": "Material", "PlannedCost": 3000.00, "ActualCost": 1800.00, "Currency": "USD"},
            {"CostElement": "Labour", "PlannedCost": 4000.00, "ActualCost": 2400.00, "Currency": "USD"},
            {"CostElement": "External", "PlannedCost": 1500.00, "ActualCost": 1000.00, "Currency": "USD"},
        ],
    },
    "4000046": {
        "order_id": "4000046",
        "total_estimated": 3200.00,
        "total_actual": 2900.00,
        "categories": [
            {"CostElement": "Material", "PlannedCost": 800.00, "ActualCost": 750.00, "Currency": "USD"},
            {"CostElement": "Labour", "PlannedCost": 2400.00, "ActualCost": 2150.00, "Currency": "USD"},
        ],
    },
}

# ── Confirmations ────────────────────────────────────────────────────────────

MOCK_CONFIRMATIONS = {
    "4000045": {
        "order_id": "4000045",
        "operations": [
            {
                "operation": "0010",
                "description": "Isolate pump and lock-out/tag-out",
                "is_confirmed": True,
                "is_finally_confirmed": True,
                "actual_work": 2.0,
                "planned_work": 2.0,
                "progress_pct": 100.0,
            },
            {
                "operation": "0020",
                "description": "Remove and replace bearing assembly",
                "is_confirmed": True,
                "is_finally_confirmed": False,
                "actual_work": 4.5,
                "planned_work": 6.0,
                "progress_pct": 75.0,
            },
            {
                "operation": "0030",
                "description": "Alignment check and test run",
                "is_confirmed": False,
                "is_finally_confirmed": False,
                "actual_work": 0.0,
                "planned_work": 3.0,
                "progress_pct": 0.0,
            },
        ],
    },
}

# ── Purchase Orders ──────────────────────────────────────────────────────────

MOCK_PURCHASE_ORDERS = {
    "4500001": {
        "PurchaseOrder": "4500001",
        "PurchaseOrderType": "NB",
        "Supplier": "VENDOR-001",
        "SupplierName": "Industrial Bearings Co.",
        "PurchaseOrderDate": "2026-04-18",
        "items": [
            {
                "PurchaseOrderItem": "10",
                "Material": "100-100",
                "MaterialName": "Ball Bearing 6205-2RS",
                "OrderQuantity": "4.000",
                "NetPriceAmount": "120.00",
                "Currency": "USD",
                "MaintenanceOrder": "4000045",
            }
        ],
    },
}
