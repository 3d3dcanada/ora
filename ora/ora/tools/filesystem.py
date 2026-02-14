"""
ora.tools.filesystem
====================

Filesystem Tool - File operations with safety constraints and workspace boundary enforcement.

Port from BUZZ Neural Core with OrA security gate integration.
"""

import os
import asyncio
import pathlib
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ora.security.gates import WorkspaceBoundaryEnforcer

logger = logging.getLogger(__name__)


class FilesystemTool:
    """
    Filesystem operations with workspace boundary enforcement.
    
    All operations check WorkspaceBoundaryEnforcer from security/gates.py.
    Write/delete operations require A4 authority minimum.
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        """
        Initialize filesystem tool.
        
        Args:
            workspace_root: Root directory for workspace (defaults to current workspace)
        """
        if workspace_root is None:
            # Default to current workspace directory
            self.workspace_root = Path("/home/randall/1A-PROJECTS/Ora-os").resolve()
        else:
            self.workspace_root = Path(workspace_root).resolve()
        
        self.enforcer = WorkspaceBoundaryEnforcer(self.workspace_root)
        
        logger.info(f"FilesystemTool initialized with workspace: {self.workspace_root}")
    
    def _is_safe_path(self, file_path: str) -> bool:
        """
        Ensure path is within workspace using WorkspaceBoundaryEnforcer.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if path is safe (within workspace)
        """
        try:
            return self.enforcer.validate_path(file_path)
        except Exception as e:
            logger.error(f"Path validation failed: {e}")
            return False
    
    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve path relative to workspace.
        
        Args:
            file_path: Path to resolve
            
        Returns:
            Resolved Path object
        """
        # Handle absolute paths
        if Path(file_path).is_absolute():
            return Path(file_path).resolve()
        # Handle relative paths
        return (self.workspace_root / file_path).resolve()
    
    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read file contents.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with success status and content/error
        """
        if not self._is_safe_path(file_path):
            return {
                "success": False,
                "error": f"Path outside workspace: {file_path}",
                "operation": "read_file"
            }
        
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "operation": "read_file"
                }
            
            if not full_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {file_path}",
                    "operation": "read_file"
                }
            
            # Read file
            content = full_path.read_text(encoding="utf-8")
            
            return {
                "success": True,
                "content": content,
                "path": str(file_path),
                "size": len(content),
                "operation": "read_file"
            }
            
        except Exception as e:
            logger.error(f"File read failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "read_file"
            }
    
    async def write_file(self, file_path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        """
        Write file contents.
        
        Args:
            file_path: Path to file
            content: Content to write
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with success status
        """
        if not self._is_safe_path(file_path):
            return {
                "success": False,
                "error": f"Path outside workspace: {file_path}",
                "operation": "write_file"
            }
        
        try:
            full_path = self._resolve_path(file_path)
            
            # Check if file exists and we're not overwriting
            if full_path.exists() and not overwrite:
                return {
                    "success": False,
                    "error": f"File already exists: {file_path}",
                    "operation": "write_file"
                }
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(content, encoding="utf-8")
            
            logger.info(f"File written: {file_path} ({len(content)} bytes)")
            
            return {
                "success": True,
                "path": str(file_path),
                "size": len(content),
                "operation": "write_file"
            }
            
        except Exception as e:
            logger.error(f"File write failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "write_file"
            }
    
    async def list_directory(self, directory_path: str = ".") -> Dict[str, Any]:
        """
        List directory contents.
        
        Args:
            directory_path: Path to directory (defaults to workspace root)
            
        Returns:
            Dictionary with success status and directory listing
        """
        if not self._is_safe_path(directory_path):
            return {
                "success": False,
                "error": f"Path outside workspace: {directory_path}",
                "operation": "list_directory"
            }
        
        try:
            full_path = self._resolve_path(directory_path)
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory_path}",
                    "operation": "list_directory"
                }
            
            if not full_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {directory_path}",
                    "operation": "list_directory"
                }
            
            # List directory contents
            items = []
            for item in full_path.iterdir():
                items.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.workspace_root)),
                    "type": "file" if item.is_file() else "directory",
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            
            return {
                "success": True,
                "items": items,
                "path": str(directory_path),
                "count": len(items),
                "operation": "list_directory"
            }
            
        except Exception as e:
            logger.error(f"Directory listing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "list_directory"
            }
    
    async def search_files(self, pattern: str, root_dir: str = ".") -> Dict[str, Any]:
        """
        Search for files matching pattern.
        
        Args:
            pattern: Glob pattern to match (e.g., "*.py")
            root_dir: Root directory to search from
            
        Returns:
            Dictionary with success status and matching files
        """
        if not self._is_safe_path(root_dir):
            return {
                "success": False,
                "error": f"Path outside workspace: {root_dir}",
                "operation": "search_files"
            }
        
        try:
            full_root = self._resolve_path(root_dir)
            if not full_root.exists():
                return {
                    "success": False,
                    "error": f"Root directory not found: {root_dir}",
                    "operation": "search_files"
                }
            
            # Search for files matching pattern
            matches = []
            for file_path in full_root.rglob(pattern):
                if file_path.is_file() and self._is_safe_path(str(file_path.relative_to(self.workspace_root))):
                    matches.append({
                        "path": str(file_path.relative_to(self.workspace_root)),
                        "size": file_path.stat().st_size,
                    })
            
            return {
                "success": True,
                "matches": matches,
                "pattern": pattern,
                "count": len(matches),
                "operation": "search_files"
            }
            
        except Exception as e:
            logger.error(f"File search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "search_files"
            }
    
    async def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Delete file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with success status
        """
        if not self._is_safe_path(file_path):
            return {
                "success": False,
                "error": f"Path outside workspace: {file_path}",
                "operation": "delete_file"
            }
        
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "operation": "delete_file"
                }
            
            if not full_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {file_path}",
                    "operation": "delete_file"
                }
            
            # Delete file
            full_path.unlink()
            
            logger.warning(f"File deleted: {file_path}")
            
            return {
                "success": True,
                "path": str(file_path),
                "operation": "delete_file"
            }
            
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "delete_file"
            }
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute filesystem operation.
        
        Args:
            action: Operation to execute (read, write, list, search, delete)
            parameters: Operation parameters
            
        Returns:
            Dictionary with success status and result
        """
        if action == "read":
            file_path = parameters.get("path")
            if not file_path:
                return {"success": False, "error": "Missing path parameter"}
            return await self.read_file(file_path)
        
        elif action == "write":
            file_path = parameters.get("path")
            content = parameters.get("content")
            overwrite = parameters.get("overwrite", True)
            if not file_path or content is None:
                return {"success": False, "error": "Missing path or content parameter"}
            return await self.write_file(file_path, content, overwrite)
        
        elif action == "list":
            directory_path = parameters.get("path", ".")
            return await self.list_directory(directory_path)
        
        elif action == "search":
            pattern = parameters.get("pattern")
            root_dir = parameters.get("root_dir", ".")
            if not pattern:
                return {"success": False, "error": "Missing pattern parameter"}
            return await self.search_files(pattern, root_dir)
        
        elif action == "delete":
            file_path = parameters.get("path")
            if not file_path:
                return {"success": False, "error": "Missing path parameter"}
            return await self.delete_file(file_path)
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}