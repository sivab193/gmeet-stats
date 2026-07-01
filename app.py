import os
import json
import analyzer

try:
    from flask import Flask, request, jsonify, send_from_directory, redirect
    FLASK_AVAILABLE = True
except ImportError:
    class Flask:
        def __init__(self, *args, **kwargs): pass
        def route(self, *args, **kwargs): return lambda f: f
        def run(self, *args, **kwargs): pass
    FLASK_AVAILABLE = False

# ─── Pre-load owner's public stats from bundled CSV ───────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_static_records = None
_uploaded_records = None  # Runtime-uploaded data (in-memory, per-process)

def _get_static_records():
    global _static_records
    if _static_records is None:
        _static_records = analyzer.load_and_clean_data()
    return _static_records

def _get_active_records():
    """Return uploaded data if present, else fall back to static CSV."""
    if _uploaded_records is not None:
        return _uploaded_records
    return _get_static_records()

# ─── Flask App (Top-Level for Vercel Serverless Runtime) ───────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")

if FLASK_AVAILABLE:
    @app.route("/")
    def home():
        return send_from_directory(os.path.join(BASE_DIR, "templates"), "upload.html")

    @app.route("/upload")
    def upload_page():
        return send_from_directory(os.path.join(BASE_DIR, "templates"), "upload.html")

    @app.route("/dashboard")
    def dashboard_page():
        return send_from_directory(os.path.join(BASE_DIR, "templates"), "dashboard.html")

    @app.route("/static/<path:filename>")
    def static_files(filename):
        return send_from_directory(os.path.join(BASE_DIR, "static"), filename)

    @app.route("/api/public-stats")
    def public_stats():
        """Always returns stats from the owner's bundled CSV (no upload needed)."""
        records = _get_static_records()
        data = analyzer.compute_analytics(records=records)
        return jsonify(data)

    @app.route("/api/stats")
    def api_stats():
        year = request.args.get("year", "ALL")
        room = request.args.get("room", "ALL")
        mode = request.args.get("mode", "")
        records = _get_static_records() if mode == "owner" else _get_active_records()
        data = analyzer.compute_analytics(records=records, year_filter=year, room_filter=room)
        return jsonify(data)

    @app.route("/api/meetings")
    def api_meetings():
        global _uploaded_records
        search = request.args.get("search", "").lower().strip()
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        sort_by = request.args.get("sort", "date_desc")
        mode = request.args.get("mode", "")

        records = list(_get_static_records() if mode == "owner" else _get_active_records())

        if search:
            records = [
                r for r in records
                if search in r["meeting_code"].lower()
                or search in r["start_time"].lower()
                or search in r["duration_fmt"].lower()
            ]

        if sort_by == "duration_desc":
            records.sort(key=lambda x: x["duration_sec"], reverse=True)
        elif sort_by == "date_asc":
            records.sort(key=lambda x: x["start_time"])
        else:
            records.sort(key=lambda x: x["start_time"], reverse=True)

        total_records = len(records)
        total_pages = max(1, (total_records + limit - 1) // limit)
        start_idx = (page - 1) * limit
        paginated = records[start_idx:start_idx + limit]

        return jsonify({
            "records": paginated,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": total_pages
            }
        })

    @app.route("/api/upload", methods=["POST"])
    def api_upload():
        global _uploaded_records
        if "records_file" not in request.files:
            return jsonify({"error": "No file provided. Expected field: records_file"}), 400

        file = request.files["records_file"]
        if not file.filename or not file.filename.endswith(".csv"):
            return jsonify({"error": "Invalid file. Please upload a .csv file."}), 400

        tmp_path = os.path.join("/tmp", "_upload_tmp.csv")
        try:
            file.save(tmp_path)
            records = analyzer.load_and_clean_data(filepath=tmp_path)
            if not records:
                return jsonify({"error": "CSV parsed but contained no valid records. Check the file format."}), 400
            _uploaded_records = records
            return jsonify({"success": True, "record_count": len(records)})
        except Exception as e:
            return jsonify({"error": f"Failed to process CSV: {str(e)}"}), 500
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @app.route("/api/has-data")
    def has_data():
        return jsonify({"has_data": True})  # always true; we have bundled CSV

# ─── Fallback: stdlib HTTP server (no Flask) ───────────────────────────────────
else:
    import urllib.parse
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class DashboardHandler(BaseHTTPRequestHandler):
        def send_json(self, data, status=200):
            content = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)

        def send_file(self, filepath):
            if not os.path.exists(filepath):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 Not Found")
                return
            with open(filepath, "rb") as f:
                content = f.read()
            ext = os.path.splitext(filepath)[1].lower()
            content_types = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
            }
            self.send_response(200)
            self.send_header("Content-Type", content_types.get(ext, "text/plain"))
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            global _uploaded_records
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = dict(urllib.parse.parse_qsl(parsed.query))

            if path in ("/", "/upload"):
                self.send_file(os.path.join(BASE_DIR, "templates", "upload.html"))
            elif path == "/dashboard":
                self.send_file(os.path.join(BASE_DIR, "templates", "dashboard.html"))
            elif path.startswith("/static/"):
                self.send_file(os.path.join(BASE_DIR, "static", path[8:]))
            elif path == "/api/public-stats":
                records = _get_static_records()
                self.send_json(analyzer.compute_analytics(records=records))
            elif path == "/api/stats":
                year = query.get("year", "ALL")
                room = query.get("room", "ALL")
                mode = query.get("mode", "")
                records = _get_static_records() if mode == "owner" else _get_active_records()
                self.send_json(analyzer.compute_analytics(records=records, year_filter=year, room_filter=room))
            elif path == "/api/meetings":
                search = query.get("search", "").lower().strip()
                page = int(query.get("page", 1))
                limit = int(query.get("limit", 20))
                mode = query.get("mode", "")
                records = list(_get_static_records() if mode == "owner" else _get_active_records())
                if search:
                    records = [r for r in records if search in r["meeting_code"].lower() or search in r["start_time"].lower()]
                records.sort(key=lambda x: x["start_time"], reverse=True)
                total = len(records)
                start = (page - 1) * limit
                self.send_json({"records": records[start:start+limit], "pagination": {"page": page, "limit": limit, "total_records": total, "total_pages": max(1,(total+limit-1)//limit)}})
            elif path == "/api/has-data":
                self.send_json({"has_data": True})
            else:
                self.send_response(404); self.end_headers(); self.wfile.write(b"Not Found")

        def do_POST(self):
            global _uploaded_records
            if self.path != "/api/upload":
                self.send_response(404); self.end_headers(); return
            content_length = int(self.headers.get("Content-Length", 0))
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self.send_json({"error": "Expected multipart/form-data"}, 400); return
            boundary = content_type.split("boundary=")[-1].encode()
            body = self.rfile.read(content_length)
            # Simple multipart extraction
            csv_data = None
            for part in body.split(b"--" + boundary):
                if b"records_file" in part:
                    sep = part.find(b"\r\n\r\n")
                    if sep != -1:
                        raw = part[sep+4:].rstrip(b"\r\n--")
                        try: csv_data = raw.decode("utf-8")
                        except: csv_data = raw.decode("latin-1")
                        break
            if not csv_data:
                self.send_json({"error": "No CSV file found in upload"}, 400); return
            tmp = os.path.join("/tmp", "_upload_tmp.csv")
            try:
                with open(tmp, "w", encoding="utf-8") as f: f.write(csv_data)
                records = analyzer.load_and_clean_data(filepath=tmp)
                if not records:
                    self.send_json({"error": "CSV had no valid records"}, 400); return
                _uploaded_records = records
                self.send_json({"success": True, "record_count": len(records)})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            finally:
                if os.path.exists(tmp): os.remove(tmp)

        def log_message(self, format, *args): pass

PORT = int(os.environ.get("PORT", 1903))

def run_server():
    if FLASK_AVAILABLE:
        print(f"🚀 Running with Flask at http://127.0.0.1:{PORT}")
        app.run(host="0.0.0.0", port=PORT, debug=False)
    else:
        httpd = HTTPServer(("", PORT), DashboardHandler)
        print(f"🚀 Running with stdlib at http://127.0.0.1:{PORT} (install Flask for Vercel deployment)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping."); httpd.server_close()

if __name__ == "__main__":
    run_server()
