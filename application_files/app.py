from flask import Flask, request, jsonify
import logging
import time
from  create_application_service import *
from get_deployment_info_service import *
from prometheus_client import Counter, Histogram, Summary, start_http_server,make_wsgi_app
from kubernetes import client, config
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import create_predefined

app = Flask(__name__)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('flask_request_count', 'Total request count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('flask_request_latency_seconds', 'Request latency', ['endpoint'])
REQUEST_LATENCY_SUMMARY = Summary('flask_request_latency_summary_seconds', 'Request latency summary', ['endpoint'])
DATABASE_ERRORS = Counter('database_errors', 'Total database errors')

# Load Kubernetes configuration
try:
    config.load_incluster_config()  # If running within a Kubernetes cluster
except config.config_exception.ConfigException:
    config.load_kube_config()  # Load default kubeconfig if outside cluster

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
        apps_v1_api = client.AppsV1Api()
        deployments = apps_v1_api.list_namespaced_deployment(namespace=namespace)

        all_deployment_statuses = []
        for deployment in deployments.items:
            app_name = deployment.metadata.name
            deployment_status = get_deployment_status_and_pods(namespace=namespace, app_name=app_name)
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

        secret_name = f"{app_name}-secret"
        secret_data = {
            'username': 'saraida',
            'password': 'saraida'
        }
        create_predefined.create_or_update_secret(secret_name, secret_data)

        postgres_config = {
            'shared_buffers': '128MB',
            'max_connections': '100'
        }
        config_map_name = f"{app_name}-postgres-config"
        create_predefined.create_or_update_config_map(config_map_name, postgres_config)

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
                        time.sleep(5)
                    else:
                        raise e
                else:
                    raise e

        create_predefined.create_or_update_deployment(app_name, secret_name, config_map_name, resources)

        return jsonify({"message": f"Deployed predefined app {app_name} successfully"}), 201

    except client.exceptions.ApiException as e:
        logger.error(f"Kubernetes API error: {e}")
        return jsonify({"message": f"Error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    request_latency = time.time() - request.start_time
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.path).observe(request_latency)
    REQUEST_LATENCY_SUMMARY.labels(request.path).observe(request_latency)
    return response

@app.route('/metrics', methods=['GET'])
def metrics():
    from prometheus_client import generate_latest
    return generate_latest()
@app.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

# @app.route('/healthz', methods=['GET'])
# def health_check():
#     return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # start_http_server(8001)  # Start Prometheus metrics exporter
    app.run(debug=True,host='0.0.0.0', port=4040)
