#!/usr/bin/env python3
"""
TAURUS PropertyVet™ - MCP Orchestration Controller
Coordinates all MCP agents for comprehensive background checks
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import os

# Add the agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '01-AGENTS'))

# Import all MCP agents
from chromedata_mcp_agent import ChromeDataMCPAgent
from perplexity_mcp_agent import PerplexityMCPAgent
from firecrawl_mcp_agent import FirecrawlMCPAgent
from github_mcp_agent import GitHubMCPAgent
from dev21_mcp_agent import Dev21MCPAgent
from spiderfoot_osint_agent import SpiderFootOSINTAgent

class MCPOrchestrationController:
    """MCP Orchestration Controller for PropertyVet™"""
    
    def __init__(self, config_path: str = None):
        self.controller_id = "mcp_orchestration_controller"
        self.version = "1.0.0"
        self.status = "initializing"
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize agents
        self.agents = {
            "chromedata": ChromeDataMCPAgent(),
            "perplexity": PerplexityMCPAgent(),
            "firecrawl": FirecrawlMCPAgent(),
            "github": GitHubMCPAgent(),
            "dev21": Dev21MCPAgent(),
            "spiderfoot": SpiderFootOSINTAgent()
        }
        
        self.active_workflows = {}
        self.agent_status = {}
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load orchestration configuration"""
        default_config = {
            "workflow_templates": {
                "basic_background_check": {
                    "agents": ["chromedata", "firecrawl"],
                    "parallel_execution": True,
                    "timeout": 600,  # 10 minutes
                    "retry_attempts": 2
                },
                "standard_background_check": {
                    "agents": ["chromedata", "perplexity", "firecrawl"],
                    "parallel_execution": True,
                    "timeout": 1200,  # 20 minutes
                    "retry_attempts": 2
                },
                "comprehensive_background_check": {
                    "agents": ["chromedata", "perplexity", "firecrawl", "spiderfoot"],
                    "parallel_execution": True,
                    "timeout": 1800,  # 30 minutes
                    "retry_attempts": 3
                },
                "enterprise_background_check": {
                    "agents": ["chromedata", "perplexity", "firecrawl", "spiderfoot", "dev21"],
                    "parallel_execution": True,
                    "timeout": 2400,  # 40 minutes
                    "retry_attempts": 3
                }
            },
            "orchestration_settings": {
                "max_concurrent_workflows": 10,
                "agent_health_check_interval": 30,  # seconds
                "workflow_persistence": True,
                "real_time_monitoring": True
            },
            "quality_assurance": {
                "min_data_sources": 3,
                "confidence_threshold": 75,
                "cross_validation": True,
                "human_review_threshold": 50
            },
            "performance_optimization": {
                "load_balancing": True,
                "caching": True,
                "result_aggregation": True,
                "intelligent_routing": True
            }
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                custom_config = json.load(f)
                default_config.update(custom_config)
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for MCP Orchestration Controller"""
        logger = logging.getLogger(self.controller_id)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize MCP Orchestration Controller"""
        try:
            self.logger.info("Initializing MCP Orchestration Controller...")
            
            # Initialize all agents
            initialization_results = {}
            for agent_name, agent in self.agents.items():
                self.logger.info(f"Initializing {agent_name} agent...")
                result = await agent.initialize()
                initialization_results[agent_name] = result
                self.agent_status[agent_name] = result.get("status", "error")
            
            # Check if minimum agents are available
            active_agents = [name for name, status in self.agent_status.items() if status == "success"]
            
            if len(active_agents) >= 2:  # Minimum 2 agents required
                self.status = "active"
                self.logger.info("MCP Orchestration Controller initialized successfully")
                
                return {
                    "status": "success",
                    "controller_id": self.controller_id,
                    "version": self.version,
                    "active_agents": active_agents,
                    "total_agents": len(self.agents),
                    "agent_initialization": initialization_results,
                    "workflow_templates": list(self.config["workflow_templates"].keys()),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                self.status = "degraded"
                return {
                    "status": "degraded",
                    "error": "Insufficient agents initialized",
                    "active_agents": active_agents,
                    "agent_initialization": initialization_results,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.status = "error"
            self.logger.error(f"Failed to initialize MCP Orchestration Controller: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def execute_background_check_workflow(self, applicant_data: Dict[str, Any], check_level: str = "standard") -> Dict[str, Any]:
        """Execute comprehensive background check workflow"""
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            self.logger.info(f"Starting background check workflow: {workflow_id}")
            
            # Validate check level
            template_key = f"{check_level}_background_check"
            if template_key not in self.config["workflow_templates"]:
                raise ValueError(f"Invalid check level: {check_level}")
            
            template = self.config["workflow_templates"][template_key]
            
            # Create workflow session
            self.active_workflows[workflow_id] = {
                "start_time": datetime.now(),
                "status": "processing",
                "check_level": check_level,
                "applicant_data": applicant_data,
                "template": template
            }
            
            workflow_results = {
                "workflow_id": workflow_id,
                "check_level": check_level,
                "applicant_name": applicant_data.get("applicantName", ""),
                "started_at": datetime.now().isoformat(),
                "agent_results": {},
                "workflow_metrics": {}
            }
            
            # Execute agents based on template
            required_agents = template["agents"]
            available_agents = [agent for agent in required_agents if self.agent_status.get(agent) == "success"]
            
            if not available_agents:
                raise Exception("No available agents for this workflow")
            
            # Execute agent tasks
            if template["parallel_execution"]:
                agent_tasks = []
                for agent_name in available_agents:
                    if agent_name == "chromedata":
                        task = self.agents[agent_name].execute_background_check(applicant_data)
                    elif agent_name == "perplexity":
                        task = self.agents[agent_name].research_applicant(applicant_data)
                    elif agent_name == "firecrawl":
                        task = self.agents[agent_name].scrape_background_data(applicant_data)
                    elif agent_name == "spiderfoot":
                        task = self.agents[agent_name].conduct_osint_investigation(applicant_data, check_level)
                    elif agent_name == "dev21":
                        task = self.agents[agent_name].get_system_health()
                    else:
                        continue
                    
                    agent_tasks.append((agent_name, task))
                
                # Execute tasks concurrently
                results = await asyncio.gather(*[task for _, task in agent_tasks], return_exceptions=True)
                
                # Process results
                for i, (agent_name, _) in enumerate(agent_tasks):
                    if not isinstance(results[i], Exception):
                        workflow_results["agent_results"][agent_name] = results[i]
                    else:
                        workflow_results["agent_results"][agent_name] = {
                            "status": "error",
                            "error": str(results[i]),
                            "timestamp": datetime.now().isoformat()
                        }
            
            # Aggregate and analyze results
            aggregated_results = await self._aggregate_workflow_results(workflow_results)
            workflow_results["aggregated_analysis"] = aggregated_results
            
            # Generate final recommendation
            final_recommendation = await self._generate_final_recommendation(workflow_results)
            workflow_results["final_recommendation"] = final_recommendation
            
            # Calculate workflow metrics
            workflow_metrics = await self._calculate_workflow_metrics(workflow_results)
            workflow_results["workflow_metrics"] = workflow_metrics
            
            # Update workflow status
            self.active_workflows[workflow_id]["status"] = "completed"
            self.active_workflows[workflow_id]["results"] = workflow_results
            
            workflow_results["completed_at"] = datetime.now().isoformat()
            workflow_results["status"] = "success"
            
            self.logger.info(f"Background check workflow completed: {workflow_id}")
            return workflow_results
            
        except Exception as e:
            self.logger.error(f"Workflow failed for {workflow_id}: {str(e)}")
            
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = str(e)
            
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _aggregate_workflow_results(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from all agents"""
        try:
            self.logger.info("Aggregating workflow results...")
            
            agent_results = workflow_data.get("agent_results", {})
            
            # Collect all data points
            aggregated_data = {
                "identity_verification": {},
                "background_check": {},
                "employment_verification": {},
                "public_records": {},
                "digital_footprint": {},
                "risk_assessment": {}
            }
            
            confidence_scores = []
            data_sources_count = 0
            
            # Process ChromeData results
            if "chromedata" in agent_results and agent_results["chromedata"].get("status") == "success":
                chromedata_results = agent_results["chromedata"]
                if "components" in chromedata_results:
                    components = chromedata_results["components"]
                    
                    if "identity_verification" in components:
                        aggregated_data["identity_verification"]["chromedata"] = components["identity_verification"]
                        confidence_scores.append(components["identity_verification"].get("confidence_score", 0))
                    
                    if "public_records" in components:
                        aggregated_data["public_records"]["chromedata"] = components["public_records"]
                    
                    if "employment_verification" in components:
                        aggregated_data["employment_verification"]["chromedata"] = components["employment_verification"]
                
                data_sources_count += 1
            
            # Process Perplexity results
            if "perplexity" in agent_results and agent_results["perplexity"].get("status") == "success":
                perplexity_results = agent_results["perplexity"]
                if "research_categories" in perplexity_results:
                    categories = perplexity_results["research_categories"]
                    
                    for category, data in categories.items():
                        if category in aggregated_data:
                            aggregated_data[category]["perplexity"] = data
                            if "confidence_score" in data:
                                confidence_scores.append(data["confidence_score"])
                
                data_sources_count += 1
            
            # Process Firecrawl results
            if "firecrawl" in agent_results and agent_results["firecrawl"].get("status") == "success":
                firecrawl_results = agent_results["firecrawl"]
                if "data_sources" in firecrawl_results:
                    sources = firecrawl_results["data_sources"]
                    
                    for source, data in sources.items():
                        if source == "public_records":
                            aggregated_data["public_records"]["firecrawl"] = data
                        elif source == "employment_data":
                            aggregated_data["employment_verification"]["firecrawl"] = data
                        elif source == "social_media_presence":
                            aggregated_data["digital_footprint"]["firecrawl"] = data
                
                data_sources_count += 1
            
            # Process SpiderFoot results
            if "spiderfoot" in agent_results and agent_results["spiderfoot"].get("status") == "success":
                spiderfoot_results = agent_results["spiderfoot"]
                if "investigation_categories" in spiderfoot_results:
                    categories = spiderfoot_results["investigation_categories"]
                    
                    for category, data in categories.items():
                        if "confidence_score" in data:
                            confidence_scores.append(data["confidence_score"])
                        
                        if category == "identity_intelligence":
                            aggregated_data["identity_verification"]["spiderfoot"] = data
                        elif category == "background_intelligence":
                            aggregated_data["background_check"]["spiderfoot"] = data
                        elif category == "digital_footprint":
                            aggregated_data["digital_footprint"]["spiderfoot"] = data
                
                data_sources_count += 1
            
            # Calculate overall confidence
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                "aggregation_summary": {
                    "data_sources_integrated": data_sources_count,
                    "confidence_scores_collected": len(confidence_scores),
                    "overall_confidence": round(overall_confidence, 2),
                    "data_completeness": (data_sources_count / len(workflow_data.get("agent_results", {}))) * 100
                },
                "integrated_data": aggregated_data,
                "cross_validation": {
                    "identity_verified": len([d for d in aggregated_data["identity_verification"].values() if d.get("status") == "verified"]) >= 1,
                    "background_clear": len([d for d in aggregated_data["background_check"].values() if d.get("status") == "completed"]) >= 1,
                    "employment_confirmed": len([d for d in aggregated_data["employment_verification"].values() if d.get("status") == "verified"]) >= 1
                },
                "aggregation_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Result aggregation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_final_recommendation(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final recommendation based on all agent results"""
        try:
            self.logger.info("Generating final recommendation...")
            
            aggregated_analysis = workflow_data.get("aggregated_analysis", {})
            aggregation_summary = aggregated_analysis.get("aggregation_summary", {})
            cross_validation = aggregated_analysis.get("cross_validation", {})
            
            overall_confidence = aggregation_summary.get("overall_confidence", 0)
            
            # Determine recommendation
            if overall_confidence >= 85 and all(cross_validation.values()):
                recommendation = "approve"
                risk_level = "low"
                confidence_level = "high"
            elif overall_confidence >= 70 and sum(cross_validation.values()) >= 2:
                recommendation = "approve_with_conditions"
                risk_level = "medium"
                confidence_level = "medium"
            elif overall_confidence >= 50:
                recommendation = "manual_review"
                risk_level = "medium"
                confidence_level = "low"
            else:
                recommendation = "decline"
                risk_level = "high"
                confidence_level = "very_low"
            
            return {
                "final_decision": {
                    "recommendation": recommendation,
                    "risk_level": risk_level,
                    "confidence_level": confidence_level,
                    "overall_score": round(overall_confidence, 2)
                },
                "supporting_evidence": {
                    "identity_verified": cross_validation.get("identity_verified", False),
                    "background_clear": cross_validation.get("background_clear", False),
                    "employment_confirmed": cross_validation.get("employment_confirmed", False),
                    "data_sources_count": aggregation_summary.get("data_sources_integrated", 0)
                },
                "recommended_actions": self._get_recommended_actions(recommendation, risk_level),
                "quality_metrics": {
                    "data_completeness": aggregation_summary.get("data_completeness", 0),
                    "confidence_threshold_met": overall_confidence >= self.config["quality_assurance"]["confidence_threshold"],
                    "min_sources_met": aggregation_summary.get("data_sources_integrated", 0) >= self.config["quality_assurance"]["min_data_sources"]
                },
                "recommendation_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Final recommendation generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_recommended_actions(self, recommendation: str, risk_level: str) -> List[str]:
        """Get recommended actions based on decision"""
        actions = []
        
        if recommendation == "approve":
            actions = [
                "Proceed with standard lease terms",
                "Standard security deposit required",
                "Consider preferred tenant benefits",
                "Schedule lease signing appointment"
            ]
        elif recommendation == "approve_with_conditions":
            actions = [
                "Approve with additional security deposit",
                "Require co-signer or guarantor",
                "Consider shorter initial lease term",
                "Additional income verification required"
            ]
        elif recommendation == "manual_review":
            actions = [
                "Schedule manual review with leasing manager",
                "Request additional documentation",
                "Consider alternative verification methods",
                "Set review deadline within 48 hours"
            ]
        else:  # decline
            actions = [
                "Decline application professionally",
                "Provide adverse action notice if required",
                "Suggest alternative properties if appropriate",
                "Document decision reasoning"
            ]
        
        return actions
    
    async def _calculate_workflow_metrics(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate workflow performance metrics"""
        try:
            start_time = datetime.fromisoformat(workflow_data.get("started_at", datetime.now().isoformat()))
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            agent_results = workflow_data.get("agent_results", {})
            successful_agents = len([r for r in agent_results.values() if r.get("status") in ["success", "completed"]])
            total_agents = len(agent_results)
            
            return {
                "performance_metrics": {
                    "total_duration_seconds": round(total_duration, 2),
                    "agent_success_rate": (successful_agents / total_agents * 100) if total_agents > 0 else 0,
                    "agents_executed": total_agents,
                    "agents_successful": successful_agents,
                    "average_agent_duration": round(total_duration / total_agents, 2) if total_agents > 0 else 0
                },
                "quality_metrics": {
                    "data_confidence": workflow_data.get("aggregated_analysis", {}).get("aggregation_summary", {}).get("overall_confidence", 0),
                    "cross_validation_success": sum(workflow_data.get("aggregated_analysis", {}).get("cross_validation", {}).values()),
                    "recommendation_confidence": workflow_data.get("final_recommendation", {}).get("final_decision", {}).get("confidence_level", "unknown")
                },
                "efficiency_metrics": {
                    "cost_per_check": 2.50,  # Estimated cost
                    "time_efficiency": "excellent" if total_duration < 300 else "good" if total_duration < 600 else "needs_improvement",
                    "resource_utilization": (successful_agents / 6) * 100  # Based on 6 total agents
                },
                "metrics_calculated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Workflow metrics calculation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a specific workflow"""
        if workflow_id not in self.active_workflows:
            return {
                "status": "error",
                "error": "Workflow not found",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "workflow_id": workflow_id,
            "status": self.active_workflows[workflow_id]["status"],
            "results": self.active_workflows[workflow_id].get("results", {}),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "controller_status": self.status,
            "agent_status": self.agent_status,
            "active_workflows": len(self.active_workflows),
            "system_health": "healthy" if self.status == "active" else "degraded",
            "capabilities": list(self.config["workflow_templates"].keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup MCP Orchestration Controller and all agents"""
        try:
            self.logger.info("Cleaning up MCP Orchestration Controller...")
            
            # Cleanup all agents
            cleanup_results = {}
            for agent_name, agent in self.agents.items():
                try:
                    result = await agent.cleanup()
                    cleanup_results[agent_name] = result
                except Exception as e:
                    cleanup_results[agent_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            self.status = "stopped"
            self.active_workflows.clear()
            self.agent_status.clear()
            
            self.logger.info("MCP Orchestration Controller cleanup completed")
            
            return {
                "status": "success",
                "message": "Controller and all agents cleaned up",
                "agent_cleanup_results": cleanup_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# PropertyVet™ Integration
async def main():
    """Main execution for testing MCP Orchestration Controller"""
    controller = MCPOrchestrationController()
    
    # Initialize controller
    init_result = await controller.initialize()
    print(f"Controller Initialization: {json.dumps(init_result, indent=2)}")
    
    if init_result["status"] in ["success", "degraded"]:
        # Test background check workflow
        test_applicant = {
            "applicantName": "John Doe",
            "email": "john.doe@email.com",
            "phone": "+1-555-123-4567",
            "propertyAddress": "123 Main St, Anytown, ST 12345",
            "ssn": "123-45-6789",
            "dateOfBirth": "1990-01-15",
            "checkLevel": "comprehensive"
        }
        
        workflow_result = await controller.execute_background_check_workflow(test_applicant, "comprehensive")
        print(f"Workflow Result: {json.dumps(workflow_result, indent=2)}")
        
        # Get system status
        system_status = await controller.get_system_status()
        print(f"System Status: {json.dumps(system_status, indent=2)}")
    
    # Cleanup
    cleanup_result = await controller.cleanup()
    print(f"Cleanup: {json.dumps(cleanup_result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())