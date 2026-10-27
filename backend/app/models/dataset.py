"""
Dataset and benchmark sample models
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base

class Dataset(Base):
    """A collection of benchmark programming tasks"""
    
    __tablename__ = "datasets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Dataset identification
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    version = Column(String, nullable=True)
    source = Column(String, nullable=True)  # instruct_prime, custom, etc.
    
    # Metadata
    total_samples = Column(Integer, default=0)
    languages_covered = Column(JSON, default=[])  # List of languages
    cwe_categories_covered = Column(JSON, default=[])  # List of CWE IDs
    
    # Import tracking
    imported_at = Column(DateTime, default=datetime.utcnow)
    imported_by = Column(String, nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    is_research_benchmark = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    samples = relationship("BenchmarkSample", back_populates="dataset", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="dataset")


class BenchmarkSample(Base):
    """Individual programming task from a benchmark dataset"""
    
    __tablename__ = "benchmark_samples"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False, index=True)
    
    # Sample identification
    sample_identifier = Column(String, nullable=False, index=True)  # Unique within dataset
    task = Column(Text, nullable=False)
    
    # Classification
    language = Column(String, nullable=False, index=True)
    primary_cwe = Column(String, nullable=True, index=True)  # CWE-89, etc.
    cwe_name = Column(String, nullable=True)
    vulnerability_family = Column(String, nullable=True)  # injection, crypto, etc.
    
    # Additional CWEs (some samples may test multiple)
    secondary_cwes = Column(JSON, default=[])
    
    # Metadata from original benchmark
    difficulty = Column(String, nullable=True)
    tags = Column(JSON, default=[])
    reference_solution = Column(Text, nullable=True)
    reference_is_secure = Column(Boolean, nullable=True)
    
    # Original dataset metadata
    original_metadata = Column(JSON, default={})
    
    # Usage tracking
    times_evaluated = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="samples")
    evaluations = relationship("Evaluation", back_populates="sample")
