import { useCallback, useEffect, useRef, useState } from "react";
import { listDocuments, uploadDocument } from "../api";
import { useAuth } from "../auth/AuthContext";

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function DocumentsPage() {
  const { token } = useAuth();
  const inputRef = useRef(null);
  const [documents, setDocuments] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState({ type: "", message: "" });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const refreshDocuments = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await listDocuments(token));
    } catch (error) {
      setStatus({ type: "error", message: error.message });
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { refreshDocuments(); }, [refreshDocuments]);

  async function handleUpload(event) {
    event.preventDefault();
    if (!selectedFile) return;
    setUploading(true);
    setStatus({ type: "processing", message: `Processing ${selectedFile.name}...` });
    try {
      await uploadDocument(token, selectedFile);
      setSelectedFile(null);
      if (inputRef.current) inputRef.current.value = "";
      setStatus({ type: "success", message: "Document indexed and ready." });
      await refreshDocuments();
    } catch (error) {
      setStatus({ type: "error", message: error.message });
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="workspace-page">
      <header className="page-header">
        <div><p className="eyebrow">Document library</p><h2>Everything your team has made searchable.</h2></div>
        <span className="count-badge">{documents.length.toString().padStart(2, "0")} files</span>
      </header>

      <section className="upload-panel">
        <div><p className="eyebrow">Add source material</p><h3>Bring a document into the room.</h3><p>PDF files are parsed, chunked, embedded, and indexed before they appear as ready.</p></div>
        <form className="upload-form" onSubmit={handleUpload}>
          <label className="file-picker"><span>{selectedFile ? selectedFile.name : "Choose a PDF"}</span><input ref={inputRef} type="file" accept="application/pdf,.pdf" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} /></label>
          <button className="primary-button" disabled={!selectedFile || uploading}>{uploading ? "Indexing..." : "Upload document"}</button>
        </form>
        {status.message && <p className={`status-message ${status.type}`} role="status">{status.message}</p>}
      </section>

      <section className="documents-section">
        <div className="section-heading"><div><p className="eyebrow">Your sources</p><h3>Indexed documents</h3></div><button className="refresh-button" onClick={refreshDocuments} disabled={loading}>↻ Refresh</button></div>
        <div className="document-table" role="table" aria-label="Uploaded documents">
          <div className="table-row table-header" role="row"><span>Filename</span><span>Status</span><span>Uploaded</span></div>
          {loading ? <div className="empty-state">Loading your document library...</div> : documents.length === 0 ? <div className="empty-state">No documents yet. Upload a PDF to begin.</div> : documents.map((document) => <div className="table-row" role="row" key={document.document_id}><strong>{document.filename}</strong><span className="ready-status"><i /> Ready</span><span>{formatDate(document.timestamp)}</span></div>)}
        </div>
      </section>
    </div>
  );
}
