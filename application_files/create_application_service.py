from kubernetes import client, config
from kubernetes.client.rest import ApiException
import datetime
import base64
import random
import string

config.load_kube_config()
print(config.list_kube_config_contexts())

# Kubernetes API clients
apps_v1_api = client.AppsV1Api()
core_v1_api = client.CoreV1Api()
networking_v1_api = client.NetworkingV1Api()

def create_application(app_data):
    try:
        app_name = app_data["AppName"]
        replicas = app_data.get("Replicas", 1)
        image_address = app_data["ImageAddress"]
        image_tag = app_data.get("ImageTag", "latest")
        cpu_request = app_data["Resources"]["CPU"]
        ram_request = app_data["Resources"]["RAM"]
        envs = app_data.get("Envs", [])

        print(f"Creating application '{app_name}'...")
        
        # Handle secrets
        secrets = []
        for env in envs:
            if env.get("IsSecret", False):
                secret_name = f"{app_name.lower()}-secret-{generate_random_name()}"
                secret_data = {env["Key"]: base64.b64encode(env["Value"].encode()).decode()}  # Encode the secret data
                secret = client.V1Secret(
                    api_version="v1",
                    kind="Secret",
                    metadata=client.V1ObjectMeta(name=secret_name),
                    data=secret_data
                )
                secrets.append(secret)
                # Create the secret
                try:
                    core_v1_api.create_namespaced_secret(namespace="default", body=secret)
                    print(f"Secret '{secret_name}' created.")
                except ApiException as e:
                    if e.status == 409:
                        print(f"Secret '{secret_name}' already exists.")
                    else:
                        raise

        # Generate a unique deployment name
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        deployment_name = f"{app_name.lower()}-deployment-{timestamp}"

        print(f"Creating deployment '{deployment_name}'...")
        
        # Define container specification
        container = client.V1Container(
            name=app_name.lower(),
            image=f"{image_address}:{image_tag}",
            resources=client.V1ResourceRequirements(
                requests={"cpu": cpu_request, "memory": ram_request}
            ),
            env=[client.V1EnvVar(name=env["Key"], value_from=client.V1EnvVarSource(secret_key_ref=client.V1SecretKeySelector(name=secret.metadata.name, key=env["Key"]))) if env.get("IsSecret", False) else client.V1EnvVar(name=env["Key"], value=env["Value"]) for env in envs]
        )

        # Define deployment metadata
        metadata = client.V1ObjectMeta(name=deployment_name)

        # Define pod template specification
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": app_name}),
            spec=client.V1PodSpec(containers=[container]),
        )

        # Define deployment specification
        spec = client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(match_labels={"app": app_name}),
            template=template
        )

        # Define deployment object
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=metadata,
            spec=spec
        )

        # Create the deployment using Kubernetes API
        deployment_response = apps_v1_api.create_namespaced_deployment(
            body=deployment,
            namespace="default"
        )

        print(f"Deployment '{deployment_name}' created successfully.")
        
        # Create the service
        print(f"Creating service for '{app_name}'...")
        create_service(app_data)

        # Generate a unique Ingress name
        ingress_name = f"{app_name.lower()}-ingress-{generate_random_name()}"

        # Optionally, create an Ingress object
        if app_data.get("DomainAddress") and app_data.get("ServicePort"):
            ingress_body = {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "Ingress",
                "metadata": {"name": ingress_name},
                "spec": {
                    "rules": [{
                        "host": app_data["DomainAddress"],
                        "http": {
                            "paths": [{
                                "path": "/",
                                "pathType": "ImplementationSpecific",  # Specify a valid pathType
                                "backend": {
                                    "service": {
                                        "name": app_name.lower(),
                                        "port": {
                                            "number": app_data["ServicePort"]
                                        }
                                    }
                                }
                            }]
                        }
                    }]
                }
            }
            try:
                networking_v1_api.create_namespaced_ingress(namespace="default", body=ingress_body)
                print(f"Ingress '{ingress_name}' created.")
            except ApiException as e:
                if e.status == 409:
                    print(f"Ingress '{ingress_name}' already exists.")
                else:
                    raise

        return deployment_response

    except ApiException as e:
        print(f"Exception when creating Deployment: {e}")
        return None

def create_service(app_data):
    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=app_data['AppName'].lower()),
        spec=client.V1ServiceSpec(
            selector={"app": app_data['AppName']},
            ports=[client.V1ServicePort(port=80, target_port=app_data['ServicePort'])]
        )
    )

    try:
        api_response = core_v1_api.create_namespaced_service(
            namespace="default",
            body=service
        )
        print(f"Service '{app_data['AppName'].lower()}' created. Status: '{api_response.status}'")
    except ApiException as e:
        print(f"Exception when creating service: {e}")

def generate_random_name(length=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
