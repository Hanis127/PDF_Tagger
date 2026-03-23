"""
DMC Doc Tagger - Flask backend
Run with: python app.py
Then open: http://localhost:5000
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, abort

app = Flask(__name__)

# ── CONFIG ──────────────────────────────────────────────────────────────────
ADMIN_PASSWORD = ""               # Change this!
DATA_FILE = Path("tags.json")             # Stored next to app.py
SHARE_ROOT = r"\\fsczmc01\TEST_DOC_SCAN"  # Root of the file browser
# ────────────────────────────────────────────────────────────────────────────


def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tags": [], "docs": []}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── PAGES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API: AUTH ────────────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    pw = request.json.get("password", "")
    if pw == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Incorrect password"}), 401


# ── API: TAGS ─────────────────────────────────────────────────────────────────

@app.route("/api/tags", methods=["GET"])
def get_tags():
    data = load_data()
    return jsonify(data["tags"])


@app.route("/api/tags", methods=["POST"])
def create_tag():
    name = request.json.get("name", "").strip().upper()
    if not name:
        return jsonify({"error": "Name required"}), 400
    data = load_data()
    if name in data["tags"]:
        return jsonify({"error": "Tag already exists"}), 409
    data["tags"].append(name)
    save_data(data)
    return jsonify({"ok": True, "tag": name})


@app.route("/api/tags/<name>", methods=["DELETE"])
def delete_tag(name):
    data = load_data()
    name = name.upper()
    data["tags"] = [t for t in data["tags"] if t != name]
    for doc in data["docs"]:
        doc["tags"] = [t for t in doc["tags"] if t != name]
    save_data(data)
    return jsonify({"ok": True})


# ── API: DOCS ─────────────────────────────────────────────────────────────────

@app.route("/api/docs", methods=["GET"])
def get_docs():
    data = load_data()
    # Return docs without file data (just metadata)
    return jsonify([dict({k: v for k, v in d.items() if k != "path"}, has_file=bool(d.get("path"))) for d in data["docs"]])


@app.route("/api/docs", methods=["POST"])
def create_doc():
    payload = request.json
    name = payload.get("name", "").strip()
    path = payload.get("path", "").strip()
    tags = payload.get("tags", [])

    if not name:
        return jsonify({"error": "Name required"}), 400
    if not path:
        return jsonify({"error": "File path required"}), 400

    # Validate the path exists
    if not Path(path).exists():
        return jsonify({"error": f"File not found: {path}"}), 400
    if not path.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    data = load_data()
    doc_id = f"doc_{len(data['docs'])}_{Path(path).stem}"[:40]
    # Make sure id is unique
    existing_ids = {d["id"] for d in data["docs"]}
    if doc_id in existing_ids:
        doc_id = doc_id + "_2"

    doc = {
        "id": doc_id,
        "name": name,
        "path": path,
        "tags": [t.upper() for t in tags],
        "filename": Path(path).name,
    }
    data["docs"].append(doc)
    save_data(data)
    return jsonify({"ok": True, "id": doc_id})


@app.route("/api/docs/<doc_id>", methods=["PUT"])
def update_doc(doc_id):
    payload = request.json
    data = load_data()
    doc = next((d for d in data["docs"] if d["id"] == doc_id), None)
    if not doc:
        return jsonify({"error": "Not found"}), 404

    if "name" in payload:
        doc["name"] = payload["name"].strip()
    if "path" in payload and payload["path"]:
        p = payload["path"].strip()
        if not Path(p).exists():
            return jsonify({"error": f"File not found: {p}"}), 400
        doc["path"] = p
        doc["filename"] = Path(p).name
    if "tags" in payload:
        doc["tags"] = [t.upper() for t in payload["tags"]]

    save_data(data)
    return jsonify({"ok": True})


@app.route("/api/docs/<doc_id>", methods=["DELETE"])
def delete_doc(doc_id):
    data = load_data()
    data["docs"] = [d for d in data["docs"] if d["id"] != doc_id]
    save_data(data)
    return jsonify({"ok": True})


# ── PDF SERVING ───────────────────────────────────────────────────────────────

@app.route("/pdf/<doc_id>")
def serve_pdf(doc_id):
    data = load_data()
    doc = next((d for d in data["docs"] if d["id"] == doc_id), None)
    if not doc:
        abort(404)
    path = Path(doc["path"])
    if not path.exists():
        abort(404)
    return send_file(path, mimetype="application/pdf")


# ── FILE BROWSER ─────────────────────────────────────────────────────────────

@app.route("/api/browse")
def browse():
    """
    List directories and PDF files within SHARE_ROOT.
    ?path=   sub-path relative to SHARE_ROOT (empty = SHARE_ROOT itself)
    ?search= filter filenames (searches recursively across entire share)
    Returns: { path, parent, entries: [{name, path, type}] }
    """
    root = Path(SHARE_ROOT)
    search = request.args.get("search", "").strip().lower()

    # ── SEARCH MODE: recursive scan of entire share ──
    if search:
        results = []
        try:
            for item in root.rglob("*.pdf"):
                if search in item.name.lower():
                    results.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "pdf",
                        "rel": str(item.relative_to(root)),
                    })
            results.sort(key=lambda x: x["name"].lower())
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        return jsonify({"path": str(root), "parent": None, "search": search, "entries": results})

    # ── BROWSE MODE: navigate subdirectory ──
    req_path = request.args.get("path", "").strip()

    if req_path:
        p = Path(req_path)
        # Security: ensure path stays inside SHARE_ROOT
        try:
            p.relative_to(root)
        except ValueError:
            return jsonify({"error": "Access denied"}), 403
    else:
        p = root

    if not p.exists() or not p.is_dir():
        return jsonify({"error": "Not a directory"}), 400

    entries = []
    try:
        items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        for item in items:
            try:
                if item.is_dir() and not item.name.startswith("."):
                    entries.append({"name": item.name, "path": str(item), "type": "dir"})
                elif item.is_file() and item.suffix.lower() == ".pdf":
                    entries.append({"name": item.name, "path": str(item), "type": "pdf"})
            except PermissionError:
                pass
    except PermissionError:
        return jsonify({"error": "Permission denied"}), 403

    # Parent: don't go above SHARE_ROOT
    if str(p) == str(root):
        parent = None
    else:
        parent = str(p.parent)

    return jsonify({"path": str(p), "parent": parent, "entries": entries})


# ── SEARCH ────────────────────────────────────────────────────────────────────

@app.route("/api/search")
def search():
    tag = request.args.get("tag", "").strip().upper()
    if not tag:
        return jsonify([])
    data = load_data()
    results = [
        {k: v for k, v in d.items() if k != "path"}
        for d in data["docs"]
        if tag in [t.upper() for t in d.get("tags", [])]
    ]
    return jsonify(results)


if __name__ == "__main__":
    print("=" * 50)
    print("  DMC Doc Tagger is running!")
    print("  Open: http://localhost:5001")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5001)
