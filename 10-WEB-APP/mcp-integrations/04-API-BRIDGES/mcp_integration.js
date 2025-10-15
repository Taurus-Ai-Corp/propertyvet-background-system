// TAURUS PropertyVet™ - MCP Integration Module
// Integration between Express.js backend and MCP orchestration system

const axios = require('axios');

// MCP Bridge Configuration
const MCP_BRIDGE_URL = process.env.MCP_BRIDGE_URL || 'http://localhost:5000';
const MCP_API_KEY = process.env.MCP_API_KEY || 'taurus_propvet_mcp_integration_key';

class MCPIntegration {
    constructor() {
        this.bridgeUrl = MCP_BRIDGE_URL;
        this.apiKey = MCP_API_KEY;
        this.activeWorkflows = new Map();
        this.systemStatus = 'initializing';
        
        // Initialize MCP system
        this.initializeMCPSystem();
    }
    
    async initializeMCPSystem() {
        try {
            console.log('🚀 Initializing MCP Integration System...');
            
            const response = await axios.post(`${this.bridgeUrl}/api/mcp/initialize`, {}, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-MCP-API-Key': this.apiKey
                },
                timeout: 30000
            });
            
            if (response.data.status === 'success') {
                this.systemStatus = 'active';
                console.log('✅ MCP Integration System initialized successfully');
                console.log(`📊 Active Agents: ${response.data.active_agents?.join(', ') || 'N/A'}`);
            } else {
                this.systemStatus = 'error';
                console.error('❌ MCP Integration System initialization failed:', response.data.error);
            }
            
        } catch (error) {
            this.systemStatus = 'error';
            console.error('❌ Failed to initialize MCP Integration System:', error.message);
        }
    }
    
    async processMCPBackgroundCheck(applicantData) {
        try {
            console.log(`🤖 Processing MCP background check for: ${applicantData.applicantName}`);
            console.log(`📋 Check Level: ${applicantData.checkLevel || 'standard'}`);
            
            const startTime = Date.now();
            
            const response = await axios.post(`${this.bridgeUrl}/api/mcp/background-check`, applicantData, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-MCP-API-Key': this.apiKey
                },
                timeout: 300000 // 5 minutes
            });
            
            const processingTime = (Date.now() - startTime) / 1000;
            console.log(`⏱️ MCP processing completed in ${processingTime}s`);
            
            // Store workflow for tracking
            if (response.data.workflow_id) {
                this.activeWorkflows.set(response.data.workflow_id, {
                    applicantName: applicantData.applicantName,
                    startTime: new Date(),
                    status: response.data.status,
                    processingTime
                });
            }
            
            return {
                ...response.data,
                processingTime,
                mcpIntegrationStatus: 'success'
            };
            
        } catch (error) {
            console.error('❌ MCP background check failed:', error.message);
            
            // Return error with fallback processing
            return {
                status: 'error',
                error: `MCP integration failed: ${error.message}`,
                mcpIntegrationStatus: 'failed',
                fallbackRequired: true,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async getMCPWorkflowStatus(workflowId) {
        try {
            const response = await axios.get(`${this.bridgeUrl}/api/mcp/workflow/${workflowId}`, {
                headers: {
                    'X-MCP-API-Key': this.apiKey
                }
            });
            
            return response.data;
            
        } catch (error) {
            console.error('❌ MCP workflow status check failed:', error.message);
            return {
                status: 'error',
                error: `Failed to get workflow status: ${error.message}`,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async checkMCPSystemHealth() {
        try {
            const response = await axios.get(`${this.bridgeUrl}/api/mcp/health`, {
                timeout: 10000
            });
            
            return {
                status: 'healthy',
                mcpBridge: response.data,
                systemStatus: this.systemStatus,
                activeWorkflows: this.activeWorkflows.size,
                timestamp: new Date().toISOString()
            };
            
        } catch (error) {
            console.error('❌ MCP health check failed:', error.message);
            return {
                status: 'unhealthy',
                error: error.message,
                systemStatus: 'error',
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async getMCPAgentsStatus() {
        try {
            const response = await axios.get(`${this.bridgeUrl}/api/mcp/agents/status`, {
                headers: {
                    'X-MCP-API-Key': this.apiKey
                }
            });
            
            return response.data;
            
        } catch (error) {
            console.error('❌ MCP agents status check failed:', error.message);
            return {
                status: 'error',
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    handleMCPNotification(notificationData) {
        try {
            console.log('📥 Received MCP notification:', notificationData);
            
            const { workflow_id, status, recommendation } = notificationData;
            
            // Update workflow tracking
            if (this.activeWorkflows.has(workflow_id)) {
                const workflow = this.activeWorkflows.get(workflow_id);
                workflow.status = status;
                workflow.completedTime = new Date();
                workflow.recommendation = recommendation;
                
                console.log(`📋 Workflow ${workflow_id} updated: ${status}`);
            }
            
            // Here you would typically update your database
            // This is where you'd integrate with your background check storage
            
            return {
                status: 'received',
                workflow_id,
                timestamp: new Date().toISOString()
            };
            
        } catch (error) {
            console.error('❌ Failed to handle MCP notification:', error.message);
            return {
                status: 'error',
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    // Convert MCP results to PropertyVet format
    convertMCPResultToPropertyVetFormat(mcpResult) {
        try {
            if (mcpResult.status !== 'success') {
                return {
                    status: 'error',
                    error: mcpResult.error || 'MCP processing failed'
                };
            }
            
            const finalRecommendation = mcpResult.final_recommendation?.final_decision || {};
            const workflowMetrics = mcpResult.workflow_metrics?.performance_metrics || {};
            
            // Convert to PropertyVet format
            return {
                id: mcpResult.workflow_id,
                applicantName: mcpResult.applicant_name,
                status: this.mapMCPStatusToPropertyVet(finalRecommendation.recommendation),
                score: this.calculatePropertyVetScore(finalRecommendation.overall_score),
                riskLevel: finalRecommendation.risk_level || 'medium',
                processingTime: workflowMetrics.total_duration_seconds || 0,
                mcpData: {
                    workflowId: mcpResult.workflow_id,
                    checkLevel: mcpResult.check_level,
                    agentResults: mcpResult.agent_results,
                    recommendation: finalRecommendation,
                    metrics: workflowMetrics
                },
                completedAt: mcpResult.completed_at,
                createdAt: mcpResult.started_at
            };
            
        } catch (error) {
            console.error('❌ Failed to convert MCP result:', error.message);
            return {
                status: 'error',
                error: `Result conversion failed: ${error.message}`
            };
        }
    }
    
    mapMCPStatusToPropertyVet(mcpRecommendation) {
        const statusMap = {
            'approve': 'approved',
            'approve_with_conditions': 'approved',
            'manual_review': 'flagged',
            'decline': 'declined'
        };
        
        return statusMap[mcpRecommendation] || 'processing';
    }
    
    calculatePropertyVetScore(mcpScore) {
        // Convert MCP confidence score (0-100) to PropertyVet score (300-850)
        if (typeof mcpScore !== 'number') return 650; // Default score
        
        // Map 0-100 to 300-850 range
        const minScore = 300;
        const maxScore = 850;
        const range = maxScore - minScore;
        
        return Math.round(minScore + (mcpScore / 100) * range);
    }
    
    // Middleware for Express.js integration
    createExpressMiddleware() {
        return {
            // MCP notification handler
            handleNotification: (req, res, next) => {
                if (req.path === '/api/mcp/notification' && req.method === 'POST') {
                    const result = this.handleMCPNotification(req.body);
                    res.json(result);
                } else {
                    next();
                }
            },
            
            // Enhanced background check processor
            enhanceBackgroundCheck: async (req, res, next) => {
                try {
                    // Only enhance if MCP is available
                    if (this.systemStatus === 'active') {
                        req.mcpIntegration = this;
                        req.useMCP = true;
                    } else {
                        req.useMCP = false;
                    }
                    next();
                } catch (error) {
                    console.error('❌ MCP middleware error:', error.message);
                    req.useMCP = false;
                    next();
                }
            }
        };
    }
    
    // Health monitoring
    startHealthMonitoring() {
        setInterval(async () => {
            try {
                const health = await this.checkMCPSystemHealth();
                if (health.status !== 'healthy' && this.systemStatus === 'active') {
                    console.warn('⚠️ MCP system health degraded, attempting reconnection...');
                    await this.initializeMCPSystem();
                }
            } catch (error) {
                console.error('❌ Health monitoring error:', error.message);
            }
        }, 60000); // Check every minute
    }
}

// Create singleton instance
const mcpIntegration = new MCPIntegration();

// Start health monitoring
mcpIntegration.startHealthMonitoring();

module.exports = {
    MCPIntegration,
    mcpIntegration,
    
    // Export individual functions for compatibility
    processMCPBackgroundCheck: (data) => mcpIntegration.processMCPBackgroundCheck(data),
    getMCPWorkflowStatus: (id) => mcpIntegration.getMCPWorkflowStatus(id),
    checkMCPSystemHealth: () => mcpIntegration.checkMCPSystemHealth(),
    handleMCPNotification: (data) => mcpIntegration.handleMCPNotification(data),
    
    // Middleware exports
    mcpMiddleware: mcpIntegration.createExpressMiddleware()
};