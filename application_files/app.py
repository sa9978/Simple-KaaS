from flask import Flask, request, jsonify
import logging
import time
from  create_application_service import *
from get_deployment_info_service import *
import create_predefined


app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a route to create the Kubernetes application
@app.route('/create_application', methods=['POST'])
def create_kubernetes_application():
    try:
        app_data = request.get_json()
        response = create_application(app_data)

        if response:
            return jsonify({"message": "Deployment created successfully", "data": response.to_dict()}), 201
        else:
            return jsonify({"message": "Failed to create Deployment"}), 500

    except Exception as e:
        return jsonify({"message": f"Error creating deployment: {str(e)}"}), 500
    

@app.route('/deployment_status', methods=['GET'])
def deployment_status():
    app_name = request.args.get('app_name')
    namespace = request.args.get('namespace', 'default')

    if not app_name:
        return jsonify({"error": "Missing 'app_name' parameter"}), 400

    try:
        result = get_deployment_status_and_pods(app_name, namespace)
        return jsonify(result)
    except client.exceptions.ApiException as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/all_applications', methods=['GET'])
def all_applications():
    namespace = request.args.get('namespace', 'default')

    try:
        # Load the kubeconfig from default location or in-cluster configuration
        config.load_incluster_config() #if running within a cluster

        # Create an API client for the AppsV1Api
        apps_v1_api = client.AppsV1Api()

        # List all deployments in the given namespace
        deployments = apps_v1_api.list_namespaced_deployment(namespace=namespace)

        # Collect status information for each deployment
        all_deployment_statuses = []
        for deployment in deployments.items:
            app_name = deployment.metadata.name

            deployment_status = get_deployment_status_and_pods(namespace=namespace,app_name=app_name)
            all_deployment_statuses.append(deployment_status)

        return jsonify(all_deployment_statuses)
    except client.exceptions.ApiException as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/deploy-predefined-app', methods=['POST'])
def deploy_predefined_application():
    try:
        app_data = request.json
        app_name = app_data.get('AppName')
        resources = app_data.get('Resources', {})
        external = app_data.get('External', False)

        # Create or update Secrets for user information
        secret_name = f"{app_name}-secret"
        secret_data = {
            'username': 'saraida', 
            'password': 'saraida'
        }
        create_predefined.create_or_update_secret(secret_name, secret_data)

        # Create or update ConfigMap for PostgreSQL configuration
        postgres_config = {
            'shared_buffers': '128MB',
            'max_connections': '100'
        }
        config_map_name = f"{app_name}-postgres-config"
        create_predefined.create_or_update_config_map(config_map_name, postgres_config)

        # Depending on external flag, configure Kubernetes Service
        service_type = 'LoadBalancer' if external else 'ClusterIP'
        service_name = f"{app_name}-service"
        
        retry_attempts = 5
        for attempt in range(retry_attempts):
            try:
                create_predefined.create_or_update_service(service_name, service_type, app_name)
                break
            except client.exceptions.ApiException as e:
                if e.status == 500:
                    if attempt < retry_attempts - 1:
                        logger.warning(f"Service creation failed (attempt {attempt+1}/{retry_attempts}): {e}")
                        time.sleep(5)  # Wait before retrying
                    else:
                        raise e
                else:
                    raise e

        # Create or update Deployment for PostgreSQL Pod
        create_predefined.create_or_update_deployment(app_name, secret_name, config_map_name, resources)

        return jsonify({"message": f"Deployed predefined app {app_name} successfully"}), 201

    except client.exceptions.ApiException as e:
        logger.error(f"Kubernetes API error: {e}")
        return jsonify({"message": f"Error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True,port=4040)
