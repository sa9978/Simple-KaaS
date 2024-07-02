from kubernetes import client, config

def get_deployment_status_and_pods(app_name, namespace='default'):
    # Load the kubeconfig from default location or in-cluster configuration
    print(config.load_incluster_config()) #if running within a cluster

    # Create an API client for the AppsV1Api and CoreV1Api
    apps_v1_api = client.AppsV1Api()
    core_v1_api = client.CoreV1Api()

    # Get the deployment
    deployment = apps_v1_api.read_namespaced_deployment(name=app_name, namespace=namespace)

    # Extract deployment status
    deployment_status = {
        "DeploymentName": app_name,
        "Replicas": deployment.status.replicas,
        "ReadyReplicas": deployment.status.ready_replicas,
        "PodStatuses": []
    }

    # Get the selector labels from the deployment spec
    selector_labels = deployment.spec.selector.match_labels
    selector = ','.join([f"{key}={value}" for key, value in selector_labels.items()])

    # List the pods using the selector
    pods = core_v1_api.list_namespaced_pod(namespace=namespace, label_selector=selector)

    # Populate pod statuses
    for pod in pods.items:
        pod_status = {
            "Name": pod.metadata.name,
            "Phase": pod.status.phase,
            "HostIP": pod.status.host_ip or "",
            "PodIP": pod.status.pod_ip or "",
            "StartTime": pod.status.start_time.strftime("%Y-%m-%dT%H:%M:%SZ") if pod.status.start_time else ""
        }
        deployment_status["PodStatuses"].append(pod_status)

    return deployment_status