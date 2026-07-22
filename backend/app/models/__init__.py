"""
DCBrain Models Package
Import all models so SQLAlchemy can discover them for table creation.
"""

from app.models.equipment import Equipment, Vendor, Zone, EquipmentStatus, EquipmentCategory
from app.models.compliance import Specification, PurchaseOrder, NCR, NCRSeverity, NCRStatus
from app.models.schedule import ScheduleTask, TaskDependency, TaskStatus
from app.models.supply_chain import Shipment, ShipmentStatus
from app.models.commissioning import CommissioningTest, TestResult, TestCategory
from app.models.knowledge import ProjectDocument, RFI, CascadeEvent, RFIStatus, RFIPriority

__all__ = [
    # Equipment
    "Equipment", "Vendor", "Zone", "EquipmentStatus", "EquipmentCategory",
    # Compliance
    "Specification", "PurchaseOrder", "NCR", "NCRSeverity", "NCRStatus",
    # Schedule
    "ScheduleTask", "TaskDependency", "TaskStatus",
    # Supply Chain
    "Shipment", "ShipmentStatus",
    # Commissioning
    "CommissioningTest", "TestResult", "TestCategory",
    # Knowledge
    "ProjectDocument", "RFI", "CascadeEvent", "RFIStatus", "RFIPriority",
]
