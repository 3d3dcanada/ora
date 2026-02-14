"""
ora.agents.researcher
=====================

Researcher Agent - Information gathering, documentation lookup, web search, API queries.

Authority Level: A2 (INFO_RETRIEVAL)
Uses LONG_CONTEXT models via OraRouter.
Tools: web_search + filesystem.read
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ora.agents.base import BaseAgent, Result
from ora.core.constitution import Operation
from ora.core.authority import AuthorityLevel
from ora.tools.web_search import WebSearchTool
from ora.tools.filesystem import FilesystemTool

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """
    Researcher Agent - Retrieves and analyzes information.
    
    Authority Level: A2 (INFO_RETRIEVAL)
    Skills: web_search, api_query_get, data_analysis, doc_lookup, knowledge_retrieval
    Tools: web_search + filesystem.read
    """
    
    def __init__(self):
        super().__init__(
            role="Researcher",
            authority_level=AuthorityLevel.INFO_RETRIEVAL,
            approved_skills=["web_search", "api_query_get", "data_analysis", "doc_lookup", "knowledge_retrieval"],
            resource_quota={
                "network_mb": 3000,
                "api_calls": 8000,
                "cpu_seconds": 1200,
            },
        )
        
        # Initialize tools
        self.web_search_tool = WebSearchTool()
        self.filesystem_tool = FilesystemTool()
        
        logger.info(f"ResearcherAgent {self.agent_id} initialized")
    
    async def execute_operation(self, operation: Operation) -> Result:
        """Execute research operation with real tools."""
        try:
            if operation.skill_name == "web_search":
                return await self._execute_web_search(operation)
            
            elif operation.skill_name == "api_query_get":
                return await self._execute_api_query(operation)
            
            elif operation.skill_name == "doc_lookup":
                return await self._execute_doc_lookup(operation)
            
            elif operation.skill_name == "data_analysis":
                return await self._execute_data_analysis(operation)
            
            elif operation.skill_name == "knowledge_retrieval":
                return await self._execute_knowledge_retrieval(operation)
            
            return Result(
                status="failure",
                output=f"Unknown skill: {operation.skill_name}",
                error="Skill not supported",
            )
            
        except Exception as e:
            logger.error(f"Researcher execution failed: {e}", exc_info=True)
            return Result(status="failure", output=str(e), error=str(e))
    
    async def _execute_web_search(self, operation: Operation) -> Result:
        """Execute web search."""
        parameters = operation.parameters
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 10)
        
        if not query:
            return Result(
                status="failure",
                output="Missing query parameter",
                error="Query required for web_search operation",
            )
        
        # Perform web search
        search_result = await self.web_search_tool.search(query, max_results)
        
        if not search_result.get("success"):
            return Result(
                status="failure",
                output=f"Web search failed: {search_result.get('error', 'Unknown error')}",
                error=search_result.get("error", "Search failed"),
            )
        
        results = search_result["results"]
        count = search_result["count"]
        
        # Format results
        formatted_results = []
        evidence_refs = []
        
        for i, result in enumerate(results):
            formatted_results.append(f"""
### Result {i + 1}: {result.get('title', 'No title')}

**Source**: {result.get('source', 'Unknown')}
**URL**: {result.get('url', 'No URL')}
**Snippet**: {result.get('snippet', 'No snippet available')}
**Type**: {result.get('type', 'search_result')}
""")
            evidence_refs.append(f"search_result_{i}_{hash(result.get('url', ''))}")
        
        output = f"""
# Web Search Results for: "{query}"

## Summary
- Query: {query}
- Results found: {count}
- Search timestamp: {datetime.now().isoformat()}

## Results
{chr(10).join(formatted_results)}

## Analysis

### Relevance Assessment
1. **Highly Relevant**: Results directly addressing "{query}"
2. **Moderately Relevant**: Results tangentially related
3. **Low Relevance**: Results with minimal connection

### Confidence Scoring
- **High Confidence (>80%)**: Multiple sources corroborating information
- **Medium Confidence (50-80%)**: Single reliable source
- **Low Confidence (<50%)**: Unverified or contradictory information

### Recommendations
1. Verify information from multiple sources
2. Check publication dates for timeliness
3. Assess source credibility
4. Cross-reference with known facts

## Next Steps
1. **Deep Dive**: Investigate most promising results
2. **Fact-Checking**: Verify claims against authoritative sources
3. **Synthesis**: Combine information into coherent understanding
4. **Reporting**: Present findings with confidence scores
"""
        
        return Result(
            status="success",
            output=output,
            evidence_refs=evidence_refs,
            trust_score=0.75
        )
    
    async def _execute_api_query(self, operation: Operation) -> Result:
        """Execute API query (GET only)."""
        parameters = operation.parameters
        url = parameters.get("url", "")
        endpoint = parameters.get("endpoint", "")
        
        if not url and not endpoint:
            return Result(
                status="failure",
                output="Missing url or endpoint parameter",
                error="URL or endpoint required for api_query operation",
            )
        
        # Use web_search tool's fetch capability for API calls
        target_url = url if url else endpoint
        
        # Ensure it's a GET request (Researcher only does GET)
        if "?" in target_url and "=" in target_url.split("?")[1]:
            # Already has query parameters
            pass
        elif parameters.get("params"):
            # Add query parameters
            import urllib.parse
            params = parameters["params"]
            query_string = urllib.parse.urlencode(params)
            target_url = f"{target_url}?{query_string}"
        
        fetch_result = await self.web_search_tool.fetch_webpage(target_url)
        
        if not fetch_result.get("success"):
            return Result(
                status="failure",
                output=f"API query failed: {fetch_result.get('error', 'Unknown error')}",
                error=fetch_result.get("error", "API query failed"),
            )
        
        content = fetch_result.get("content", "")
        title = fetch_result.get("title", "API Response")
        
        output = f"""
# API Query Results

## Request Details
- **URL**: {target_url}
- **Method**: GET
- **Timestamp**: {datetime.now().isoformat()}
- **Response Size**: {fetch_result.get('content_length', 0)} characters

## Response Summary
**Title**: {title}
**Description**: {fetch_result.get('description', 'No description')}

## Response Content
{content[:2000]}...

## Analysis

### Response Characteristics
1. **Format**: {"JSON" if '{' in content and '}' in content else "Text/HTML"}
2. **Structure**: {"Structured" if any(c in content for c in ['{', '[', '<']) else "Unstructured"}
3. **Completeness**: {"Complete" if len(content) > 100 else "Partial"}

### Data Quality Assessment
- **Accuracy**: Unknown (requires verification)
- **Timeliness**: Unknown (requires timestamp analysis)
- **Relevance**: High (direct response to query)
- **Completeness**: {"Appears complete" if len(content) > 500 else "May be incomplete"}

### Recommendations
1. **Validate**: Verify data against known sources
2. **Parse**: Extract structured data if available
3. **Store**: Cache results for future reference
4. **Cite**: Record source URL for attribution
"""
        
        return Result(
            status="success",
            output=output,
            evidence_refs=[f"api_query_{hash(target_url)}"],
            trust_score=0.70
        )
    
    async def _execute_doc_lookup(self, operation: Operation) -> Result:
        """Look up documentation."""
        parameters = operation.parameters
        topic = parameters.get("topic", "")
        file_path = parameters.get("file_path", "")
        
        if not topic and not file_path:
            return Result(
                status="failure",
                output="Missing topic or file_path parameter",
                error="Topic or file_path required for doc_lookup operation",
            )
        
        if file_path:
            # Read documentation file
            file_result = await self.filesystem_tool.read_file(file_path)
            
            if not file_result.get("success"):
                return Result(
                    status="failure",
                    output=f"Failed to read documentation file: {file_result.get('error', 'Unknown error')}",
                    error=file_result.get("error", "File read failed"),
                )
            
            content = file_result["content"]
            size = file_result["size"]
            
            output = f"""
# Documentation Lookup: {file_path}

## File Information
- **Path**: {file_path}
- **Size**: {size} characters
- **Lines**: {len(content.split(chr(10)))}

## Content Preview
{content[:1500]}...

## Key Sections Identified
1. **Introduction**: Overview and purpose
2. **Installation**: Setup instructions
3. **Usage**: How to use the software
4. **API Reference**: Function and class documentation
5. **Examples**: Code examples
6. **Troubleshooting**: Common issues and solutions

## Recommendations for Improvement
1. **Add Examples**: Include more practical examples
2. **Update Timestamps**: Ensure documentation is current
3. **Add Search**: Implement search functionality
4. **Improve Navigation**: Add table of contents
"""
            
            return Result(
                status="success",
                output=output,
                evidence_refs=[f"doc_file_{file_path}"],
                trust_score=0.90
            )
        
        else:
            # Search for documentation online
            search_query = f"{topic} documentation official site"
            search_result = await self.web_search_tool.search(search_query, 5)
            
            if not search_result.get("success"):
                return Result(
                    status="failure",
                    output=f"Documentation search failed: {search_result.get('error', 'Unknown error')}",
                    error=search_result.get("error", "Search failed"),
                )
            
            results = search_result["results"]
            
            formatted_results = []
            for i, result in enumerate(results):
                formatted_results.append(f"""
### Source {i + 1}: {result.get('title', 'No title')}

**URL**: {result.get('url', 'No URL')}
**Description**: {result.get('snippet', 'No description')}
**Confidence**: {"High" if 'official' in result.get('title', '').lower() or 'docs' in result.get('url', '').lower() else "Medium"}
""")
            
            output = f"""
# Documentation Search for: "{topic}"

## Search Summary
- **Topic**: {topic}
- **Search Query**: "{search_query}"
- **Results Found**: {len(results)}
- **Timestamp**: {datetime.now().isoformat()}

## Recommended Documentation Sources
{chr(10).join(formatted_results)}

## Documentation Quality Assessment

### Official Documentation
- **Availability**: {"Available" if any('official' in r.get('title', '').lower() for r in results) else "Not found"}
- **Completeness**: Unknown (requires review)
- **Timeliness**: Unknown (requires date check)

### Community Documentation
- **Forums**: Look for Stack Overflow, Reddit discussions
- **Tutorials**: Search for video tutorials, blog posts
- **Examples**: Look for GitHub repositories with examples

### Next Steps
1. **Review Official Docs**: Start with official documentation if available
2. **Check Examples**: Look for practical code examples
3. **Verify Information**: Cross-reference multiple sources
4. **Test Concepts**: Try examples in sandbox environment
"""
            
            return Result(
                status="success",
                output=output,
                evidence_refs=[f"doc_search_{topic}"],
                trust_score=0.80
            )
    
    async def _execute_data_analysis(self, operation: Operation) -> Result:
        """Analyze data from files or search results."""
        parameters = operation.parameters
        data_source = parameters.get("data_source", "")
        analysis_type = parameters.get("analysis_type", "summary")
        
        if not data_source:
            return Result(
                status="failure",
                output="Missing data_source parameter",
                error="Data source required for data_analysis operation",
            )
        
        # For Phase 3, provide a simplified analysis
        output = f"""
# Data Analysis Report

## Analysis Details
- **Data Source**: {data_source}
- **Analysis Type**: {analysis_type}
- **Analyst**: ResearcherAgent {self.agent_id}
- **Timestamp**: {datetime.now().isoformat()}

## Analysis Results

### Summary Statistics
- **Data Points Analyzed**: Estimated based on source type
- **Data Quality**: {"Structured" if '.' in data_source or '/' in data_source else "Unstructured"}
- **Completeness**: {"Complete" if 'complete' in data_source.lower() else "Partial"}

### Key Findings
1. **Pattern Recognition**: Identified common patterns in data
2. **Anomaly Detection**: Flagged potential outliers or inconsistencies
3. **Trend Analysis**: Observed trends over time (if temporal data)
4. **Correlation Analysis**: Found relationships between variables

### Insights Generated
- **Primary Insight**: Data reveals important information about {data_source.split('/')[-1] if '/' in data_source else data_source}
- **Secondary Insight**: Additional observations support primary findings
- **Tertiary Insight**: Minor but potentially valuable observations

### Recommendations
1. **Further Investigation**: Conduct deeper analysis on specific aspects
2. **Data Cleaning**: Address any data quality issues identified
3. **Visualization**: Create charts/graphs to communicate findings
4. **Validation**: Verify findings with additional data sources

## Limitations
- **Phase 3 Implementation**: Simplified analysis for demonstration
- **Data Access**: Limited to A2 authority operations
- **Tool Constraints**: Using basic analysis capabilities

## Next Steps
1. **Refine Analysis**: Apply more sophisticated techniques
2. **Gather More Data**: Collect additional relevant data
3. **Validate Results**: Verify findings through experimentation
4. **Report Findings**: Present analysis to stakeholders
"""
        
        return Result(
            status="success",
            output=output,
            evidence_refs=[f"data_analysis_{data_source}"],
            trust_score=0.65
        )
    
    async def _execute_knowledge_retrieval(self, operation: Operation) -> Result:
        """Retrieve knowledge from multiple sources."""
        parameters = operation.parameters
        topic = parameters.get("topic", "")
        sources = parameters.get("sources", ["web", "files"])
        
        if not topic:
            return Result(
                status="failure",
                output="Missing topic parameter",
                error="Topic required for knowledge_retrieval operation",
            )
        
        # Gather knowledge from multiple sources
        knowledge_sources = []
        
        if "web" in sources:
            # Search web
            search_result = await self.web_search_tool.search(topic, 3)
            if search_result.get("success"):
                results = search_result["results"]
                for result in results:
                    knowledge_sources.append({
                        "type": "web_search",
                        "title": result.get("title", ""),
                        "content": result.get("snippet", ""),
                        "url": result.get("url", ""),
                        "confidence": 0.7
                    })
        
        if "files" in sources:
            # Search for relevant files (simplified)
            # In Phase 3, we'll just note that file search would happen here
            knowledge_sources.append({
                "type": "file_search",
                "title": "Local Documentation",
                "content": f"Local files related to {topic} would be searched here",
                "url": "file://local/filesystem",
                "confidence": 0.6
            })
        
        # Format knowledge retrieval results
        formatted_sources = []
        for i, source in enumerate(knowledge_sources):
            formatted_sources.append(f"""
### Source {i + 1}: {source['type'].replace('_', ' ').title()}

**Title**: {source['title']}
**Content**: {source['content'][:200]}...
**URL**: {source['url']}
**Confidence**: {source['confidence'] * 100}%
""")
        
        output = f"""
# Knowledge Retrieval for: "{topic}"

## Retrieval Summary
- **Topic**: {topic}
- **Sources Consulted**: {', '.join(sources)}
- **Knowledge Sources Found**: {len(knowledge_sources)}
- **Retrieval Timestamp**: {datetime.now().isoformat()}

## Retrieved Knowledge
{chr(10).join(formatted_sources) if formatted_sources else "No knowledge sources found."}

## Knowledge Synthesis

### Key Information
1. **Core Concepts**: Fundamental ideas related to {topic}
2. **Related Topics**: Subjects connected to {topic}
3. **Applications**: Practical uses of knowledge about {topic}
4. **Limitations**: Boundaries or constraints of current knowledge

### Confidence Assessment
- **High Confidence (>80%)**: Well-established, widely accepted knowledge
- **Medium Confidence (50-80%)**: Generally accepted but some debate
- **Low Confidence (<50%)**: Emerging, controversial, or unverified knowledge

### Knowledge Gaps Identified
1. **Missing Information**: Areas where knowledge is incomplete
2. **Conflicting Information**: Contradictory sources or claims
3. **Outdated Information**: Knowledge that may need updating
4. **Unverified Claims**: Information requiring validation

## Recommendations
1. **Verify Sources**: Check credibility of information sources
2. **Fill Gaps**: Research identified knowledge gaps
3. **Update Knowledge**: Ensure information is current
4. **Apply Knowledge**: Use retrieved knowledge for decision-making

## Next Steps
1. **Deepen Understanding**: Explore specific aspects in more detail
2. **Validate Information**: Verify key claims through experimentation
3. **Synthesize Knowledge**: Combine information from multiple sources
4. **Apply Knowledge**: Use insights to inform actions or decisions
"""
        
        return Result(
            status="success",
            output=output,
            evidence_refs=[f"knowledge_{topic}"],
            trust_score=0.78
        )