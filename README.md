# TagDocs

A lightweight document tagging system. The admin tags PDFs stored on a network share;
users scan or type a tag to find and view matching documents in the browser.

## Requirements
- Python 3.8+
- Flask

## Setup

### 1. Install dependencies
```
pip install flask
```
Or:
```
pip install -r requirements.txt
```

### 2. Configure

Open `app.py` and change the admin password:
```python
ADMIN_PASSWORD = "your_secure_password"
```

### 3. Run
```
python app.py
```

Then open **http://localhost:5000** in any browser.

To make it accessible to all 30 users on the network, run it on a machine they can all reach:
```
python app.py
```
It already listens on `0.0.0.0:5000`, so users open `http://<server-ip>:5000`.

---

## How it works

### Admin workflow
1. Create a PDF from the Word document, save it to the network share
2. Open http://server-ip:5000 → click **Admin** → enter password
3. Create any tags you need (e.g. `SAFETY`, `ONBOARDING`, `MAINTENANCE-LINE-A`)
4. Click **Add Document**: enter a display name, paste the full network path to the PDF, select tags → Save

### User workflow
1. Open http://server-ip:5000
2. Scan a barcode, type a tag, or click a tag pill
3. See all matching documents → expand to view PDF inline

---

## Data storage
- `tags.json` — created automatically next to `app.py`, stores all tags and document metadata
- PDFs are **not** copied — they stay on the network share, served directly by Flask

## Notes
- The network share path must be accessible from the machine running `app.py`
- On Windows paths use backslashes: `\\server\share\docs\file.pdf`
- On Linux/Mac mount the share first: `/mnt/share/docs/file.pdf`
- To run as a Windows service (so it starts automatically), use NSSM or Task Scheduler
