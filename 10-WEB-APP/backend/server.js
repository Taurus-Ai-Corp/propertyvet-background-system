const express = require('express');
const cors = require('cors');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const path = require('path');
const fs = require('fs').promises;
const { v4: uuidv4 } = require('uuid');

// TAURUS PropertyVet™ MCP Integration
const { mcpIntegration, mcpMiddleware } = require('../mcp-integrations/04-API-BRIDGES/mcp_integration.js');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors({
    origin: ['https://propvet.taurusai.io', 'http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5000'],
    credentials: true
}));
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// MCP Integration Middleware
app.use(mcpMiddleware.handleNotification);
app.use(mcpMiddleware.enhanceBackgroundCheck);

// In-memory database (replace with PostgreSQL in production)
let users = [];
let backgroundChecks = [];
let subscriptions = [];

// Sample data
const sampleChecks = [
    {
        id: 'check_001',
        applicantName: 'Sarah Johnson',
        property: 'Unit 205',
        date: '2025-10-14',
        status: 'approved',
        score: 742,
        riskLevel: 'low',
        processingTime: 16.3
    },
    {
        id: 'check_002',
        applicantName: 'Mike Chen',
        property: 'Unit 103',
        date: '2025-10-13',
        status: 'flagged',
        score: 620,
        riskLevel: 'medium',
        processingTime: 18.7
    },
    {
        id: 'check_003',
        applicantName: 'Alex Kim',
        property: 'Unit 401',
        date: '2025-10-12',
        status: 'processing',
        score: null,
        riskLevel: null,
        processingTime: null
    }
];

// Initialize sample data
backgroundChecks = [...sampleChecks];

// JWT secret (use environment variable in production)
const JWT_SECRET = process.env.JWT_SECRET || 'taurus_propvet_secret_key_2025';

// Authentication middleware
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.status(401).json({ error: 'Access token required' });
    }

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) {
            return res.status(403).json({ error: 'Invalid or expired token' });
        }
        req.user = user;
        next();
    });
};

// Routes

// Health check
app.get('/api/health', async (req, res) => {
    try {
        // Check MCP system health
        const mcpHealth = await mcpIntegration.checkMCPSystemHealth();
        
        res.json({
            status: 'operational',
            service: 'TAURUS PropertyVet™ API',
            version: '1.0.0',
            timestamp: new Date().toISOString(),
            environment: process.env.NODE_ENV || 'development',
            mcpSystem: mcpHealth
        });
    } catch (error) {
        res.json({
            status: 'operational',
            service: 'TAURUS PropertyVet™ API',
            version: '1.0.0',
            timestamp: new Date().toISOString(),
            environment: process.env.NODE_ENV || 'development',
            mcpSystem: { status: 'error', error: error.message }
        });
    }
});

// MCP System Status
app.get('/api/mcp/status', authenticateToken, async (req, res) => {
    try {
        const [systemHealth, agentsStatus] = await Promise.all([
            mcpIntegration.checkMCPSystemHealth(),
            mcpIntegration.getMCPAgentsStatus()
        ]);
        
        res.json({
            status: 'success',
            systemHealth,
            agentsStatus,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        console.error('MCP status check failed:', error);
        res.status(500).json({
            status: 'error',
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
});

// Get MCP Workflow Status
app.get('/api/mcp/workflow/:workflowId', authenticateToken, async (req, res) => {
    try {
        const workflowStatus = await mcpIntegration.getMCPWorkflowStatus(req.params.workflowId);
        res.json(workflowStatus);
    } catch (error) {
        console.error('MCP workflow status check failed:', error);
        res.status(500).json({
            status: 'error',
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
});

// User registration
app.post('/api/auth/register', async (req, res) => {
    try {
        const { email, password, companyName, fullName, phone } = req.body;

        // Validate required fields
        if (!email || !password || !companyName || !fullName) {
            return res.status(400).json({ error: 'All fields are required' });
        }

        // Check if user already exists
        const existingUser = users.find(user => user.email === email);
        if (existingUser) {
            return res.status(409).json({ error: 'User already exists' });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Create user
        const user = {
            id: uuidv4(),
            email,
            password: hashedPassword,
            companyName,
            fullName,
            phone,
            createdAt: new Date().toISOString(),
            subscription: 'trial',
            checksRemaining: 5
        };

        users.push(user);

        // Generate JWT token
        const token = jwt.sign(
            { userId: user.id, email: user.email },
            JWT_SECRET,
            { expiresIn: '24h' }
        );

        res.status(201).json({
            message: 'User registered successfully',
            token,
            user: {
                id: user.id,
                email: user.email,
                companyName: user.companyName,
                fullName: user.fullName,
                subscription: user.subscription,
                checksRemaining: user.checksRemaining
            }
        });
    } catch (error) {
        console.error('Registration error:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// User login
app.post('/api/auth/login', async (req, res) => {
    try {
        const { email, password } = req.body;

        // Find user
        const user = users.find(u => u.email === email);
        if (!user) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        // Check password
        const isPasswordValid = await bcrypt.compare(password, user.password);
        if (!isPasswordValid) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        // Generate JWT token
        const token = jwt.sign(
            { userId: user.id, email: user.email },
            JWT_SECRET,
            { expiresIn: '24h' }
        );

        res.json({
            message: 'Login successful',
            token,
            user: {
                id: user.id,
                email: user.email,
                companyName: user.companyName,
                fullName: user.fullName,
                subscription: user.subscription,
                checksRemaining: user.checksRemaining
            }
        });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Get dashboard stats
app.get('/api/dashboard/stats', authenticateToken, (req, res) => {
    const userChecks = backgroundChecks.filter(check => check.userId === req.user.userId);
    
    const stats = {
        totalProperties: 156,
        totalChecks: userChecks.length,
        approvalRate: 89,
        monthlySavings: 7500,
        occupancyRate: 91,
        avgProcessingTime: 16.3
    };

    res.json(stats);
});

// Get recent background checks
app.get('/api/background-checks', authenticateToken, (req, res) => {
    const userChecks = backgroundChecks.filter(check => check.userId === req.user.userId);
    res.json(userChecks);
});

// Start background check
app.post('/api/background-checks', authenticateToken, async (req, res) => {
    try {
        const {
            applicantName,
            email,
            phone,
            propertyAddress,
            ssn,
            dateOfBirth,
            checkLevel
        } = req.body;

        // Validate required fields
        if (!applicantName || !email || !ssn || !dateOfBirth || !checkLevel) {
            return res.status(400).json({ error: 'All required fields must be provided' });
        }

        // Check user's remaining checks
        const user = users.find(u => u.id === req.user.userId);
        if (user.checksRemaining <= 0 && user.subscription === 'trial') {
            return res.status(402).json({ error: 'No remaining checks. Please upgrade your subscription.' });
        }

        // Create background check record
        const backgroundCheck = {
            id: uuidv4(),
            userId: req.user.userId,
            applicantName,
            email,
            phone,
            propertyAddress,
            ssn: ssn.replace(/\d(?=\d{4})/g, "*"), // Mask SSN for storage
            dateOfBirth,
            checkLevel,
            status: 'processing',
            createdAt: new Date().toISOString(),
            estimatedCompletion: new Date(Date.now() + 15 * 60 * 1000).toISOString(), // 15 minutes
            mcpEnabled: req.useMCP || false
        };

        backgroundChecks.push(backgroundCheck);

        // Decrease user's remaining checks
        if (user.subscription === 'trial') {
            user.checksRemaining--;
        }

        // Enhanced MCP Background Check Processing
        if (req.useMCP && req.mcpIntegration) {
            console.log('🤖 Starting MCP-enhanced background check...');
            
            try {
                // Prepare data for MCP processing (without exposing full SSN)
                const mcpData = {
                    applicantName,
                    email,
                    phone,
                    propertyAddress,
                    dateOfBirth,
                    checkLevel,
                    checkId: backgroundCheck.id
                };
                
                // Process through MCP system
                const mcpResult = await req.mcpIntegration.processMCPBackgroundCheck(mcpData);
                
                if (mcpResult.status === 'success') {
                    // Convert MCP result to PropertyVet format
                    const convertedResult = req.mcpIntegration.convertMCPResultToPropertyVetFormat(mcpResult);
                    
                    // Update background check with MCP results
                    const checkIndex = backgroundChecks.findIndex(c => c.id === backgroundCheck.id);
                    if (checkIndex !== -1) {
                        backgroundChecks[checkIndex] = {
                            ...backgroundChecks[checkIndex],
                            ...convertedResult,
                            mcpProcessed: true,
                            mcpWorkflowId: mcpResult.workflow_id
                        };
                    }
                    
                    console.log(`✅ MCP processing completed for ${applicantName}`);
                    
                    res.status(201).json({
                        message: 'MCP-enhanced background check started',
                        checkId: backgroundCheck.id,
                        workflowId: mcpResult.workflow_id,
                        estimatedCompletion: backgroundCheck.estimatedCompletion,
                        mcpEnhanced: true
                    });
                    
                } else {
                    // MCP failed, fall back to standard processing
                    console.warn('⚠️ MCP processing failed, falling back to standard processing');
                    setTimeout(() => {
                        processBackgroundCheck(backgroundCheck.id);
                    }, 2000);
                    
                    res.status(201).json({
                        message: 'Background check started (standard processing)',
                        checkId: backgroundCheck.id,
                        estimatedCompletion: backgroundCheck.estimatedCompletion,
                        mcpFallback: true
                    });
                }
                
            } catch (mcpError) {
                console.error('❌ MCP processing error:', mcpError.message);
                // Fall back to standard processing
                setTimeout(() => {
                    processBackgroundCheck(backgroundCheck.id);
                }, 2000);
                
                res.status(201).json({
                    message: 'Background check started (standard processing)',
                    checkId: backgroundCheck.id,
                    estimatedCompletion: backgroundCheck.estimatedCompletion,
                    mcpError: mcpError.message
                });
            }
            
        } else {
            // Standard background check processing
            console.log('📋 Starting standard background check...');
            setTimeout(() => {
                processBackgroundCheck(backgroundCheck.id);
            }, 2000);

            res.status(201).json({
                message: 'Background check started',
                checkId: backgroundCheck.id,
                estimatedCompletion: backgroundCheck.estimatedCompletion
            });
        }
        
    } catch (error) {
        console.error('Background check error:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Get specific background check
app.get('/api/background-checks/:id', authenticateToken, (req, res) => {
    const check = backgroundChecks.find(c => c.id === req.params.id && c.userId === req.user.userId);
    
    if (!check) {
        return res.status(404).json({ error: 'Background check not found' });
    }

    res.json(check);
});

// Subscription plans
app.get('/api/subscription/plans', (req, res) => {
    const plans = [
        {
            id: 'starter',
            name: 'Starter',
            price: 49,
            features: [
                '50 background checks/month',
                'Basic public record searches',
                'Standard reporting',
                'Email support'
            ],
            checksIncluded: 50
        },
        {
            id: 'professional',
            name: 'Professional',
            price: 149,
            features: [
                '200 background checks/month',
                'Credit bureau integration',
                'Advanced AI risk scoring',
                'Multi-region support',
                'Priority support'
            ],
            checksIncluded: 200,
            popular: true
        },
        {
            id: 'enterprise',
            name: 'Enterprise',
            price: 449,
            features: [
                'Unlimited background checks',
                'All data sources included',
                'White-label branding',
                'API access for integrations',
                'Dedicated customer success'
            ],
            checksIncluded: -1 // Unlimited
        }
    ];

    res.json(plans);
});

// Process payment (Stripe integration placeholder)
app.post('/api/payments/process', authenticateToken, async (req, res) => {
    try {
        const { planId, paymentMethodId } = req.body;

        // In production, integrate with Stripe or other payment processor
        // For demo, we'll simulate successful payment
        
        const user = users.find(u => u.id === req.user.userId);
        user.subscription = planId;
        
        // Update checks remaining based on plan
        if (planId === 'starter') {
            user.checksRemaining = 50;
        } else if (planId === 'professional') {
            user.checksRemaining = 200;
        } else if (planId === 'enterprise') {
            user.checksRemaining = -1; // Unlimited
        }

        res.json({
            message: 'Payment processed successfully',
            subscription: user.subscription,
            checksRemaining: user.checksRemaining
        });
    } catch (error) {
        console.error('Payment error:', error);
        res.status(500).json({ error: 'Payment processing failed' });
    }
});

// Background check processing simulation
function processBackgroundCheck(checkId) {
    const check = backgroundChecks.find(c => c.id === checkId);
    if (!check) return;

    // Simulate processing steps with delays
    const steps = [
        { name: 'Identity Verification', delay: 2000 },
        { name: 'Credit History Analysis', delay: 5000 },
        { name: 'Public Records Search', delay: 3000 },
        { name: 'Employment Verification', delay: 4000 },
        { name: 'Final Report Generation', delay: 1000 }
    ];

    let totalDelay = 0;
    steps.forEach((step, index) => {
        totalDelay += step.delay;
        setTimeout(() => {
            if (index === steps.length - 1) {
                // Complete the check
                completeBackgroundCheck(checkId);
            }
        }, totalDelay);
    });
}

function completeBackgroundCheck(checkId) {
    const check = backgroundChecks.find(c => c.id === checkId);
    if (!check) return;

    // Generate mock results
    const mockResults = {
        status: 'completed',
        completedAt: new Date().toISOString(),
        processingTime: Math.floor(Math.random() * 10) + 10, // 10-20 minutes
        results: {
            overallScore: Math.floor(Math.random() * 200) + 650, // 650-850
            riskLevel: 'low', // Will be calculated based on score
            identityVerification: {
                status: 'verified',
                confidence: 'high'
            },
            creditScore: {
                score: Math.floor(Math.random() * 200) + 650,
                grade: 'excellent',
                source: 'Equifax'
            },
            criminalBackground: {
                status: 'clear',
                recordsFound: 0
            },
            employmentVerification: {
                status: 'verified',
                employer: 'Tech Solutions Inc.',
                income: '$4,200/month'
            },
            rentalHistory: {
                status: 'positive',
                propertiesCount: 3,
                referencesContacted: 3
            },
            recommendations: [
                'Excellent tenant candidate - approve with confidence',
                'Standard security deposit recommended',
                '12-month lease term acceptable',
                'Consider offering preferred tenant benefits'
            ]
        }
    };

    // Determine risk level based on score
    if (mockResults.results.overallScore >= 750) {
        mockResults.results.riskLevel = 'low';
    } else if (mockResults.results.overallScore >= 650) {
        mockResults.results.riskLevel = 'medium';
    } else {
        mockResults.results.riskLevel = 'high';
    }

    // Update the check with results
    Object.assign(check, mockResults);
}

// Serve frontend
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 TAURUS PropertyVet™ Server running on port ${PORT}`);
    console.log(`🌐 Access your application at: http://localhost:${PORT}`);
    console.log(`🔗 Production URL: https://propvet.taurusai.io`);
    console.log(`📊 API Health Check: http://localhost:${PORT}/api/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down gracefully');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('SIGINT received, shutting down gracefully');
    process.exit(0);
});

module.exports = app;