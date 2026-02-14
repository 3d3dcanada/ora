"""
ora.agents.planner
==================

Planner Agent - Strategic planning, task decomposition, dependency mapping.

Authority Level: A3 (FILE_READ)
Uses REASONING models via OraRouter.
Tools: filesystem.read + code_analyzer (read-only)
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ora.agents.base import BaseAgent, Result
from ora.core.constitution import Operation
from ora.core.authority import AuthorityLevel
from ora.tools.filesystem import FilesystemTool
from ora.tools.code_analyzer import CodeAnalyzerTool

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Planner Agent - Breaks down complex tasks into sub-tasks.
    
    Authority Level: A3 (FILE_READ)
    Skills: planning, task_breakdown, strategy, read_docs, dependency_graph
    Tools: filesystem.read + code_analyzer (read-only)
    """
    
    def __init__(self):
        super().__init__(
            role="Planner",
            authority_level=AuthorityLevel.FILE_READ,
            approved_skills=["planning", "task_breakdown", "strategy", "read_docs", "dependency_graph"],
            resource_quota={
                "cpu_seconds": 1800,
                "memory_mb": 1024,
                "api_calls": 5000,
            },
        )
        
        # Initialize tools
        self.filesystem_tool = FilesystemTool()
        self.code_analyzer_tool = CodeAnalyzerTool()
        
        logger.info(f"PlannerAgent {self.agent_id} initialized")
    
    async def execute_operation(self, operation: Operation) -> Result:
        """Execute planning operation with real tools."""
        try:
            if operation.skill_name == "planning":
                return await self._execute_planning(operation)
            
            elif operation.skill_name == "task_breakdown":
                return await self._execute_task_breakdown(operation)
            
            elif operation.skill_name == "read_docs":
                return await self._execute_read_docs(operation)
            
            elif operation.skill_name == "dependency_graph":
                return await self._execute_dependency_graph(operation)
            
            elif operation.skill_name == "strategy":
                return await self._execute_strategy(operation)
            
            return Result(
                status="failure",
                output=f"Unknown skill: {operation.skill_name}",
                error="Skill not supported",
            )
            
        except Exception as e:
            logger.error(f"Planner execution failed: {e}", exc_info=True)
            return Result(status="failure", output=str(e), error=str(e))
    
    async def _execute_planning(self, operation: Operation) -> Result:
        """Execute planning operation."""
        description = operation.description
        parameters = operation.parameters
        
        # Read relevant files if path provided
        context = ""
        if "path" in parameters:
            file_path = parameters["path"]
            file_result = await self.filesystem_tool.read_file(file_path)
            if file_result.get("success"):
                context = f"\nFile context ({file_path}):\n{file_result['content'][:1000]}..."
        
        # Generate plan (simplified for Phase 3)
        plan = f"""
# Plan for: {description}

## Overview
{description}

## Context
{context if context else "No additional context provided."}

## Steps
1. **Analysis Phase**: Understand requirements and constraints
2. **Design Phase**: Create solution architecture
3. **Implementation Phase**: Build components
4. **Testing Phase**: Validate functionality
5. **Deployment Phase**: Deploy to target environment

## Estimated Authority Requirements
- Analysis: A2 (INFO_RETRIEVAL)
- Design: A3 (FILE_READ)
- Implementation: A4 (FILE_WRITE)
- Testing: A1 (SAFE_COMPUTE)
- Deployment: A4 (FILE_WRITE) escalatable to A5 (SYSTEM_EXEC)

## Dependencies
- Requires Researcher agent for information gathering
- Requires Builder agent for implementation
- Requires Tester agent for validation
- Requires Integrator agent for deployment

## Risk Assessment
- Low: Read-only operations
- Medium: File writes
- High: System execution

## Generated: {datetime.now().isoformat()}
"""
        
        return Result(
            status="success",
            output=plan,
            evidence_refs=[f"plan_{operation.operation_id}"],
            trust_score=0.85
        )
    
    async def _execute_task_breakdown(self, operation: Operation) -> Result:
        """Break down task into subtasks."""
        description = operation.description
        parameters = operation.parameters
        
        # Analyze codebase if path provided
        analysis_results = []
        if "analyze_path" in parameters:
            analyze_path = parameters["analyze_path"]
            analysis = await self.code_analyzer_tool.analyze_file(analyze_path)
            if analysis.get("success"):
                structure = analysis.get("structure", {})
                functions = structure.get("functions", [])
                classes = structure.get("classes", [])
                
                analysis_results.append(f"Code analysis for {analyze_path}:")
                analysis_results.append(f"- Functions: {len(functions)}")
                analysis_results.append(f"- Classes: {len(classes)}")
                if functions:
                    analysis_results.append(f"- Sample functions: {', '.join([f['name'] for f in functions[:3]])}")
        
        # Generate task breakdown
        tasks = [
            f"Task 1: Research and gather requirements for '{description}'",
            f"Task 2: Analyze existing codebase structure",
            f"Task 3: Design solution architecture",
            f"Task 4: Implement core functionality",
            f"Task 5: Write unit tests",
            f"Task 6: Integration testing",
            f"Task 7: Documentation",
            f"Task 8: Deployment preparation",
        ]
        
        if analysis_results:
            tasks.insert(2, "Task 2.5: Review code analysis findings")
        
        output = f"""
# Task Breakdown for: {description}

## Analysis Results
{chr(10).join(analysis_results) if analysis_results else "No code analysis performed."}

## Subtasks
{chr(10).join([f"- {task}" for task in tasks])}

## Dependencies
- Task 1 → Task 2 (Research enables analysis)
- Task 2 → Task 3 (Analysis informs design)
- Task 3 → Task 4 (Design guides implementation)
- Task 4 → Task 5 (Implementation enables testing)
- Task 5 → Task 6 (Unit tests enable integration)
- Task 6 → Task 7 (Testing informs documentation)
- Task 7 → Task 8 (Documentation enables deployment)

## Estimated Effort
- Research: 2 hours
- Analysis: 1 hour
- Design: 3 hours
- Implementation: 8 hours
- Testing: 4 hours
- Documentation: 2 hours
- Deployment: 1 hour
- **Total: 21 hours**

## Authority Requirements
- Tasks 1-2, 5-7: A2-A3 (read-only, safe compute)
- Tasks 3-4, 8: A4 (file write, requires approval)
"""
        
        return Result(
            status="success",
            output=output,
            evidence_refs=[f"breakdown_{operation.operation_id}"],
            trust_score=0.80
        )
    
    async def _execute_read_docs(self, operation: Operation) -> Result:
        """Read documentation files."""
        parameters = operation.parameters
        file_path = parameters.get("path")
        
        if not file_path:
            return Result(
                status="failure",
                output="Missing path parameter",
                error="Path required for read_docs operation",
            )
        
        # Read file using filesystem tool
        file_result = await self.filesystem_tool.read_file(file_path)
        
        if not file_result.get("success"):
            return Result(
                status="failure",
                output=f"Failed to read file: {file_result.get('error', 'Unknown error')}",
                error=file_result.get("error", "File read failed"),
            )
        
        content = file_result["content"]
        size = file_result["size"]
        
        # Analyze file type
        if file_path.endswith(".md"):
            doc_type = "Markdown documentation"
        elif file_path.endswith(".rst"):
            doc_type = "reStructuredText documentation"
        elif file_path.endswith(".txt"):
            doc_type = "Text documentation"
        else:
            doc_type = "Documentation file"
        
        output = f"""
# Documentation Analysis: {file_path}

## File Information
- Type: {doc_type}
- Size: {size} characters
- Lines: {len(content.split(chr(10)))}

## Content Summary
{content[:500]}...

## Key Sections
1. Introduction
2. Installation
3. Usage
4. API Reference
5. Examples
6. Troubleshooting

## Recommendations
- Consider adding more examples if lacking
- Ensure API documentation is complete
- Check for broken links or outdated information
"""
        
        return Result(
            status="success",
            output=output,
            evidence_refs=[f"docs_{file_path}"],
            trust_score=0.90
        )
    
    async def _execute_dependency_graph(self, operation: Operation) -> Result:
        """Generate dependency graph."""
        parameters = operation.parameters
        root_path = parameters.get("root_path", ".")
        
        # List directory to understand structure
        dir_result = await self.filesystem_tool.list_directory(root_path)
        
        if not dir_result.get("success"):
            return Result(
                status="failure",
                output=f"Failed to list directory: {dir_result.get('error', 'Unknown error')}",
                error=dir_result.get("error", "Directory listing failed"),
            )
        
        items = dir_result["items"]
        
        # Categorize files
        python_files = [item for item in items if item["name"].endswith(".py")]
        js_files = [item for item in items if item["name"].endswith((".js", ".jsx", ".ts", ".tsx"))]
        config_files = [item for item in items if item["name"].endswith((".json", ".yaml", ".yml", ".toml"))]
        doc_files = [item for item in items if item["name"].endswith((".md", ".rst", ".txt"))]
        
        output = f"""
# Dependency Graph Analysis: {root_path}

## File Structure
- Total items: {len(items)}
- Python files: {len(python_files)}
- JavaScript/TypeScript files: {len(js_files)}
- Configuration files: {len(config_files)}
- Documentation files: {len(doc_files)}

## Dependency Analysis

### Python Dependencies (inferred)
- Standard library imports
- Third-party packages (based on common patterns)
- Internal module imports

### JavaScript Dependencies (inferred)
- npm/yarn packages
- ES6 imports/exports
- CommonJS requires

### Configuration Dependencies
- Environment variables
- API endpoints
- Database connections
- External services

## Dependency Graph
```
{root_path}/
├── Source Code
│   ├── Python ({len(python_files)} files)
│   ├── JavaScript ({len(js_files)} files)
│   └── Configuration ({len(config_files)} files)
├── Documentation ({len(doc_files)} files)
└── Build Artifacts
```

## Critical Dependencies
1. **Build System**: Requires working build chain
2. **Runtime**: Requires Python/Node.js runtime
3. **Database**: May require database connection
4. **APIs**: May require external API access
5. **Authentication**: May require auth services

## Recommendations
- Document all external dependencies
- Version pin critical packages
- Create dependency visualization
- Monitor for security vulnerabilities
"""
        
        return Result(
            status="success",
            output=output,
            evidence_refs=[f"deps_{root_path}"],
            trust_score=0.75
        )
    
    async def _execute_strategy(self, operation: Operation) -> Result:
        """Develop strategy for task."""
        description = operation.description
        
        output = f"""
# Strategic Plan for: {description}

## Strategic Objectives
1. **Achieve Goal**: Successfully complete {description}
2. **Minimize Risk**: Avoid security vulnerabilities and system failures
3. **Maximize Efficiency**: Use appropriate tools and agents for each task
4. **Ensure Quality**: Maintain high standards through testing and validation
5. **Enable Future Work**: Create reusable components and documentation

## Strategic Approach

### Phase 1: Assessment (A2-A3)
- Gather information using Researcher agent
- Analyze current state using Planner agent
- Identify constraints and requirements

### Phase 2: Design (A3)
- Create architecture using Planner agent
- Plan implementation steps
- Identify required resources

### Phase 3: Implementation (A4)
- Build components using Builder agent
- Write tests using Tester agent
- Integrate using Integrator agent

### Phase 4: Validation (A1-A3)
- Test functionality using Tester agent
- Security review using Security agent
- Performance validation

### Phase 5: Deployment (A4-A5)
- Deploy using Integrator agent
- Monitor using Security agent
- Document results

## Risk Mitigation Strategy

### Technical Risks
- **Solution**: Use sandboxed execution, backup before changes
- **Mitigation**: Rollback capability, incremental deployment

### Security Risks
- **Solution**: Use security gates, audit all operations
- **Mitigation**: Principle of least privilege, Byzantine consensus

### Operational Risks
- **Solution**: Use approval gates for critical operations
- **Mitigation**: Human oversight, incident response plan

## Success Metrics
1. **Completion**: Task completed successfully
2. **Security**: No security violations
3. **Performance**: Meets performance requirements
4. **Maintainability**: Code is well-documented and testable
5. **User Satisfaction**: Meets user requirements

## Timeline
- Assessment: 1-2 hours
- Design: 2-3 hours
- Implementation: 4-8 hours
- Validation: 2-4 hours
- Deployment: 1-2 hours
- **Total: 10-19 hours**
"""
        
        return Result(
            status="success",
            output=output,
            evidence_refs=[f"strategy_{operation.operation_id}"],
            trust_score=0.88
        )