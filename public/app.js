const form = document.querySelector('#chat-form')
const input = document.querySelector('#message-input')
const messages = document.querySelector('#messages')
const statusLabel = document.querySelector('#status')
const hero = document.querySelector('#hero')
const button = form.querySelector('button')

function addMessage(text, type) {
  const article = document.createElement('article')
  article.className = `message message--${type}`

  const paragraph = document.createElement('p')
  paragraph.textContent = text

  article.appendChild(paragraph)
  messages.appendChild(article)
  messages.scrollTop = messages.scrollHeight

  return article
}

function setLoading(isLoading) {
  button.disabled = isLoading
  input.disabled = isLoading
  statusLabel.textContent = isLoading ? 'pensando' : 'pronto'
  statusLabel.classList.remove('status--error')
}

form.addEventListener('submit', async (event) => {
  event.preventDefault()

  const text = input.value.trim()
  if (!text) return

  hero.classList.add('is-hidden')
  addMessage(text, 'user')
  input.value = ''
  setLoading(true)

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mensagem: text }),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.erro || 'Erro ao falar com o agente.')
    }

    addMessage(data.resposta || 'Sem resposta.', 'bot')
  } catch (error) {
    statusLabel.textContent = 'erro'
    statusLabel.classList.add('status--error')
    addMessage(error.message, 'error')
  } finally {
    setLoading(false)
    input.focus()
  }
})
