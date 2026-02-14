"""
ora.agents.security_agent
=======================

Security Agent - Vulnerability scanning, audit review, threat detection, security policy enforcement.

Authority Level: A3 (FILE_READ)
Uses REASONING models via OraRouter.
Tools: code_analyzer + filesystem.read + audit query
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ora.agents.base import BaseAgent, Result
from ora.core.constitution import Operation
from ora.core.authority import AuthorityLevel
from ora.tools.code_analyzer import CodeAnalyzerTool
from ora.tools.filesystem import FilesystemTool
from ora.security.gates import SecurityGateCoordinator, SecurityCheckResult
from ora.security.authority_kernel import AuthorityKernel

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """
    Security Agent - Scans for vulnerabilities, reviews audit logs, detects threats.
    
    Authority Level: A3 (FILE_READ)
    Skills: security_scan, vulnerability_assessment, threat_detection, audit_review
    Tools: code_analyzer + filesystem.read + audit query
    """
    
    def __init__(self):
        super().__init__(
            role="Security",
            authority_level=AuthorityLevel.FILE_READ,
            approved_skills=["security_scan", "vulnerability_assessment", "threat_detection", "audit_review"],
            resource_quota={
                "cpu_seconds": 1800,
                "memory_mb": 1024,
                "api_calls": 3000,
            },
        )
        
        # Initialize tools
        self.code_analyzer_tool = CodeAnalyzerTool()
        self.filesystem_tool = FilesystemTool()
        
        # Initialize security components
        self.security_gates = SecurityGateCoordinator(workspace_root=str(Path.cwd()))
        self.authority_kernel = AuthorityKernel()
        
        logger.info(f"SecurityAgent {self.agent_id} initialized")
    
    async def execute_operation(self, operation: Operation) -> Result:
        """
        Execute security operation.
        
        Supported operations:
        - security_scan: Scan code/files for vulnerabilities
        - vulnerability_assessment: Assess vulnerability severity
        - threat_detection: Detect security threats in audit logs
        - audit_review: Review and analyze audit trail
        """
        try:
            skill = operation.skill_name
            params = operation.parameters
            
            logger.info(f"SecurityAgent executing {skill} with params: {params}")
            
            # Check if skill is approved
            if skill not in self.approved_skills:
                return Result(
                    status="failure",
                    output=f"Skill '{skill}' not approved for SecurityAgent",
                    error="UNAUTHORIZED_SKILL",
                    evidence_refs=[],
                )
            
            # Execute based on skill
            if skill == "security_scan":
                return await self._execute_security_scan(params)
            elif skill == "vulnerability_assessment":
                return await self._execute_vulnerability_assessment(params)
            elif skill == "threat_detection":
                return await self._execute_threat_detection(params)
            elif skill == "audit_review":
                return await self._execute_audit_review(params)
            else:
                return Result(
                    status="failure",
                    output=f"Unknown skill '{skill}' for SecurityAgent",
                    error="UNKNOWN_SKILL",
                    evidence_refs=[],
                )
                
        except Exception as e:
            logger.error(f"SecurityAgent execution error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"SecurityAgent execution failed: {str(e)}",
                error="EXECUTION_ERROR",
                evidence_refs=[],
            )
    
    async def _execute_security_scan(self, params: Dict[str, Any]) -> Result:
        """
        Scan code/files for vulnerabilities.
        
        Parameters:
        - target_path: Path to scan (file or directory)
        - scan_type: "code", "dependencies", "secrets", "all"
        - depth: Recursion depth for directories
        """
        try:
            target_path = params.get("target_path", ".")
            scan_type = params.get("scan_type", "all")
            depth = params.get("depth", 2)
            
            evidence_refs = []
            findings = []
            
            # Check workspace boundary first
            boundary_check = self.security_gates.check_workspace_boundary(target_path)
            if not boundary_check.passed:
                return Result(
                    status="failure",
                    output=f"Security scan blocked: {boundary_check.blocked_reason}",
                    error="WORKSPACE_VIOLATION",
                    evidence_refs=evidence_refs,
                )
            
            # Perform scan based on type
            if scan_type in ["code", "all"]:
                code_findings = await self._scan_code_vulnerabilities(target_path, depth)
                findings.extend(code_findings)
                evidence_refs.append(f"code_scan_{datetime.now().isoformat()}")
            
            if scan_type in ["dependencies", "all"]:
                dep_findings = await self._scan_dependencies(target_path)
                findings.extend(dep_findings)
                evidence_refs.append(f"dep_scan_{datetime.now().isoformat()}")
            
            if scan_type in ["secrets", "all"]:
                secret_findings = await self._scan_secrets(target_path, depth)
                findings.extend(secret_findings)
                evidence_refs.append(f"secret_scan_{datetime.now().isoformat()}")
            
            # Run security gates on findings
            gate_results = []
            for finding in findings:
                if "description" in finding:
                    gate_check = self.security_gates.check_prompt(finding["description"], source="security_scan")
                    gate_results.append({
                        "finding": finding.get("title", "Unknown"),
                        "gate_passed": gate_check.passed,
                        "threat_level": gate_check.threat_level,
                    })
            
            return Result(
                status="success",
                output={
                    "scan_type": scan_type,
                    "target_path": target_path,
                    "findings_count": len(findings),
                    "findings": findings,
                    "gate_results": gate_results,
                    "timestamp": datetime.now().isoformat(),
                },
                error=None,
                evidence_refs=evidence_refs,
            )
            
        except Exception as e:
            logger.error(f"Security scan error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"Security scan failed: {str(e)}",
                error="SCAN_ERROR",
                evidence_refs=[],
            )
    
    async def _scan_code_vulnerabilities(self, target_path: str, depth: int) -> List[Dict[str, Any]]:
        """Scan code for vulnerabilities using code_analyzer."""
        findings = []
        
        try:
            # Use code_analyzer to parse and analyze code
            analysis_result = await self.code_analyzer_tool.run({
                "action": "analyze_code",
                "file_path": target_path,
                "depth": depth,
            }, authority=self.authority_level.value)
            
            if analysis_result.get("success", False):
                analysis_data = analysis_result.get("data", {})
                
                # Check for common vulnerabilities
                if "complexity" in analysis_data and analysis_data["complexity"] > 15:
                    findings.append({
                        "title": "High Cyclomatic Complexity",
                        "description": f"Code complexity {analysis_data['complexity']} exceeds threshold (15)",
                        "severity": "MEDIUM",
                        "location": target_path,
                        "recommendation": "Refactor code to reduce complexity",
                    })
                
                if "functions" in analysis_data:
                    for func in analysis_data["functions"]:
                        # Check for potential injection vulnerabilities
                        if any(keyword in func.get("name", "").lower() for keyword in ["eval", "exec", "system"]):
                            findings.append({
                                "title": "Potential Code Injection",
                                "description": f"Function '{func.get('name')}' may allow code injection",
                                "severity": "HIGH",
                                "location": f"{target_path}:{func.get('line', 0)}",
                                "recommendation": "Use safe alternatives to eval/exec",
                            })
            
        except Exception as e:
            logger.warning(f"Code vulnerability scan failed: {e}")
        
        return findings
    
    async def _scan_dependencies(self, target_path: str) -> List[Dict[str, Any]]:
        """Scan dependencies for known vulnerabilities."""
        findings = []
        
        try:
            # Check for package files
            package_files = ["package.json", "pyproject.toml", "requirements.txt", "Cargo.toml"]
            
            for pkg_file in package_files:
                file_path = Path(target_path) / pkg_file
                if file_path.exists():
                    findings.append({
                        "title": "Dependency File Found",
                        "description": f"Found {pkg_file} - manual review recommended",
                        "severity": "INFO",
                        "location": str(file_path),
                        "recommendation": "Run dependency audit tools",
                    })
        
        except Exception as e:
            logger.warning(f"Dependency scan failed: {e}")
        
        return findings
    
    async def _scan_secrets(self, target_path: str, depth: int) -> List[Dict[str, Any]]:
        """Scan for exposed secrets."""
        findings = []
        
        try:
            # Common secret patterns
            secret_patterns = {
                "API_KEY": r"(?i)(api[_-]?key|apikey)[\s:=]['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
                "SECRET": r"(?i)(secret|password|token)[\s:=]['\"]?([a-zA-Z0-9_\-]{10,})['\"]?",
                "AWS": r"(?i)(AKIA|ASIA)[A-Z0-9]{16}",
                "GITHUB": r"(?i)gh[pousr]_[A-Za-z0-9_]{36}",
                "SLACK": r"(?i)xox[baprs]-[A-Za-z0-9-]+",
            }
            
            # Search files for patterns
            search_result = await self.filesystem_tool.run({
                "action": "search_files",
                "pattern": "*.{py,js,ts,json,env,yaml,yml,toml}",
                "directory": target_path,
                "recursive": depth > 0,
                "max_depth": depth,
            }, authority=self.authority_level.value)
            
            if search_result.get("success", False):
                files = search_result.get("data", {}).get("files", [])
                
                for file_info in files:
                    file_path = file_info.get("path", "")
                    
                    # Read file content
                    read_result = await self.filesystem_tool.run({
                        "action": "read_file",
                        "file_path": file_path,
                    }, authority=self.authority_level.value)
                    
                    if read_result.get("success", False):
                        content = read_result.get("data", {}).get("content", "")
                        
                        for secret_type, pattern in secret_patterns.items():
                            import re
                            matches = re.findall(pattern, content)
                            if matches:
                                findings.append({
                                    "title": f"Potential {secret_type} Exposure",
                                    "description": f"Found {len(matches)} potential {secret_type} patterns in {file_path}",
                                    "severity": "HIGH",
                                    "location": file_path,
                                    "recommendation": "Remove or encrypt secrets",
                                })
        
        except Exception as e:
            logger.warning(f"Secret scan failed: {e}")
        
        return findings
    
    async def _execute_vulnerability_assessment(self, params: Dict[str, Any]) -> Result:
        """
        Assess vulnerability severity and provide recommendations.
        
        Parameters:
        - vulnerability_data: Vulnerability findings from scan
        - context: Additional context about the system
        """
        try:
            vulnerability_data = params.get("vulnerability_data", {})
            context = params.get("context", {})
            
            # Analyze severity based on context
            findings = vulnerability_data.get("findings", [])
            assessed_findings = []
            
            for finding in findings:
                severity = finding.get("severity", "UNKNOWN")
                location = finding.get("location", "")
                
                # Adjust severity based on context
                adjusted_severity = severity
                if "production" in context.get("environment", "").lower():
                    # Increase severity in production
                    if severity == "LOW":
                        adjusted_severity = "MEDIUM"
                    elif severity == "MEDIUM":
                        adjusted_severity = "HIGH"
                
                assessed_findings.append({
                    **finding,
                    "adjusted_severity": adjusted_severity,
                    "risk_score": self._calculate_risk_score(finding, context),
                    "assessment_time": datetime.now().isoformat(),
                })
            
            return Result(
                status="success",
                output={
                    "original_findings_count": len(findings),
                    "assessed_findings_count": len(assessed_findings),
                    "assessed_findings": assessed_findings,
                    "risk_summary": self._generate_risk_summary(assessed_findings),
                    "timestamp": datetime.now().isoformat(),
                },
                error=None,
                evidence_refs=[f"vuln_assessment_{datetime.now().isoformat()}"],
            )
            
        except Exception as e:
            logger.error(f"Vulnerability assessment error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"Vulnerability assessment failed: {str(e)}",
                error="ASSESSMENT_ERROR",
                evidence_refs=[],
            )
    
    def _calculate_risk_score(self, finding: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate risk score 0-100 based on finding and context."""
        base_scores = {
            "CRITICAL": 90,
            "HIGH": 80,
            "MEDIUM": 60,
            "LOW": 30,
            "INFO": 10,
        }
        
        severity = finding.get("severity", "INFO").upper()
        base_score = base_scores.get(severity, 10)
        
        # Adjust based on context
        adjustments = 0
        
        # Production environment increases risk
        if "production" in context.get("environment", "").lower():
            adjustments += 20
        
        # External exposure increases risk
        if finding.get("exposed_externally", False):
            adjustments += 30
        
        # Critical data involved increases risk
        if any(keyword in finding.get("description", "").lower() 
               for keyword in ["password", "secret", "key", "token"]):
            adjustments += 25
        
        return min(100, base_score + adjustments)
    
    def _generate_risk_summary(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate risk summary from assessed findings."""
        summary = {
            "total_findings": len(findings),
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "info_count": 0,
            "average_risk_score": 0,
            "max_risk_score": 0,
        }
        
        if findings:
            risk_scores = []
            for finding in findings:
                severity = finding.get("adjusted_severity", "INFO").upper()
                if severity == "CRITICAL":
                    summary["critical_count"] += 1
                elif severity == "HIGH":
                    summary["high_count"] += 1
                elif severity == "MEDIUM":
                    summary["medium_count"] += 1
                elif severity == "LOW":
                    summary["low_count"] += 1
                else:
                    summary["info_count"] += 1
                
                risk_score = finding.get("risk_score", 0)
                risk_scores.append(risk_score)
                summary["max_risk_score"] = max(summary["max_risk_score"], risk_score)
            
            summary["average_risk_score"] = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        return summary
    
    async def _execute_threat_detection(self, params: Dict[str, Any]) -> Result:
        """
        Detect security threats in audit logs.
        
        Parameters:
        - time_window: Time window to analyze (hours)
        - threat_types: Types of threats to detect
        """
        try:
            time_window = params.get("time_window", 24)  # hours
            threat_types = params.get("threat_types", ["all"])
            
            # Get threat data from authority kernel
            threats_detected = []
            
            # Check for rapid file operations
            rapid_file_ops = self.authority_kernel._detect_rapid_file_ops()
            if rapid_file_ops:
                threats_detected.append({
                    "type": "RAPID_FILE_OPERATIONS",
                    "description": f"Detected {rapid_file_ops['count']} file operations in {rapid_file_ops['window_sec']} seconds",
                    "severity": "HIGH",
                    "timestamp": datetime.now().isoformat(),
                })
            
            # Check for failed authentication attempts
            failed_auth = self.authority_kernel._detect_failed_auth()
            if failed_auth:
                threats_detected.append({
                    "type": "FAILED_AUTHENTICATION",
                    "description": f"Detected {failed_auth['count']} failed authentication attempts",
                    "severity": "MEDIUM",
                    "timestamp": datetime.now().isoformat(),
                })
            
            # Check security gate violations
            gate_violations = []
            # This would query the security gates for recent violations
            
            return Result(
                status="success",
                output={
                    "time_window_hours": time_window,
                    "threat_types_checked": threat_types,
                    "threats_detected": threats_detected,
                    "threat_count": len(threats_detected),
                    "gate_violations": gate_violations,
                    "timestamp": datetime.now().isoformat(),
                },
                error=None,
                evidence_refs=[f"threat_detection_{datetime.now().isoformat()}"],
            )
            
        except Exception as e:
            logger.error(f"Threat detection error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"Threat detection failed: {str(e)}",
                error="DETECTION_ERROR",
                evidence_refs=[],
            )
    
    async def _execute_audit_review(self, params: Dict[str, Any]) -> Result:
        """
        Review and analyze audit trail.
        
        Parameters:
        - start_time: Start time for audit review
        - end_time: End time for audit review
        - filter_types: Filter by operation types
        - filter_actors: Filter by actor IDs
        """
        try:
            start_time = params.get("start_time")
            end_time = params.get("end_time")
            filter_types = params.get("filter_types", [])
            filter_actors = params.get("filter_actors", [])
            
            # Query audit log
            audit_entries = []
            # This would query the ImmutableAuditLog
            
            # Analyze audit patterns
            analysis = {
                "total_entries": len(audit_entries),
                "by_operation_type": {},
                "by_actor": {},
                "by_authority_level": {},
                "success_rate": 0,
                "anomalies": [],
            }
            
            if audit_entries:
                success_count = sum(1 for entry in audit_entries if entry.get("status") == "success")
                analysis["success_rate"] = success_count / len(audit_entries) * 100
                
                # Group by operation type
                for entry in audit_entries:
                    op_type = entry.get("operation", "unknown")
                    analysis["by_operation_type"][op_type] = analysis["by_operation_type"].get(op_type, 0) + 1
                    
                    actor = entry.get("actor", {}).get("id", "unknown")
                    analysis["by_actor"][actor] = analysis["by_actor"].get(actor, 0) + 1
                    
                    auth_level = entry.get("authority_level", "unknown")
                    analysis["by_authority_level"][auth_level] = analysis["by_authority_level"].get(auth_level, 0) + 1
            
            return Result(
                status="success",
                output={
                    "time_range": {
                        "start": start_time,
                        "end": end_time,
                    },
                    "filters_applied": {
                        "types": filter_types,
                        "actors": filter_actors,
                    },
                    "audit_summary": analysis,
                    "sample_entries": audit_entries[:10] if audit_entries else [],
                    "timestamp": datetime.now().isoformat(),
                },
                error=None,
                evidence_refs=[f"audit_review_{datetime.now().isoformat()}"],
            )
            
        except Exception as e:
            logger.error(f"Audit review error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"Audit review failed: {str(e)}",
                error="REVIEW_ERROR",
                evidence_refs=[],
            )
    
    def vote_on_operation(self, operation: Operation, approved: bool = True) -> Dict[str, Any]:
        """
        Security Agent's vote on operations (for Byzantine consensus).
        
        Security Agent has special veto power for security violations.
        """
        vote = {
            "agent_id": self.agent_id,
            "agent_role": self.role,
            "approved": approved,
            "timestamp": datetime.now().isoformat(),
            "signature": self.sign({"operation": operation.to_dict(), "approved": approved}),
        }
        
        # Security Agent can veto based on security analysis
        if not approved:
            # Run security gates on the operation
            gate_check = self.security_gates.run_all_gates({
                "operation": operation.skill_name,
                "parameters": operation.parameters,
                "actor": f"agent:{self.agent_id}",
            })
            
            if not gate_check.get("passed", True):
                vote["veto_reason"] = "Security gate violation"
                vote["gate_results"] = gate_check.get("gate_results", {})
                vote["threat_level"] = gate_check.get("threat_level", 0)
        
        return vote