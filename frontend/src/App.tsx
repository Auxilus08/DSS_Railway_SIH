import React, { useEffect, useState } from 'react'
import * as d3 from 'd3'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function App() {
  const [health, setHealth] = useState('loading...')
  const [dbStatus, setDbStatus] = useState('loading...')

  useEffect(() => {
    axios.get(`${API_BASE}/api/health`).then(r => setHealth(JSON.stringify(r.data))).catch(e => setHealth(String(e)))
    axios.get(`${API_BASE}/api/db-check`).then(r => setDbStatus(JSON.stringify(r.data))).catch(e => setDbStatus(String(e)))

    // D3 sample: render a simple bar
    const svg = d3.select('#viz').append('svg').attr('width', 200).attr('height', 50)
    svg.append('rect').attr('x', 10).attr('y', 10).attr('width', 180).attr('height', 20).attr('fill', '#4f46e5')
    svg.append('text').attr('x', 100).attr('y', 25).attr('fill', '#fff').attr('text-anchor', 'middle').attr('dominant-baseline', 'middle').text('D3 Ready')
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">SIH Hackathon Starter</h1>
      <p className="mt-2">Backend health: {health}</p>
      <p className="mt-2">DB check: {dbStatus}</p>
      <div id="viz" className="mt-4"></div>
    </div>
  )
}
