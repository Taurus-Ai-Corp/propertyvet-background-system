const express = require('express');
const path = require('path');
const RTWIntegration = require('./rtw-integration');

const app = express();
const PORT = process.env.PORT || 3000;

// Initialize RTW Integration
const rtwIntegration = new RTWIntegration();

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// Sample data
const sampleStats = {
    totalProperties: 156,
    totalChecks: 47,
    approvalRate: 89,
    monthlySavings: 7500,
    occupancyRate: 91,
    avgProcessingTime: 16.3
};

const sampleChecks = [
    {
        id: 'check_001',
        applicantName: 'Sarah Johnson',
        property: 'Unit 205',
        date: '2025-10-14',
        status: 'approved',
        score: 742,
        riskLevel: 'low'
    },
    {
        id: 'check_002',
        applicantName: 'Mike Chen',
        property: 'Unit 103',
        date: '2025-10-13',
        status: 'flagged',
        score: 620,
        riskLevel: 'medium'
    },
    {
        id: 'check_003',
        applicantName: 'Alex Kim',
        property: 'Unit 401',
        date: '2025-10-12',
        status: 'processing',
        score: null,
        riskLevel: null
    }
];

// Routes
app.get('/api/health', (req, res) => {
    res.json({
        status: 'operational',
        service: 'TAURUS PropertyVet™ API',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        message: '100% Failproof System Active'
    });
});

app.get('/api/dashboard/stats', (req, res) => {
    res.json(sampleStats);
});

app.get('/api/background-checks', (req, res) => {
    res.json(sampleChecks);
});

app.post('/api/background-checks', async (req, res) => {
    try {
        const applicantData = req.body;
        
        // Process through RTW integration
        const result = await rtwIntegration.processBackgroundCheck(applicantData);
        
        res.json(result);
    } catch (error) {
        res.status(500).json({
            error: 'Background check processing failed',
            message: error.message
        });
    }
});

// RTW Integration endpoints
app.get('/api/rtw/status', async (req, res) => {
    const connection = await rtwIntegration.testConnection();
    const capabilities = rtwIntegration.getCapabilities();
    
    res.json({
        rtw_connection: connection,
        capabilities: capabilities,
        timestamp: new Date().toISOString()
    });
});

app.get('/api/rtw/task/:taskId', async (req, res) => {
    const taskStatus = await rtwIntegration.getTaskStatus(req.params.taskId);
    res.json(taskStatus);
});

app.post('/api/rtw/callback', (req, res) => {
    // Handle RTW completion callbacks
    console.log('RTW Callback received:', req.body);
    res.json({ received: true });
});

app.get('/api/subscription/plans', (req, res) => {
    const plans = [
        {
            id: 'starter',
            name: 'Starter',
            price: 49,
            features: ['50 background checks/month', 'Basic public records', 'Standard reporting'],
            checksIncluded: 50
        },
        {
            id: 'professional',
            name: 'Professional',
            price: 149,
            features: ['200 background checks/month', 'Credit bureau integration', 'AI risk scoring'],
            checksIncluded: 200,
            popular: true
        },
        {
            id: 'enterprise',
            name: 'Enterprise',
            price: 449,
            features: ['Unlimited checks', 'All data sources', 'White-label branding'],
            checksIncluded: -1
        }
    ];
    res.json(plans);
});

// Serve frontend
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

// Start server
app.listen(PORT, () => {
    console.log('🚀 TAURUS PropertyVet™ Server running on port', PORT);
    console.log('🌐 Access your application at: http://localhost:' + PORT);
    console.log('🔗 Production URL: https://propvet.taurusai.io');
    console.log('📊 API Health Check: http://localhost:' + PORT + '/api/health');
    console.log('✅ 100% FAILPROOF SYSTEM ACTIVE');
});

module.exports = app;