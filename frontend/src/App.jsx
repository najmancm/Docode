
import { useState } from 'react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [uploadedDocuments, setUploadedDocuments] = useState([])

  const handleUpload = async () => {
    if (!file) {
      setMessage('Please select a document first.')
      setUploadSuccess(false)
      return
    }

    const extension = file.name.split('.').pop().toLowerCase()

    const formData = new FormData()
    formData.append('title', file.name)
    formData.append('original_file', file)
    formData.append('file_type', extension)

    try {
      setLoading(true)
      setMessage('Uploading your document...')
      setUploadSuccess(false)

      const response = await fetch(
        'http://127.0.0.1:8000/api/documents/',
        {
          method: 'POST',
          body: formData,
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(JSON.stringify(data))
      }

      setUploadedDocuments(previous => [data, ...previous])
      setMessage('Your document has been uploaded successfully!')
      setUploadSuccess(true)
      setFile(null)

    } catch (error) {
      setMessage(`Upload failed: ${error.message}`)
      setUploadSuccess(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-layout">

      <aside className="sidebar">
        <div className="logo">
          DO<span>CODE</span>
        </div>

        <p className="sidebar-label">WORKSPACE</p>

        <div className="nav-item active">▣ Dashboard</div>
        <div className="nav-item">▤ My Documents</div>
        <div className="nav-item">⇄ Converter</div>

        <div className="sidebar-bottom">
          <strong>DOCODE</strong>
          <p>Your documents. Transformed into code.</p>
          <small>Document Converter</small>
        </div>
      </aside>

      <main className="main-content">

        <header className="topbar">
          <div className="topbar-title">
            Workspace / Dashboard
          </div>

          <div className="user-avatar">D</div>
        </header>

        <section className="page-heading">
          <h1>Document Converter</h1>
          <p>
            Transform your documents into responsive web pages.
          </p>
        </section>

        <section className="upload-card">
          <h2>Upload your document</h2>

          <p className="upload-description">
            Select a document from your device to get started.
          </p>

          <div className="drop-zone">

            <div className="upload-icon">↑</div>

            <h3>Choose a document to upload</h3>

            <p>
              PDF, PowerPoint or Word documents
            </p>

            <label className="choose-button">
              Browse files

              <input
                className="file-input"
                type="file"
                accept=".pdf,.ppt,.pptx,.doc,.docx"
                onChange={(event) => {
                  setFile(event.target.files[0] || null)
                  setMessage('')
                  setUploadSuccess(false)
                }}
              />
            </label>

            {file && (
              <div className="selected-file">
                Selected: {file.name}
              </div>
            )}

          </div>

          <button
            className="upload-button"
            onClick={handleUpload}
            disabled={loading}
          >
            {loading ? 'Uploading...' : 'Upload Document'}
          </button>

          {message && (
            <p className={`message ${
              uploadSuccess ? 'success-message' : 'error-message'
            }`}>
              {message}
            </p>
          )}

          <div className="supported-formats">
            <span className="format">PDF</span>
            <span className="format">PPT</span>
            <span className="format">PPTX</span>
            <span className="format">DOC</span>
            <span className="format">DOCX</span>
            <span className="format">MAX 20 MB</span>
          </div>
        </section>

        <section className="recent-section">
          <h2>Recent uploads</h2>

          {uploadedDocuments.length === 0 ? (
            <div className="recent-card">
              Your uploaded documents will appear here.
            </div>
          ) : (
            uploadedDocuments.map(document => (
              <div className="recent-card" key={document.id}>
                <strong>{document.title}</strong>
                <p>Type: {document.file_type}</p>
                <p>Status: {document.status}</p>
              </div>
            ))
          )}
        </section>

      </main>
    </div>
  )
}

export default App
