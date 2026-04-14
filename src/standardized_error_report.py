"""
Standardized Error Report Module for AI-DB-QC

This module provides standardized error report generation capabilities with
support for both JSON and Markdown formats. It integrates with the Root Cause
Analyzer to produce comprehensive, actionable error reports.

Features:
- Error report templates
- Multi-format report generation (JSON, Markdown)
- Report persistence and management
- Integration with MRE Generator and Root Cause Analyzer
- Structured error documentation

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-04-14
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from src.root_cause_analyzer import (
    RootCauseResult,
    RootCauseCategory,
    SeverityLevel
)
from src.mre_generator import (
    MinimalReproducibleExample,
    ErrorContext
)


# ============================================================================
# Report Format Enum
# ============================================================================

class ReportFormat(Enum):
    """Supported error report formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


# ============================================================================
# Error Report Status
# ============================================================================

class ReportStatus(Enum):
    """Status of an error report."""

    INITIAL = "initial"
    ANALYZED = "analyzed"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ============================================================================
# Error Report Data Class
# ============================================================================

@dataclass
class ErrorReport:
    """
    Standardized error report structure.

    This report combines error information, root cause analysis,
    and remediation guidance into a single document.

    Attributes:
        report_id: Unique identifier for this report
        timestamp: When the report was generated
        status: Current status of the report
        error_info: Basic error information
        error_context: Extended error context from MRE
        root_cause_result: Root cause analysis result
        mre_reference: Reference to associated MRE if available
        affected_components: List of affected system components
        fix_suggestions: Actionable fix suggestions
        prevention_measures: Measures to prevent recurrence
        related_reports: IDs of related error reports
        metadata: Additional metadata
    """

    report_id: str
    timestamp: str
    status: ReportStatus = ReportStatus.INITIAL
    error_info: Dict[str, Any] = field(default_factory=dict)
    error_context: Dict[str, Any] = field(default_factory=dict)
    root_cause_result: Dict[str, Any] = field(default_factory=dict)
    mre_reference: Optional[str] = None
    affected_components: List[str] = field(default_factory=list)
    fix_suggestions: List[str] = field(default_factory=list)
    prevention_measures: List[str] = field(default_factory=list)
    related_reports: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        if self.root_cause_result:
            if isinstance(self.root_cause_result, RootCauseResult):
                data['root_cause_result'] = self.root_cause_result.to_dict()
        return data

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorReport':
        """Create ErrorReport from dictionary."""
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ReportStatus(data['status'])
        return cls(**data)


# ============================================================================
# Report Template
# ============================================================================

class ErrorReportTemplate:
    """
    Template engine for generating standardized error reports.

    Provides pre-defined templates for different report formats
    and customizable template variables.
    """

    # Markdown Template
    MARKDOWN_TEMPLATE = """# Error Report: {report_id}

## Report Information

| Field | Value |
|-------|-------|
| Report ID | {report_id} |
| Generated | {timestamp} |
| Status | {status} |
| Severity | {severity} |
| Category | {category} |

## Error Summary

**Error Type:** {error_type}

**Error Message:**
```
{error_message}
```

## Root Cause Analysis

**Root Cause Category:** `{category}`

**Severity Level:** {severity}

**Confidence Score:** {confidence:.2%}

**Root Cause Summary:**
{root_cause_summary}

### Detailed Analysis

{detailed_analysis}

## Affected Components

{affected_components_list}

## Error Context

{error_context_section}

## Remediation

### Fix Suggestions

{fix_suggestions_list}

### Prevention Measures

{prevention_measures_list}

## Related Information

### MRE Reference

{mre_reference}

### Related Historical Errors

{related_errors_section}

## Stack Trace

```
{stack_trace}
```

## Metadata

{metadata_section}

---

*Report generated at {timestamp}*
"""

    # JSON Template Structure
    JSON_TEMPLATE = {
        "report_info": {
            "report_id": "",
            "timestamp": "",
            "status": "",
            "generator_version": "1.0.0"
        },
        "error_summary": {
            "error_type": "",
            "error_message": "",
            "severity": "",
            "category": ""
        },
        "root_cause_analysis": {
            "category": "",
            "summary": "",
            "detailed_analysis": "",
            "confidence_score": 0.0
        },
        "affected_components": [],
        "remediation": {
            "fix_suggestions": [],
            "prevention_measures": []
        },
        "related_information": {
            "mre_reference": None,
            "related_errors": []
        },
        "stack_trace": "",
        "metadata": {}
    }

    @classmethod
    def format_markdown(
        cls,
        report: ErrorReport,
        root_cause_result: Optional[RootCauseResult] = None
    ) -> str:
        """
        Format report as Markdown using template.

        Args:
            report: The error report to format
            root_cause_result: Optional root cause result for additional context

        Returns:
            Markdown formatted report string
        """
        # Get values with fallbacks
        severity = "Unknown"
        category = "unknown"
        confidence = 0.0
        root_cause_summary = "Not available"
        detailed_analysis = "No detailed analysis available"
        stack_trace = "No stack trace available"

        if root_cause_result:
            severity = root_cause_result.severity.value.upper()
            category = root_cause_result.root_cause_category.value
            confidence = root_cause_result.confidence_score
            root_cause_summary = root_cause_result.root_cause_summary
            detailed_analysis = root_cause_result.detailed_analysis
            stack_trace = root_cause_result.stack_trace or "No stack trace available"

        # Format affected components
        if report.affected_components:
            affected_components_list = "\n".join(
                f"- {comp}" for comp in report.affected_components
            )
        else:
            affected_components_list = "_No components specified_"

        # Format fix suggestions
        suggestions = report.fix_suggestions
        if root_cause_result and root_cause_result.fix_suggestions:
            suggestions = root_cause_result.fix_suggestions

        if suggestions:
            fix_suggestions_list = "\n".join(
                f"{i}. {s}" for i, s in enumerate(suggestions, 1)
            )
        else:
            fix_suggestions_list = "_No suggestions available_"

        # Format prevention measures
        measures = report.prevention_measures
        if root_cause_result and root_cause_result.prevention_measures:
            measures = root_cause_result.prevention_measures

        if measures:
            prevention_measures_list = "\n".join(
                f"{i}. {m}" for i, m in enumerate(measures, 1)
            )
        else:
            prevention_measures_list = "_No measures specified_"

        # Format error context
        if report.error_context:
            ctx_items = []
            for key, value in report.error_context.items():
                if value:
                    ctx_items.append(f"- **{key}:** {value}")
            error_context_section = "\n".join(ctx_items) if ctx_items else "_No context available_"
        else:
            error_context_section = "_No context available_"

        # Format MRE reference
        mre_ref = report.mre_reference or "Not available"

        # Format related errors
        related_errors = []
        if root_cause_result and root_cause_result.related_errors:
            for err in root_cause_result.related_errors[-5:]:
                related_errors.append(
                    f"- [{err.get('timestamp', 'N/A')}] "
                    f"{err.get('root_cause_category', 'N/A')}: "
                    f"{err.get('error_message', 'N/A')[:50]}..."
                )

        if related_errors:
            related_errors_section = "\n".join(related_errors)
        else:
            related_errors_section = "_No related errors found_"

        # Format metadata
        if report.metadata:
            metadata_items = []
            for key, value in report.metadata.items():
                metadata_items.append(f"- **{key}:** {value}")
            metadata_section = "\n".join(metadata_items)
        else:
            metadata_section = "_No metadata_"

        # Get error info
        error_type = "Unknown"
        error_message = "No error message"

        if report.error_info:
            error_type = report.error_info.get("error_type", error_type)
            error_message = report.error_info.get("error_message", error_message)

        return cls.MARKDOWN_TEMPLATE.format(
            report_id=report.report_id,
            timestamp=report.timestamp,
            status=report.status.value.upper(),
            severity=severity,
            category=category,
            error_type=error_type,
            error_message=error_message,
            root_cause_summary=root_cause_summary,
            detailed_analysis=detailed_analysis,
            affected_components_list=affected_components_list,
            error_context_section=error_context_section,
            fix_suggestions_list=fix_suggestions_list,
            prevention_measures_list=prevention_measures_list,
            mre_reference=mre_ref,
            related_errors_section=related_errors_section,
            stack_trace=stack_trace,
            metadata_section=metadata_section,
            confidence=confidence
        )

    @classmethod
    def format_json(
        cls,
        report: ErrorReport,
        root_cause_result: Optional[RootCauseResult] = None
    ) -> str:
        """
        Format report as JSON.

        Args:
            report: The error report to format
            root_cause_result: Optional root cause result

        Returns:
            JSON formatted report string
        """
        return report.to_json()


# ============================================================================
# Error Report Generator
# ============================================================================

class ErrorReportGenerator:
    """
    Generates standardized error reports integrating with MRE and RCA.

    This class provides comprehensive error report generation including:
    - Error information aggregation from multiple sources
    - Root cause analysis integration
    - Multi-format output (JSON, Markdown)
    - Report persistence and management
    - Related error correlation
    """

    def __init__(
        self,
        reports_dir: str = ".trae/error_reports",
        enable_auto_save: bool = True
    ):
        """
        Initialize the error report generator.

        Args:
            reports_dir: Directory for storing error reports
            enable_auto_save: Whether to automatically save reports
        """
        self.reports_dir = Path(reports_dir)
        self.enable_auto_save = enable_auto_save

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Create reports directory
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Report index
        self._report_index: Dict[str, str] = {}

        self.logger.info("ErrorReportGenerator initialized")

    def generate_report(
        self,
        exception: Exception,
        error_context: Optional[ErrorContext] = None,
        mre: Optional[MinimalReproducibleExample] = None,
        root_cause_result: Optional[RootCauseResult] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ErrorReport:
        """
        Generate a comprehensive error report.

        Args:
            exception: The exception that triggered the report
            error_context: Error context from MRE Generator
            mre: MRE for additional context
            root_cause_result: Pre-computed root cause result
            additional_context: Additional context information

        Returns:
            ErrorReport object
        """
        from src.root_cause_analyzer import RootCauseAnalyzer

        # Generate report ID
        report_id = self._generate_report_id(exception)

        # Analyze error if no root cause result provided
        if root_cause_result is None:
            analyzer = RootCauseAnalyzer()
            root_cause_result = analyzer.analyze_error(
                exception=exception,
                error_context=error_context,
                mre=mre,
                additional_context=additional_context
            )

        # Build error info
        error_info = {
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "timestamp": datetime.now().isoformat()
        }

        # Build error context from MRE
        report_error_context = {}
        if mre:
            if hasattr(mre, 'error_context') and mre.error_context:
                report_error_context = {
                    "component": getattr(mre.error_context, 'component', ''),
                    "error_category": getattr(mre.error_context, 'error_category', ''),
                    "error_code": getattr(mre.error_context, 'error_code', ''),
                    "additional_context": getattr(mre.error_context, 'additional_context', {})
                }

            report_error_context.update({
                "mre_id": mre.mre_id,
                "mre_timestamp": mre.timestamp
            })

        # Build affected components
        affected_components = list(root_cause_result.affected_components) if root_cause_result.affected_components else []

        # Build fix suggestions
        fix_suggestions = list(root_cause_result.fix_suggestions) if root_cause_result.fix_suggestions else []

        # Build prevention measures
        prevention_measures = list(root_cause_result.prevention_measures) if root_cause_result.prevention_measures else []

        # Create report
        report = ErrorReport(
            report_id=report_id,
            timestamp=datetime.now().isoformat(),
            status=ReportStatus.ANALYZED if root_cause_result else ReportStatus.INITIAL,
            error_info=error_info,
            error_context=report_error_context,
            root_cause_result=root_cause_result,
            mre_reference=mre.mre_id if mre else None,
            affected_components=affected_components,
            fix_suggestions=fix_suggestions,
            prevention_measures=prevention_measures,
            metadata={
                "generator": "ErrorReportGenerator",
                "generator_version": "1.0.0",
                "has_mre": mre is not None,
                "has_root_cause_analysis": root_cause_result is not None
            }
        )

        # Auto-save if enabled
        if self.enable_auto_save:
            self.save_report(report)

        return report

    def _generate_report_id(self, exception: Exception) -> str:
        """
        Generate a unique report ID.

        Args:
            exception: The exception for ID generation

        Returns:
            Unique report ID string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_type = type(exception).__name__
        return f"ERR_{error_type}_{timestamp}"

    def save_report(
        self,
        report: ErrorReport,
        format: ReportFormat = ReportFormat.JSON
    ) -> str:
        """
        Save report to disk.

        Args:
            report: The report to save
            format: Output format

        Returns:
            Path to the saved report
        """
        # Create date-based subdirectory
        date_str = datetime.now().strftime("%Y-%m-%d")
        report_dir = self.reports_dir / date_str
        report_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename
        extension = format.value
        filename = f"{report.report_id}.{extension}"
        filepath = report_dir / filename

        try:
            if format == ReportFormat.JSON:
                content = report.to_json()
            elif format == ReportFormat.MARKDOWN:
                content = ErrorReportTemplate.format_markdown(
                    report, report.root_cause_result
                )
            else:
                content = report.to_json()

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            # Update index
            self._report_index[report.report_id] = str(filepath)

            # Also save index
            self._save_report_index()

            self.logger.info(f"Report saved to {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
            return ""

    def _save_report_index(self) -> None:
        """Save report index to disk."""
        index_file = self.reports_dir / "report_index.json"

        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self._report_index, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save report index: {e}")

    def load_report(self, report_id: str) -> Optional[ErrorReport]:
        """
        Load a report from disk.

        Args:
            report_id: ID of the report to load

        Returns:
            ErrorReport if found, None otherwise
        """
        if report_id not in self._report_index:
            # Try to find the report
            self._load_report_index()

        if report_id not in self._report_index:
            return None

        filepath = self._report_index[report_id]

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return ErrorReport.from_dict(data)

        except Exception as e:
            self.logger.error(f"Failed to load report {report_id}: {e}")
            return None

    def _load_report_index(self) -> None:
        """Load report index from disk."""
        index_file = self.reports_dir / "report_index.json"

        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    self._report_index = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load report index: {e}")

    def generate_and_save_report(
        self,
        exception: Exception,
        error_context: Optional[ErrorContext] = None,
        mre: Optional[MinimalReproducibleExample] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        formats: List[ReportFormat] = None
    ) -> Dict[str, str]:
        """
        Generate and save report in one step.

        Args:
            exception: The exception that triggered the report
            error_context: Error context from MRE Generator
            mre: MRE for additional context
            additional_context: Additional context information
            formats: List of formats to save (default: [JSON, MARKDOWN])

        Returns:
            Dictionary mapping format to saved file path
        """
        formats = formats or [ReportFormat.JSON, ReportFormat.MARKDOWN]

        # Generate report
        report = self.generate_report(
            exception=exception,
            error_context=error_context,
            mre=mre,
            additional_context=additional_context
        )

        # Save in each format
        saved_paths = {}
        for fmt in formats:
            path = self.save_report(report, fmt)
            if path:
                saved_paths[fmt.value] = path

        return saved_paths

    def list_reports(
        self,
        date_filter: Optional[str] = None,
        status_filter: Optional[ReportStatus] = None
    ) -> List[ErrorReport]:
        """
        List available reports.

        Args:
            date_filter: Optional date string (YYYY-MM-DD) to filter
            status_filter: Optional status to filter by

        Returns:
            List of ErrorReport objects
        """
        reports = []

        # Load index
        self._load_report_index()

        for report_id, filepath in self._report_index.items():
            try:
                report = self.load_report(report_id)
                if report:
                    # Apply filters
                    if date_filter:
                        if not report.timestamp.startswith(date_filter):
                            continue

                    if status_filter and report.status != status_filter:
                        continue

                    reports.append(report)
            except Exception:
                continue

        # Sort by timestamp descending
        reports.sort(key=lambda r: r.timestamp, reverse=True)

        return reports

    def get_report_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all reports.

        Returns:
            Dictionary with report statistics
        """
        self._load_report_index()

        # Count by status
        status_counts = {}
        category_counts = {}

        for report_id in self._report_index.keys():
            try:
                report = self.load_report(report_id)
                if report:
                    # Count by status
                    status = report.status.value
                    status_counts[status] = status_counts.get(status, 0) + 1

                    # Count by category
                    if report.root_cause_result:
                        category = report.root_cause_result.root_cause_category.value
                        category_counts[category] = category_counts.get(category, 0) + 1
            except Exception:
                continue

        return {
            "total_reports": len(self._report_index),
            "by_status": status_counts,
            "by_category": category_counts,
            "reports_directory": str(self.reports_dir)
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_error_report(
    exception: Exception,
    mre: Optional[MinimalReproducibleExample] = None,
    root_cause_result: Optional[RootCauseResult] = None
) -> ErrorReport:
    """
    Create an error report with minimal configuration.

    Args:
        exception: The exception to report
        mre: Optional MRE for context
        root_cause_result: Optional pre-computed root cause result

    Returns:
        ErrorReport object
    """
    generator = ErrorReportGenerator()
    return generator.generate_report(
        exception=exception,
        error_context=mre.error_context if mre and hasattr(mre, 'error_context') else None,
        mre=mre,
        root_cause_result=root_cause_result
    )


def save_error_report(
    report: ErrorReport,
    format: ReportFormat = ReportFormat.JSON
) -> str:
    """
    Save an error report to disk.

    Args:
        report: The report to save
        format: Output format

    Returns:
        Path to saved file
    """
    generator = ErrorReportGenerator()
    return generator.save_report(report, format)


def generate_markdown_report(
    exception: Exception,
    mre: Optional[MinimalReproducibleExample] = None
) -> str:
    """
    Generate a Markdown formatted error report.

    Args:
        exception: The exception to report
        mre: Optional MRE for context

    Returns:
        Markdown formatted report string
    """
    generator = ErrorReportGenerator()
    report = generator.generate_report(
        exception=exception,
        error_context=mre.error_context if mre and hasattr(mre, 'error_context') else None,
        mre=mre
    )

    return ErrorReportTemplate.format_markdown(
        report, report.root_cause_result
    )