from kubernetes import client, config
import requests
from database_manager import DB
def list_pods(namespace='default'):
    # Load kube config
    config.load_incluster_config()
    
    # Create a v1 client
    v1 = client.CoreV1Api()
    db = DB()
    # List pods in the specified namespace
    print(f"Listing pods in namespace '{namespace}' with their IPs:")
    ret = v1.list_namespaced_pod(namespace)
    for i in ret.items:
        # print(i.metadata.labels.keys())
        if "monitor" in i.metadata.labels.keys():
            if i.metadata.labels["monitor"] == "true":
                print(f"{i.status.pod_ip}\t{i.metadata.namespace}\t{i.metadata.name}")
                pod_ip = i.status.pod_ip
                port = i.spec.containers[0].ports[0].container_port
                url = f"http://{pod_ip}:{port}/healthz"
                try:
                    response = requests.get(url)
                    db.new_update(i.metadata.name,True)
                    print(f"GET {url} response from pod {i.metadata.name}: {response.status_code} - {response.text}")

                except requests.exceptions.RequestException as e:
                    db.new_update(i.metadata.name,False)
                    print(f"Failed to GET {url} from pod {i.metadata.name}: {str(e)}")
        
    print(f"current state: \n {db.current_state()}")
    
if __name__ == "__main__":
    list_pods()
