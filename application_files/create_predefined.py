from kubernetes import client, config
import base64
import logging
# Load Kubernetes configuration
config.load_incluster_config()


core_v1_api = client.CoreV1Api()
apps_v1_api = client.AppsV1Api()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_or_update_secret(secret_name, secret_data):
    secret_name = secret_name.lower().replace('_', '-')
    secret_body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(name=secret_name),
        data={k: base64.b64encode(v.encode()).decode() for k, v in secret_data.items()}
    )
    try:
        core_v1_api.create_namespaced_secret(namespace='default', body=secret_body)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            logger.info(f"Secret {secret_name} already exists. Updating it.")
            core_v1_api.patch_namespaced_secret(name=secret_name, namespace='default', body=secret_body)
        else:
            raise e

def create_or_update_config_map(config_map_name, config_data):
    config_map_body = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(name=config_map_name),
        data=config_data
    )
    try:
        core_v1_api.create_namespaced_config_map(namespace='default', body=config_map_body)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            logger.info(f"ConfigMap {config_map_name} already exists. Updating it.")
            core_v1_api.patch_namespaced_config_map(name=config_map_name, namespace='default', body=config_map_body)
        else:
            raise e

def create_or_update_service(service_name, service_type, app_name):
    service_body = client.V1Service(
        api_version='v1',
        kind='Service',
        metadata=client.V1ObjectMeta(name=service_name),
        spec=client.V1ServiceSpec(
            type=service_type,
            ports=[client.V1ServicePort(port=5432, target_port=5432)],
            selector={'app': app_name}
        )
    )
    try:
        core_v1_api.create_namespaced_service(namespace='default', body=service_body)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            logger.info(f"Service {service_name} already exists. Updating it.")
            core_v1_api.patch_namespaced_service(name=service_name, namespace='default', body=service_body)
        else:
            raise e

def create_or_update_deployment(app_name, secret_name, config_map_name, resources):
    container = client.V1Container(
        name=f"{app_name}-postgres",
        image='postgres:latest',
        ports=[client.V1ContainerPort(container_port=5432)],
        env=[
            client.V1EnvVar(
                name='POSTGRES_USER',
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name=secret_name,
                        key='username'
                    )
                )
            ),
            client.V1EnvVar(
                name='POSTGRES_PASSWORD',
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name=secret_name,
                        key='password'
                    )
                )
            )
        ],
        volume_mounts=[
            client.V1VolumeMount(
                name='postgres-config-volume',
                mount_path='/etc/postgresql'
            )
        ],
        resources=client.V1ResourceRequirements(
            requests={
                'cpu': resources.get('cpu', '100m'),
                'memory': resources.get('memory', '512Mi')
            },
            limits={
                'cpu': resources.get('cpu', '100m'),
                'memory': resources.get('memory', '512Mi')
            }
        )
    )

    volume = client.V1Volume(
        name='postgres-config-volume',
        config_map=client.V1ConfigMapVolumeSource(
            name=config_map_name
        )
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={'app': app_name}),
        spec=client.V1PodSpec(containers=[container], volumes=[volume])
    )

    spec = client.V1DeploymentSpec(
        replicas=1,
        template=template,
        selector={'matchLabels': {'app': app_name}}
    )

    deployment_body = client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(name=f"{app_name}-deployment"),
        spec=spec
    )

    try:
        apps_v1_api.create_namespaced_deployment(namespace='default', body=deployment_body)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            logger.info(f"Deployment {app_name}-deployment already exists. Updating it.")
            apps_v1_api.patch_namespaced_deployment(name=f"{app_name}-deployment", namespace='default', body=deployment_body)
        else:
            raise e

