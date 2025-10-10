from flask import Flask, request, jsonify
import subprocess
import os
from controller.collector_kafka import get_jwt_token

app = Flask(__name__)

# Almacenará la configuración actual
current_config = {
    'script': None,
    'params': None
}

# Directorio base para los scripts
SCRIPT_BASE_DIR = "/home/tid/PoT"

@app.route('/run-service', methods=['POST'])
def run_command():
    global current_config
    data = request.get_json()
    deploy = data.get('deploy')
    
    if not deploy or not isinstance(deploy, str):
        return jsonify({'status': 'error', 'message': 'Deploy must be provided and must be a string'}), 400

    # Diferenciar según el 'deploy' solicitado
    if deploy == "PoT_Service":
        number1 = data.get('NodePoT')
        number2 = data.get('NodeNoPoT')
        option = data.get('option')
        
        if not isinstance(number1, int) or not (1 <= number1 <= 10):
            return jsonify({'status': 'error', 'message': 'NodePoT must be an integer between 1 and 10'}), 400
        if not isinstance(number2, int) or not (0 <= number2 <= 10):
            return jsonify({'status': 'error', 'message': 'NodeNoPoT must be an integer between 0 and 10'}), 400
        if not option or not isinstance(option, str):
            return jsonify({'status': 'error', 'message': 'Option must be provided and must be a string'}), 400
        
        script = "scenario-generator_nodes.sh"
        args = [str(number1), str(number2), option]
    
    else:
        # Caso por defecto para otros servicios
        number = data.get('number')
        option = data.get('option')

        if not isinstance(number, int) or not (0 <= number <= 10):
            return jsonify({'status': 'error', 'message': 'Number must be an integer between 0 and 10'}), 400
        if not option or not isinstance(option, str):
            return jsonify({'status': 'error', 'message': 'Option must be provided and must be a string'}), 400

        script = "scenario-generator.sh"
        args = [str(number), option]

    # Construcción del path y comando
    full_script_path = os.path.join(SCRIPT_BASE_DIR, script)
    current_config = {
        'script': full_script_path,
        'params': args
    }
    command = " ".join([full_script_path] + args)

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        jwt_token = get_jwt_token()
        return jsonify({
            'STATUS': 'Success',
            'SSSS OUTPUT': result.stdout,
            'JWT_TOKEN': jwt_token
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete-service', methods=['DELETE'])
def delete_script():
    data = request.get_json()
    deploy = data.get('deploy')

    if not deploy or not isinstance(deploy, str):
        return jsonify({'status': 'error', 'message': 'Deploy must be provided and must be a string'}), 400

    try:
        destroy_script = os.path.join(SCRIPT_BASE_DIR, 'destroy.sh')
        command = f"{destroy_script}"

        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return jsonify({
            'STATUS': 'Success',
            'DELETE STATUS': 'Service with UUID 57310caf-bcc4-4008-82b8-6cfa6263bbc DELETED'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get-config', methods=['GET'])
def get_config():
    return jsonify(current_config)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
