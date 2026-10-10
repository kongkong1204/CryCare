"""예산 초과 시 프로젝트 결제를 끊어 비용을 막는다 (스펙 §4 운영 안전).

예산 알림(Pub/Sub) → 이 함수. 사용액이 예산을 넘으면 프로젝트의 결제 계정 연결을 해제한다.
해제되면 Cloud Run 등 유료 리소스가 멈춘다. 복구: 콘솔 결제 화면에서 결제 계정을 다시 연결.
예산 미만 알림이 올 때는 결제 해제 권한이 있는지만 확인해 로그로 남긴다.
"""
import base64
import json
import logging
import os

import functions_framework
from googleapiclient import discovery

PROJECT_ID = os.environ["TARGET_PROJECT"]
PROJECT_NAME = f"projects/{PROJECT_ID}"
UNLINK_PERMISSION = "resourcemanager.projects.deleteBillingAssignment"

logging.getLogger().setLevel(logging.INFO)


@functions_framework.cloud_event
def stop_billing(cloud_event):
    data = json.loads(base64.b64decode(cloud_event.data["message"]["data"]).decode())
    cost, budget = data["costAmount"], data["budgetAmount"]
    logging.info("예산 알림: 사용 %s / 예산 %s %s", cost, budget, data.get("currencyCode"))

    if cost < budget:
        crm = discovery.build("cloudresourcemanager", "v1", cache_discovery=False)
        granted = crm.projects().testIamPermissions(
            resource=PROJECT_ID, body={"permissions": [UNLINK_PERMISSION]}
        ).execute().get("permissions", [])
        logging.info("예산 미만, 결제 해제 권한 %s", "있음" if granted else "없음")
        return

    billing = discovery.build("cloudbilling", "v1", cache_discovery=False)
    info = billing.projects().getBillingInfo(name=PROJECT_NAME).execute()
    if not info.get("billingEnabled"):
        logging.info("이미 결제가 해제돼 있음")
        return
    billing.projects().updateBillingInfo(name=PROJECT_NAME, body={"billingAccountName": ""}).execute()
    logging.warning("예산 초과로 프로젝트 결제를 해제함: %s", PROJECT_ID)
