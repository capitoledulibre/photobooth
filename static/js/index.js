let video = document.getElementById('video')
let canvas = document.getElementById('canvas')
let context = canvas.getContext('2d')
let debounce = document.getElementById('debounce')
let secondScreenContainer = document.getElementById('secondScreenContainer')
let qrcodeImg = document.getElementById('qrcode')
let form = document.getElementById('form')
let error = document.getElementById('error')
let success = document.getElementById('success')
let email = document.getElementById('inputEmail')
let debounceEnd = document.getElementById('debounceEnd')
let interval = null
let intervalDebounceEnd
let image = null
let i = 5
let iDebounceEnd = 45
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

// if settings.USE_QR_CODE is True

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
      const myRequest = new Request('/photo/', {
        method: 'POST',
        body: canvasToBase64()
      })
      fetch(myRequest).then(async function(response) {
        currentPhotoUUID = await response.text()
        if (use_qr_code) {
          form.style.display = 'none'
          qrcode.src = '/qrcode/' + currentPhotoUUID + '/'
          setInterval(() => {
            if (iDebounceEnd === 0) {
              window.location.reload()
            } else {
              const secText = iDebounceEnd <= 1 ? 'seconde' : 'secondes'
              debounceEnd.innerHTML = "Cette page s'auto-détruira dans " + iDebounceEnd + ' ' + secText
              iDebounceEnd = iDebounceEnd - 1
            }
          }, 1000)
        } else {
          qrcode.style.display = 'none'
        }
      })
    } else {
      debounce.innerText = i + '...'
      i = i - 1
    }
  }, 1000)
}

// if settings.USE_QR_CODE is False

email.addEventListener('input', function() {
  error.innerText = ''
})

document.getElementById('submit').addEventListener('click', function(e) {
  e.preventDefault()
  if (!email.value || email.value === '' || !validateEmail(email.value)) {
    error.innerText = 'Veuillez insérer une adresse mail valide'
    return
  }
  const myRequest = new Request('/email/', {
    method: 'POST',
    body: JSON.stringify({ email: email.value, uuid: currentPhotoUUID })
  })
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
