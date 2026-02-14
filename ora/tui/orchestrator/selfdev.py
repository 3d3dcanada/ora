"""Self-development agent for OrA to work on its own codebase."""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CodeChange:
    """A proposed code change."""
    file_path: str
    description: str
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    change_type: str = "modify"  # modify, create, delete
    approved: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SelfDevelopmentAgent:
    """
    Agent that allows OrA to work on its own codebase.
    
    Features:
    - Read/analyze OrA source files
    - Propose code modifications
    - Track changes and improvements
    - Persist development history
    """
    
    ORA_ROOT = Path.home() / "ora"
    SOURCE_DIR = ORA_ROOT / "src" / "ora"
    HISTORY_FILE = ORA_ROOT / ".selfdev_history.json"
    
    # Safe directories OrA can modify
    ALLOWED_PATHS = [
        "src/ora",
        "tests",
        "bin",
        ".agent",
    ]
    
    # Protected files that require explicit confirmation
    PROTECTED_FILES = [
        ".env",
        "pyproject.toml",
        ".git",
    ]
    
    def __init__(self):
        self.pending_changes: List[CodeChange] = []
        self.history: List[Dict[str, Any]] = []
        self._load_history()
    
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
            relative = resolved.relative_to(ora_root)
            
            # Check if in allowed paths
            rel_str = str(relative)
            return any(rel_str.startswith(allowed) for allowed in self.ALLOWED_PATHS)
        except (ValueError, Exception):
            return False
    
    def _is_protected(self, path: str) -> bool:
        """Check if file is protected."""
        try:
            resolved = Path(path).resolve()
            ora_root = self.ORA_ROOT.resolve()
            relative = resolved.relative_to(ora_root)
            rel_str = str(relative)
            return any(prot in rel_str for prot in self.PROTECTED_FILES)
        except Exception:
            return True  # If unsure, protect it
    
    def list_source_files(self, pattern: str = "*.py") -> List[str]:
        """List all Python source files in OrA."""
        files = []
        for path in self.SOURCE_DIR.rglob(pattern):
            if "__pycache__" not in str(path):
                files.append(str(path.relative_to(self.ORA_ROOT)))
        return sorted(files)
    
    def read_file(self, relative_path: str) -> Optional[str]:
        """Read a file from OrA codebase."""
        full_path = self.ORA_ROOT / relative_path
        
        if not full_path.exists():
            return None
        
        if not self._is_safe_path(str(full_path)):
            return f"[ACCESS DENIED] Path outside allowed directories: {relative_path}"
        
        try:
            with open(full_path, "r") as f:
                return f.read()
        except Exception as e:
            return f"[ERROR] Could not read file: {e}"
    
    def analyze_codebase(self) -> Dict[str, Any]:
        """Analyze OrA's codebase structure."""
        analysis = {
            "modules": [],
            "total_files": 0,
            "total_lines": 0,
            "components": {
                "widgets": [],
                "backend": [],
                "orchestrator": [],
                "memory": [],
            },
        }
        
        for py_file in self.SOURCE_DIR.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                rel_path = str(py_file.relative_to(self.SOURCE_DIR))
                analysis["total_files"] += 1
                
                try:
                    with open(py_file, "r") as f:
                        lines = len(f.readlines())
                        analysis["total_lines"] += lines
                except Exception:
                    lines = 0
                
                # Categorize
                if "widgets" in rel_path:
                    analysis["components"]["widgets"].append(rel_path)
                elif "backend" in rel_path:
                    analysis["components"]["backend"].append(rel_path)
                elif "orchestrator" in rel_path:
                    analysis["components"]["orchestrator"].append(rel_path)
                elif "memory" in rel_path:
                    analysis["components"]["memory"].append(rel_path)
                else:
                    analysis["modules"].append(rel_path)
        
        return analysis
    
    def propose_change(
        self,
        file_path: str,
        description: str,
        new_content: str,
        change_type: str = "modify",
    ) -> CodeChange:
        """Propose a code change for review."""
        full_path = self.ORA_ROOT / file_path
        
        original = None
        if full_path.exists() and change_type == "modify":
            try:
                with open(full_path, "r") as f:
                    original = f.read()
            except Exception:
                pass
        
        change = CodeChange(
            file_path=file_path,
            description=description,
            original_content=original,
            new_content=new_content,
            change_type=change_type,
        )
        
        self.pending_changes.append(change)
        return change
    
    def get_pending_changes(self) -> List[CodeChange]:
        """Get all pending changes awaiting approval."""
        return [c for c in self.pending_changes if not c.approved]
    
    def approve_change(self, index: int) -> bool:
        """Approve and apply a pending change."""
        if index >= len(self.pending_changes):
            return False
        
        change = self.pending_changes[index]
        full_path = self.ORA_ROOT / change.file_path
        
        # Safety checks
        if not self._is_safe_path(str(full_path)):
            return False
        
        if self._is_protected(str(full_path)):
            # Require explicit confirmation for protected files
            return False
        
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
            })
            self._save_history()
            
            return True
        except Exception:
            return False
    
    def reject_change(self, index: int) -> bool:
        """Reject a pending change."""
        if index >= len(self.pending_changes):
            return False
        
        self.pending_changes.pop(index)
        return True
    
    def get_improvement_suggestions(self) -> List[str]:
        """Generate suggestions for codebase improvements."""
        suggestions = []
        analysis = self.analyze_codebase()
        
        # Check for TODO comments
        for py_file in self.SOURCE_DIR.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                try:
                    content = py_file.read_text()
                    if "TODO" in content or "FIXME" in content:
                        rel_path = str(py_file.relative_to(self.ORA_ROOT))
                        suggestions.append(f"Review TODOs in {rel_path}")
                except Exception:
                    pass
        
        # Check for missing docstrings
        # Check for test coverage
        # etc.
        
        return suggestions
    
    def create_backup(self) -> str:
        """Create a backup of the current OrA state."""
        import shutil
        from datetime import datetime
        
        backup_dir = self.ORA_ROOT / ".backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"ora_backup_{timestamp}"
        
        try:
            shutil.copytree(
                self.SOURCE_DIR,
                backup_path,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            return str(backup_path)
        except Exception as e:
            return f"Backup failed: {e}"


# Singleton instance for use by orchestrator
self_dev_agent = SelfDevelopmentAgent()
