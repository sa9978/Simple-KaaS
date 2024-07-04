from flask import Flask, jsonify
from database_manager import DB

app = Flask(__name__)

@app.route('/health/<string:app_name>', methods=['GET'])
def health_check(app_name):
    db = DB()
    result = db.get_app_info(app_name)
    response = {
        "app_name": app_name,
        "result": result
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5000)
