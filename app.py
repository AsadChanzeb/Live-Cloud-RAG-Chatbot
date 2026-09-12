import os
import shutil
import sys
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from query_data import query_rag_detailed, query_rag_stream, invalidate_db_cache, warm_up, DEFAULT_MODEL
from populate_database import add_single_file_to_chroma, clear_database, load_documents, split_documents, add_to_chroma

app = Flask(__name__, static_folder='.', static_url_path='')

DATA_FOLDER = os.getenv('DATA_FOLDER', 'data')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_UPLOAD_MB = 50  # Reject files larger than 50 MB early

app.config['DATA_FOLDER'] = DATA_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024
os.makedirs(DATA_FOLDER, exist_ok=True)


def init_app():
    """Warm up cache and auto-index any seed documents on startup if DB is empty."""
    warm_up()
    try:
        from query_data import _get_db
        db = _get_db()
        existing = db.get(include=[])
        if len(existing.get("ids", [])) == 0 and os.path.exists(DATA_FOLDER):
            pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith('.pdf')]
            if pdf_files:
                print(f"Startup: indexing {len(pdf_files)} initial documents in '{DATA_FOLDER}'...")
                docs = load_documents()
                chunks = split_documents(docs)
                add_to_chroma(chunks)
                invalidate_db_cache()
                print("Startup: initial documents successfully indexed.")
    except Exception as e:
        print(f"Startup indexing notice: {e}")


init_app()



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/query', methods=['POST'])
def query():
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Query cannot be empty"}), 400

    query_text = data['query'].strip()
    model_name = data.get('model', DEFAULT_MODEL).strip()
    if not query_text:
        return jsonify({"error": "Query cannot be empty"}), 400

    try:
        result = query_rag_detailed(query_text, model_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/query/stream', methods=['GET'])
def query_stream():
    query_text = request.args.get('query', '').strip()
    model_name = request.args.get('model', DEFAULT_MODEL).strip()

    if not query_text:
        return jsonify({"error": "Query cannot be empty"}), 400

    def generate():
        try:
            for chunk in query_rag_stream(query_text, model_name):
                yield chunk
        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Transfer-Encoding': 'chunked',
        }
    )


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file in request"}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['DATA_FOLDER'], filename)
    file.save(file_path)

    try:
        # Index ONLY this new file — not the entire data folder
        chunk_count = add_single_file_to_chroma(file_path)

        # Invalidate the cached DB so the next query sees the new chunks
        invalidate_db_cache()

        return jsonify({
            "success": True,
            "message": f"Uploaded and indexed '{filename}' ({chunk_count} chunks)."
        })
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": f"Indexing failed: {str(e)}"}), 500


@app.route('/api/documents', methods=['GET'])
def get_documents():
    try:
        files = [
            f for f in os.listdir(DATA_FOLDER)
            if os.path.isfile(os.path.join(DATA_FOLDER, f)) and f.lower().endswith('.pdf')
        ] if os.path.exists(DATA_FOLDER) else []
        return jsonify({"documents": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset_database():
    try:
        # Release DB connection FIRST so Windows file locks are freed
        invalidate_db_cache()
        clear_database()

        if os.path.exists(DATA_FOLDER):
            for name in os.listdir(DATA_FOLDER):
                path = os.path.join(DATA_FOLDER, name)
                try:
                    if os.path.isfile(path) or os.path.islink(path):
                        os.unlink(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                except Exception as e:
                    print(f"Could not delete {path}: {e}")

        return jsonify({"success": True, "message": "Database and files reset."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": f"File too large. Maximum size is {MAX_UPLOAD_MB} MB."}), 413


if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

