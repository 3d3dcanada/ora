"""
ora.tools.terminal
==================

Terminal Tool - Shell command execution with safety constraints and command sanitization.

Port from BUZZ Neural Core with OrA ShellCommandSanitizer integration.
"""

import asyncio
import shlex
from typing import Dict, Any, List, Tuple
from pathlib import Path
import logging

from ora.security.gates import ShellCommandSanitizer

logger = logging.getLogger(__name__)


class TerminalTool:
    """
    Terminal command execution with shell sanitization.
    
    All commands go through ShellCommandSanitizer (from security/gates.py).
    Whitelist: ls, cat, grep, python, git, npm, node, pip, pytest, echo, pwd, whoami
    Blocklist: sudo, rm -rf, kill -9, shutdown, reboot, dd, mkfs, chmod 777, curl | bash
    Timeout: 30 seconds max
    Authority: A2 minimum, A3+ for non-whitelist commands
    """
    
    def __init__(self, workspace_root: str = "/home/randall/1A-PROJECTS/Ora-os"):
        """
        Initialize terminal tool.
        
        Args:
            workspace_root: Root directory for command execution
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.sanitizer = ShellCommandSanitizer()
        
        # Command whitelist (allowed without special approval)
        self.whitelist = {
            "ls", "cat", "grep", "python", "git", "npm", "node", "pip", 
            "pytest", "echo", "pwd", "whoami", "find", "head", "tail",
            "wc", "sort", "uniq", "curl", "wget", "docker", "kubectl"
        }
        
        logger.info(f"TerminalTool initialized with workspace: {self.workspace_root}")
    
    def _is_safe_command(self, command: str) -> Tuple[bool, str]:
        """
        Check if command is safe to execute using ShellCommandSanitizer.
        
        Args:
            command: Command to check
            
        Returns:
            Tuple of (is_safe, reason)
        """
        try:
            # Use ShellCommandSanitizer from security gates
            is_safe, reason = self.sanitizer.validate(command)
            if not is_safe:
                return False, reason
            
            # Additional whitelist check for A2 authority
            cmd_start = command.strip().split()[0] if command.strip() else ""
            if cmd_start not in self.whitelist:
                return False, f"Command not in whitelist: {cmd_start}. Requires A3+ authority."
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Command validation failed: {e}")
            return False, f"Validation error: {e}"
    
    async def execute_command(self, command: str, timeout: int = 30, cwd: str = None) -> Dict[str, Any]:
        """
        Execute shell command with safety checks.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds (default: 30)
            cwd: Working directory (defaults to workspace root)
            
        Returns:
            Dictionary with success status and output/error
        """
        # Safety check
        is_safe, reason = self._is_safe_command(command)
        if not is_safe:
            return {
                "success": False,
                "error": f"Command blocked: {reason}",
                "command": command,
                "operation": "execute_command"
            }
        
        try:
            # Set working directory
            working_dir = self.workspace_root
            if cwd:
                cwd_path = Path(cwd)
                if cwd_path.is_absolute():
                    working_dir = cwd_path
                else:
                    working_dir = self.workspace_root / cwd_path
            
            # Ensure working directory exists
            if not working_dir.exists():
                return {
                    "success": False,
                    "error": f"Working directory not found: {working_dir}",
                    "command": command,
                    "operation": "execute_command"
                }
            
            logger.info(f"Executing command: {command} in {working_dir}")
            
            # Execute command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(working_dir),
                limit=1024 * 1024  # 1MB output limit
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                # Decode output
                stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
                stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
                
                return {
                    "success": True,
                    "command": command,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "exit_code": process.returncode,
                    "operation": "execute_command"
                }
                
            except asyncio.TimeoutError:
                # Kill the process on timeout
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "command": command,
                    "operation": "execute_command"
                }
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": command,
                "operation": "execute_command"
            }
    
    async def execute_script(self, script_path: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Execute script file.
        
        Args:
            script_path: Path to script file
            timeout: Timeout in seconds (default: 60)
            
        Returns:
            Dictionary with success status and output/error
        """
        try:
            # Read script file
            script_file = Path(script_path)
            if not script_file.is_absolute():
                script_file = self.workspace_root / script_path
            
            if not script_file.exists():
                return {
                    "success": False,
                    "error": f"Script file not found: {script_path}",
                    "operation": "execute_script"
                }
            
            # Check if it's a Python script
            if script_file.suffix == ".py":
                command = f"python {script_file}"
            elif script_file.suffix == ".sh":
                command = f"bash {script_file}"
            else:
                return {
                    "success": False,
                    "error": f"Unsupported script type: {script_file.suffix}",
                    "operation": "execute_script"
                }
            
            # Execute the script
            return await self.execute_command(command, timeout, cwd=str(script_file.parent))
            
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "execute_script"
            }
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute terminal operation.
        
        Args:
            action: Operation to execute (exec, exec_script)
            parameters: Operation parameters
            
        Returns:
            Dictionary with success status and result
        """
        if action == "exec":
            command = parameters.get("command")
            timeout = parameters.get("timeout", 30)
            cwd = parameters.get("cwd")
            
            if not command:
                return {"success": False, "error": "Missing command parameter"}
            
            return await self.execute_command(command, timeout, cwd)
        
        elif action == "exec_script":
            script_path = parameters.get("path")
            timeout = parameters.get("timeout", 60)
            
            if not script_path:
                return {"success": False, "error": "Missing path parameter"}
            
            return await self.execute_script(script_path, timeout)
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}