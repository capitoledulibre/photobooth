let video = document.getElementById('video')
let canvas = document.getElementById('canvas')
let context = canvas.getContext('2d')
let debounce = document.getElementById('debounce')
let email = document.getElementById('inputEmail')
let error = document.getElementById('error')
let success = document.getElementById('success')
let secondScreenContainer = document.getElementById('secondScreenContainer')
let interval = null
let image = null
let i = 5
let currentPhotoUUID = null

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
document.getElementById('snap').addEventListener('click', function () {
  document.getElementById('snap').style.display = 'none'
  debounce.innerHTML = 'Pensez à sourir :)'
  interval = setInterval(() => {
    if (i === 0) {
      clearInterval(interval)
      debounce.innerText = ''
      context.drawImage(video, 0, 0, 1049, 540)
      image = canvasToBase64()
      i = 5
      const myRequest = new Request(
        '/photo/',
        {
          method: 'POST', body: image
        },
      )
      fetch(myRequest).then(response => {
        currentPhotoUUID = response.text().then(v => {
          currentPhotoUUID = v
          console.log('Photo is', currentPhotoUUID)
          if (use_qr_code) {
            window.location = "/qrcode/" + currentPhotoUUID + "/"
          }
          video.style.display = 'none'
          secondScreenContainer.style.display = 'block'
        })
      })
    } else {
      debounce.innerText = i + '...'
      i = i - 1
    }
  }, 1000)
})

email.addEventListener('input', function () {
  error.innerText = ''
})

document.getElementById('submit').addEventListener('click', function (e) {
  e.preventDefault()
  if (!email.value || email.value === '' || !validateEmail(email.value)) {
    error.innerText = 'Veuillez insérer une adresse mail valide'
    return
  }
  console.log('send photo and email to backend')
  const myRequest = new Request(
    '/email/',
    {
      method: 'POST', body: JSON.stringify({ "email": email.value, "uuid": currentPhotoUUID })
    },
  )
  fetch(myRequest).then(response => {
    secondScreenContainer.style.display = 'none'
    success.style.display = 'block'
    setTimeout(() => {
      window.location.reload()
    }, 5000)
  })
})

function canvasToBase64() {
  return canvas.toDataURL('image/jpeg')
}

function validateEmail(email) {
  var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
  return re.test(email)
}
