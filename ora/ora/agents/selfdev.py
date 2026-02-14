"""
ora.agents.selfdev
==================

Self-Development Agent - Self-improvement of OrA's own codebase.

Authority Level: A4 (FILE_WRITE) within OrA project only
Uses CODING models via OraRouter.
Tools: filesystem (OrA project only) + code_analyzer + git_ops
"""

import logging
import json
import os
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

from ora.agents.base import BaseAgent, Result
from ora.core.constitution import Operation
from ora.core.authority import AuthorityLevel
from ora.tools.filesystem import FilesystemTool
from ora.tools.code_analyzer import CodeAnalyzerTool

logger = logging.getLogger(__name__)


@dataclass
class CodeChange:
    """A proposed code change for self-development."""
    file_path: str
    description: str
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    change_type: str = "modify"  # modify, create, delete
    approved: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SelfDevAgent(BaseAgent):
    """
    Self-Development Agent - Allows OrA to work on its own codebase.
    
    Authority Level: A4 (FILE_WRITE) within OrA project only
    Skills: self_analyze, self_propose, self_backup, self_improve
    Tools: filesystem (OrA project only) + code_analyzer + git_ops
    
    Constitutional Prohibition: "No agent shall modify its own kernel or governance code."
    - Self-Dev can modify OrA application code
    - Self-Dev CANNOT modify: constitution, authority kernel, security gates, audit system
    """
    
    # OrA project root (current workspace)
    ORA_ROOT = Path("/home/randall/1A-PROJECTS/Ora-os")
    
    # Safe directories OrA can modify
    ALLOWED_PATHS = [
        "backend/ora",
        "backend/tests",
        "app/src",
        ".agent",
    ]
    
    # Protected files that require double confirmation
    PROTECTED_FILES = [
        ".env",
        "pyproject.toml",
        ".git",
        "AGENTS.md",
        "BUILD-PROMPT.md",
    ]
    
    # Files Self-Dev CANNOT modify (constitutional prohibition)
    PROHIBITED_FILES = [
        "backend/ora/core/constitution.py",
        "backend/ora/security/authority_kernel.py",
        "backend/ora/security/gates.py",
        "backend/ora/audit/immutable_log.py",
        "backend/ora/core/kernel.py",
    ]
    
    HISTORY_FILE = ORA_ROOT / ".selfdev_history.json"
    
    def __init__(self):
        super().__init__(
            role="SelfDev",
            authority_level=AuthorityLevel.FILE_WRITE,
            approved_skills=["self_analyze", "self_propose", "self_backup", "self_improve"],
            resource_quota={
                "cpu_seconds": 1200,
                "memory_mb": 512,
                "disk_mb": 1000,  # OrA project directory only
            },
        )
        
        # Initialize tools with workspace restriction
        self.filesystem_tool = FilesystemTool()
        self.code_analyzer_tool = CodeAnalyzerTool()
        
        # Self-dev state
        self.pending_changes: List[CodeChange] = []
        self.history: List[Dict[str, Any]] = []
        self._load_history()
        
        logger.info(f"SelfDevAgent {self.agent_id} initialized")
    
    def _load_history(self) -> None:
        """Load development history from disk."""
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, "r") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
    
    def _save_history(self) -> None:
        """Save development history to disk."""
        try:
            with open(self.HISTORY_FILE, "w") as f:
                json.dump(self.history[-100:], f, indent=2)  # Keep last 100
        except Exception:
            pass
    
    def _is_safe_path(self, path: str) -> bool:
        """Check if path is within allowed directories."""
        try:
            resolved = Path(path).resolve()
            ora_root = self.ORA_ROOT.resolve()
            
            # Must be within OrA project
            if not str(resolved).startswith(str(ora_root)):
                return False
            
            relative = resolved.relative_to(ora_root)
            
            # Check if in allowed paths
            rel_str = str(relative)
            return any(rel_str.startswith(allowed) for allowed in self.ALLOWED_PATHS)
        except (ValueError, Exception):
            return False
    
    def _is_protected(self, path: str) -> bool:
        """Check if file is protected (requires double confirmation)."""
        try:
            resolved = Path(path).resolve()
            ora_root = self.ORA_ROOT.resolve()
            relative = resolved.relative_to(ora_root)
            rel_str = str(relative)
            return any(prot in rel_str for prot in self.PROTECTED_FILES)
        except Exception:
            return True  # If unsure, protect it
    
    def _is_prohibited(self, path: str) -> bool:
        """Check if file is constitutionally prohibited from modification."""
        try:
            resolved = Path(path).resolve()
            ora_root = self.ORA_ROOT.resolve()
            relative = resolved.relative_to(ora_root)
            rel_str = str(relative)
            return any(prohibited in rel_str for prohibited in self.PROHIBITED_FILES)
        except Exception:
            return True  # If unsure, prohibit it
    
    async def execute_operation(self, operation: Operation) -> Result:
        """
        Execute self-development operation.
        
        Supported operations:
        - self_analyze: Analyze OrA codebase structure
        - self_propose: Propose code changes for review
        - self_backup: Create backup of OrA state
        - self_improve: Generate improvement suggestions
        """
        try:
            skill = operation.skill_name
            params = operation.parameters
            
            logger.info(f"SelfDevAgent executing {skill} with params: {params}")
            
            # Check if skill is approved
            if skill not in self.approved_skills:
                return Result(
                    status="failure",
                    output=f"Skill '{skill}' not approved for SelfDevAgent",
                    error="UNAUTHORIZED_SKILL",
                    evidence_refs=[],
                )
            
            # Execute based on skill
            if skill == "self_analyze":
                return await self._execute_self_analyze(params)
            elif skill == "self_propose":
                return await self._execute_self_propose(params)
            elif skill == "self_backup":
                return await self._execute_self_backup(params)
            elif skill == "self_improve":
                return await self._execute_self_improve(params)
            else:
                return Result(
                    status="failure",
                    output=f"Unknown skill '{skill}' for SelfDevAgent",
                    error="UNKNOWN_SKILL",
                    evidence_refs=[],
                )
                
        except Exception as e:
            logger.error(f"SelfDevAgent execution error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"SelfDevAgent execution failed: {str(e)}",
                error="EXECUTION_ERROR",
                evidence_refs=[],
            )
    
    async def _execute_self_analyze(self, params: Dict[str, Any]) -> Result:
        """
        Analyze OrA codebase structure.
        
        Parameters:
        - detail_level: "basic", "detailed", "full"
        - include_metrics: Whether to include code metrics
        """
        try:
            detail_level = params.get("detail_level", "basic")
            include_metrics = params.get("include_metrics", False)
            
            analysis = {
                "modules": [],
                "total_files": 0,
                "total_lines": 0,
                "components": {
                    "agents": [],
                    "tools": [],
                    "security": [],
                    "orchestrator": [],
                    "core": [],
                },
                "timestamp": datetime.now().isoformat(),
            }
            
            # Scan backend/ora directory
            ora_dir = self.ORA_ROOT / "backend" / "ora"
            if ora_dir.exists():
                for py_file in ora_dir.rglob("*.py"):
                    if "__pycache__" not in str(py_file):
                        rel_path = str(py_file.relative_to(self.ORA_ROOT))
                        analysis["total_files"] += 1
                        
                        if include_metrics:
                            try:
                                with open(py_file, "r") as f:
                                    lines = len(f.readlines())
                                    analysis["total_lines"] += lines
                            except Exception:
                                lines = 0
                        
                        # Categorize
                        if "agents" in rel_path:
                            analysis["components"]["agents"].append(rel_path)
                        elif "tools" in rel_path:
                            analysis["components"]["tools"].append(rel_path)
                        elif "security" in rel_path:
                            analysis["components"]["security"].append(rel_path)
                        elif "orchestrator" in rel_path:
                            analysis["components"]["orchestrator"].append(rel_path)
                        elif "core" in rel_path:
                            analysis["components"]["core"].append(rel_path)
                        else:
                            analysis["modules"].append(rel_path)
            
            # Include more detail if requested
            if detail_level in ["detailed", "full"]:
                # Count pending changes
                analysis["pending_changes"] = len(self.pending_changes)
                analysis["history_entries"] = len(self.history)
            
            if detail_level == "full":
                # Analyze code quality metrics
                metrics = await self._analyze_code_metrics()
                analysis["metrics"] = metrics
            
            return Result(
                status="success",
                output=analysis,
                error=None,
                evidence_refs=[f"self_analyze_{datetime.now().isoformat()}"],
            )
            
        except Exception as e:
            logger.error(f"Self-analyze error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"Self-analyze failed: {str(e)}",
                error="ANALYSIS_ERROR",
                evidence_refs=[],
            )
    
    async def _analyze_code_metrics(self) -> Dict[str, Any]:
        """Analyze code quality metrics."""
        metrics = {
            "complexity": {},
            "coverage": {},
            "quality": {},
        }
        
        try:
            # Use code_analyzer tool
            analysis_result = await self.code_analyzer_tool.run({
                "action": "analyze_code",
                "file_path": str(self.ORA_ROOT / "backend" / "ora"),
                "depth": 2,
            }, authority=self.authority_level.value)
            
            if analysis_result.get("success", False):
                metrics["complexity"] = analysis_result.get("data", {})
        
        except Exception as e:
            logger.warning(f"Code metrics analysis failed: {e}")
        
        return metrics
    
    async def _execute_self_propose(self, params: Dict[str, Any]) -> Result:
        """
        Propose code changes for review.
        
        Parameters:
        - file_path: Path to file to modify
        - description: Description of change
        - new_content: New content for file
        - change_type: "modify", "create", "delete"
        """
        try:
            file_path = params.get("file_path", "")
            description = params.get("description", "")
            new_content = params.get("new_content", "")
            change_type = params.get("change_type", "modify")
            
            # Validate file path
            if not file_path:
                return Result(
                    status="failure",
                    output="File path is required",
                    error="VALIDATION_ERROR",
                    evidence_refs=[],
                )
            
            full_path = self.ORA_ROOT / file_path
            
            # Check constitutional prohibition
            if self._is_prohibited(str(full_path)):
                return Result(
                    status="failure",
                    output=f"File '{file_path}' is constitutionally prohibited from modification",
                    error="CONSTITUTIONAL_VIOLATION",
                    evidence_refs=[],
                )
            
            # Check if path is safe
            if not self._is_safe_path(str(full_path)):
                return Result(
                    status="failure",
                    output=f"Path '{file_path}' is outside allowed directories",
                    error="PATH_VIOLATION",
                    evidence_refs=[],
                )
            
            # Check if file is protected
            is_protected = self._is_protected(str(full_path))
            
            # Read original content if modifying existing file
            original_content = None
            if full_path.exists() and change_type == "modify":
                try:
                    read_result = await self.filesystem_tool.run({
                        "action": "read_file",
                        "file_path": str(full_path),
                    }, authority=self.authority_level.value)
                    
                    if read_result.get("success", False):
                        original_content = read_result.get("data", {}).get("content", "")
                except Exception:
                    pass
            
            # Create change proposal
            change = CodeChange(
                file_path=file_path,
                description=description,
                original_content=original_content,
                new_content=new_content,
                change_type=change_type,
            )
            
            self.pending_changes.append(change)
            
            output = {
                "change_id": len(self.pending_changes) - 1,
                "file_path": file_path,
                "description": description,
                "change_type": change_type,
                "protected": is_protected,
                "requires_double_confirmation": is_protected,
                "timestamp": change.timestamp,
                "message": "Change proposed successfully. Requires human approval.",
            }
            
            if is_protected:
                output["warning"] = "File is protected - requires double confirmation"
            
            return Result(
                status="success",
                output=output,
                error=None,
                evidence_refs=[f"self_propose_{datetime.now().isoformat()}"],
            )
            
        except Exception as e:
            logger.error(f"Self-propose error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"Self-propose failed: {str(e)}",
                error="PROPOSAL_ERROR",
                evidence_refs=[],
            )
    
    async def _execute_self_backup(self, params: Dict[str, Any]) -> Result:
        """
        Create backup of OrA state.
        
        Parameters:
        - backup_name: Optional name for backup
        - include_history: Whether to include development history
        """
        try:
            backup_name = params.get("backup_name", "")
            include_history = params.get("include_history", True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if backup_name:
                backup_dir_name = f"ora_backup_{backup_name}_{timestamp}"
            else:
                backup_dir_name = f"ora_backup_{timestamp}"
            
            backup_dir = self.ORA_ROOT / ".backups" / backup_dir_name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup backend/ora directory
            ora_source = self.ORA_ROOT / "backend" / "ora"
            if ora_source.exists():
                shutil.copytree(
                    ora_source,
                    backup_dir / "backend" / "ora",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
                )
            
            # Backup app/src directory
            app_source = self.ORA_ROOT / "app" / "src"
            if app_source.exists():
                shutil.copytree(
                    app_source,
                    backup_dir / "app" / "src",
                    ignore=shutil.ignore_patterns("node_modules", "dist", "build"),
                )
            
            # Include history if requested
            if include_history and self.HISTORY_FILE.exists():
                shutil.copy2(self.HISTORY_FILE, backup_dir / ".selfdev_history.json")
            
            # Create backup manifest
            manifest = {
                "timestamp": datetime.now().isoformat(),
                "backup_name": backup_dir_name,
                "source_directories": [
                    str(ora_source.relative_to(self.ORA_ROOT)),
                    str(app_source.relative_to(self.ORA_ROOT)),
                ],
                "total_size_bytes": self._get_directory_size(backup_dir),
                "agent_id": self.agent_id,
            }
            
            manifest_file = backup_dir / "backup_manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)
            
            return Result(
                status="success",
                output={
                    "backup_path": str(backup_dir.relative_to(self.ORA_ROOT)),
                    "backup_name": backup_dir_name,
                    "manifest": manifest,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Backup created successfully at {backup_dir}",
                },
                error=None,
                evidence_refs=[f"self_backup_{datetime.now().isoformat()}"],
            )
            
        except Exception as e:
            logger.error(f"Self-backup error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"Self-backup failed: {str(e)}",
                error="BACKUP_ERROR",
                evidence_refs=[],
            )
    
    def _get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    async def _execute_self_improve(self, params: Dict[str, Any]) -> Result:
        """
        Generate improvement suggestions for OrA codebase.
        
        Parameters:
        - suggestion_types: Types of suggestions to generate
        - max_suggestions: Maximum number of suggestions
        """
        try:
            suggestion_types = params.get("suggestion_types", ["all"])
            max_suggestions = params.get("max_suggestions", 10)
            
            suggestions = []
            
            # Check for TODO comments
            if "todos" in suggestion_types or "all" in suggestion_types:
                todo_suggestions = await self._find_todo_comments()
                suggestions.extend(todo_suggestions)
            
            # Check for missing tests
            if "tests" in suggestion_types or "all" in suggestion_types:
                test_suggestions = await self._find_missing_tests()
                suggestions.extend(test_suggestions)
            
            # Check for code quality issues
            if "quality" in suggestion_types or "all" in suggestion_types:
                quality_suggestions = await self._find_quality_issues()
                suggestions.extend(quality_suggestions)
            
            # Limit suggestions
            suggestions = suggestions[:max_suggestions]
            
            return Result(
                status="success",
                output={
                    "suggestions_count": len(suggestions),
                    "suggestions": suggestions,
                    "suggestion_types": suggestion_types,
                    "timestamp": datetime.now().isoformat(),
                },
                error=None,
                evidence_refs=[f"self_improve_{datetime.now().isoformat()}"],
            )
            
        except Exception as e:
            logger.error(f"Self-improve error: {e}", exc_info=True)
            return Result(
                status="failure",
                output=f"Self-improve failed: {str(e)}",
                error="IMPROVEMENT_ERROR",
                evidence_refs=[],
            )
    
    async def _find_todo_comments(self) -> List[str]:
        """Find TODO comments in codebase."""
        suggestions = []
        
        try:
            # Search for TODO comments in Python files
            search_result = await self.filesystem_tool.run({
                "action": "search_files",
                "pattern": "*.py",
                "directory": str(self.ORA_ROOT / "backend" / "ora"),
                "recursive": True,
                "max_depth": 3,
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
                        
                        if "TODO" in content or "FIXME" in content:
                            rel_path = str(Path(file_path).relative_to(self.ORA_ROOT))
                            suggestions.append(f"Review TODO/FIXME comments in {rel_path}")
        
        except Exception as e:
            logger.warning(f"TODO search failed: {e}")
        
        return suggestions
    
    async def _find_missing_tests(self) -> List[str]:
        """Find modules with missing tests."""
        suggestions = []
        
        try:
            # List Python files in backend/ora
            list_result = await self.filesystem_tool.run({
                "action": "list_directory",
                "directory": str(self.ORA_ROOT / "backend" / "ora"),
                "recursive": True,
                "max_depth": -1,
            }, authority=self.authority_level.value)
            
            if list_result.get("success", False):
                items = list_result.get("data", {}).get("items", [])
                
                python_files = [
                    item for item in items 
                    if item.get("type") == "file" and item.get("name", "").endswith(".py")
                    and "__pycache__" not in item.get("path", "")
                    and "test" not in item.get("name", "").lower()
                ]
                
                for file_info in python_files:
                    file_path = file_info.get("path", "")
                    file_name = file_info.get("name", "")
                    
                    # Check if test file exists
                    test_file = file_path.replace(".py", "_test.py")
                    if not Path(test_file).exists():
                        rel_path = str(Path(file_path).relative_to(self.ORA_ROOT))
                        suggestions.append(f"Add tests for {rel_path}")
        
        except Exception as e:
            logger.warning(f"Missing test search failed: {e}")
        
        return suggestions
    
    async def _find_quality_issues(self) -> List[str]:
        """Find code quality issues."""
        suggestions = []
        
        try:
            # Use code_analyzer to find quality issues
            analysis_result = await self.code_analyzer_tool.run({
                "action": "lint_code",
                "file_path": str(self.ORA_ROOT / "backend" / "ora"),
                "depth": 2,
            }, authority=self.authority_level.value)
            
            if analysis_result.get("success", False):
                issues = analysis_result.get("data", {}).get("issues", [])
                
                for issue in issues[:5]:  # Limit to top 5
                    suggestions.append(f"Code quality issue: {issue.get('message', 'Unknown')}")
        
        except Exception as e:
            logger.warning(f"Quality issue search failed: {e}")
        
        return suggestions
    
    def get_pending_changes(self) -> List[CodeChange]:
        """Get all pending changes awaiting approval."""
        return [c for c in self.pending_changes if not c.approved]
    
    def approve_change(self, change_id: int) -> Dict[str, Any]:
        """
        Approve and apply a pending change.
        
        Note: This requires human approval and should be called via the approval gate.
        """
        if change_id >= len(self.pending_changes):
            return {"success": False, "error": "Invalid change ID"}
        
        change = self.pending_changes[change_id]
        full_path = self.ORA_ROOT / change.file_path
        
        # Safety checks
        if not self._is_safe_path(str(full_path)):
            return {"success": False, "error": "Path outside allowed directories"}
        
        if self._is_prohibited(str(full_path)):
            return {"success": False, "error": "File constitutionally prohibited from modification"}
        
        if self._is_protected(str(full_path)):
            # Protected files require double confirmation
            return {"success": False, "error": "File protected - requires double confirmation"}
        
        try:
            if change.change_type == "delete":
                if full_path.exists():
                    os.remove(full_path)
            elif change.change_type in ("create", "modify"):
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(change.new_content or "")
            
            change.approved = True
            
            # Record in history
            self.history.append({
                "timestamp": change.timestamp,
                "file": change.file_path,
                "description": change.description,
                "type": change.change_type,
                "agent_id": self.agent_id,
            })
            self._save_history()
            
            return {"success": True, "message": "Change applied successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to apply change: {str(e)}"}
    
    def reject_change(self, change_id: int) -> Dict[str, Any]:
        """Reject a pending change."""
        if change_id >= len(self.pending_changes):
            return {"success": False, "error": "Invalid change ID"}
        
        try:
            self.pending_changes.pop(change_id)
            return {"success": True, "message": "Change rejected"}
        except Exception as e:
            return {"success": False, "error": f"Failed to reject change: {str(e)}"}
    
    def vote_on_operation(self, operation: Operation, approved: bool = True) -> Dict[str, Any]:
        """
        Self-Dev Agent's vote on operations (for Byzantine consensus).
        
        Self-Dev Agent always requires human approval for its own operations.
        """
        vote = {
            "agent_id": self.agent_id,
            "agent_role": self.role,
            "approved": approved,
            "timestamp": datetime.now().isoformat(),
            "signature": self.sign({"operation": operation.to_dict(), "approved": approved}),
            "requires_human_approval": True,  # Self-Dev always requires human approval
        }
        
        # Check if operation involves self-modification
        if operation.skill_name in ["self_propose"]:
            vote["self_modification"] = True
            vote["warning"] = "Self-modification requires extra scrutiny"
        
        return vote