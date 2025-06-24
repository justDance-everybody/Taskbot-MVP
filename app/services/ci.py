"""
CI integration service
Handles GitHub Actions status parsing and CI result processing
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse

import httpx

from ..config import get_settings
from ..bitable import CIState

logger = logging.getLogger(__name__)


class CIResult:
    """CI result data structure"""
    
    def __init__(self, state: CIState, message: str, details: Optional[str] = None,
                 url: Optional[str] = None, timestamp: Optional[datetime] = None):
        self.state = state
        self.message = message
        self.details = details
        self.url = url
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "state": self.state.value,
            "message": self.message,
            "details": self.details,
            "url": self.url,
            "timestamp": self.timestamp.isoformat()
        }


class GitHubCIService:
    """GitHub CI integration service"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def parse_webhook_payload(self, payload: Dict[str, Any]) -> Optional[CIResult]:
        """Parse GitHub webhook payload"""
        try:
            action = payload.get("action")
            workflow_run = payload.get("workflow_run")
            
            if not workflow_run:
                logger.warning("No workflow_run in payload")
                return None
            
            # Extract basic information
            status = workflow_run.get("status")
            conclusion = workflow_run.get("conclusion")
            workflow_name = workflow_run.get("name", "Unknown Workflow")
            html_url = workflow_run.get("html_url")
            created_at = workflow_run.get("created_at")
            
            # Parse timestamp
            timestamp = None
            if created_at:
                try:
                    timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp: {e}")
            
            # Determine CI state and message
            if status == "completed":
                if conclusion == "success":
                    state = CIState.SUCCESS
                    message = f"✅ {workflow_name} 执行成功"
                elif conclusion == "failure":
                    state = CIState.FAILURE
                    message = f"❌ {workflow_name} 执行失败"
                elif conclusion == "cancelled":
                    state = CIState.ERROR
                    message = f"⚠️ {workflow_name} 被取消"
                else:
                    state = CIState.ERROR
                    message = f"⚠️ {workflow_name} 状态异常: {conclusion}"
            elif status == "in_progress":
                state = CIState.PENDING
                message = f"🔄 {workflow_name} 正在执行"
            else:
                state = CIState.PENDING
                message = f"⏳ {workflow_name} 状态: {status}"
            
            # Extract additional details
            details = self._extract_workflow_details(workflow_run)
            
            return CIResult(
                state=state,
                message=message,
                details=details,
                url=html_url,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Error parsing GitHub webhook payload: {e}")
            return None
    
    def _extract_workflow_details(self, workflow_run: Dict[str, Any]) -> str:
        """Extract detailed information from workflow run"""
        details = []
        
        # Basic info
        if workflow_run.get("head_branch"):
            details.append(f"分支: {workflow_run['head_branch']}")
        
        if workflow_run.get("head_sha"):
            short_sha = workflow_run["head_sha"][:7]
            details.append(f"提交: {short_sha}")
        
        # Timing info
        if workflow_run.get("run_started_at"):
            details.append(f"开始时间: {workflow_run['run_started_at']}")
        
        if workflow_run.get("updated_at"):
            details.append(f"更新时间: {workflow_run['updated_at']}")
        
        # Actor info
        actor = workflow_run.get("actor", {})
        if actor.get("login"):
            details.append(f"触发者: {actor['login']}")
        
        return "\n".join(details) if details else None
    
    def extract_repository_info(self, payload: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract repository information from payload"""
        try:
            repository = payload.get("repository", {})
            return {
                "name": repository.get("name", ""),
                "full_name": repository.get("full_name", ""),
                "html_url": repository.get("html_url", ""),
                "clone_url": repository.get("clone_url", "")
            }
        except Exception as e:
            logger.error(f"Error extracting repository info: {e}")
            return None
    
    async def fetch_workflow_logs(self, workflow_url: str) -> Optional[str]:
        """Fetch workflow logs from GitHub (if accessible)"""
        try:
            # This is a simplified implementation
            # In practice, you'd need GitHub API token and proper authentication
            async with httpx.AsyncClient() as client:
                response = await client.get(workflow_url)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.warning(f"Failed to fetch workflow logs: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching workflow logs: {e}")
            return None
    
    def parse_submission_url(self, url: str) -> Dict[str, Any]:
        """Parse submission URL to extract repository and commit info"""
        try:
            parsed = urlparse(url)
            
            # GitHub URL patterns
            github_patterns = [
                r"github\.com/([^/]+)/([^/]+)/commit/([a-f0-9]+)",
                r"github\.com/([^/]+)/([^/]+)/pull/(\d+)",
                r"github\.com/([^/]+)/([^/]+)/tree/([^/]+)",
                r"github\.com/([^/]+)/([^/]+)"
            ]
            
            for pattern in github_patterns:
                match = re.search(pattern, url)
                if match:
                    groups = match.groups()
                    result = {
                        "platform": "github",
                        "owner": groups[0],
                        "repo": groups[1],
                        "url": url
                    }
                    
                    if len(groups) > 2:
                        if "commit" in pattern:
                            result["commit"] = groups[2]
                        elif "pull" in pattern:
                            result["pull_request"] = groups[2]
                        elif "tree" in pattern:
                            result["branch"] = groups[2]
                    
                    return result
            
            # Generic URL
            return {
                "platform": "unknown",
                "url": url,
                "domain": parsed.netloc
            }
            
        except Exception as e:
            logger.error(f"Error parsing submission URL: {e}")
            return {"platform": "unknown", "url": url}
    
    async def check_repository_ci_status(self, repo_info: Dict[str, Any]) -> Optional[CIResult]:
        """Check CI status for a repository"""
        try:
            # This would require GitHub API integration
            # For now, return a placeholder
            return CIResult(
                state=CIState.PENDING,
                message="CI状态检查功能待实现",
                details="需要GitHub API集成"
            )
        except Exception as e:
            logger.error(f"Error checking repository CI status: {e}")
            return None


class CIService:
    """General CI service supporting multiple platforms"""
    
    def __init__(self):
        self.github_service = GitHubCIService()
    
    def parse_webhook(self, platform: str, payload: Dict[str, Any]) -> Optional[CIResult]:
        """Parse webhook from different CI platforms"""
        if platform.lower() == "github":
            return self.github_service.parse_webhook_payload(payload)
        else:
            logger.warning(f"Unsupported CI platform: {platform}")
            return None
    
    def parse_submission_url(self, url: str) -> Dict[str, Any]:
        """Parse submission URL to determine platform and extract info"""
        if "github.com" in url:
            return self.github_service.parse_submission_url(url)
        else:
            # Generic URL parsing
            parsed = urlparse(url)
            return {
                "platform": "unknown",
                "url": url,
                "domain": parsed.netloc
            }
    
    async def check_submission_status(self, url: str) -> CIResult:
        """Check CI status for a submission URL"""
        try:
            url_info = self.parse_submission_url(url)
            platform = url_info.get("platform")
            
            if platform == "github":
                # Check GitHub CI status
                result = await self.github_service.check_repository_ci_status(url_info)
                if result:
                    return result
            
            # Fallback: assume success if URL is accessible
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.head(url, timeout=10)
                    if response.status_code == 200:
                        return CIResult(
                            state=CIState.SUCCESS,
                            message="✅ 提交链接可访问",
                            details=f"HTTP状态码: {response.status_code}",
                            url=url
                        )
                    else:
                        return CIResult(
                            state=CIState.FAILURE,
                            message="❌ 提交链接不可访问",
                            details=f"HTTP状态码: {response.status_code}",
                            url=url
                        )
                except httpx.TimeoutException:
                    return CIResult(
                        state=CIState.ERROR,
                        message="⚠️ 提交链接访问超时",
                        details="请检查链接是否正确",
                        url=url
                    )
                except Exception as e:
                    return CIResult(
                        state=CIState.ERROR,
                        message="⚠️ 无法检查提交链接",
                        details=str(e),
                        url=url
                    )
                    
        except Exception as e:
            logger.error(f"Error checking submission status: {e}")
            return CIResult(
                state=CIState.ERROR,
                message="❌ CI状态检查失败",
                details=str(e),
                url=url
            )


# Global CI service instance
_ci_service: Optional[CIService] = None


def get_ci_service() -> CIService:
    """Get global CI service instance"""
    global _ci_service
    if _ci_service is None:
        _ci_service = CIService()
    return _ci_service
