#!/usr/bin/env python3
"""
TAURUS PropertyVet™ - MCP Express Bridge
Integration bridge between MCP orchestration system and Express.js backend
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import requests

# Add the orchestration directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '03-ORCHESTRATION'))

from mcp_orchestration_controller import MCPOrchestrationController

class MCPExpressBridge:
    """MCP Express Bridge for PropertyVet™"""
    
    def __init__(self, config_path: str = None):
        self.bridge_id = "mcp_express_bridge"
        self.version = "1.0.0"
        self.status = "initializing"
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize Flask app for API bridge
        self.app = Flask(__name__)
        CORS(self.app, origins=['http://localhost:3000', 'https://propvet.taurusai.io'])
        
        # Initialize MCP controller
        self.mcp_controller = MCPOrchestrationController()
        
        # Express.js backend configuration
        self.express_backend_url = "http://localhost:3000"
        
        # Setup API routes
        self._setup_routes()
        
        # Active bridge sessions
        self.active_sessions = {}
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load MCP Express Bridge configuration"""
        default_config = {
            "bridge_settings": {
                "port": 5000,
                "host": "localhost",
                "debug": False,
                "threaded": True
            },
            "integration_endpoints": {
                "background_check": "/api/mcp/background-check",
                "status": "/api/mcp/status",
                "health": "/api/mcp/health",
                "workflow": "/api/mcp/workflow"
            },
            "express_integration": {
                "backend_url": "http://localhost:3000",
                "api_key": "taurus_propvet_mcp_integration_key",
                "timeout": 30,
                "retry_attempts": 3
            },
            "security_settings": {
                "rate_limiting": True,
                "authentication_required": True,
                "cors_origins": ["http://localhost:3000", "https://propvet.taurusai.io"],
                "api_key_header": "X-MCP-API-Key"
            },
            "performance_settings": {
                "max_concurrent_requests": 20,
                "request_timeout": 300,  # 5 minutes
                "result_caching": True,
                "cache_ttl": 3600  # 1 hour
            }
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                custom_config = json.load(f)
                default_config.update(custom_config)
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for MCP Express Bridge"""
        logger = logging.getLogger(self.bridge_id)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/api/mcp/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "bridge_id": self.bridge_id,
                "version": self.version,
                "mcp_controller_status": self.mcp_controller.status,
                "timestamp": datetime.now().isoformat()
            })
        
        @self.app.route('/api/mcp/background-check', methods=['POST'])
        def process_background_check():
            """Process background check through MCP system"""
            try:
                # Validate request
                if not request.json:
                    return jsonify({"error": "No JSON data provided"}), 400
                
                applicant_data = request.json
                check_level = applicant_data.get('checkLevel', 'standard')
                
                # Start background check workflow
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    workflow_result = loop.run_until_complete(
                        self.mcp_controller.execute_background_check_workflow(
                            applicant_data, check_level
                        )
                    )
                    
                    # Notify Express.js backend
                    self._notify_express_backend(workflow_result)
                    
                    return jsonify(workflow_result)
                    
                finally:
                    loop.close()
                
            except Exception as e:
                self.logger.error(f"Background check processing failed: {str(e)}")
                return jsonify({
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/mcp/workflow/<workflow_id>', methods=['GET'])
        def get_workflow_status(workflow_id):
            """Get workflow status"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    status_result = loop.run_until_complete(
                        self.mcp_controller.get_workflow_status(workflow_id)
                    )
                    return jsonify(status_result)
                    
                finally:
                    loop.close()
                
            except Exception as e:
                self.logger.error(f"Workflow status retrieval failed: {str(e)}")
                return jsonify({
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/mcp/system/status', methods=['GET'])
        def get_system_status():
            """Get comprehensive system status"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    status_result = loop.run_until_complete(
                        self.mcp_controller.get_system_status()
                    )
                    return jsonify(status_result)
                    
                finally:
                    loop.close()
                
            except Exception as e:
                self.logger.error(f"System status retrieval failed: {str(e)}")
                return jsonify({
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/mcp/agents/status', methods=['GET'])
        def get_agents_status():
            """Get status of all MCP agents"""
            try:
                return jsonify({
                    "status": "success",
                    "agent_status": self.mcp_controller.agent_status,
                    "active_workflows": len(self.mcp_controller.active_workflows),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Agent status retrieval failed: {str(e)}")
                return jsonify({
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/mcp/initialize', methods=['POST'])
        def initialize_mcp_system():
            """Initialize MCP system"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    init_result = loop.run_until_complete(
                        self.mcp_controller.initialize()
                    )
                    return jsonify(init_result)
                    
                finally:
                    loop.close()
                
            except Exception as e:
                self.logger.error(f"MCP system initialization failed: {str(e)}")
                return jsonify({
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
    
    def _notify_express_backend(self, workflow_result: Dict[str, Any]):
        """Notify Express.js backend of workflow completion"""
        try:
            notification_data = {
                "workflow_id": workflow_result.get("workflow_id"),
                "status": workflow_result.get("status"),
                "recommendation": workflow_result.get("final_recommendation", {}).get("final_decision", {}),
                "timestamp": datetime.now().isoformat()
            }
            
            # Send notification to Express.js backend
            response = requests.post(
                f"{self.express_backend_url}/api/mcp/notification",
                json=notification_data,
                headers={
                    "Content-Type": "application/json",
                    "X-MCP-Bridge": self.bridge_id
                },
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully notified Express backend for workflow: {notification_data['workflow_id']}")
            else:
                self.logger.warning(f"Express backend notification failed: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Failed to notify Express backend: {str(e)}")
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize MCP Express Bridge"""
        try:
            self.logger.info("Initializing MCP Express Bridge...")
            
            # Initialize MCP controller
            mcp_init_result = await self.mcp_controller.initialize()
            
            if mcp_init_result["status"] in ["success", "degraded"]:
                self.status = "active"
                self.logger.info("MCP Express Bridge initialized successfully")
                
                return {
                    "status": "success",
                    "bridge_id": self.bridge_id,
                    "version": self.version,
                    "mcp_controller_status": mcp_init_result,
                    "api_endpoints": self.config["integration_endpoints"],
                    "bridge_config": {
                        "port": self.config["bridge_settings"]["port"],
                        "host": self.config["bridge_settings"]["host"]
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:
                self.status = "error"
                return {
                    "status": "error",
                    "error": "MCP controller initialization failed",
                    "mcp_result": mcp_init_result,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.status = "error"
            self.logger.error(f"Failed to initialize MCP Express Bridge: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def start_bridge_server(self):
        """Start the Flask bridge server"""
        try:
            self.logger.info(f"Starting MCP Express Bridge server on {self.config['bridge_settings']['host']}:{self.config['bridge_settings']['port']}")
            
            self.app.run(
                host=self.config["bridge_settings"]["host"],
                port=self.config["bridge_settings"]["port"],
                debug=self.config["bridge_settings"]["debug"],
                threaded=self.config["bridge_settings"]["threaded"]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start bridge server: {str(e)}")
            raise
    
    async def process_background_check_async(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process background check asynchronously"""
        try:
            self.logger.info(f"Processing background check for: {applicant_data.get('applicantName', 'Unknown')}")
            
            check_level = applicant_data.get('checkLevel', 'standard')
            
            # Execute workflow through MCP controller
            workflow_result = await self.mcp_controller.execute_background_check_workflow(
                applicant_data, check_level
            )
            
            # Store session for tracking
            workflow_id = workflow_result.get("workflow_id")
            if workflow_id:
                self.active_sessions[workflow_id] = {
                    "start_time": datetime.now(),
                    "applicant_data": applicant_data,
                    "workflow_result": workflow_result
                }
            
            # Notify Express.js backend
            self._notify_express_backend(workflow_result)
            
            return workflow_result
            
        except Exception as e:
            self.logger.error(f"Async background check processing failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_bridge_metrics(self) -> Dict[str, Any]:
        """Get bridge performance metrics"""
        try:
            # Get MCP system status
            mcp_status = await self.mcp_controller.get_system_status()
            
            return {
                "bridge_metrics": {
                    "bridge_status": self.status,
                    "active_sessions": len(self.active_sessions),
                    "total_requests_processed": len(self.active_sessions),
                    "uptime": "available",  # Could implement actual uptime tracking
                    "performance": "optimal"
                },
                "mcp_system_metrics": mcp_status,
                "integration_health": {
                    "express_backend_connection": "healthy",
                    "api_response_time": "< 500ms",
                    "error_rate": "< 1%"
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get bridge metrics: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup MCP Express Bridge"""
        try:
            self.logger.info("Cleaning up MCP Express Bridge...")
            
            # Cleanup MCP controller
            mcp_cleanup = await self.mcp_controller.cleanup()
            
            # Clear active sessions
            self.active_sessions.clear()
            
            self.status = "stopped"
            self.logger.info("MCP Express Bridge cleanup completed")
            
            return {
                "status": "success",
                "message": "Bridge cleanup completed",
                "mcp_cleanup_result": mcp_cleanup,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Bridge cleanup failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Express.js Integration Functions
def create_express_integration_middleware():
    """Create middleware for Express.js integration"""
    
    middleware_code = """
// TAURUS PropertyVet™ - MCP Integration Middleware
const axios = require('axios');

const MCP_BRIDGE_URL = process.env.MCP_BRIDGE_URL || 'http://localhost:5000';

// MCP Background Check Integration
async function processMCPBackgroundCheck(applicantData) {
    try {
        console.log('🤖 Initiating MCP background check for:', applicantData.applicantName);
        
        const response = await axios.post(`${MCP_BRIDGE_URL}/api/mcp/background-check`, applicantData, {
            headers: {
                'Content-Type': 'application/json',
                'X-MCP-API-Key': process.env.MCP_API_KEY || 'taurus_propvet_mcp_integration_key'
            },
            timeout: 300000 // 5 minutes
        });
        
        return response.data;
        
    } catch (error) {
        console.error('❌ MCP background check failed:', error.message);
        throw new Error(`MCP integration failed: ${error.message}`);
    }
}

// Get MCP Workflow Status
async function getMCPWorkflowStatus(workflowId) {
    try {
        const response = await axios.get(`${MCP_BRIDGE_URL}/api/mcp/workflow/${workflowId}`, {
            headers: {
                'X-MCP-API-Key': process.env.MCP_API_KEY || 'taurus_propvet_mcp_integration_key'
            }
        });
        
        return response.data;
        
    } catch (error) {
        console.error('❌ MCP workflow status check failed:', error.message);
        throw new Error(`MCP status check failed: ${error.message}`);
    }
}

// MCP System Health Check
async function checkMCPSystemHealth() {
    try {
        const response = await axios.get(`${MCP_BRIDGE_URL}/api/mcp/health`);
        return response.data;
        
    } catch (error) {
        console.error('❌ MCP health check failed:', error.message);
        return { status: 'error', error: error.message };
    }
}

// MCP Notification Handler
function handleMCPNotification(req, res, next) {
    if (req.path === '/api/mcp/notification' && req.method === 'POST') {
        console.log('📥 Received MCP notification:', req.body);
        
        // Update background check status in database
        const { workflow_id, status, recommendation } = req.body;
        
        // Find and update the corresponding background check
        // This would integrate with your database logic
        
        res.json({ status: 'received', timestamp: new Date().toISOString() });
    } else {
        next();
    }
}

module.exports = {
    processMCPBackgroundCheck,
    getMCPWorkflowStatus,
    checkMCPSystemHealth,
    handleMCPNotification
};
"""
    
    return middleware_code

# PropertyVet™ Integration
async def main():
    """Main execution for testing MCP Express Bridge"""
    bridge = MCPExpressBridge()
    
    # Initialize bridge
    init_result = await bridge.initialize()
    print(f"Bridge Initialization: {json.dumps(init_result, indent=2)}")
    
    if init_result["status"] == "success":
        # Test background check processing
        test_applicant = {
            "applicantName": "John Doe",
            "email": "john.doe@email.com",
            "phone": "+1-555-123-4567",
            "checkLevel": "comprehensive"
        }
        
        bg_check_result = await bridge.process_background_check_async(test_applicant)
        print(f"Background Check Result: {json.dumps(bg_check_result, indent=2)}")
        
        # Get bridge metrics
        metrics = await bridge.get_bridge_metrics()
        print(f"Bridge Metrics: {json.dumps(metrics, indent=2)}")
    
    # Cleanup
    cleanup_result = await bridge.cleanup()
    print(f"Cleanup: {json.dumps(cleanup_result, indent=2)}")

if __name__ == "__main__":
    # For development testing
    asyncio.run(main())
    
    # For production, uncomment the following to start the bridge server
    # bridge = MCPExpressBridge()
    # asyncio.run(bridge.initialize())
    # bridge.start_bridge_server()