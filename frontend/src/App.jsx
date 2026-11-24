import { useEffect, useState } from 'react'
import telesomLogo from './assets/branding/telesom-academy-logo.png'
import './App.css'
import TelesomApp from './TelesomApp.jsx'

const API = 'http://127.0.0.1:8000'

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[2]) : ''
}

async function api(path, options = {}) {
  const csrf = getCookie('csrftoken')
  const headers = { ...(options.headers || {}) }
  if (options.method && options.method !== 'GET') headers['X-CSRFToken'] = csrf

  const response = await fetch(API + path, {
    ...options,
    headers,
    credentials: 'include',
  })

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : null
  if (!response.ok) throw new Error(data?.error || data?.detail || 'Request failed')
  return data
}

function BrandIdentity() {
  return (
    <div className="brand official-brand">
      <img src={telesomLogo} alt="Telesom Academy" />
    </div>
  )
}

function Icon({ name }) {
  const icons = {
    dashboard: '▦', documents: '▤', convert: '＋', history: '↻', settings: '⚙',
    logout: '⇥', upload: '↑', download: '↓', eye: '◉', desktop: '▭', mobile: '▯',
  }
  return <span className="nav-icon" aria-hidden="true">{icons[name] || '•'}</span>
}

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(API + '/api/auth/csrf/', { credentials: 'include' }).catch(() => {})
  }, [])

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api('/api/auth/csrf/', { method: 'GET' })
      const result = await api('/api/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      onLogin(result.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <BrandIdentity />
        <div className="login-heading">
          <p className="eyebrow">ADMINISTRATOR PORTAL</p>
          <h1>Welcome back</h1>
          <p>Sign in to manage document conversions.</p>
        </div>
        <form onSubmit={submit}>
          <label>Username
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required />
          </label>
          <label>Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
          </label>
          {error && <div className="alert error">{error}</div>}
          <button className="primary-button login-button" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}

function StatusBadge({ status }) {
  const labels = { uploaded: 'Uploaded', processing: 'Processing', completed: 'Completed', failed: 'Failed', deleted: 'Deleted' }
  return <span className={`status ${status || 'uploaded'}`}><i />{labels[status] || status}</span>
}

function DocumentTable({ documents, openDocument }) {
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Document</th><th>Type</th><th>Status</th><th>Uploaded</th><th></th></tr></thead>
        <tbody>
          {documents.map((document) => (
            <tr key={document.id}>
              <td><div className="document-name"><span className="file-badge">{(document.file_type || 'doc').toUpperCase()}</span><strong>{document.title}</strong></div></td>
              <td>{(document.file_type || 'doc').toUpperCase()}</td>
              <td><StatusBadge status={document.status} /></td>
              <td>{document.uploaded_at ? new Date(document.uploaded_at).toLocaleDateString() : '—'}</td>
              <td><button className="table-action" onClick={() => openDocument(document)}>Open</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Dashboard({ documents, openDocument }) {
  const counts = documents.reduce((result, document) => {
    result[document.status] = (result[document.status] || 0) + 1
    return result
  }, {})

  const cards = [
    ['Total documents', documents.length, 'documents'],
    ['Completed', counts.completed || 0, 'completed'],
    ['Processing', counts.processing || 0, 'processing'],
    ['Failed', counts.failed || 0, 'failed'],
  ]

  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">OVERVIEW</p><h1>Dashboard</h1></div></div>
      <div className="stat-grid">
        {cards.map(([label, value, tone]) => (
          <div className="stat-card" key={label}><div className={`stat-icon ${tone}`}>▦</div><div><strong>{value}</strong><span>{label}</span></div></div>
        ))}
      </div>
      <section className="panel">
        <div className="panel-header"><div><p className="eyebrow">RECENT ACTIVITY</p><h2>Recent documents</h2></div></div>
        {documents.length === 0 ? (
          <div className="empty-state"><div className="empty-icon">▤</div><h3>No documents yet</h3><p>Upload a PDF, PowerPoint or Word document to begin.</p></div>
        ) : <DocumentTable documents={documents.slice(0, 6)} openDocument={openDocument} />}
      </section>
    </>
  )
}

function Converter({ openDocument, refreshDocuments }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [converting, setConverting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const upload = async () => {
    if (!file) return
    setError('')
    setMessage('')
    setUploading(true)
    setProgress(10)

    const form = new FormData()
    form.append('title', file.name)
    form.append('original_file', file)
    form.append('file_type', file.name.split('.').pop().toLowerCase())

    try {
      const response = await fetch(API + '/api/documents/', {
        method: 'POST', body: form, credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      })
      const document = await response.json()
      if (!response.ok) throw new Error(document.original_file?.[0] || document.detail || 'Upload failed')

      setProgress(35)
      setUploading(false)
      setConverting(true)
      setMessage('Extracting document content...')

      const result = await api(`/api/extractor/${document.id}/extract/`, { method: 'POST' })
      setProgress(result.progress || 100)
      setMessage('Conversion completed')
      await refreshDocuments()
      openDocument({ ...document, status: 'completed', generated_html: 'available' })
    } catch (err) {
      setError(err.message)
      setMessage('')
    } finally {
      setUploading(false)
      setConverting(false)
      setFile(null)
    }
  }

  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">CONVERSION WORKSPACE</p><h1>Convert document</h1></div></div>
      <section className="converter-grid">
        <div className="panel upload-panel">
          <div className="panel-header"><div><p className="eyebrow">SOURCE DOCUMENT</p><h2>Upload file</h2></div></div>
          <label className={`drop-zone ${file ? 'has-file' : ''}`}>
            <input type="file" accept=".pdf,.ppt,.pptx,.doc,.docx" onChange={(event) => setFile(event.target.files[0] || null)} />
            <div className="upload-mark"><Icon name="upload" /></div>
            <h3>{file ? file.name : 'Drag and drop or browse'}</h3>
            <p>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'PDF, PPT, PPTX, DOC or DOCX • Maximum 20 MB'}</p>
            {!file && <span className="secondary-button">Browse files</span>}
          </label>
          <div className="format-list"><span>PDF</span><span>PPT</span><span>PPTX</span><span>DOC</span><span>DOCX</span></div>
          <button className="primary-button full" onClick={upload} disabled={!file || uploading || converting}>{uploading ? 'Uploading...' : converting ? 'Converting...' : 'Upload and convert'}</button>
          {error && <div className="alert error">{error}</div>}
        </div>
        <div className="panel progress-panel">
          <div className="panel-header"><div><p className="eyebrow">CONVERSION STATUS</p><h2>Progress</h2></div></div>
          <div className="progress-ring" style={{ '--progress': `${progress * 3.6}deg` }}><div><strong>{progress}%</strong><span>Progress</span></div></div>
          <div className="progress-steps"><div className={progress >= 10 ? 'done' : ''}><i>1</i><span>Upload</span></div><div className={progress >= 35 ? 'done' : ''}><i>2</i><span>Extract</span></div><div className={progress >= 100 ? 'done' : ''}><i>3</i><span>Generate HTML</span></div></div>
          {message && <div className="alert success">{message}</div>}
        </div>
      </section>
    </>
  )
}

function DocumentLibrary({ documents, openDocument, refreshDocuments }) {
  const [search, setSearch] = useState('')
  const filtered = documents.filter((document) => document.title.toLowerCase().includes(search.toLowerCase()))

  const removeDocument = async (document) => {
    if (!window.confirm(`Move "${document.title}" to deleted items?`)) return
    await api(`/api/documents/${document.id}/`, { method: 'DELETE' })
    await refreshDocuments()
  }

  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">DOCUMENT CENTER</p><h1>My Documents</h1></div></div>
      <section className="panel">
        <div className="panel-header library-header"><div><p className="eyebrow">ALL DOCUMENTS</p><h2>Saved library</h2></div><input className="search-input" placeholder="Search documents" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
        {filtered.length === 0 ? <div className="empty-state"><div className="empty-icon">▤</div><h3>No matching documents</h3></div> : (
          <div className="library-list">{filtered.map((document) => (
            <article className="library-row" key={document.id}>
              <span className="file-badge large">{(document.file_type || 'doc').toUpperCase()}</span>
              <div className="library-info"><strong>{document.title}</strong><span>{new Date(document.uploaded_at).toLocaleString()}</span></div>
              <StatusBadge status={document.status} />
              <div className="row-actions"><button className="secondary-button" onClick={() => openDocument(document)}>Open</button><button className="danger-button" onClick={() => removeDocument(document)}>Delete</button></div>
            </article>
          ))}</div>
        )}
      </section>
    </>
  )
}

function PreviewWorkspace({ document, closePreview }) {
  const [device, setDevice] = useState('desktop')
  const [downloadError, setDownloadError] = useState('')

  const download = async () => {
    setDownloadError('')
    try {
      const response = await fetch(API + `/api/extractor/${document.id}/download/`, { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') } })
      if (!response.ok) throw new Error('Could not download the generated HTML')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = `${document.title.replace(/\.[^.]+$/, '')}.html`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      setDownloadError(error.message)
    }
  }

  return (
    <div className="preview-page">
      <div className="preview-toolbar">
        <button className="back-button" onClick={closePreview}>← Back</button>
        <div><p className="eyebrow">HTML PREVIEW</p><h1>{document.title}</h1></div>
        <div className="preview-actions"><div className="device-toggle"><button className={device === 'desktop' ? 'active' : ''} onClick={() => setDevice('desktop')}><Icon name="desktop" /> Desktop</button><button className={device === 'mobile' ? 'active' : ''} onClick={() => setDevice('mobile')}><Icon name="mobile" /> Mobile</button></div><button className="primary-button" onClick={download}><Icon name="download" /> Download HTML</button></div>
      </div>
      {downloadError && <div className="alert error preview-alert">{downloadError}</div>}
      <div className="preview-stage">
        {document.status === 'completed' && document.generated_html ? (
          <iframe className={`lesson-preview ${device}`} src={`${API}/api/extractor/${document.id}/preview/`} sandbox="allow-same-origin" title="Generated HTML preview" />
        ) : <div className="empty-state"><h3>HTML preview unavailable</h3><p>Convert the document before opening its preview.</p></div>}
      </div>
    </div>
  )
}

function Settings() {
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">SYSTEM</p><h1>Settings</h1></div></div>
      <section className="panel settings-panel"><div className="panel-header"><div><p className="eyebrow">APPLICATION</p><h2>TELESOM ACADEMY</h2></div></div><div className="settings-grid"><div><span>Supported formats</span><strong>PDF, PPT, PPTX, DOC, DOCX</strong></div><div><span>Maximum upload size</span><strong>20 MB</strong></div><div><span>Database mode</span><strong>SQLite currently, MySQL ready</strong></div></div></section>
    </>
  )
}

function App() {
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [activePage, setActivePage] = useState('dashboard')
  const [documents, setDocuments] = useState([])
  const [previewDocument, setPreviewDocument] = useState(null)

  const refreshDocuments = async () => {
    try {
      const data = await api('/api/documents/')
      setDocuments(data.results || data)
    } catch {
      setDocuments([])
    }
  }

  useEffect(() => {
    api('/api/auth/me/').then((data) => { setUser(data.user); refreshDocuments() }).catch(() => setUser(null)).finally(() => setAuthChecked(true))
  }, [])

  const logout = async () => {
    try { await api('/api/auth/logout/', { method: 'POST' }) } finally { setUser(null); setPreviewDocument(null) }
  }

  if (!authChecked) return <div className="loading-screen"><BrandIdentity /><span>Loading workspace...</span></div>
  if (!user) return <Login onLogin={(account) => { setUser(account); refreshDocuments() }} />

  const openDocument = async (document) => {
    try {
      const detail = await api(`/api/documents/${document.id}/`)
      setPreviewDocument(detail)
    } catch {
      setPreviewDocument(document)
    }
  }

  const navItems = [
    ['dashboard', 'Dashboard', 'dashboard'],
    ['converter', 'Convert Document', 'convert'],
    ['documents', 'My Documents', 'documents'],
    ['settings', 'Settings', 'settings'],
  ]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <BrandIdentity />
        <nav>{navItems.map(([page, label, icon]) => <button key={page} className={activePage === page ? 'active' : ''} onClick={() => { setPreviewDocument(null); setActivePage(page) }}><Icon name={icon} />{label}</button>)}</nav>
        <div className="sidebar-account"><div className="account-avatar">A</div><div><strong>{user.username}</strong><span>Administrator</span></div><button onClick={logout} title="Sign out"><Icon name="logout" /></button></div>
      </aside>
      <main className="main-area">
        <header className="topbar"><div><span>TELESOM ACADEMY</span><b> / {navItems.find((item) => item[0] === activePage)?.[1]}</b></div><button className="topbar-avatar" title="Administrator">A</button></header>
        {previewDocument ? <PreviewWorkspace document={previewDocument} closePreview={() => setPreviewDocument(null)} /> : (
          <div className="content-area">
            {activePage === 'dashboard' && <Dashboard documents={documents} openDocument={openDocument} />}
            {activePage === 'converter' && <Converter openDocument={openDocument} refreshDocuments={refreshDocuments} />}
            {activePage === 'documents' && <DocumentLibrary documents={documents} openDocument={openDocument} refreshDocuments={refreshDocuments} />}
            {activePage === 'settings' && <Settings />}
          </div>
        )}
      </main>
    </div>
  )
}

export default TelesomApp
