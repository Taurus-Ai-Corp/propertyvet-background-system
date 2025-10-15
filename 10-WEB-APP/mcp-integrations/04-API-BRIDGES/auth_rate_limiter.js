// TAURUS PropertyVet™ - Authentication & Rate Limiting Middleware
// Advanced security and rate limiting for MCP system

const rateLimit = require('express-rate-limit');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

class AuthRateLimiter {
    constructor(config = {}) {
        this.config = {
            // Rate limiting settings
            windowMs: config.windowMs || 15 * 60 * 1000, // 15 minutes
            maxRequests: config.maxRequests || 100,
            skipSuccessfulRequests: config.skipSuccessfulRequests || false,
            skipFailedRequests: config.skipFailedRequests || false,
            
            // Authentication settings
            jwtSecret: config.jwtSecret || process.env.JWT_SECRET || 'taurus_propvet_secret_key_2025',
            apiKeySecret: config.apiKeySecret || process.env.MCP_API_KEY || 'taurus_propvet_mcp_integration_key',
            
            // Security settings
            enableApiKeyAuth: config.enableApiKeyAuth !== false,
            enableJwtAuth: config.enableJwtAuth !== false,
            enableIpWhitelist: config.enableIpWhitelist || false,
            ipWhitelist: config.ipWhitelist || [],
            
            // Advanced rate limiting
            enableDynamicRateLimit: config.enableDynamicRateLimit || true,
            enableUserBasedLimiting: config.enableUserBasedLimiting || true,
            enableEndpointSpecificLimits: config.enableEndpointSpecificLimits || true,
            
            ...config
        };
        
        this.failedAttempts = new Map();
        this.userRateLimits = new Map();
        this.endpointLimits = new Map();
        
        this.setupEndpointLimits();
    }
    
    setupEndpointLimits() {
        // Define specific rate limits for different endpoints
        this.endpointLimits.set('/api/mcp/background-check', {
            windowMs: 60 * 1000, // 1 minute
            maxRequests: 10,     // 10 background checks per minute
            message: 'Too many background check requests'
        });
        
        this.endpointLimits.set('/api/mcp/workflow', {
            windowMs: 60 * 1000, // 1 minute
            maxRequests: 20,     // 20 workflow requests per minute
            message: 'Too many workflow requests'
        });
        
        this.endpointLimits.set('/api/mcp/status', {
            windowMs: 60 * 1000, // 1 minute
            maxRequests: 60,     // 60 status checks per minute
            message: 'Too many status check requests'
        });
        
        this.endpointLimits.set('/api/auth/login', {
            windowMs: 15 * 60 * 1000, // 15 minutes
            maxRequests: 5,           // 5 login attempts per 15 minutes
            message: 'Too many login attempts'
        });
    }
    
    // General rate limiter
    createGeneralRateLimiter() {
        return rateLimit({
            windowMs: this.config.windowMs,
            max: this.config.maxRequests,
            skipSuccessfulRequests: this.config.skipSuccessfulRequests,
            skipFailedRequests: this.config.skipFailedRequests,
            standardHeaders: true,
            legacyHeaders: false,
            handler: (req, res) => {
                res.status(429).json({
                    error: 'Too many requests',
                    message: 'Rate limit exceeded. Please try again later.',
                    retryAfter: Math.round(this.config.windowMs / 1000),
                    timestamp: new Date().toISOString()
                });
            },
            keyGenerator: (req) => {
                // Use IP + User ID for more granular limiting
                const userId = req.user?.userId || 'anonymous';
                return `${req.ip}:${userId}`;
            }
        });
    }
    
    // MCP-specific rate limiter
    createMCPRateLimiter() {
        return rateLimit({
            windowMs: 5 * 60 * 1000, // 5 minutes
            max: 20, // 20 MCP requests per 5 minutes
            skipSuccessfulRequests: false,
            skipFailedRequests: false,
            standardHeaders: true,
            legacyHeaders: false,
            handler: (req, res) => {
                console.warn(`🚨 MCP rate limit exceeded for ${req.ip}`);
                res.status(429).json({
                    error: 'MCP rate limit exceeded',
                    message: 'Too many MCP requests. Background checks are resource intensive.',
                    retryAfter: 300, // 5 minutes
                    timestamp: new Date().toISOString()
                });
            },
            keyGenerator: (req) => {
                return `mcp:${req.ip}:${req.user?.userId || 'anonymous'}`;
            }
        });
    }
    
    // Dynamic endpoint-specific rate limiter
    createEndpointRateLimiter() {
        return (req, res, next) => {
            const endpoint = this.getEndpointPattern(req.path);
            const limitConfig = this.endpointLimits.get(endpoint);
            
            if (!limitConfig) {
                return next();
            }
            
            const key = `${endpoint}:${req.ip}:${req.user?.userId || 'anonymous'}`;
            const now = Date.now();
            const windowStart = now - limitConfig.windowMs;
            
            // Get or create request history for this key
            if (!this.userRateLimits.has(key)) {
                this.userRateLimits.set(key, []);
            }
            
            const requests = this.userRateLimits.get(key);
            
            // Remove old requests outside the window
            const validRequests = requests.filter(timestamp => timestamp > windowStart);
            this.userRateLimits.set(key, validRequests);
            
            // Check if limit is exceeded
            if (validRequests.length >= limitConfig.maxRequests) {
                console.warn(`🚨 Endpoint rate limit exceeded: ${endpoint} for ${req.ip}`);
                return res.status(429).json({
                    error: 'Endpoint rate limit exceeded',
                    message: limitConfig.message,
                    endpoint: endpoint,
                    retryAfter: Math.round(limitConfig.windowMs / 1000),
                    timestamp: new Date().toISOString()
                });
            }
            
            // Add current request
            validRequests.push(now);
            this.userRateLimits.set(key, validRequests);
            
            next();
        };
    }
    
    // API Key authentication middleware
    createApiKeyAuth() {
        return (req, res, next) => {
            if (!this.config.enableApiKeyAuth) {
                return next();
            }
            
            const apiKey = req.headers['x-mcp-api-key'] || req.headers['x-api-key'];
            
            if (!apiKey) {
                return res.status(401).json({
                    error: 'API key required',
                    message: 'Missing API key in request headers',
                    timestamp: new Date().toISOString()
                });
            }
            
            // Validate API key
            if (!this.validateApiKey(apiKey)) {
                this.recordFailedAttempt(req.ip);
                return res.status(401).json({
                    error: 'Invalid API key',
                    message: 'The provided API key is invalid',
                    timestamp: new Date().toISOString()
                });
            }
            
            req.apiKeyValid = true;
            next();
        };
    }
    
    // Enhanced JWT authentication middleware
    createJwtAuth() {
        return (req, res, next) => {
            if (!this.config.enableJwtAuth) {
                return next();
            }
            
            const authHeader = req.headers['authorization'];
            const token = authHeader && authHeader.split(' ')[1];
            
            if (!token) {
                return res.status(401).json({
                    error: 'Access token required',
                    message: 'Missing JWT token in Authorization header',
                    timestamp: new Date().toISOString()
                });
            }
            
            try {
                const decoded = jwt.verify(token, this.config.jwtSecret);
                req.user = decoded;
                req.jwtValid = true;
                next();
            } catch (error) {
                this.recordFailedAttempt(req.ip);
                
                let errorMessage = 'Invalid token';
                if (error.name === 'TokenExpiredError') {
                    errorMessage = 'Token expired';
                } else if (error.name === 'JsonWebTokenError') {
                    errorMessage = 'Malformed token';
                }
                
                return res.status(403).json({
                    error: errorMessage,
                    message: 'JWT token validation failed',
                    timestamp: new Date().toISOString()
                });
            }
        };
    }
    
    // IP whitelist middleware
    createIpWhitelist() {
        return (req, res, next) => {
            if (!this.config.enableIpWhitelist || this.config.ipWhitelist.length === 0) {
                return next();
            }
            
            const clientIp = req.ip || req.connection.remoteAddress;
            
            if (!this.config.ipWhitelist.includes(clientIp)) {
                console.warn(`🚨 Blocked request from non-whitelisted IP: ${clientIp}`);
                return res.status(403).json({
                    error: 'IP not allowed',
                    message: 'Your IP address is not authorized to access this resource',
                    timestamp: new Date().toISOString()
                });
            }
            
            next();
        };
    }
    
    // Brute force protection
    createBruteForceProtection() {
        return (req, res, next) => {
            const ip = req.ip;
            const attempts = this.failedAttempts.get(ip) || { count: 0, lastAttempt: 0 };
            
            const now = Date.now();
            const timeSinceLastAttempt = now - attempts.lastAttempt;
            
            // Reset attempts if more than 1 hour has passed
            if (timeSinceLastAttempt > 60 * 60 * 1000) {
                attempts.count = 0;
            }
            
            // Block if too many failed attempts
            if (attempts.count >= 10) {
                const blockTimeRemaining = (60 * 60 * 1000) - timeSinceLastAttempt;
                if (blockTimeRemaining > 0) {
                    console.warn(`🚨 Blocked IP due to brute force: ${ip}`);
                    return res.status(429).json({
                        error: 'Too many failed attempts',
                        message: 'IP temporarily blocked due to multiple failed authentication attempts',
                        retryAfter: Math.round(blockTimeRemaining / 1000),
                        timestamp: new Date().toISOString()
                    });
                }
            }
            
            next();
        };
    }
    
    // Security headers middleware
    createSecurityHeaders() {
        return (req, res, next) => {
            // Security headers
            res.setHeader('X-Content-Type-Options', 'nosniff');
            res.setHeader('X-Frame-Options', 'DENY');
            res.setHeader('X-XSS-Protection', '1; mode=block');
            res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
            res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
            res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';");
            
            // Remove identifying headers
            res.removeHeader('X-Powered-By');
            res.removeHeader('Server');
            
            next();
        };
    }
    
    // Helper methods
    validateApiKey(apiKey) {
        // In production, this should validate against a database or secure store
        return apiKey === this.config.apiKeySecret;
    }
    
    recordFailedAttempt(ip) {
        const attempts = this.failedAttempts.get(ip) || { count: 0, lastAttempt: 0 };
        attempts.count++;
        attempts.lastAttempt = Date.now();
        this.failedAttempts.set(ip, attempts);
        
        console.warn(`🚨 Failed authentication attempt from ${ip} (${attempts.count} attempts)`);
    }
    
    getEndpointPattern(path) {
        // Match endpoint patterns
        for (const [pattern, _] of this.endpointLimits.entries()) {
            if (path.startsWith(pattern)) {
                return pattern;
            }
        }
        return path;
    }
    
    // Get comprehensive middleware stack
    getMiddlewareStack() {
        return [
            this.createSecurityHeaders(),
            this.createIpWhitelist(),
            this.createBruteForceProtection(),
            this.createGeneralRateLimiter(),
            this.createEndpointRateLimiter(),
            this.createApiKeyAuth(),
            this.createJwtAuth()
        ];
    }
    
    // Get MCP-specific middleware stack
    getMCPMiddlewareStack() {
        return [
            this.createSecurityHeaders(),
            this.createIpWhitelist(),
            this.createBruteForceProtection(),
            this.createMCPRateLimiter(),
            this.createApiKeyAuth(),
            this.createJwtAuth()
        ];
    }
    
    // Cleanup old entries periodically
    startCleanup() {
        setInterval(() => {
            const now = Date.now();
            const oneHour = 60 * 60 * 1000;
            
            // Clean failed attempts
            for (const [ip, attempts] of this.failedAttempts.entries()) {
                if (now - attempts.lastAttempt > oneHour) {
                    this.failedAttempts.delete(ip);
                }
            }
            
            // Clean rate limit data
            for (const [key, requests] of this.userRateLimits.entries()) {
                const validRequests = requests.filter(timestamp => now - timestamp < oneHour);
                if (validRequests.length === 0) {
                    this.userRateLimits.delete(key);
                } else {
                    this.userRateLimits.set(key, validRequests);
                }
            }
            
        }, 5 * 60 * 1000); // Clean every 5 minutes
    }
}

// Create singleton instance
const authRateLimiter = new AuthRateLimiter();

// Start cleanup process
authRateLimiter.startCleanup();

module.exports = {
    AuthRateLimiter,
    authRateLimiter,
    
    // Export middleware functions
    generalRateLimit: authRateLimiter.createGeneralRateLimiter(),
    mcpRateLimit: authRateLimiter.createMCPRateLimiter(),
    endpointRateLimit: authRateLimiter.createEndpointRateLimiter(),
    apiKeyAuth: authRateLimiter.createApiKeyAuth(),
    jwtAuth: authRateLimiter.createJwtAuth(),
    ipWhitelist: authRateLimiter.createIpWhitelist(),
    bruteForceProtection: authRateLimiter.createBruteForceProtection(),
    securityHeaders: authRateLimiter.createSecurityHeaders(),
    
    // Middleware stacks
    fullSecurityStack: authRateLimiter.getMiddlewareStack(),
    mcpSecurityStack: authRateLimiter.getMCPMiddlewareStack()
};