import { useEffect, useState } from 'react'
import './TelesomApp.css'
import telesomLogo from './assets/branding/telesom-academy-logo.png'

const API = 'http://127.0.0.1:8000'

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`))
  return match ? decodeURIComponent(match[2]) : ''
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (options.method && options.method !== 'GET') headers['X-CSRFToken'] = getCookie('csrftoken')
  const response = await fetch(API + path, { ...options, headers, credentials: 'include' })
  const type = response.headers.get('content-type') || ''
  const data = type.includes('application/json') ? await response.json() : null
  if (!response.ok) throw new Error(data?.error || data?.detail || 'Request failed')
  return data
}

function Brand({ compact = false }) {
  return <div className={`brand ${compact ? 'brand-compact' : ''}`}><img src={telesomLogo} alt="Telesom Academy" /></div>
}

function Icon({ children }) {
  return <span className="ui-icon" aria-hidden="true">{children}</span>
}

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => { fetch(API + '/api/auth/csrf/', { credentials: 'include' }).catch(() => {}) }, [])

  const submit = async (event) => {
    event.preventEvent?.()
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api('/api/auth/csrf/')
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
    <main className="login-screen">
      <section className="login-card">
        <Brand />
        <h1>Sign in</h1>
        <form onSubmit={submit}>
          <label>
            <span>Username</span>
            <div className="input-shell"><Icon>◉</Icon><input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></div>
          </label>
          <label>
            <span>Password</span>
            <div className="input-shell"><Icon>◇</Icon><input type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /><button type="button" className="password-toggle" onClick={() => setShowPassword((value) => !value)}>{showPassword ? 'Hide' : 'Show'}</button></div>
          </label>
          {error && <div className="login-error">{error}</div>}
          <button className="primary-button login-submit" disabled={loading}>{loading ? 'Signing in...' : 'Sign In'}</button>
        </form>
      </section>
    </main>
  )
}

function Status({ status }) {
  return <span className={`status status-${status || 'uploaded'}`}><i />{(status || 'uploaded').replace(/^./, (value) => value.toUpperCase())}</span>
}

function Dashboard({ documents, openDocument, navigate }) {
  const completed = documents.filter((document) => document.status === 'completed').length
  const processing = documents.filter((document) => document.status === 'processing').length
  const failed = documents.filter((document) => document.status === 'failed').length

  return (
    <>
      <div className="page-title dashboard-title">
        <div><h1>Dashboard</h1></div>
        <button className="primary-button dashboard-upload" onClick={() => navigate('convert')}><Icon>＋</Icon>Upload Document</button>
      </div>

      <div className="dashboard-overview">
        <div className="stat-grid dashboard-stat-grid">
          <article className="stat-card"><span className="stat-label">Documents</span><strong>{documents.length}</strong></article>
          <article className="stat-card"><span className="stat-label">Completed</span><strong>{completed}</strong></article>
          <article className="stat-card"><span className="stat-label">Processing</span><strong>{processing}</strong></article>
          <article className="stat-card stat-card-gold"><span className="stat-label">Failed</span><strong>{failed}</strong></article>
        </div>

        <section className="dashboard-grid">
          <div className="workspace-card recent-documents">
            <div className="card-heading">
              <div><span className="title-kicker">RECENT</span><h2>Recent Documents</h2></div>
              <button className="text-button" onClick={() => navigate('history')}>View all</button>
            </div>
            {documents.length === 0 ? (
              <div className="empty-state"><strong>No documents</strong><span>Upload a document to begin.</span></div>
            ) : (
              <div className="recent-document-list">
                {documents.slice(0, 5).map((document) => (
                  <button className="recent-document-row" key={document.id} onClick={() => openDocument(document)}>
                    <span className="document-icon">{(document.file_type || 'DOC').toUpperCase()}</span>
                    <span className="recent-document-info"><strong>{document.title}</strong><small>{(document.file_type || 'doc').toUpperCase()} · {new Date(document.updated_at || document.uploaded_at).toLocaleDateString()}</small></span>
                    <Status status={document.status} />
                    <span className="recent-open">Open <b>›</b></span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <aside className="dashboard-side">
            <button className="quick-action" onClick={() => navigate('convert')}><span className="quick-action-icon">＋</span><span><strong>Convert document</strong><small>Upload and generate HTML</small></span><b>›</b></button>
            <button className="quick-action" onClick={() => navigate('templates')}><span className="quick-action-icon template-action-icon">▧</span><span><strong>Lesson templates</strong><small>Academy, Editorial, Interactive, Presentation</small></span><b>›</b></button>
          </aside>
        </section>
      </div>
    </>
  )
}

const TEMPLATES = [
  { key: 'academy', name: 'Academy', description: 'Structured navigation and lesson sections.' },
  { key: 'editorial', name: 'Editorial', description: 'Refined typography for reading-led lessons.' },
  { key: 'interactive', name: 'Interactive', description: 'Expandable sections and learning elements.' },
  { key: 'presentation', name: 'Presentation', description: 'Slide-inspired layout with controls.' },
]

function TemplateGallery({ onSelect, onPreview, selected }) {
  return (
    <div className="template-grid">
      {TEMPLATES.map((template) => (
        <article className={`template-card template-${template.key} ${selected === template.key ? 'selected' : ''}`} key={template.key}>
          <div className="template-preview">
            <div className="mini-browser"><i /><i /><i /></div>
            {template.key === 'academy' && <div className="academy-thumb"><aside /><main><b /><b /><span /><span /></main></div>}
            {template.key === 'editorial' && <div className="editorial-thumb"><header /><article><b /><span /><span /><span /></article></div>}
            {template.key === 'interactive' && <div className="interactive-thumb"><header /><div><b /><span /></div><div><b /><span /></div><div><b /><span /></div></div>}
            {template.key === 'presentation' && <div className="presentation-thumb"><aside /><main><b /><span /><span /><nav>‹ 1 / 4 ›</nav></main></div>}
          </div>
          <div className="template-copy"><div><h3>{template.name}</h3><p>{template.description}</p></div><div className="template-actions"><button type="button" className="secondary-button" onClick={() => onPreview?.(template.key)}>Preview</button><button type="button" className={selected === template.key ? 'secondary-button selected-button' : 'primary-button'} onClick={() => onSelect(template.key)}>{selected === template.key ? 'Selected' : 'Select template'}</button></div></div>
        </article>
      ))}
    </div>
  )
}

function Converter({ openDocument, refreshDocuments, draftTemplate }) {
  const [file, setFile] = useState(null)
  const [document, setDocument] = useState(null)
  const [step, setStep] = useState('upload')
  const [selectedTemplate, setSelectedTemplate] = useState(draftTemplate || 'academy')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const uploadAndExtract = async () => {
    if (!file) return
    setError('')
    setBusy(true)
    setProgress(12)
    const form = new FormData()
    form.append('title', file.name)
    form.append('original_file', file)
    form.append('file_type', file.name.split('.').pop().toLowerCase())
    try {
      const response = await fetch(API + '/api/documents/', {
        method: 'POST', body: form, credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') },
      })
      const uploaded = await response.json()
      if (!response.ok) throw new Error(uploaded.original_file?.[0] || uploaded.detail || 'Upload failed')
      setProgress(38)
      const result = await api(`/api/extractor/${uploaded.id}/extract/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ template: 'academy' }) })
      setProgress(72)
      await refreshDocuments()
      setDocument({ ...uploaded, status: 'completed', extracted_data: result.data, selected_template: 'academy' })
      setStep('templates')
      setProgress(100)
    } catch (err) {
      setError(err.message)
      setProgress(0)
    } finally {
      setBusy(false)
    }
  }

  const selectTemplate = (key) => setSelectedTemplate(key)

  const generate = async () => {
    if (!document) return
    setBusy(true)
    setError('')
    try {
      await api(`/api/extractor/${document.id}/generate/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ template: selectedTemplate }),
      })
      await refreshDocuments()
      openDocument({ ...document, status: 'completed', selected_template: selectedTemplate, generated_html: 'available' })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-title"><div><span className="title-kicker">CONVERT</span><h1>Convert document</h1></div></div>
      {step === 'upload' ? (
        <section className="convert-layout">
          <div className="workspace-card upload-card">
            <div className="card-heading"><div><span className="title-kicker">SOURCE</span><h2>Upload document</h2></div></div>
            <label className={`upload-zone ${file ? 'has-file' : ''}`}>
              <input type="file" accept=".pdf,.pptx,.docx" onChange={(event) => setFile(event.target.files[0] || null)} />
              <span className="upload-icon">↑</span>
              <strong>{file ? file.name : 'Choose a document'}</strong>
              <small>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'PDF, PPTX or DOCX • 20 MB maximum'}</small>
              {!file && <span className="secondary-button">Browse files</span>}
            </label>
            <div className="format-row"><span>PDF</span><span>PPTX</span><span>DOCX</span></div>
            {error && <div className="inline-error">{error}</div>}
            <button className="primary-button full-button" onClick={uploadAndExtract} disabled={!file || busy}>{busy ? 'Processing...' : 'Upload and extract'}</button>
          </div>
          <aside className="workspace-card progress-card">
            <div className="card-heading"><div><span className="title-kicker">STATUS</span><h2>Progress</h2></div></div>
            <div className="progress-ring" style={{ '--progress': `${progress * 3.6}deg` }}><strong>{progress}%</strong></div>
            <div className="progress-list"><div className={progress >= 12 ? 'active' : ''}><i>1</i><span>Upload</span></div><div className={progress >= 38 ? 'active' : ''}><i>2</i><span>Extract</span></div><div className={progress >= 72 ? 'active' : ''}><i>3</i><span>Template</span></div></div>
          </aside>
        </section>
      ) : (
        <section className="template-workspace">
          <div className="template-toolbar"><div><span className="title-kicker">DESIGN</span><h2>Choose a template</h2></div><button className="primary-button" onClick={generate} disabled={busy}>{busy ? 'Generating...' : 'Generate HTML'}</button></div>
          {error && <div className="inline-error">{error}</div>}
          <TemplateGallery selected={selectedTemplate} onSelect={selectTemplate} onPreview={() => {}} />
        </section>
      )}
    </>
  )
}

function DocumentLibrary({ documents, openDocument, refreshDocuments }) {
  const [search, setSearch] = useState('')
  const visible = documents.filter((document) => document.title.toLowerCase().includes(search.toLowerCase()))

  const removeDocument = async (document) => {
    if (!window.confirm(`Move ${document.title} to deleted items?`)) return
    await api(`/api/documents/${document.id}/`, { method: 'DELETE' })
    await refreshDocuments()
  }

  return (
    <>
      <div className="page-title"><div><span className="title-kicker">DOCUMENTS</span><h1>Library</h1></div></div>
      <section className="workspace-card">
        <div className="card-heading"><div><span className="title-kicker">ALL FILES</span><h2>Saved documents</h2></div><input className="search-input" placeholder="Search" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
        {visible.length === 0 ? <div className="empty-state"><strong>No documents</strong></div> : (
          <div className="document-table">
            <div className="table-row table-head"><span>Document</span><span>Template</span><span>Status</span><span>Updated</span><span /></div>
            {visible.map((document) => (
              <div className="table-row" key={document.id}><span className="document-cell"><b className="format-mark">{(document.file_type || 'doc').toUpperCase()}</b><strong>{document.title}</strong></span><span>{document.selected_template || 'Academy'}</span><span><Status status={document.status} /></span><span>{new Date(document.updated_at || document.uploaded_at).toLocaleDateString()}</span><span className="row-actions"><button className="row-button" onClick={() => openDocument(document)}>Open</button><button className="row-button danger" onClick={() => removeDocument(document)}>Delete</button></span></div>
            ))}
          </div>
        )}
      </section>
    </>
  )
}

function Preview({ document, closePreview }) {
  const [device, setDevice] = useState('desktop')

  const downloadZip = async () => {
    const response = await fetch(API + `/api/extractor/${document.id}/download-assets/`, { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') } })
    if (!response.ok) throw new Error('Download failed')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = window.document.createElement('a')
    anchor.href = url
    anchor.download = `${document.title.replace(/\.[^.]+$/, '')}-lesson.zip`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="preview-screen">
      <div className="preview-toolbar"><button className="back-button" onClick={closePreview}>← Back</button><div><span className="title-kicker">PREVIEW</span><h1>{document.title}</h1></div><div className="preview-actions"><div className="device-switch"><button className={device === 'desktop' ? 'active' : ''} onClick={() => setDevice('desktop')}>Desktop</button><button className={device === 'mobile' ? 'active' : ''} onClick={() => setDevice('mobile')}>Mobile</button></div><button className="primary-button" onClick={downloadZip}>Download</button></div></div>
      <div className="preview-stage"><iframe className={`lesson-frame ${device}`} src={`${API}/api/extractor/${document.id}/preview/`} sandbox="allow-same-origin" title="Generated lesson preview" /></div>
    </section>
  )
}

function History({ documents, openDocument }) {
  return <><div className="page-title"><div><span className="title-kicker">ACTIVITY</span><h1>Conversion history</h1></div></div><section className="workspace-card"><div className="card-heading"><div><span className="title-kicker">ALL ACTIVITY</span><h2>Conversions</h2></div></div>{documents.length === 0 ? <div className="empty-state"><strong>No history</strong></div> : <div className="document-table">{documents.map((document) => <div className="table-row" key={document.id}><span className="document-cell"><b className="format-mark">{(document.file_type || 'doc').toUpperCase()}</b><strong>{document.title}</strong></span><span>{document.selected_template || 'Academy'}</span><span><Status status={document.status} /></span><button className="row-button" onClick={() => openDocument(document)}>Open</button></div>)}</div>}</section></>
}

function Settings({ theme, setTheme }) {
  const themes = [
    { key: 'light', name: 'Light', description: 'White and soft grey' },
    { key: 'sage', name: 'Sage', description: 'Soft green surfaces' },
    { key: 'gold', name: 'Gold', description: 'Warm neutral accents' },
  ]

  return (
    <>
      <div className="page-title"><div><span className="title-kicker">SYSTEM</span><h1>Settings</h1></div></div>
      <section className="workspace-card">
        <div className="card-heading"><div><span className="title-kicker">APPEARANCE</span><h2>Theme</h2></div></div>
        <div className="theme-grid">
          {themes.map((item) => (
            <button type="button" className={`theme-option theme-${item.key} ${theme === item.key ? 'active' : ''}`} onClick={() => setTheme(item.key)} key={item.key}>
              <span className="theme-preview"><i /><i /><i /></span>
              <strong>{item.name}</strong>
              <small>{item.description}</small>
            </button>
          ))}
        </div>
      </section>
      <section className="workspace-card settings-system-card">
        <div className="card-heading"><div><span className="title-kicker">APPLICATION</span><h2>System</h2></div></div>
        <div className="settings-grid"><div><span>Formats</span><strong>PDF, PPTX, DOCX</strong></div><div><span>Upload limit</span><strong>20 MB</strong></div><div><span>Database</span><strong>SQLite / MySQL ready</strong></div></div>
      </section>
    </>
  )
}

function TemplatesPage({ selected, setSelected }) {
  const [previewKey, setPreviewKey] = useState(null)
  const previewTemplate = TEMPLATES.find((template) => template.key === previewKey)

  return (
    <>
      <div className="page-title"><div><span className="title-kicker">DESIGN</span><h1>Lesson templates</h1></div></div>
      <section className="template-workspace">
        <TemplateGallery selected={selected} onSelect={setSelected} onPreview={setPreviewKey} />
      </section>
      {previewTemplate && (
        <div className="template-modal-backdrop" role="presentation" onClick={() => setPreviewKey(null)}>
          <section className="template-modal" role="dialog" aria-modal="true" aria-label={`${previewTemplate.name} preview`} onClick={(event) => event.stopPropagation()}>
            <div className="template-modal-heading"><div><span className="title-kicker">PREVIEW</span><h2>{previewTemplate.name}</h2></div><button type="button" className="modal-close" onClick={() => setPreviewKey(null)}>×</button></div>
            <div className={`template-modal-preview template-${previewTemplate.key}`}>
              {previewTemplate.key === 'academy' && <div className="preview-academy"><aside><b>Lesson</b><span /><span /></aside><article><h3>Academy lesson</h3><p>Structured sections and navigation.</p><div /><div /></article></div>}
              {previewTemplate.key === 'editorial' && <div className="preview-editorial"><header /><article><h3>Editorial lesson</h3><p>Elegant reading hierarchy.</p><div /><div /></article></div>}
              {previewTemplate.key === 'interactive' && <div className="preview-interactive"><h3>Interactive lesson</h3><div><b>Lesson section</b><span>Expand to review</span></div><div><b>Learning check</b><span>Review the key idea</span></div></div>}
              {previewTemplate.key === 'presentation' && <div className="preview-presentation"><aside /><article><span>Lesson 1</span><h3>Presentation lesson</h3><p>Slide-inspired content.</p><nav>‹  1 / 4  ›</nav></article></div>}
            </div>
            <div className="template-modal-footer"><button type="button" className="secondary-button" onClick={() => setPreviewKey(null)}>Close</button><button type="button" className="primary-button" onClick={() => { setSelected(previewTemplate.key); setPreviewKey(null) }}>Select template</button></div>
          </section>
        </div>
      )}
    </>
  )
}

export default function TelesomApp() {
  const [user, setUser] = useState(null)
  const [checked, setChecked] = useState(false)
  const [page, setPage] = useState('dashboard')
  const [documents, setDocuments] = useState([])
  const [preview, setPreview] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [theme, setTheme] = useState(() => localStorage.getItem('telesom-theme') || 'light')
  const [draftTemplate, setDraftTemplate] = useState(() => localStorage.getItem('telesom-draft-template') || 'academy')

  const refreshDocuments = async () => {
    try { const data = await api('/api/documents/'); setDocuments(data.results || data) } catch { setDocuments([]) }
  }

  useEffect(() => { api('/api/auth/me/').then((data) => { setUser(data.user); refreshDocuments() }).catch(() => setUser(null)).finally(() => setChecked(true)) }, [])

  const openDocument = async (document) => {
    try { setPreview(await api(`/api/documents/${document.id}/`)) } catch { setPreview(document) }
  }
  const logout = async () => { try { await api('/api/auth/logout/', { method: 'POST' }) } finally { setUser(null); setPreview(null) } }

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('telesom-theme', theme)
  }, [theme])
  useEffect(() => {
    localStorage.setItem('telesom-draft-template', draftTemplate)
  }, [draftTemplate])

  if (!checked) return <main className="loading-screen"><Brand /><span>Loading</span></main>
  if (!user) return <Login onLogin={(account) => { setUser(account); refreshDocuments() }} />

  const nav = [['dashboard','Dashboard','▦'],['convert','Convert','＋'],['documents','Documents','▤'],['history','History','↻'],['templates','Templates','▧']]

  return (
    <div className={`app-shell theme-${theme}`}>
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <Brand />
        <nav>{nav.map(([key,label,icon]) => <button key={key} className={page === key ? 'active' : ''} onClick={() => { setPage(key); setPreview(null); setSidebarOpen(false) }}><Icon>{icon}</Icon><span>{label}</span></button>)}</nav>
        <button className="sidebar-settings" onClick={() => { setPage('settings'); setPreview(null); setSidebarOpen(false) }}><Icon>⚙</Icon><span>Settings</span></button>
        <div className="sidebar-user"><span>A</span><div><strong>{user.username}</strong><small>Administrator</small></div><button className="logout-button" onClick={logout}><span>↦</span> Sign out</button></div>
      </aside>
      <main className="main-shell">
        <header className="topbar"><button className="menu-button" onClick={() => setSidebarOpen((value) => !value)}>☰</button><div className="topbar-logo"><Brand compact /></div><div className="topbar-status"><i />Workspace ready</div><button className="topbar-avatar" title="Administrator">A</button></header>
        {preview ? <Preview document={preview} closePreview={() => setPreview(null)} /> : <div className="content">
          {page === 'dashboard' && <Dashboard documents={documents} openDocument={openDocument} navigate={setPage} />}
          {page === 'convert' && <Converter openDocument={openDocument} refreshDocuments={refreshDocuments} draftTemplate={draftTemplate} />}
          {page === 'documents' && <DocumentLibrary documents={documents} openDocument={openDocument} refreshDocuments={refreshDocuments} />}
          {page === 'history' && <History documents={documents} openDocument={openDocument} />}
          {page === 'templates' && <TemplatesPage selected={draftTemplate} setSelected={setDraftTemplate} />}
          {page === 'settings' && <Settings theme={theme} setTheme={setTheme} />}
        </div>}
      </main>
    </div>
  )
}
