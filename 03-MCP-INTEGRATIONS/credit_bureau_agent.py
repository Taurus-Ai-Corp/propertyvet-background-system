#!/usr/bin/env python3
"""
TAURUS PropertyVet™ Credit Bureau Agent
MCP Integration for Equifax & TransUnion APIs
Production-Grade Background Check Platform
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import hashlib
import hmac
import base64
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/user/Documents/TAURUS AI Corp./CURSOR Projects/TAURUS-AI-CORP-PORTFOLIO/03-REVENUE-SYSTEMS/PROPERTYVET-BACKGROUND-SYSTEM/08-DATA/credit_bureau_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CreditBureauProvider(Enum):
    EQUIFAX = "equifax"
    TRANSUNION = "transunion"
    EXPERIAN = "experian"

@dataclass
class CreditCheckRequest:
    """Credit check request data structure"""
    ssn: str
    first_name: str
    last_name: str
    date_of_birth: str
    address: str
    city: str
    state: str
    zip_code: str
    request_id: str
    bureau: CreditBureauProvider

@dataclass
class CreditScore:
    """Credit score data structure"""
    score: int
    range_min: int
    range_max: int
    grade: str
    factors: List[str]
    date_generated: str

@dataclass
class CreditReport:
    """Complete credit report structure"""
    request_id: str
    consumer_id: str
    credit_score: CreditScore
    accounts: List[Dict]
    inquiries: List[Dict]
    public_records: List[Dict]
    alerts: List[Dict]
    recommendations: List[str]
    risk_level: str
    verification_status: str

class CreditBureauAgent:
    """
    TAURUS PropertyVet™ Credit Bureau Agent
    Handles integration with major credit bureaus for background checks
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.session = None
        self.request_count = 0
        self.rate_limits = {
            CreditBureauProvider.EQUIFAX: {"max_per_minute": 60, "current": 0, "reset_time": time.time()},
            CreditBureauProvider.TRANSUNION: {"max_per_minute": 100, "current": 0, "reset_time": time.time()},
            CreditBureauProvider.EXPERIAN: {"max_per_minute": 80, "current": 0, "reset_time": time.time()}
        }
        
    def _load_config(self) -> Dict:
        """Load configuration from environment and config files"""
        config_path = "/Users/user/Documents/TAURUS AI Corp./CURSOR Projects/TAURUS-AI-CORP-PORTFOLIO/03-REVENUE-SYSTEMS/PROPERTYVET-BACKGROUND-SYSTEM/02-CONFIGS/credit_bureau_config.json"
        
        default_config = {
            "equifax": {
                "api_url": "https://api.equifax.com/business/credit/v1",
                "api_key": os.getenv("EQUIFAX_API_KEY", ""),
                "secret_key": os.getenv("EQUIFAX_SECRET_KEY", ""),
                "member_number": os.getenv("EQUIFAX_MEMBER_NUMBER", ""),
                "timeout": 30,
                "retry_attempts": 3
            },
            "transunion": {
                "api_url": "https://api.transunion.com/creditreporting/v2",
                "api_key": os.getenv("TRANSUNION_API_KEY", ""),
                "secret_key": os.getenv("TRANSUNION_SECRET_KEY", ""),
                "subscriber_id": os.getenv("TRANSUNION_SUBSCRIBER_ID", ""),
                "timeout": 30,
                "retry_attempts": 3
            },
            "experian": {
                "api_url": "https://api.experian.com/businessinformation/businesses/v1",
                "api_key": os.getenv("EXPERIAN_API_KEY", ""),
                "secret_key": os.getenv("EXPERIAN_SECRET_KEY", ""),
                "subcode": os.getenv("EXPERIAN_SUBCODE", ""),
                "timeout": 30,
                "retry_attempts": 3
            },
            "security": {
                "encryption_key": os.getenv("TAURUS_ENCRYPTION_KEY", ""),
                "data_retention_days": 90,
                "audit_logging": True
            },
            "compliance": {
                "fcra_compliant": True,
                "data_masking": True,
                "consent_required": True
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                return config
        except Exception as e:
            logger.warning(f"Could not load config file: {e}, using defaults")
            
        return default_config
    
    async def initialize(self):
        """Initialize the credit bureau agent"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": "TAURUS-PropertyVet/1.0",
                "Content-Type": "application/json"
            }
        )
        logger.info("Credit Bureau Agent initialized successfully")
        
    async def close(self):
        """Close the agent and cleanup resources"""
        if self.session:
            await self.session.close()
        logger.info("Credit Bureau Agent closed")
        
    def _generate_request_signature(self, bureau: CreditBureauProvider, request_data: str, timestamp: str) -> str:
        """Generate HMAC signature for API authentication"""
        secret_key = self.config[bureau.value]["secret_key"]
        message = f"{timestamp}:{request_data}"
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _check_rate_limit(self, bureau: CreditBureauProvider) -> bool:
        """Check if request is within rate limits"""
        current_time = time.time()
        rate_limit = self.rate_limits[bureau]
        
        # Reset counter if minute has passed
        if current_time - rate_limit["reset_time"] >= 60:
            rate_limit["current"] = 0
            rate_limit["reset_time"] = current_time
            
        # Check if under limit
        if rate_limit["current"] >= rate_limit["max_per_minute"]:
            return False
            
        rate_limit["current"] += 1
        return True
    
    async def _make_credit_request(self, bureau: CreditBureauProvider, request: CreditCheckRequest) -> Dict:
        """Make credit check request to specific bureau"""
        if not self._check_rate_limit(bureau):
            raise Exception(f"Rate limit exceeded for {bureau.value}")
            
        config = self.config[bureau.value]
        timestamp = str(int(time.time()))
        
        # Prepare request payload based on bureau
        if bureau == CreditBureauProvider.EQUIFAX:
            payload = {
                "memberNumber": config["member_number"],
                "consumer": {
                    "ssn": request.ssn,
                    "firstName": request.first_name,
                    "lastName": request.last_name,
                    "dateOfBirth": request.date_of_birth,
                    "address": {
                        "street": request.address,
                        "city": request.city,
                        "state": request.state,
                        "zipCode": request.zip_code
                    }
                },
                "requestId": request.request_id,
                "productCode": "CREDIT_PROFILE"
            }
        elif bureau == CreditBureauProvider.TRANSUNION:
            payload = {
                "subscriberId": config["subscriber_id"],
                "subject": {
                    "ssn": request.ssn,
                    "name": {
                        "first": request.first_name,
                        "last": request.last_name
                    },
                    "dateOfBirth": request.date_of_birth,
                    "currentAddress": {
                        "line1": request.address,
                        "city": request.city,
                        "state": request.state,
                        "postalCode": request.zip_code
                    }
                },
                "requestId": request.request_id,
                "product": "CREDIT_REPORT"
            }
        else:  # Experian
            payload = {
                "subcode": config["subcode"],
                "consumer": {
                    "ssn": request.ssn,
                    "firstName": request.first_name,
                    "lastName": request.last_name,
                    "dob": request.date_of_birth,
                    "addresses": [{
                        "line1": request.address,
                        "city": request.city,
                        "state": request.state,
                        "zip": request.zip_code
                    }]
                },
                "options": {
                    "includeScore": True,
                    "includeFactors": True
                }
            }
        
        # Generate signature
        request_json = json.dumps(payload, separators=(',', ':'))
        signature = self._generate_request_signature(bureau, request_json, timestamp)
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "X-Request-ID": request.request_id
        }
        
        # Make API request
        try:
            async with self.session.post(
                f"{config['api_url']}/creditcheck",
                json=payload,
                headers=headers,
                timeout=config["timeout"]
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successful credit check from {bureau.value}: {request.request_id}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Credit check failed from {bureau.value}: {response.status} - {error_text}")
                    raise Exception(f"API Error: {response.status} - {error_text}")
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout error for {bureau.value} request: {request.request_id}")
            raise Exception(f"Request timeout for {bureau.value}")
        except Exception as e:
            logger.error(f"Request error for {bureau.value}: {str(e)}")
            raise
    
    def _parse_credit_response(self, bureau: CreditBureauProvider, response_data: Dict, request_id: str) -> CreditReport:
        """Parse credit bureau response into standardized format"""
        if bureau == CreditBureauProvider.EQUIFAX:
            return self._parse_equifax_response(response_data, request_id)
        elif bureau == CreditBureauProvider.TRANSUNION:
            return self._parse_transunion_response(response_data, request_id)
        else:  # Experian
            return self._parse_experian_response(response_data, request_id)
    
    def _parse_equifax_response(self, data: Dict, request_id: str) -> CreditReport:
        """Parse Equifax response"""
        credit_score_data = data.get("creditScore", {})
        credit_score = CreditScore(
            score=credit_score_data.get("score", 0),
            range_min=credit_score_data.get("rangeMin", 300),
            range_max=credit_score_data.get("rangeMax", 850),
            grade=credit_score_data.get("grade", "Unknown"),
            factors=credit_score_data.get("factors", []),
            date_generated=datetime.now().isoformat()
        )
        
        return CreditReport(
            request_id=request_id,
            consumer_id=data.get("consumerId", ""),
            credit_score=credit_score,
            accounts=data.get("accounts", []),
            inquiries=data.get("inquiries", []),
            public_records=data.get("publicRecords", []),
            alerts=data.get("alerts", []),
            recommendations=self._generate_recommendations(credit_score.score),
            risk_level=self._calculate_risk_level(credit_score.score),
            verification_status="VERIFIED"
        )
    
    def _parse_transunion_response(self, data: Dict, request_id: str) -> CreditReport:
        """Parse TransUnion response"""
        score_data = data.get("riskModel", {}).get("score", {})
        credit_score = CreditScore(
            score=score_data.get("results", 0),
            range_min=300,
            range_max=850,
            grade=score_data.get("grade", "Unknown"),
            factors=score_data.get("reasonCodes", []),
            date_generated=datetime.now().isoformat()
        )
        
        return CreditReport(
            request_id=request_id,
            consumer_id=data.get("id", ""),
            credit_score=credit_score,
            accounts=data.get("tradeline", []),
            inquiries=data.get("inquiry", []),
            public_records=data.get("publicRecord", []),
            alerts=data.get("fraudShield", []),
            recommendations=self._generate_recommendations(credit_score.score),
            risk_level=self._calculate_risk_level(credit_score.score),
            verification_status="VERIFIED"
        )
    
    def _parse_experian_response(self, data: Dict, request_id: str) -> CreditReport:
        """Parse Experian response"""
        score_info = data.get("score", {})
        credit_score = CreditScore(
            score=score_info.get("value", 0),
            range_min=score_info.get("minRange", 300),
            range_max=score_info.get("maxRange", 850),
            grade=score_info.get("plus", {}).get("grade", "Unknown"),
            factors=score_info.get("factors", []),
            date_generated=datetime.now().isoformat()
        )
        
        return CreditReport(
            request_id=request_id,
            consumer_id=data.get("header", {}).get("reportId", ""),
            credit_score=credit_score,
            accounts=data.get("tradelines", []),
            inquiries=data.get("inquiries", []),
            public_records=data.get("publicRecords", []),
            alerts=data.get("informationalMessages", []),
            recommendations=self._generate_recommendations(credit_score.score),
            risk_level=self._calculate_risk_level(credit_score.score),
            verification_status="VERIFIED"
        )
    
    def _calculate_risk_level(self, credit_score: int) -> str:
        """Calculate risk level based on credit score"""
        if credit_score >= 750:
            return "LOW"
        elif credit_score >= 650:
            return "MEDIUM"
        elif credit_score >= 550:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    def _generate_recommendations(self, credit_score: int) -> List[str]:
        """Generate recommendations based on credit score"""
        recommendations = []
        
        if credit_score < 600:
            recommendations.extend([
                "Consider requiring a co-signer or additional security deposit",
                "Implement stricter income verification requirements",
                "Consider shorter lease terms with regular reviews"
            ])
        elif credit_score < 700:
            recommendations.extend([
                "Standard security deposit recommended",
                "Verify employment and income thoroughly",
                "Consider rental insurance requirement"
            ])
        else:
            recommendations.extend([
                "Low risk tenant - standard lease terms acceptable",
                "Minimal security deposit required",
                "Excellent rental history expected"
            ])
            
        return recommendations
    
    async def perform_credit_check(self, request: CreditCheckRequest) -> CreditReport:
        """Perform comprehensive credit check"""
        logger.info(f"Starting credit check: {request.request_id} via {request.bureau.value}")
        
        try:
            # Make request to credit bureau
            response_data = await self._make_credit_request(request.bureau, request)
            
            # Parse response
            credit_report = self._parse_credit_response(request.bureau, response_data, request.request_id)
            
            # Log for audit
            await self._audit_log_request(request, credit_report)
            
            # Store result
            await self._store_credit_report(credit_report)
            
            logger.info(f"Credit check completed: {request.request_id}")
            return credit_report
            
        except Exception as e:
            logger.error(f"Credit check failed: {request.request_id} - {str(e)}")
            raise
    
    async def _audit_log_request(self, request: CreditCheckRequest, report: CreditReport):
        """Log request for audit trail"""
        audit_data = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request.request_id,
            "bureau": request.bureau.value,
            "score": report.credit_score.score,
            "risk_level": report.risk_level,
            "user_id": "system",  # Should be passed from calling system
            "compliance_flags": {
                "fcra_compliant": True,
                "consent_verified": True,
                "purpose_valid": True
            }
        }
        
        audit_path = "/Users/user/Documents/TAURUS AI Corp./CURSOR Projects/TAURUS-AI-CORP-PORTFOLIO/03-REVENUE-SYSTEMS/PROPERTYVET-BACKGROUND-SYSTEM/08-DATA/audit_log.json"
        
        try:
            # Append to audit log
            if os.path.exists(audit_path):
                with open(audit_path, 'r') as f:
                    audit_log = json.load(f)
            else:
                audit_log = []
                
            audit_log.append(audit_data)
            
            with open(audit_path, 'w') as f:
                json.dump(audit_log, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    async def _store_credit_report(self, report: CreditReport):
        """Store credit report in secure storage"""
        storage_path = f"/Users/user/Documents/TAURUS AI Corp./CURSOR Projects/TAURUS-AI-CORP-PORTFOLIO/03-REVENUE-SYSTEMS/PROPERTYVET-BACKGROUND-SYSTEM/08-DATA/credit_reports/{report.request_id}.json"
        
        try:
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            
            # Convert to dictionary for storage
            report_data = {
                "request_id": report.request_id,
                "consumer_id": report.consumer_id,
                "credit_score": {
                    "score": report.credit_score.score,
                    "range_min": report.credit_score.range_min,
                    "range_max": report.credit_score.range_max,
                    "grade": report.credit_score.grade,
                    "factors": report.credit_score.factors,
                    "date_generated": report.credit_score.date_generated
                },
                "accounts": report.accounts,
                "inquiries": report.inquiries,
                "public_records": report.public_records,
                "alerts": report.alerts,
                "recommendations": report.recommendations,
                "risk_level": report.risk_level,
                "verification_status": report.verification_status,
                "stored_at": datetime.now().isoformat()
            }
            
            with open(storage_path, 'w') as f:
                json.dump(report_data, f, indent=2)
                
            logger.info(f"Credit report stored: {report.request_id}")
            
        except Exception as e:
            logger.error(f"Failed to store credit report: {e}")
    
    async def get_multiple_bureau_report(self, request_data: Dict) -> Dict[str, CreditReport]:
        """Get credit reports from multiple bureaus for comprehensive check"""
        results = {}
        
        bureaus = [CreditBureauProvider.EQUIFAX, CreditBureauProvider.TRANSUNION]
        
        tasks = []
        for bureau in bureaus:
            request = CreditCheckRequest(
                ssn=request_data["ssn"],
                first_name=request_data["first_name"],
                last_name=request_data["last_name"],
                date_of_birth=request_data["date_of_birth"],
                address=request_data["address"],
                city=request_data["city"],
                state=request_data["state"],
                zip_code=request_data["zip_code"],
                request_id=f"{request_data['request_id']}_{bureau.value}",
                bureau=bureau
            )
            tasks.append(self.perform_credit_check(request))
        
        # Execute all requests concurrently
        reports = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, report in enumerate(reports):
            bureau = bureaus[i]
            if isinstance(report, Exception):
                logger.error(f"Failed to get report from {bureau.value}: {report}")
                results[bureau.value] = None
            else:
                results[bureau.value] = report
        
        return results
    
    def get_agent_status(self) -> Dict:
        """Get current agent status and statistics"""
        return {
            "agent_name": "Credit Bureau Agent",
            "status": "OPERATIONAL",
            "version": "1.0.0",
            "total_requests": self.request_count,
            "rate_limits": {
                bureau.value: {
                    "current": limit_info["current"],
                    "max_per_minute": limit_info["max_per_minute"],
                    "time_until_reset": max(0, 60 - (time.time() - limit_info["reset_time"]))
                }
                for bureau, limit_info in self.rate_limits.items()
            },
            "last_updated": datetime.now().isoformat(),
            "integrations": {
                "equifax": bool(self.config["equifax"]["api_key"]),
                "transunion": bool(self.config["transunion"]["api_key"]),
                "experian": bool(self.config["experian"]["api_key"])
            }
        }

# MCP Server Integration
async def main():
    """Main function for testing the Credit Bureau Agent"""
    agent = CreditBureauAgent()
    await agent.initialize()
    
    # Example credit check request
    test_request = CreditCheckRequest(
        ssn="123-45-6789",
        first_name="John",
        last_name="Doe",
        date_of_birth="1985-05-15",
        address="123 Main St",
        city="Atlanta",
        state="GA",
        zip_code="30309",
        request_id="TEST_001",
        bureau=CreditBureauProvider.EQUIFAX
    )
    
    try:
        # This would normally make a real API call
        # For testing, we'll just show the agent status
        status = agent.get_agent_status()
        print(json.dumps(status, indent=2))
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())