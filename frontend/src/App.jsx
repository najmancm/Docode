
import { useEffect, useState } from 'react'

function App() {
  const [message, setMessage] = useState('Connecting to DOCODE...')
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/')
      .then(response => {
        if (!response.ok) {
          throw new Error('Server response error')
        }
        return response.json()
      })
      .then(data => {
        setMessage(data.message)
        setStatus('success')
      })
      .catch(error => {
        setMessage('Could not connect to Django backend.')
        setStatus('error')
        console.error(error)
      })
  }, [])

  return (
    <div style={{ padding: '40px', fontFamily: 'Arial' }}>
      <h1>DOCODE</h1>
      <h2>{message}</h2>
      <p>Status: {status}</p>
    </div>
  )
}

export default App
