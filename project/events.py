import uuid

from cloudevents.http import from_http
from flask import Blueprint, Response, current_app, request
from kubernetes import client, config

bp = Blueprint("events", __name__)


@bp.route("/", methods=["POST"])
def receiveEvent():
    event = from_http(request.headers, request.get_data())
    current_app.logger.info(
        "Received CloudEvent of type %s and data %s", event["type"], event.data
    )
    if event["type"] != "org.lowcomote.panoptes.actionExecution.trigger":
        return Response(status=400)
    triggerExecution(event.data)
    return Response(status=200)


def triggerExecution(eventData):
    envList = [
        {"name": "deploymentName", "value": eventData["deployment"]},
        {"name": "startDate", "value": eventData["startDate"]},
        {"name": "endDate", "value": eventData["endDate"]},
        {
            "name": "FEAST_S3_ENDPOINT_URL",
            "value": "http://minio-service.kubeflow.svc.cluster.local:9000",
        },
        {"name": "AWS_ACCESS_KEY_ID", "value": "minio"},
        {"name": "AWS_SECRET_ACCESS_KEY", "value": "minio123"},
        {"name": "ioNames", "value": eventData["parameters"]["ioNames"]},
    ]
    config.load_incluster_config()
    batch_v1 = client.BatchV1Api()
    containerImage = eventData["parameters"]["containerImage"]
    job = create_job_object(containerImage, envList)
    batch_v1.create_namespaced_job(body=job, namespace="panoptes")


def create_job_object(containerImage, envList):
    # Configureate Pod template container
    container = client.V1Container(
        name="retrain-container",
        image=containerImage,
        env=envList,
    )
    # Create and configure a spec section
    template = client.V1PodTemplateSpec(
        spec=client.V1PodSpec(
            image_pull_secrets=[{"name": "panoptes-registry-credentials"}],
            restart_policy="Never",
            containers=[container],
        )
    )
    # Create the specification of deployment
    spec = client.V1JobSpec(
        template=template, backoff_limit=4, ttl_seconds_after_finished=300
    )
    # Instantiate the job object
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="model-retraining-" + str(uuid.uuid4())),
        spec=spec,
    )

    return job
