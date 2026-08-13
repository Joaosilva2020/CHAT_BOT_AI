require('dotenv').config();
import express from 'express'
import { execFile } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const app = express()
const PORT = 3001
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

app.use(express.json())
app.use(express.static(path.join(__dirname, 'public')))

app.post('/api/chat', (req, res) => {
    const mensagem = String(req.body?.mensagem || '').trim()

    if (!mensagem) {
        return res.status(400).json({ erro: 'Digite uma mensagem.' })
    }

    const python = path.join(__dirname, 'venv', 'bin', 'python')
    const script = path.join(__dirname, 'agente.py')

    execFile(
        python,
        [script, mensagem],
        {
            cwd: __dirname,
            env: {
                ...process.env,
                PROVEDOR_LLM: process.env.PROVEDOR_LLM || 'ollama',
            },
            timeout: 180000,
            maxBuffer: 1024 * 1024,
        },
        (erro, stdout, stderr) => {
            if (erro) {
                return res.status(500).json({
                    erro: stderr.trim() || erro.message || 'Erro ao chamar o agente.',
                })
            }

            res.json({ resposta: stdout.trim() })
        }
    )
})

const server = app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT} `)
})

server.on('error', (erro) => {
    console.error('Erro no servidor:', erro.message)
})

server.on('close', () => {
    console.log('Servidor encerrado.')
})
