from kubernetes import client, watch
from kubernetes.client.exceptions import ApiException
from typing import List, Dict, Optional
import logging
from models import K8sGPTCRD, ResultCRD

logger = logging.getLogger(__name__)

class K8sGPTCRDService:
    GROUP = "core.k8sgpt.ai"
    VERSION = "v1alpha1"
    PLURAL = "k8sgpts"

    @classmethod
    def create_k8sgpt(cls, namespace: str, k8sgpt: K8sGPTCRD) -> Dict:
        try:
            custom_objects_api = client.CustomObjectsApi()
            crd_data = k8sgpt.dict(by_alias=True)
            crd_data["apiVersion"] = f"{cls.GROUP}/{cls.VERSION}"
            return custom_objects_api.create_namespaced_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                namespace=namespace,
                plural=cls.PLURAL,
                body=crd_data
            )
        except ApiException as e:
            logger.error(f"Failed to create K8sGPT CRD: {e}")
            raise

    @classmethod
    def get_k8sgpt(cls, namespace: str, name: str) -> Dict:
        try:
            custom_objects_api = client.CustomObjectsApi()
            return custom_objects_api.get_namespaced_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                namespace=namespace,
                plural=cls.PLURAL,
                name=name
            )
        except ApiException as e:
            logger.error(f"Failed to get K8sGPT CRD: {e}")
            raise

    @classmethod
    def list_k8sgpts(cls, namespace: str = None) -> List[Dict]:
        try:
            custom_objects_api = client.CustomObjectsApi()
            if namespace:
                return custom_objects_api.list_namespaced_custom_object(
                    group=cls.GROUP,
                    version=cls.VERSION,
                    namespace=namespace,
                    plural=cls.PLURAL
                )["items"]
            return custom_objects_api.list_cluster_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                plural=cls.PLURAL
            )["items"]
        except ApiException as e:
            logger.error(f"Failed to list K8sGPT CRDs: {e}")
            raise

    @classmethod
    def update_k8sgpt(cls, namespace: str, name: str, k8sgpt: K8sGPTCRD) -> Dict:
        try:
            custom_objects_api = client.CustomObjectsApi()
            return custom_objects_api.patch_namespaced_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                namespace=namespace,
                plural=cls.PLURAL,
                name=name,
                body=k8sgpt.dict(by_alias=True)
            )
        except ApiException as e:
            logger.error(f"Failed to update K8sGPT CRD: {e}")
            raise

    @classmethod
    def delete_k8sgpt(cls, namespace: str, name: str) -> Dict:
        try:
            custom_objects_api = client.CustomObjectsApi()
            return custom_objects_api.delete_namespaced_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                namespace=namespace,
                plural=cls.PLURAL,
                name=name
            )
        except ApiException as e:
            logger.error(f"Failed to delete K8sGPT CRD: {e}")
            raise

    @classmethod
    def watch_k8sgpts(cls, namespace: str = None, timeout_seconds: int = 60):
        try:
            w = watch.Watch()
            custom_objects_api = client.CustomObjectsApi()
            if namespace:
                return w.stream(
                    custom_objects_api.list_namespaced_custom_object,
                    group=cls.GROUP,
                    version=cls.VERSION,
                    namespace=namespace,
                    plural=cls.PLURAL,
                    timeout_seconds=timeout_seconds
                )
            return w.stream(
                custom_objects_api.list_cluster_custom_object,
                group=cls.GROUP,
                version=cls.VERSION,
                plural=cls.PLURAL,
                timeout_seconds=timeout_seconds
            )
        except ApiException as e:
            logger.error(f"Failed to watch K8sGPT CRDs: {e}")
            raise

class ResultCRDService:
    GROUP = "core.k8sgpt.ai"
    VERSION = "v1alpha1"
    PLURAL = "results"

    @classmethod
    def create_result(cls, namespace: str, result: ResultCRD) -> Dict:
        try:
            custom_objects_api = client.CustomObjectsApi()
            return custom_objects_api.create_namespaced_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                namespace=namespace,
                plural=cls.PLURAL,
                body=result.dict(by_alias=True)
            )
        except ApiException as e:
            logger.error(f"Failed to create Result CRD: {e}")
            raise

    @classmethod
    def get_result(cls, namespace: str, name: str) -> Dict:
        try:
            custom_objects_api = client.CustomObjectsApi()
            return custom_objects_api.get_namespaced_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                namespace=namespace,
                plural=cls.PLURAL,
                name=name
            )
        except ApiException as e:
            logger.error(f"Failed to get Result CRD: {e}")
            raise

    @classmethod
    def list_results(cls, namespace: str = None) -> List[Dict]:
        try:
            custom_objects_api = client.CustomObjectsApi()
            if namespace:
                return custom_objects_api.list_namespaced_custom_object(
                    group=cls.GROUP,
                    version=cls.VERSION,
                    namespace=namespace,
                    plural=cls.PLURAL
                )["items"]
            return custom_objects_api.list_cluster_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                plural=cls.PLURAL
            )["items"]
        except ApiException as e:
            logger.error(f"Failed to list Result CRDs: {e}")
            raise

    @classmethod
    def update_result(cls, namespace: str, name: str, result: ResultCRD) -> Dict:
        try:
            custom_objects_api = client.CustomObjectsApi()
            return custom_objects_api.patch_namespaced_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                namespace=namespace,
                plural=cls.PLURAL,
                name=name,
                body=result.dict(by_alias=True)
            )
        except ApiException as e:
            logger.error(f"Failed to update Result CRD: {e}")
            raise

    @classmethod
    def delete_result(cls, namespace: str, name: str) -> Dict:
        try:
            custom_objects_api = client.CustomObjectsApi()
            return custom_objects_api.delete_namespaced_custom_object(
                group=cls.GROUP,
                version=cls.VERSION,
                namespace=namespace,
                plural=cls.PLURAL,
                name=name
            )
        except ApiException as e:
            logger.error(f"Failed to delete Result CRD: {e}")
            raise

    @classmethod
    def watch_results(cls, namespace: str = None, timeout_seconds: int = 60):
        try:
            w = watch.Watch()
            custom_objects_api = client.CustomObjectsApi()
            if namespace:
                return w.stream(
                    custom_objects_api.list_namespaced_custom_object,
                    group=cls.GROUP,
                    version=cls.VERSION,
                    namespace=namespace,
                    plural=cls.PLURAL,
                    timeout_seconds=timeout_seconds
                )
            return w.stream(
                custom_objects_api.list_cluster_custom_object,
                group=cls.GROUP,
                version=cls.VERSION,
                plural=cls.PLURAL,
                timeout_seconds=timeout_seconds
            )
        except ApiException as e:
            logger.error(f"Failed to watch Result CRDs: {e}")
            raise