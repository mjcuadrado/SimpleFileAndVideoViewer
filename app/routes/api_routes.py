# Rutas de API
from flask import jsonify, request

def register_api_routes(app):
    @app.route('/api/stats', methods=['GET'])
    def api_stats():
        try:
            referrer = request.referrer if request.referrer else "No referrer provided"
            app.logger.info(f"Solicitud recibida en /api/stats desde: {referrer}")
            return jsonify({"error": "Endpoint no implementado aún"}), 200
        except Exception as e:
            app.logger.error(f"Error en api_stats: {str(e)}", exc_info=True)
            return jsonify({"error": "Error interno del servidor"}), 500

    @app.route('/api/version', methods=['GET'])
    def api_version():
        try:
            referrer = request.referrer if request.referrer else "No referrer provided"
            app.logger.info(f"Solicitud recibida en /api/version desde: {referrer}")
            return jsonify({"error": "Endpoint no implementado aún"}), 200
        except Exception as e:
            app.logger.error(f"Error en api_version: {str(e)}", exc_info=True)
            return jsonify({"error": "Error interno del servidor"}), 500