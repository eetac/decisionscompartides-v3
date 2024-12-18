import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv
from routes.routes import routes_bp
from logger_config import configure_logger 

# os.environ.pop('WEAVIATE_API_KEY', None)
# os.environ.pop('URL_CLUSTER', None)
# os.environ.pop('OPENAI_API_KEY', None)
load_dotenv()

#Versión 0.2.9
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['UPLOAD_FOLDER'] = 'uploads'

configure_logger(app)

app.register_blueprint(routes_bp)

@app.route('/')
def serve_index():
    return send_from_directory('static', 'user.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', debug=True, use_reloader=False)