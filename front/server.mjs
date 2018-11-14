import express from 'express'
import path from 'path'
const app = express()

const __dirname = path.resolve()

app.use(express.static(path.join(__dirname, './')))

app.use('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'))
})

const port = process.env.FRONT_PORT

app.listen(port, () => console.log(`listening on http://localhost:${port}/`))
