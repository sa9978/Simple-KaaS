from flask import Flask, request, jsonify
from  create_application_service import *
app = Flask(__name__)

# Define a route to create the Kubernetes application
@app.route('/create_application', methods=['POST'])
def create_kubernetes_application():
    print("hello")
    # try:
    #     app_data = request.get_json()
    #     response = create_application(app_data)

    #     if response:
    #         return jsonify({"message": "Deployment created successfully", "data": response.to_dict()}), 201
    #     else:
    #         return jsonify({"message": "Failed to create Deployment"}), 500

    # except Exception as e:
    #     return jsonify({"message": f"Error creating deployment: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
