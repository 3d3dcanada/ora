"""
ora.tools.code_analyzer
========================

Code Analyzer Tool - Static code analysis and vulnerability detection.

Port from BUZZ Neural Core with simplified implementation for Phase 3.
Read-only tool, A1 authority sufficient.
"""

import ast
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CodeAnalyzerTool:
    """
    Code analysis tool for static analysis and vulnerability detection.
    
    Read-only tool, A1 authority sufficient.
    """
    
    def __init__(self):
        """Initialize code analyzer tool."""
        logger.info("CodeAnalyzerTool initialized")
    
    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze file for code structure and potential issues.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            Dictionary with analysis results
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "operation": "analyze_file"
                }
            
            # Read file content
            content = file_path_obj.read_text(encoding="utf-8", errors="replace")
            
            # Determine file type
            file_ext = file_path_obj.suffix.lower()
            
            if file_ext == ".py":
                return await self._analyze_python(content, file_path)
            elif file_ext in [".js", ".jsx", ".ts", ".tsx"]:
                return await self._analyze_javascript(content, file_path)
            elif file_ext in [".json", ".yaml", ".yml", ".toml"]:
                return await self._analyze_config(content, file_path, file_ext)
            else:
                return await self._analyze_generic(content, file_path)
                
        except Exception as e:
            logger.error(f"File analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "analyze_file"
            }
    
    async def _analyze_python(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze Python code."""
        try:
            tree = ast.parse(content)
            
            # Extract basic structure
            imports = []
            functions = []
            classes = []
            variables = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
                elif isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args)
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                    })
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.append(target.id)
            
            # Check for potential vulnerabilities
            vulnerabilities = []
            
            # Check for eval()
            if "eval(" in content:
                vulnerabilities.append({
                    "type": "dangerous_function",
                    "message": "eval() function detected - potential security risk",
                    "severity": "high"
                })
            
            # Check for exec()
            if "exec(" in content:
                vulnerabilities.append({
                    "type": "dangerous_function",
                    "message": "exec() function detected - potential security risk",
                    "severity": "high"
                })
            
            # Check for hardcoded secrets patterns
            secret_patterns = [
                r"password\s*=\s*['\"].*?['\"]",
                r"api_key\s*=\s*['\"].*?['\"]",
                r"secret\s*=\s*['\"].*?['\"]",
                r"token\s*=\s*['\"].*?['\"]",
            ]
            
            for pattern in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({
                        "type": "hardcoded_secret",
                        "message": "Potential hardcoded secret detected",
                        "severity": "medium"
                    })
                    break
            
            return {
                "success": True,
                "language": "python",
                "file_path": file_path,
                "line_count": len(content.split('\n')),
                "structure": {
                    "imports": imports,
                    "functions": functions,
                    "classes": classes,
                    "variables": variables[:10]  # Limit variables
                },
                "vulnerabilities": vulnerabilities,
                "operation": "analyze_file"
            }
            
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Python syntax error: {str(e)}",
                "line": e.lineno,
                "operation": "analyze_file"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "analyze_file"
            }
    
    async def _analyze_javascript(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript code."""
        try:
            # Basic JavaScript analysis
            line_count = len(content.split('\n'))
            
            # Count functions (simple regex)
            function_pattern = r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*\([^)]*\)\s*=>|let\s+(\w+)\s*=\s*\([^)]*\)\s*=>)"
            function_matches = re.findall(function_pattern, content)
            functions = []
            
            for match in function_matches:
                for name in match:
                    if name:
                        functions.append(name)
                        break
            
            # Check for potential vulnerabilities
            vulnerabilities = []
            
            # Check for eval()
            if "eval(" in content:
                vulnerabilities.append({
                    "type": "dangerous_function",
                    "message": "eval() function detected - potential security risk",
                    "severity": "high"
                })
            
            # Check for innerHTML
            if "innerHTML" in content and "=" in content.split("innerHTML")[1][:10]:
                vulnerabilities.append({
                    "type": "xss_vulnerability",
                    "message": "innerHTML assignment detected - potential XSS vulnerability",
                    "severity": "medium"
                })
            
            return {
                "success": True,
                "language": "javascript",
                "file_path": file_path,
                "line_count": line_count,
                "structure": {
                    "functions": functions[:20],  # Limit functions
                },
                "vulnerabilities": vulnerabilities,
                "operation": "analyze_file"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "analyze_file"
            }
    
    async def _analyze_config(self, content: str, file_path: str, file_ext: str) -> Dict[str, Any]:
        """Analyze configuration files."""
        try:
            line_count = len(content.split('\n'))
            
            # Check for potential issues
            vulnerabilities = []
            
            # Check for hardcoded secrets in config files
            secret_patterns = [
                r"password\s*[:=]\s*['\"].*?['\"]",
                r"api_key\s*[:=]\s*['\"].*?['\"]",
                r"secret\s*[:=]\s*['\"].*?['\"]",
                r"token\s*[:=]\s*['\"].*?['\"]",
            ]
            
            for pattern in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({
                        "type": "hardcoded_secret",
                        "message": "Potential hardcoded secret in configuration file",
                        "severity": "high"
                    })
                    break
            
            return {
                "success": True,
                "language": "config",
                "file_path": file_path,
                "line_count": line_count,
                "structure": {
                    "file_type": file_ext,
                },
                "vulnerabilities": vulnerabilities,
                "operation": "analyze_file"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "analyze_file"
            }
    
    async def _analyze_generic(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze generic file types."""
        try:
            line_count = len(content.split('\n'))
            char_count = len(content)
            
            return {
                "success": True,
                "language": "generic",
                "file_path": file_path,
                "line_count": line_count,
                "char_count": char_count,
                "operation": "analyze_file"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "analyze_file"
            }
    
    async def find_vulnerabilities(self, file_path: str) -> Dict[str, Any]:
        """
        Find vulnerabilities in code file.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            Dictionary with vulnerability findings
        """
        analysis = await self.analyze_file(file_path)
        
        if not analysis.get("success"):
            return analysis
        
        # Extract vulnerabilities from analysis
        vulnerabilities = analysis.get("vulnerabilities", [])
        
        return {
            "success": True,
            "file_path": file_path,
            "vulnerabilities": vulnerabilities,
            "count": len(vulnerabilities),
            "operation": "find_vulnerabilities"
        }
    
    async def get_complexity(self, file_path: str) -> Dict[str, Any]:
        """
        Get code complexity metrics.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            Dictionary with complexity metrics
        """
        analysis = await self.analyze_file(file_path)
        
        if not analysis.get("success"):
            return analysis
        
        # Simple complexity metrics
        line_count = analysis.get("line_count", 0)
        structure = analysis.get("structure", {})
        
        function_count = len(structure.get("functions", []))
        class_count = len(structure.get("classes", []))
        
        # Calculate simple complexity score
        complexity_score = 0
        if line_count > 0:
            complexity_score = (function_count * 5 + class_count * 10) / line_count
        
        return {
            "success": True,
            "file_path": file_path,
            "metrics": {
                "line_count": line_count,
                "function_count": function_count,
                "class_count": class_count,
                "complexity_score": round(complexity_score, 3)
            },
            "operation": "get_complexity"
        }
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute code analysis operation.
        
        Args:
            action: Operation to execute (analyze_file, find_vulnerabilities, get_complexity)
            parameters: Operation parameters
            
        Returns:
            Dictionary with success status and result
        """
        if action == "analyze_file":
            file_path = parameters.get("path")
            if not file_path:
                return {"success": False, "error": "Missing path parameter"}
            return await self.analyze_file(file_path)
        
        elif action == "find_vulnerabilities":
            file_path = parameters.get("path")
            if not file_path:
                return {"success": False, "error": "Missing path parameter"}
            return await self.find_vulnerabilities(file_path)
        
        elif action == "get_complexity":
            file_path = parameters.get("path")
            if not file_path:
                return {"success": False, "error": "Missing path parameter"}
            return await self.get_complexity(file_path)
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    async def run(self, params: Dict[str, Any], authority: int) -> Dict[str, Any]:
        """
        Run method for compatibility with agent tool interface.
        
        Args:
            params: Parameters dictionary with 'action' and other params
            authority: Authority level (not used in this tool)
            
        Returns:
            Dictionary with success status and result
        """
        action = params.get("action", "analyze_file")
        parameters = {k: v for k, v in params.items() if k != "action"}
        return await self.execute(action, parameters)