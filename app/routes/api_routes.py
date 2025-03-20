# Rutas de API
from flask import jsonify, request

def register_api_routes(app):
    @app.route('/api/stats', methods=['GET'])
    def api_stats():
        referrer = request.referrer if request.referrer else "No referrer provided"
        app.logger.info(f"Solicitud recibida en /api/stats desde: {referrer}")
        return jsonify({"error": "Endpoint no implementado aún"}), 200

    @app.route('/api/version', methods=['GET'])
    def api_version():
        referrer = request.referrer if request.referrer else "No referrer provided"
        app.logger.info(f"Solicitud recibida en /api/version desde: {referrer}")
        return jsonify({"error": "Endpoint no implementado aún"}), 200