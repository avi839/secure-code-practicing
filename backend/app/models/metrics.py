"""
Metrics snapshot model - Stores computed Repair, Regression, NetGain metrics
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base

class MetricSnapshot(Base):
    """
    Computed metrics for a transition between versions
    Based on research paper formulas:
    - Repair: (insecure→secure transitions / N) × 100%
    - Regression: (secure→insecure transitions / N) × 100%
    - NetGain: Repair - Regression
    """
    
    __tablename__ = "metric_snapshots"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String, ForeignKey("evaluations.id"), nullable=False, index=True)
    
    # Transition tracked
    from_version = Column(String, nullable=False)  # t0, t1, t2
    to_version = Column(String, nullable=False)  # t1, t2, t3
    transition_name = Column(String, nullable=False, index=True)  # t0_to_t1, t1_to_t2, t2_to_t3
    
    # Binary security labels (per research paper)
    from_label = Column(Integer, nullable=False)  # 0=secure, 1=insecure
    to_label = Column(Integer, nullable=False)  # 0=secure, 1=insecure
    
    # Core metrics (percentages)
    repair_rate = Column(Float, default=0.0)  # Percentage
    regression_rate = Column(Float, default=0.0)  # Percentage
    net_gain = Column(Float, default=0.0)  # repair_rate - regression_rate
    
    # Transition type
    is_repair = Column(Boolean, default=False)  # 1→0
    is_regression = Column(Boolean, default=False)  # 0→1
    is_unchanged_secure = Column(Boolean, default=False)  # 0→0
    is_unchanged_insecure = Column(Boolean, default=False)  # 1→1
    
    # Finding-level details (for diagnostics, not research metrics)
    findings_fixed_count = Column(Integer, default=0)
    findings_new_count = Column(Integer, default=0)
    findings_unresolved_count = Column(Integer, default=0)
    total_findings_from = Column(Integer, default=0)
    total_findings_to = Column(Integer, default=0)
    
    # Detailed comparison
    fixed_findings = Column(JSON, default=[])  # List of fixed finding IDs/descriptions
    new_findings = Column(JSON, default=[])  # List of newly introduced findings
    unresolved_findings = Column(JSON, default=[])  # List of persisting findings
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluation = relationship("Evaluation", back_populates="metric_snapshots")
