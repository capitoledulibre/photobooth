let video = document.getElementById('video')
let canvas = document.getElementById('canvas')
let context = canvas.getContext('2d')
let debounce = document.getElementById('debounce')
let secondScreenContainer = document.getElementById('secondScreenContainer')
let qrcodeImg = document.getElementById('qrcode')
let interval = null
let image = null
let i = 5

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  navigator.mediaDevices
    .getUserMedia({ video: true })
    .then(stream => {
      video.srcObject = stream
      video.play()
    })
    .catch(error => {
      console.error(error)
      alert('Can not access to camera :/')
    })
}

// Trigger photo take
document.getElementById('snapWindow').addEventListener('click', snapAndSendImage)

function snapAndSendImage() {
  document.getElementById('snapWindow').removeEventListener('click', snapAndSendImage)
  debounce.innerHTML = 'Pensez à sourir :)'
  interval = setInterval(() => {
    if (i === 0) {
      video.style.display = 'none'
      secondScreenContainer.style.display = 'block'
      clearInterval(interval)
      debounce.innerText = ''
      context.drawImage(video, 0, 0, 720, 540)
      i = 5
      data = canvasToBase64()
      const myRequest = new Request('/photo/', {
        method: 'POST',
        body: JSON.stringify({ data: data })
      })
      fetch(myRequest).then(response => {
        setTimeout(() => {
          window.location.reload()
        }, 30000)
      })
    } else {
      debounce.innerText = i + '...'
      i = i - 1
    }
  }, 1000)
}

document.getElementById('submit').addEventListener('click', function() {
  window.location.reload()
})

function canvasToBase64() {
  return canvas.toDataURL('image/jpeg')
}
