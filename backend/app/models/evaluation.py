"""
Evaluation models - Core entities for code generation and security assessment
"""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base

class EvaluationStatus(str, enum.Enum):
    """Evaluation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProgrammingLanguage(str, enum.Enum):
    """Supported programming languages"""
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    PYTHON = "python"
    PHP = "php"
    RUST = "rust"

class SecurityLabel(int, enum.Enum):
    """Binary security label per research paper"""
    SECURE = 0
    INSECURE = 1

class CodeValidationStatus(str, enum.Enum):
    """Code validation outcome"""
    COMPLETE_CODE = "complete_code"
    INCOMPLETE_CODE = "incomplete_code"
    NATURAL_LANGUAGE = "natural_language"
    MIXED = "mixed"
    NOT_VALIDATED = "not_validated"

class Evaluation(Base):
    """Main evaluation run tracking a complete reflexion workflow"""
    
    __tablename__ = "evaluations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Task details
    task = Column(Text, nullable=False)
    language = Column(SQLEnum(ProgrammingLanguage), nullable=False)
    
    # AI configuration
    ai_provider = Column(String, nullable=False)  # openai, anthropic, etc.
    ai_model = Column(String, nullable=False)
    ai_config = Column(JSON, default=dict)  # temperature, requested_provider, fallback_reason, ...
    
    # Reflexion configuration
    max_rounds = Column(Integer, default=3)
    requested_rounds = Column(Integer, default=1)
    completed_rounds = Column(Integer, default=0)
    
    # Status tracking
    status = Column(SQLEnum(EvaluationStatus), default=EvaluationStatus.PENDING, index=True)
    error_message = Column(Text, nullable=True)
    
    # Metrics summary (denormalized for quick access)
    baseline_secure = Column(Boolean, nullable=True)  # t0 security label
    final_secure = Column(Boolean, nullable=True)  # Final version security label
    total_findings_t0 = Column(Integer, default=0)
    total_findings_final = Column(Integer, default=0)
    findings_fixed = Column(Integer, default=0)
    findings_new = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_duration_seconds = Column(Float, nullable=True)
    
    # Usage tracking
    total_tokens_used = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Dataset reference (if from benchmark)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=True)
    sample_id = Column(String, ForeignKey("benchmark_samples.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="evaluations")
    code_versions = relationship("CodeVersion", back_populates="evaluation", cascade="all, delete-orphan")
    reflection_attempts = relationship("ReflectionAttempt", back_populates="evaluation", cascade="all, delete-orphan")
    metric_snapshots = relationship("MetricSnapshot", back_populates="evaluation", cascade="all, delete-orphan")
    dataset = relationship("Dataset", back_populates="evaluations")
    sample = relationship("BenchmarkSample", back_populates="evaluations")


class CodeVersion(Base):
    """A specific code version (t0, t1, t2, t3) in an evaluation"""
    
    __tablename__ = "code_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String, ForeignKey("evaluations.id"), nullable=False, index=True)
    
    # Version identifier
    version = Column(String, nullable=False)  # t0, t1, t2, t3
    round_number = Column(Integer, nullable=False)  # 0, 1, 2, 3
    
    # Generated code
    code = Column(Text, nullable=False)
    raw_response = Column(Text, nullable=False)  # Complete LLM response
    
    # Validation
    validation_status = Column(SQLEnum(CodeValidationStatus), default=CodeValidationStatus.NOT_VALIDATED)
    validation_message = Column(Text, nullable=True)
    is_valid_code = Column(Boolean, default=False)
    
    # Security assessment
    security_label = Column(SQLEnum(SecurityLabel), nullable=True)  # 0=secure, 1=insecure
    scan_completed = Column(Boolean, default=False)
    scan_error = Column(Text, nullable=True)
    
    # Generation metadata
    prompt_used = Column(Text, nullable=False)
    generation_time_seconds = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    # Reflexion round details
    diff = Column(Text, nullable=True)  # unified diff vs previous version
    explanation = Column(Text, nullable=True)  # deterministic explanation of the change
    severity_counts = Column(JSON, nullable=True)  # {CRITICAL, HIGH, MEDIUM, LOW}
    comparison = Column(JSON, nullable=True)  # {fixed, new, unresolved} vs previous version
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    evaluation = relationship("Evaluation", back_populates="code_versions")
    scan_results = relationship("ScanResult", back_populates="code_version", cascade="all, delete-orphan")
    security_findings = relationship("SecurityFinding", back_populates="code_version", cascade="all, delete-orphan")


class SecurityFinding(Base):
    """Normalized security vulnerability finding"""
    
    __tablename__ = "security_findings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code_version_id = Column(String, ForeignKey("code_versions.id"), nullable=False, index=True)
    
    # Scanner information
    analyzer = Column(String, nullable=False)  # semgrep, bandit, icd, etc.
    rule_id = Column(String, nullable=False)
    
    # CWE mapping
    cwe_id = Column(String, nullable=True, index=True)  # CWE-89, CWE-79, etc.
    cwe_name = Column(String, nullable=True)
    
    # Severity
    severity = Column(String, nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence = Column(String, nullable=True)  # HIGH, MEDIUM, LOW
    
    # Finding details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    remediation = Column(Text, nullable=True)
    
    # Location
    file_path = Column(String, nullable=True)
    start_line = Column(Integer, nullable=True)
    end_line = Column(Integer, nullable=True)
    code_snippet = Column(Text, nullable=True)
    
    # Status tracking (for comparison across versions)
    status = Column(String, default="open")  # open, fixed, unresolved, newly_introduced
    
    # Raw data
    raw_finding = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    code_version = relationship("CodeVersion", back_populates="security_findings")


class ScanResult(Base):
    """Raw scan result from a security analyzer"""
    
    __tablename__ = "scan_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code_version_id = Column(String, ForeignKey("code_versions.id"), nullable=False, index=True)
    
    # Scanner details
    analyzer = Column(String, nullable=False)  # semgrep, bandit, icd
    analyzer_version = Column(String, nullable=True)
    
    # Scan execution
    scan_started_at = Column(DateTime, nullable=False)
    scan_completed_at = Column(DateTime, nullable=False)
    scan_duration_seconds = Column(Float, nullable=False)
    
    # Results
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    findings_count = Column(Integer, default=0)
    
    # Raw output
    raw_output = Column(JSON, nullable=True)  # Complete scanner output
    
    # Configuration used
    config_used = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    code_version = relationship("CodeVersion", back_populates="scan_results")
