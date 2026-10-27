"""
Reflection attempt model - Tracks reflexion loop iterations
"""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base

class ReflectionAttempt(Base):
    """A single reflexion iteration within an evaluation"""
    
    __tablename__ = "reflection_attempts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String, ForeignKey("evaluations.id"), nullable=False, index=True)
    
    # Iteration tracking
    round_number = Column(Integer, nullable=False)  # 1, 2, 3
    previous_version = Column(String, nullable=False)  # t0, t1, t2
    new_version = Column(String, nullable=False)  # t1, t2, t3
    
    # Reflection prompt construction
    reflection_prompt = Column(Text, nullable=False)
    reflection_buffer = Column(JSON, nullable=False)  # Complete history sent to model
    
    # Feedback provided
    previous_findings = Column(JSON, nullable=False)  # Findings from previous version
    cwe_hints = Column(JSON, nullable=True)  # CWE-specific guidance
    
    # Response
    model_response = Column(Text, nullable=False)
    revised_code = Column(Text, nullable=False)
    
    # Performance
    generation_time_seconds = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    # Outcome
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluation = relationship("Evaluation", back_populates="reflection_attempts")
