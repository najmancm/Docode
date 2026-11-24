import { useCallback, useEffect, useMemo, useState } from 'react'
import './TelesomApp.css'
import logo from './assets/branding/telesom-academy-logo.png'

// Use the same host as the page (localhost or 127.0.0.1) so the login
// cookie is sent with every request.
const API = `http://${window.location.hostname}:8000`

const NAVIGATION = [
  { id: 'dashboard', label: 'Dashboard', icon: 'grid' },
  { id: 'convert', label: 'Convert document', icon: 'plus-square' },
  { id: 'documents', label: 'My documents', icon: 'files' },
  { id: 'templates', label: 'Templates', icon: 'layout' },
]

const TEMPLATES = [
  {
    id: 'academy',
    name: 'Academy',
    description: 'A structured learning layout with navigation and progress.',
    tag: 'Recommended',
  },
  {
    id: 'editorial',
    name: 'Editorial',
    description: 'A clean reading experience for detailed learning material.',
    tag: 'Reading',
  },
  {
    id: 'interactive',
    name: 'Interactive',
    description: 'Organised content sections with interactive presentation.',
    tag: 'Engaging',
  },
  {
    id: 'presentation',
    name: 'Presentation',
    description: 'A slide-based layout that follows the original presentation flow.',
    tag: 'Slides',
  },
  { id: 'modern', name: 'Modern', description: 'Contemporary cards with a clear visual hierarchy.', tag: 'Modern' },
  { id: 'minimal', name: 'Minimal', description: 'Distraction-free reading with generous spacing.', tag: 'Simple' },
  { id: 'corporate', name: 'Corporate', description: 'Formal layout for company training.', tag: 'Business' },
  { id: 'workbook', name: 'Workbook', description: 'Study sections with a notes area.', tag: 'Study' },
]

const fixMedia = (html) => html.replaceAll('src="/media/', `src="${API}/media/`)

function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(';') : []

  for (const cookie of cookies) {
    const item = cookie.trim()

    if (item.startsWith(`${name}=`)) {
      return decodeURIComponent(item.substring(name.length + 1))
    }
  }

  return ''
}

async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = { ...options.headers }

  if (!(options.body instanceof FormData) && options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrf = getCookie('csrftoken')

    if (csrf) {
      headers['X-CSRFToken'] = csrf
    }
  }

  const response = await fetch(`${API}${path}`, {
    credentials: 'include',
    ...options,
    method,
    headers,
  })

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message =
      typeof data === 'object'
        ? data.detail || data.error || data.message || JSON.stringify(data)
        : data

    throw new Error(message || `Request failed (${response.status})`)
  }

  return data
}

function Icon({ name, size = 20 }) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.7,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  }

  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
    'plus-square': <><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M12 8v8M8 12h8" /></>,
    files: <><path d="M14 2H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h8" /></>,
    layout: <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 9v12" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 5 5" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
    close: <><path d="m18 6-12 12M6 6l12 12" /></>,
    logout: <><path d="M10 17l5-5-5-5M15 12H3" /><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" /></>,
    upload: <><path d="M12 16V4m-5 5 5-5 5 5" /><path d="M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4" /></>,
    download: <><path d="M12 4v12m-5-5 5 5 5-5" /><path d="M4 20h16" /></>,
    eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></>,
    trash: <><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6" /></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></>,
    check: <><path d="m5 12 4 4L19 6" /></>,
    chevron: <><path d="m9 18 6-6-6-6" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.6a8 8 0 0 1-1.7 1l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.7-1l-1.7.6-1.4-2.4L7.3 15a8 8 0 0 1 0-2l-1.4-1.1 1.4-2.4 1.7.6a8 8 0 0 1 1.7-1l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.7 1l1.7-.6 1.4 2.4-1.4 1.1a8 8 0 0 1-.1 2Z" /></>,
    document: <><path d="M5 3h14v18H5z" /><path d="M8 8h8M8 12h8M8 16h5" /></>,
  }

  return <svg {...common}>{paths[name] || paths.file}</svg>
}

function Brand({ compact = false }) {
  return (
    <div className={`brand ${compact ? 'brand-compact' : ''}`}>
      <img src={logo} alt="Telesom Academy" />
    </div>
  )
}

function Status({ status }) {
  const value = String(status || 'uploaded').toLowerCase()

  const label = {
    completed: 'Completed',
    processing: 'Processing',
    failed: 'Failed',
    uploaded: 'Uploaded',
    deleted: 'Deleted',
  }[value] || value

  return (
    <span className={`status status-${value}`}>
      <span className="status-dot" />
      {label}
    </span>
  )
}

function formatDate(value) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return '—'

  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function getFileType(document) {
  return String(document?.file_type || document?.original_file || '')
    .split('.')
    .pop()
    .toUpperCase()
}

function getDocumentName(document) {
  return document?.title || document?.original_file?.split('/').pop() || 'Untitled document'
}

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      await request('/api/auth/csrf/')
      const result = await request('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })

      onLogin(result.user || result)
    } catch (err) {
      setError(err.message || 'Unable to sign in. Please check your details.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-screen">
      <section className="login-card">
        <Brand />

        <div className="login-heading">
          <h1>Welcome back</h1>
          <span>Sign in to your workspace</span>
        </div>

        <form onSubmit={handleSubmit}>
          <label className="login-field">
            <span>Username</span>
            <div className="input-shell">
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter your username"
                autoComplete="username"
                required
              />
            </div>
          </label>

          <label className="login-field">
            <span>Password</span>
            <div className="input-shell">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </label>

          {error && <div className="login-error">{error}</div>}

          <button className="login-submit" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="login-footer">
          <span />
          <small>TELESOM ACADEMY</small>
          <span />
        </div>
      </section>
    </main>
  )
}

function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="heading-action">{action}</div>}
    </div>
  )
}

function EmptyState({ icon = 'files', title, description, action }) {
  return (
    <div className="empty-state">
      <div className="empty-icon"><Icon name={icon} size={25} /></div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}

function DocumentTable({ documents, onPreview, onDelete, onDownload, emptyAction }) {
  if (!documents.length) {
    return (
      <EmptyState
        title="No documents yet"
        description="Upload a PDF, PowerPoint or Word document to get started."
        action={emptyAction}
      />
    )
  }

  return (
    <div className="table-wrap">
      <table className="document-table">
        <thead>
          <tr>
            <th>Document</th>
            <th>Format</th>
            <th>Date added</th>
            <th>Status</th>
            <th className="actions-heading">Actions</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((item) => (
            <tr key={item.id}>
              <td>
                <div className="document-name-cell">
                  <div className="file-icon"><Icon name="file" size={19} /></div>
                  <div>
                    <strong>{getDocumentName(item)}</strong>
                    <small>Document #{item.id}</small>
                  </div>
                </div>
              </td>
              <td><span className="file-type">{getFileType(item)}</span></td>
              <td>{formatDate(item.uploaded_at || item.created_at)}</td>
              <td><Status status={item.status} /></td>
              <td>
                <div className="table-actions">
                  <button
                    type="button"
                    className="icon-button"
                    title="Preview"
                    onClick={() => onPreview(item)}
                  >
                    <Icon name="eye" size={17} />
                  </button>
                  <button
                    type="button"
                    className="icon-button"
                    title="Download"
                    onClick={() => onDownload(item)}
                  >
                    <Icon name="download" size={17} />
                  </button>
                  <button
                    type="button"
                    className="icon-button danger"
                    title="Delete"
                    onClick={() => onDelete(item)}
                  >
                    <Icon name="trash" size={17} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TemplateCard({ template, selected, onSelect }) {
  return (
    <button
      type="button"
      className={`template-card ${selected ? 'selected' : ''}`}
      onClick={() => onSelect(template.id)}
    >
      <div className={`template-art template-art-${template.id}`}>
        <div className="template-art-sidebar" />
        <div className="template-art-content">
          <span />
          <span />
          <span />
          <div className="template-art-blocks"><i /><i /><i /></div>
          <span />
          <span />
        </div>
      </div>
      <div className="template-card-info">
        <div>
          <h3>{template.name}</h3>
          <p>{template.description}</p>
        </div>
        <span className="template-tag">{template.tag}</span>
      </div>
      <div className="template-select">
        <span>{selected ? 'Selected' : 'Choose template'}</span>
        {selected ? <Icon name="check" size={17} /> : <Icon name="chevron" size={17} />}
      </div>
    </button>
  )
}

export default function TelesomApp() {
  const [user, setUser] = useState(null)
  const [checked, setChecked] = useState(false)
  const [page, setPage] = useState('dashboard')
  const [documents, setDocuments] = useState([])
  const [preview, setPreview] = useState(null)
  const [previewHtml, setPreviewHtml] = useState('')
  const [previewTemplate, setPreviewTemplate] = useState('academy')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [pageError, setPageError] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [selectedTemplate, setSelectedTemplate] = useState('academy')
  const [converting, setConverting] = useState(false)
  const [settingsMessage] = useState('')

  const loadDocuments = useCallback(async () => {
    try {
      const result = await request('/api/documents/')
      const items = Array.isArray(result) ? result : result.results || result.documents || []
      setDocuments(items)
    } catch (err) {
      setPageError(err.message || 'Could not load documents.')
    }
  }, [])

  useEffect(() => {
    let active = true

    async function checkSession() {
      try {
        await request('/api/auth/csrf/')
        const result = await request('/api/auth/me/')

        if (active) {
          setUser(result.user || result)
        }
      } catch {
        if (active) setUser(null)
      } finally {
        if (active) setChecked(true)
      }
    }

    checkSession()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (user) loadDocuments()
  }, [user, loadDocuments])

  const filteredDocuments = useMemo(() => {
    const term = search.trim().toLowerCase()

    if (!term) return documents

    return documents.filter((item) =>
      getDocumentName(item).toLowerCase().includes(term) ||
      String(item.file_type || '').toLowerCase().includes(term) ||
      String(item.status || '').toLowerCase().includes(term)
    )
  }, [documents, search])

  const completedCount = documents.filter((item) => item.status === 'completed').length
  const processingCount = documents.filter((item) => item.status === 'processing').length
  const failedCount = documents.filter((item) => item.status === 'failed').length

  async function handleLogin(authenticatedUser) {
    setUser(authenticatedUser)
    setPage('dashboard')
    setPageError('')
  }

  async function handleLogout() {
    try {
      await request('/api/auth/logout/', { method: 'POST' })
    } catch (err) {
      console.error('Logout error:', err)
    }

    setUser(null)
    setDocuments([])
    setPreview(null)
    setPreviewHtml('')
    setPage('dashboard')
  }

  function navigate(nextPage) {
    setPage(nextPage)
    setSidebarOpen(false)
    setPageError('')
    setNotice('')
  }

  async function openPreview(item) {
    setPreview(item)
    setPreviewHtml('')
    setPreviewTemplate(item.selected_template || 'academy')
    setPage('preview')
    setPageError('')

    try {
      const result = await request(`/api/extractor/${item.id}/preview/`)
      const html = typeof result === 'string'
        ? result
        : result.html || result.preview || result.generated_html || ''

      setPreviewHtml(fixMedia(html))
    } catch (err) {
      setPageError(err.message || 'Could not load the preview.')
    }
  }

  async function deleteDocument(item) {
    const confirmed = window.confirm(`Delete "${getDocumentName(item)}"?`)
    if (!confirmed) return

    try {
      await request(`/api/documents/${item.id}/`, { method: 'DELETE' })
      setDocuments((current) => current.filter((doc) => doc.id !== item.id))
      setNotice('Document deleted.')
    } catch (err) {
      setPageError(err.message || 'Could not delete this document.')
    }
  }

  async function downloadDocument(item) {
    try {
      const response = await fetch(`${API}/api/extractor/${item.id}/download/`, {
        credentials: 'include',
      })

      if (!response.ok) throw new Error('Download could not be started.')

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = `${getDocumentName(item)}.html`
      window.document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setPageError(err.message || 'Download failed.')
    }
  }

  async function downloadAssets(item) {
    try {
      const response = await fetch(`${API}/api/extractor/${item.id}/download-assets/`, {
        credentials: 'include',
      })

      if (!response.ok) throw new Error('ZIP download could not be started.')

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = `${getDocumentName(item)}-package.zip`
      window.document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setPageError(err.message || 'Package download failed.')
    }
  }

  async function uploadAndConvert(event) {
    event.preventDefault()

    if (!selectedFile) {
      setPageError('Please choose a document first.')
      return
    }

    setConverting(true)
    setPageError('')
    setNotice('')

    try {
      const extension = selectedFile.name.split('.').pop().toLowerCase()

      const formData = new FormData()
      formData.append('title', selectedFile.name.replace(/\.[^.]+$/, ''))
      formData.append('original_file', selectedFile)
      formData.append('file_type', extension)

      const uploaded = await request('/api/documents/', {
        method: 'POST',
        body: formData,
      })

      const documentId = uploaded.id || uploaded.document?.id

      if (!documentId) {
        throw new Error('The upload succeeded, but the document ID was not returned.')
      }

      await request(`/api/extractor/${documentId}/extract/`, {
        method: 'POST',
        body: JSON.stringify({ template: selectedTemplate }),
      })

      await request(`/api/extractor/${documentId}/select-template/`, {
        method: 'POST',
        body: JSON.stringify({ template: selectedTemplate }),
      })

      await request(`/api/extractor/${documentId}/generate/`, {
        method: 'POST',
        body: JSON.stringify({ template: selectedTemplate }),
      })

      await loadDocuments()
      setSelectedFile(null)
      setNotice('Your document has been converted successfully.')

      const updatedDocument = {
        ...uploaded,
        id: documentId,
        status: 'completed',
        selected_template: selectedTemplate,
      }

      await openPreview(updatedDocument)
    } catch (err) {
      setPageError(err.message || 'Document conversion failed.')
      await loadDocuments()
    } finally {
      setConverting(false)
    }
  }

  async function regenerate(templateId) {
    if (!preview?.id) return

    setLoading(true)
    setPageError('')
    setPreviewTemplate(templateId)

    try {
      await request(`/api/extractor/${preview.id}/generate/`, {
        method: 'POST',
        body: JSON.stringify({ template: templateId }),
      })

      const result = await request(`/api/extractor/${preview.id}/preview/`)
      const html = typeof result === 'string'
        ? result
        : result.html || result.preview || result.generated_html || ''

      setPreviewHtml(fixMedia(html))
      setPreview((current) => ({ ...current, selected_template: templateId }))

      await loadDocuments()
      setNotice('Preview updated.')
    } catch (err) {
      setPageError(err.message || 'Could not regenerate the preview.')
    } finally {
      setLoading(false)
    }
  }

  function renderDashboard() {
    const recent = [...documents]
      .sort((a, b) => new Date(b.uploaded_at || 0) - new Date(a.uploaded_at || 0))
      .slice(0, 5)

    return (
      <>
        <PageHeading
          eyebrow="OVERVIEW"
          title="Dashboard"
          description="Manage your documents and learning content from one place."
        />

        <section className="welcome-panel">
          <div className="welcome-copy">
            <span className="welcome-label">YOUR WORKSPACE</span>
            <h2>Everything you need to create learning content.</h2>
            <p>Upload your training materials and transform them into responsive HTML lessons.</p>
            <button className="welcome-button" onClick={() => navigate('convert')}>
              Convert a document <Icon name="chevron" size={17} />
            </button>
          </div>
          <div className="welcome-decoration" aria-hidden="true">
            <div className="welcome-document"><Icon name="document" size={42} /></div>
            <div className="welcome-orbit orbit-one" />
            <div className="welcome-orbit orbit-two" />
          </div>
        </section>

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-top"><span>Total documents</span><span className="stat-icon"><Icon name="files" /></span></div>
            <strong>{documents.length}</strong>
            <small>Documents in your library</small>
          </div>
          <div className="stat-card">
            <div className="stat-top"><span>Completed</span><span className="stat-icon green"><Icon name="check" /></span></div>
            <strong>{completedCount}</strong>
            <small>Successfully converted</small>
          </div>
          <div className="stat-card">
            <div className="stat-top"><span>Processing</span><span className="stat-icon gold"><Icon name="clock" /></span></div>
            <strong>{processingCount}</strong>
            <small>Currently being processed</small>
          </div>
          <div className="stat-card">
            <div className="stat-top"><span>Failed</span><span className="stat-icon muted"><Icon name="file" /></span></div>
            <strong>{failedCount}</strong>
            <small>Documents needing attention</small>
          </div>
        </section>

        <section className="content-panel">
          <div className="panel-heading">
            <div>
              <h2>Recent documents</h2>
              <p>Your latest uploaded training materials</p>
            </div>
            <button className="text-button" onClick={() => navigate('documents')}>
              View all <Icon name="chevron" size={16} />
            </button>
          </div>
          <DocumentTable
            documents={recent}
            onPreview={openPreview}
            onDelete={deleteDocument}
            onDownload={downloadDocument}
            emptyAction={
              <button className="primary-button" onClick={() => navigate('convert')}>
                Upload your first document
              </button>
            }
          />
        </section>
      </>
    )
  }

  function renderConvert() {
    return (
      <>
        <PageHeading
          eyebrow="CONTENT WORKSPACE"
          title="Convert document"
          description="Turn your PDF, PowerPoint and Word files into responsive HTML lessons."
        />

        <form className="conversion-layout" onSubmit={uploadAndConvert}>
          <section className="content-panel conversion-main">
            <div className="panel-heading">
              <div>
                <h2>Upload your document</h2>
                <p>Select a source file to begin the conversion process.</p>
              </div>
            </div>

            <label className={`upload-zone ${selectedFile ? 'has-file' : ''}`}>
              <input
                type="file"
                accept=".pdf,.pptx,.docx"
                onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
              />
              <div className="upload-icon"><Icon name="upload" size={27} /></div>
              <strong>{selectedFile ? selectedFile.name : 'Drop your file here'}</strong>
              <p>{selectedFile ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB · Ready to upload` : 'or click to browse your computer'}</p>
              <span className="upload-formats">PDF · PPTX · DOCX</span>
            </label>

            <div className="conversion-note">
              <Icon name="check" size={18} />
              <span>Original uploaded files are kept in your document library.</span>
            </div>
          </section>

          <section className="content-panel conversion-options">
            <div className="panel-heading">
              <div>
                <h2>Choose a template</h2>
                <p>Select the design for your generated lesson.</p>
              </div>
            </div>

            <div className="template-choice-list">
              {TEMPLATES.map((template) => (
                <button
                  type="button"
                  key={template.id}
                  className={`template-choice ${selectedTemplate === template.id ? 'active' : ''}`}
                  onClick={() => setSelectedTemplate(template.id)}
                >
                  <span className={`choice-preview choice-${template.id}`}>
                    <i /><i /><i />
                  </span>
                  <span className="choice-text">
                    <strong>{template.name}</strong>
                    <small>{template.description}</small>
                  </span>
                  <span className="choice-radio">{selectedTemplate === template.id && <i />}</span>
                </button>
              ))}
            </div>

            <button className="primary-button convert-button" type="submit" disabled={!selectedFile || converting}>
              {converting ? 'Converting document...' : 'Generate HTML lesson'}
              {!converting && <Icon name="chevron" size={17} />}
            </button>
          </section>
        </form>
      </>
    )
  }

  function renderDocuments() {
    return (
      <>
        <PageHeading
          eyebrow="LIBRARY"
          title="My documents"
          description="Browse and manage your uploaded and converted documents."
          action={
            <button className="primary-button" onClick={() => navigate('convert')}>
              <Icon name="plus-square" size={18} /> Upload document
            </button>
          }
        />

        <section className="content-panel">
          <div className="library-toolbar">
            <div className="search-box">
              <Icon name="search" size={18} />
              <input
                type="search"
                placeholder="Search documents..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <span className="results-count">{filteredDocuments.length} documents</span>
          </div>

          <DocumentTable
            documents={filteredDocuments}
            onPreview={openPreview}
            onDelete={deleteDocument}
            onDownload={downloadDocument}
            emptyAction={
              <button className="primary-button" onClick={() => navigate('convert')}>
                Upload document
              </button>
            }
          />
        </section>
      </>
    )
  }

  function renderTemplates() {
    return (
      <>
        <PageHeading
          eyebrow="DESIGN LIBRARY"
          title="Templates"
          description="Choose the visual structure used when generating your HTML lessons."
        />

        <section className="template-gallery">
          {TEMPLATES.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              selected={selectedTemplate === template.id}
              onSelect={setSelectedTemplate}
            />
          ))}
        </section>

        <div className="template-info">
          <div className="template-info-icon"><Icon name="layout" size={21} /></div>
          <div>
            <strong>Template selection</strong>
            <p>Your selected template will be used for the next document conversion. You can also choose a template during conversion.</p>
          </div>
        </div>
      </>
    )
  }

  function renderSettings() {
    return (
      <>
        <PageHeading
          eyebrow="PREFERENCES"
          title="Settings"
          description="Account information and workspace details."
        />

        <section className="settings-grid">
          <div className="content-panel settings-panel">
            <div className="settings-section-heading">
              <div className="settings-icon"><Icon name="settings" /></div>
              <div><h2>Account information</h2><p>Your signed-in administrator account</p></div>
            </div>
            <div className="settings-row"><span>Username</span><strong>{user?.username || 'Administrator'}</strong></div>
            <div className="settings-row"><span>Account type</span><strong>Administrator</strong></div>
            <div className="settings-row"><span>Workspace</span><strong>TELESOM ACADEMY</strong></div>
          </div>

          <div className="content-panel settings-panel">
            <div className="settings-section-heading">
              <div className="settings-icon gold"><Icon name="files" /></div>
              <div><h2>Document storage</h2><p>Current workspace library</p></div>
            </div>
            <div className="settings-row"><span>Total documents</span><strong>{documents.length}</strong></div>
            <div className="settings-row"><span>Completed conversions</span><strong>{completedCount}</strong></div>
            <div className="settings-row"><span>Failed conversions</span><strong>{failedCount}</strong></div>
          </div>
        </section>

        {settingsMessage && <p className="inline-notice">{settingsMessage}</p>}
      </>
    )
  }

  function renderPreview() {
    return (
      <>
        <PageHeading
          eyebrow="LESSON VIEWER"
          title="Document preview"
          description={preview ? getDocumentName(preview) : 'Preview your generated HTML lesson.'}
          action={
            <button className="secondary-button" onClick={() => navigate('documents')}>
              Back to documents
            </button>
          }
        />

        {preview && (
          <section className="content-panel preview-panel">
            <div className="preview-toolbar">
              <div className="preview-document-title">
                <span className="preview-live-dot" />
                <strong>{getDocumentName(preview)}</strong>
              </div>
              <div className="preview-actions">
                <select
                  className="secondary-button"
                  value={previewTemplate}
                  disabled={loading}
                  onChange={(event) => regenerate(event.target.value)}
                  aria-label="Lesson template"
                >
                  {TEMPLATES.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
                <button className="secondary-button" onClick={() => regenerate(previewTemplate)} disabled={loading}>
                  {loading ? 'Updating...' : 'Regenerate'}
                </button>
                <button className="secondary-button" onClick={() => downloadDocument(preview)}>
                  <Icon name="download" size={16} /> HTML
                </button>
                <button className="primary-button" onClick={() => downloadAssets(preview)}>
                  <Icon name="download" size={16} /> Download package
                </button>
              </div>
            </div>

            <div className="preview-frame-wrap">
              {previewHtml ? (
                <iframe
                  className="lesson-iframe"
                  title="Generated lesson preview"
                  srcDoc={previewHtml}
                  sandbox="allow-scripts allow-same-origin allow-forms"
                />
              ) : (
                <EmptyState
                  icon="eye"
                  title="Preview unavailable"
                  description="The generated HTML preview could not be loaded. Try regenerating the lesson."
                  action={<button className="primary-button" onClick={() => regenerate(previewTemplate)}>Try again</button>}
                />
              )}
            </div>
          </section>
        )}
      </>
    )
  }

  function renderCurrentPage() {
    switch (page) {
      case 'dashboard': return renderDashboard()
      case 'convert': return renderConvert()
      case 'documents': return renderDocuments()
      case 'templates': return renderTemplates()
      case 'settings': return renderSettings()
      case 'preview': return renderPreview()
      default: return renderDashboard()
    }
  }

  if (!checked) {
    return (
      <div className="app-loading">
        <Brand />
        <span className="loading-spinner" />
        <p>Loading your workspace...</p>
      </div>
    )
  }

  if (!user) return <Login onLogin={handleLogin} />

  const currentPage = NAVIGATION.find((item) => item.id === page)

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <Brand />
          <button className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu">
            <Icon name="close" />
          </button>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          {NAVIGATION.map((item) => (
            <button
              type="button"
              key={item.id}
              className={`nav-item ${page === item.id ? 'active' : ''}`}
              onClick={() => navigate(item.id)}
            >
              <Icon name={item.icon} size={19} />
              <span>{item.label}</span>
              {page === item.id && <span className="nav-active-mark" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-label">PREFERENCES</div>
          <button
            type="button"
            className={`nav-item ${page === 'settings' ? 'active' : ''}`}
            onClick={() => navigate('settings')}
          >
            <Icon name="settings" size={19} />
            <span>Settings</span>
          </button>

          <div className="sidebar-account">
            <div className="account-avatar">
              {(user.username || 'A').charAt(0).toUpperCase()}
            </div>
            <div className="account-details">
              <strong>{user.username || 'Administrator'}</strong>
              <small>Administrator</small>
            </div>
            <button className="logout-button" onClick={handleLogout} title="Sign out">
              <Icon name="logout" size={18} />
            </button>
          </div>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="menu-button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Icon name="menu" size={21} />
            </button>
            <div className="breadcrumb">
              <span>Workspace</span>
              <Icon name="chevron" size={14} />
              <strong>{currentPage?.label || 'Document preview'}</strong>
            </div>
          </div>

          <div className="topbar-right">
            <div className="workspace-indicator">
              <span />
              Workspace active
            </div>
            <div className="topbar-divider" />
            <div className="topbar-user">
              <div className="account-avatar small">
                {(user.username || 'A').charAt(0).toUpperCase()}
              </div>
              <span>{user.username || 'Administrator'}</span>
            </div>
          </div>
        </header>

        <main className="content">
          {pageError && (
            <div className="app-alert error-alert">
              <span>{pageError}</span>
              <button onClick={() => setPageError('')} aria-label="Dismiss error">
                <Icon name="close" size={17} />
              </button>
            </div>
          )}

          {notice && (
            <div className="app-alert success-alert">
              <Icon name="check" size={17} />
              <span>{notice}</span>
              <button onClick={() => setNotice('')} aria-label="Dismiss notification">
                <Icon name="close" size={17} />
              </button>
            </div>
          )}

          {renderCurrentPage()}

          <footer className="app-footer">
            <span>TELESOM ACADEMY</span>
            <span>Document management workspace</span>
          </footer>
        </main>
      </div>
    </div>
  )
}