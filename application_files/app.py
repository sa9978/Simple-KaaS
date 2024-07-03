from flask import Flask, request, jsonify
from  create_application_service import *
from get_deployment_info_service import *


app = Flask(__name__)

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


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=4040)
