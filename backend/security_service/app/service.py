from kubernetes import client, config
from kubernetes.client.rest import ApiException
from fastapi import HTTPException
from typing import Dict, List, Optional
from app.logger import logger
from app.schema import VulnerabilityInfo, VulnerabilitySummary, SecurityMetrics, APIResponse
from datetime import datetime

class SecurityService:
    def __init__(self):
        self.k8s_client = None
        self.initialize_kubernetes_client()
    
    def initialize_kubernetes_client(self):
        """Initialize Kubernetes client"""
        try:
            # Try to load in-cluster config first, then fall back to local config
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            except:
                config.load_kube_config()
                logger.info("Loaded local Kubernetes configuration")
            
            self.k8s_client = client.CustomObjectsApi()
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    def get_vulnerability_reports_internal(self, namespace: Optional[str] = None) -> Dict:
        """
        Internal function to retrieve vulnerability reports from Kubernetes cluster.
        """
        try:
            group = "aquasecurity.github.io"
            version = "v1alpha1"
            plural = "vulnerabilityreports"
            
            if namespace:
                response = self.k8s_client.list_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural=plural
                )
            else:
                response = self.k8s_client.list_cluster_custom_object(
                    group=group,
                    version=version,
                    plural=plural
                )
            
            return response
        
        except ApiException as e:
            logger.error(f"Kubernetes API Exception: {e}")
            raise HTTPException(status_code=500, detail=f"Kubernetes API Error: {e}")
        except Exception as e:
            logger.error(f"Error retrieving vulnerability reports: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    def get_all_reports(self) -> APIResponse:
        """Get all vulnerability reports from all namespaces"""
        try:
            reports = self.get_vulnerability_reports_internal()
            return APIResponse(
                success=True,
                message=f"Retrieved {len(reports.get('items', []))} vulnerability reports",
                data=reports,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error in get_all_reports: {e}")
            raise

    def get_reports_by_namespace(self, namespace: str) -> APIResponse:
        """Get vulnerability reports for a specific namespace"""
        try:
            reports = self.get_vulnerability_reports_internal(namespace=namespace)
            return APIResponse(
                success=True,
                message=f"Retrieved {len(reports.get('items', []))} vulnerability reports for namespace '{namespace}'",
                data=reports,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error in get_reports_by_namespace: {e}")
            raise

    def get_vulnerability_summary(self, namespace: Optional[str] = None) -> APIResponse:
        """Get summary of vulnerability reports"""
        try:
            reports = self.get_vulnerability_reports_internal(namespace=namespace)
            summaries = []
            
            for item in reports.get('items', []):
                summary = VulnerabilitySummary(
                    report_name=item['metadata']['name'],
                    namespace=item['metadata']['namespace'],
                    container_name=item['metadata']['labels'].get('trivy-operator.container.name'),
                    image_repository=item['report']['artifact'].get('repository', ''),
                    image_tag=item['report']['artifact'].get('tag', ''),
                    critical_count=item['report']['summary']['criticalCount'],
                    high_count=item['report']['summary']['highCount'],
                    medium_count=item['report']['summary']['mediumCount'],
                    low_count=item['report']['summary']['lowCount'],
                    total_vulnerabilities=len(item['report'].get('vulnerabilities', []))
                )
                summaries.append(summary.dict())
            
            message = f"Retrieved summary for {len(summaries)} reports"
            if namespace:
                message += f" in namespace '{namespace}'"
            
            return APIResponse(
                success=True,
                message=message,
                data=summaries,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error in get_vulnerability_summary: {e}")
            raise

    def get_vulnerabilities(self, severity: Optional[str] = None, fixable_only: bool = False, 
                          limit: Optional[int] = None, namespace: Optional[str] = None) -> APIResponse:
        """Get vulnerabilities with optional filtering"""
        try:
            reports = self.get_vulnerability_reports_internal(namespace=namespace)
            vulnerabilities = []
            
            for item in reports.get('items', []):
                for vuln in item['report'].get('vulnerabilities', []):
                    # Apply severity filter
                    if severity and vuln.get('severity', '').upper() != severity.upper():
                        continue
                    
                    # Apply fixable filter
                    if fixable_only and not (vuln.get('fixedVersion') and vuln.get('fixedVersion').strip()):
                        continue
                    
                    vuln_info = VulnerabilityInfo(
                        report_name=item['metadata']['name'],
                        namespace=item['metadata']['namespace'],
                        vulnerability_id=vuln.get('vulnerabilityID', ''),
                        title=vuln.get('title', ''),
                        severity=vuln.get('severity', ''),
                        score=vuln.get('score'),
                        resource=vuln.get('resource', ''),
                        installed_version=vuln.get('installedVersion', ''),
                        fixed_version=vuln.get('fixedVersion', ''),
                        primary_link=vuln.get('primaryLink', '')
                    )
                    vulnerabilities.append(vuln_info.dict())
            
            # Apply limit
            if limit:
                vulnerabilities = vulnerabilities[:limit]
            
            return APIResponse(
                success=True,
                message=f"Retrieved {len(vulnerabilities)} vulnerabilities",
                data=vulnerabilities,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error in get_vulnerabilities: {e}")
            raise

    def get_namespaces_with_reports(self) -> APIResponse:
        """Get list of namespaces that have vulnerability reports"""
        try:
            reports = self.get_vulnerability_reports_internal()
            namespaces = set()
            
            for item in reports.get('items', []):
                namespaces.add(item['metadata']['namespace'])
            
            namespace_list = sorted(list(namespaces))
            
            return APIResponse(
                success=True,
                message=f"Found {len(namespace_list)} namespaces with vulnerability reports",
                data=namespace_list,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error in get_namespaces_with_reports: {e}")
            raise

    def get_security_metrics(self) -> APIResponse:
        """Get overall security metrics"""
        try:
            reports = self.get_vulnerability_reports_internal()
            
            total_reports = len(reports.get('items', []))
            total_vulnerabilities = 0
            critical_count = 0
            high_count = 0
            medium_count = 0
            low_count = 0
            fixable_count = 0
            namespaces = set()
            
            for item in reports.get('items', []):
                namespaces.add(item['metadata']['namespace'])
                summary = item['report']['summary']
                critical_count += summary.get('criticalCount', 0)
                high_count += summary.get('highCount', 0)
                medium_count += summary.get('mediumCount', 0)
                low_count += summary.get('lowCount', 0)
                
                # Count fixable vulnerabilities
                for vuln in item['report'].get('vulnerabilities', []):
                    total_vulnerabilities += 1
                    if vuln.get('fixedVersion') and vuln.get('fixedVersion').strip():
                        fixable_count += 1
            
            metrics = SecurityMetrics(
                total_reports=total_reports,
                total_vulnerabilities=total_vulnerabilities,
                critical_count=critical_count,
                high_count=high_count,
                medium_count=medium_count,
                low_count=low_count,
                fixable_count=fixable_count,
                affected_namespaces=len(namespaces),
                last_updated=datetime.now().isoformat()
            )
            
            return APIResponse(
                success=True,
                message="Security metrics retrieved successfully",
                data=metrics.dict(),
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error in get_security_metrics: {e}")
            raise

    def health_check(self) -> Dict:
        """Health check for the service"""
        try:
            # Test Kubernetes connection
            self.k8s_client.get_api_resources()
            return {
                "status": "healthy",
                "kubernetes": "connected",
                "service": "security-service",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

# Global service instance
security_service = SecurityService()