# 🌐 TAURUS PropertyVet™ - PRODUCTION DEPLOYMENT GUIDE
## PropVet.TaurusAI.io Live Deployment

---

## 🎯 **IMMEDIATE PRODUCTION STEPS**

### **1. NAMECHEAP DOMAIN CONFIGURATION**

**Login to Namecheap Dashboard:**
- Domain: `TaurusAI.io`
- Create Subdomain: `PropVet.TaurusAI.io`

**DNS Configuration:**
```
Type: A Record
Host: PropVet
Value: [YOUR_SERVER_IP]
TTL: Automatic
```

**Alternative CNAME Setup:**
```
Type: CNAME
Host: PropVet
Value: your-app-name.herokuapp.com (if using Heroku)
TTL: Automatic
```

---

## 🚀 **CLOUD HOSTING OPTIONS (Choose One)**

### **OPTION 1: VERCEL (Recommended - Instant)**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy from your project directory
cd "/Users/user/Documents/TAURUS AI Corp./CURSOR Projects/TAURUS-AI-CORP-PORTFOLIO/03-REVENUE-SYSTEMS/PROPERTYVET-BACKGROUND-SYSTEM/10-WEB-APP"

# Initialize and deploy
vercel

# Follow prompts:
# Project name: propertyvet-saas
# Directory: ./
# Want to override settings? N
# Domain: propvet.taurusai.io
```

### **OPTION 2: HEROKU (Full Stack)**
```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create propertyvet-saas

# Set custom domain
heroku domains:add propvet.taurusai.io

# Deploy
git init
git add .
git commit -m "Production deployment"
git push heroku main
```

### **OPTION 3: DigitalOcean (VPS)**
```bash
# Create droplet (Ubuntu 22.04)
# Connect via SSH
ssh root@your-server-ip

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt-get install -y nodejs

# Install Nginx
apt update
apt install nginx

# Configure domain
# Point PropVet.TaurusAI.io A record to your server IP
```

---

## 🔧 **PRODUCTION CONFIGURATION FILES**

### **Environment Variables (.env.production)**
```bash
NODE_ENV=production
PORT=3000
DOMAIN=propvet.taurusai.io
JWT_SECRET=your_production_jwt_secret_here
CORS_ORIGIN=https://propvet.taurusai.io

# Database (upgrade to PostgreSQL)
DATABASE_URL=postgresql://username:password@hostname:port/database

# Email Service
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# Payment Processing
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# RTW Integration
RTW_API_URL=https://rtw.taurusai.io/api
RTW_API_KEY=your_rtw_api_key

# MCP Agents
FIRECRAWL_API_KEY=fc-your-key
PERPLEXITY_API_KEY=pplx-your-key
SPIDERFOOT_API_KEY=your-spiderfoot-key
```

### **Nginx Configuration (nginx.conf)**
```nginx
server {
    listen 80;
    server_name propvet.taurusai.io;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name propvet.taurusai.io;
    
    ssl_certificate /etc/letsencrypt/live/propvet.taurusai.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/propvet.taurusai.io/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 🛡️ **SSL CERTIFICATE SETUP**

### **Let's Encrypt (Free SSL)**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d propvet.taurusai.io

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### **Cloudflare SSL (Alternative)**
1. Add domain to Cloudflare
2. Change nameservers at Namecheap to Cloudflare's
3. Enable "Flexible" SSL in Cloudflare dashboard
4. Force HTTPS redirect

---

## 🔗 **RTW INTEGRATION DEPLOYMENT**

### **Connect to Existing RTW System**
```javascript
// Add to backend/server.js
const rtwIntegration = require('./rtw-integration');

// RTW Background Check Endpoint
app.post('/api/rtw/background-check', async (req, res) => {
    try {
        const { applicantData } = req.body;
        
        // Trigger RTW orchestration
        const rtwResult = await rtwIntegration.processBackgroundCheck({
            applicant: applicantData,
            sources: ['firecrawl', 'perplexity', 'spiderfoot'],
            priority: 'high'
        });
        
        res.json({
            success: true,
            rtwTaskId: rtwResult.taskId,
            estimatedCompletion: rtwResult.eta
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});
```

### **RTW Configuration File**
```json
{
  "rtw_config": {
    "web_orchestration_url": "https://rtw.taurusai.io",
    "agents": {
      "firecrawl": {
        "enabled": true,
        "api_key": "fc-your-key",
        "rate_limit": "100/hour"
      },
      "perplexity": {
        "enabled": true,
        "api_key": "pplx-your-key",
        "model": "llama-3.1-sonar-large-128k-online"
      },
      "spiderfoot": {
        "enabled": true,
        "api_key": "your-spiderfoot-key",
        "timeout": 300
      }
    },
    "background_check_workflow": {
      "identity_verification": "spiderfoot",
      "employment_check": "firecrawl",
      "public_records": "perplexity",
      "cross_validation": "all_agents"
    }
  }
}
```

---

## 📊 **PRODUCTION MONITORING SETUP**

### **Health Monitoring Script**
```bash
#!/bin/bash
# production_monitor.sh

while true; do
    # Check main service
    if ! curl -f -s https://propvet.taurusai.io/api/health > /dev/null; then
        echo "$(date): Main service down - restarting"
        pm2 restart propertyvet
        
        # Send alert
        curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
             -d chat_id="$TELEGRAM_CHAT_ID" \
             -d text="🚨 PropertyVet service restarted at $(date)"
    fi
    
    # Check RTW integration
    if ! curl -f -s https://rtw.taurusai.io/api/health > /dev/null; then
        echo "$(date): RTW service issues detected"
    fi
    
    sleep 60
done
```

### **PM2 Process Management**
```bash
# Install PM2
npm install -g pm2

# Start with PM2
pm2 start backend/simple_server.js --name "propertyvet"

# Enable startup script
pm2 startup
pm2 save

# Monitor
pm2 monit
```

---

## 🎯 **DEPLOYMENT COMMANDS (Execute These)**

### **Quick Vercel Deployment (5 minutes)**
```bash
cd "/Users/user/Documents/TAURUS AI Corp./CURSOR Projects/TAURUS-AI-CORP-PORTFOLIO/03-REVENUE-SYSTEMS/PROPERTYVET-BACKGROUND-SYSTEM/10-WEB-APP"

# Create vercel.json
cat > vercel.json << 'EOF'
{
  "version": 2,
  "builds": [
    {
      "src": "backend/simple_server.js",
      "use": "@vercel/node"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/backend/simple_server.js"
    },
    {
      "src": "/(.*)",
      "dest": "/frontend/index.html"
    }
  ],
  "env": {
    "NODE_ENV": "production"
  }
}
EOF

# Deploy
npx vercel --prod

# Set custom domain
npx vercel domains add propvet.taurusai.io
```

### **DNS Update at Namecheap**
1. Login to Namecheap
2. Go to Domain List → TaurusAI.io → Manage
3. Advanced DNS tab
4. Add Record:
   - Type: CNAME
   - Host: PropVet
   - Value: [vercel-deployment-url]
   - TTL: Automatic

---

## ✅ **PRODUCTION CHECKLIST**

### **Before Going Live:**
- [ ] Domain DNS configured
- [ ] SSL certificate installed
- [ ] Environment variables set
- [ ] Database migrated to production
- [ ] Payment processing configured
- [ ] RTW integration tested
- [ ] Health monitoring active
- [ ] Backup system enabled

### **After Going Live:**
- [ ] Test all user flows
- [ ] Verify payment processing
- [ ] Check background check functionality
- [ ] Monitor system performance
- [ ] Set up analytics tracking

---

## 🚀 **IMMEDIATE NEXT STEPS**

1. **Choose hosting platform** (Vercel recommended for speed)
2. **Deploy with one command** using scripts above
3. **Configure DNS** at Namecheap
4. **Test live application** at https://propvet.taurusai.io
5. **Integrate RTW** for enhanced background checks
6. **Monitor and scale** as needed

**Your client will have a live, production-ready SaaS platform at PropVet.TaurusAI.io within 30 minutes!**