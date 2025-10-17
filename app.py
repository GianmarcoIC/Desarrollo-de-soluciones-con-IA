import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api
from werkzeug.utils import secure_filename
import logging

load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Límite de 16MB

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    """Renderiza la página principal"""
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    """Sube una imagen a Cloudinary"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No se encontró el archivo"}), 400
        
        file = request.files["file"]
        
        if file.filename == '':
            return jsonify({"error": "Nombre de archivo vacío"}), 400
        
        # Validar extensión del archivo
        if not allowed_file(file.filename):
            return jsonify({"error": "Tipo de archivo no permitido"}), 400
        
        # Subir a Cloudinary con opciones adicionales
        result = cloudinary.uploader.upload(
            file,
            folder="capturas",
            resource_type="auto",
            transformation=[
                {'quality': 'auto:good'},
                {'fetch_format': 'auto'}
            ]
        )
        
        logger.info(f"Imagen subida exitosamente: {result['public_id']}")
        
        return jsonify({
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "created_at": result["created_at"]
        })
    
    except Exception as e:
        logger.error(f"Error al subir imagen: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/list", methods=["GET"])
def list_images():
    """Lista todas las imágenes de la carpeta capturas"""
    try:
        resources = cloudinary.api.resources(
            type="upload",
            prefix="capturas",
            max_results=100,
            context=True
        )
        
        images = [{
            "url": res["secure_url"],
            "public_id": res["public_id"],
            "created_at": res.get("created_at", ""),
            "format": res.get("format", "")
        } for res in resources["resources"]]
        
        return jsonify({
            "success": True,
            "images": images,
            "total": len(images)
        })
    
    except Exception as e:
        logger.error(f"Error al listar imágenes: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/delete/<path:public_id>", methods=["DELETE"])
def delete_image(public_id):
    """Elimina una imagen de Cloudinary"""
    try:
        result = cloudinary.uploader.destroy(public_id)
        
        if result.get("result") == "ok":
            logger.info(f"Imagen eliminada: {public_id}")
            return jsonify({"success": True, "message": "Imagen eliminada"})
        else:
            return jsonify({"error": "No se pudo eliminar la imagen"}), 400
    
    except Exception as e:
        logger.error(f"Error al eliminar imagen: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Maneja errores de archivos muy grandes"""
    return jsonify({"error": "El archivo es demasiado grande. Máximo 16MB"}), 413

@app.errorhandler(404)
def not_found(error):
    """Maneja errores 404"""
    return jsonify({"error": "Ruta no encontrada"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Maneja errores internos del servidor"""
    logger.error(f"Error interno: {str(error)}")
    return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
