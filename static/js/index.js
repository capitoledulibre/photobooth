let video = document.getElementById('video')
let Bigcanvas = document.getElementById('Bigcanvas')
let Bigcontext = Bigcanvas.getContext('2d')
let debounce = document.getElementById('debounce')
let secondScreenContainer = document.getElementById('secondScreenContainer')
let qrcodeImg = document.getElementById('qrcode')
let qrcodeBackgroundImg = document.getElementById('qrcode_background')
let imgResult = document.getElementById('imgResult')
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
const captureWidth = 1920 * 2
const captureHeight = 1080 * 2
let cameraAspectRation = 1

Bigcanvas.width = captureWidth
Bigcanvas.height = captureHeight

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  navigator.mediaDevices
    .getUserMedia({ video: { width: captureWidth, height: captureHeight } })
    .then(stream => {
      const tracks = stream.getVideoTracks()
      const settings = tracks[0].getSettings()
      console.log("Camera is ", tracks[0].label)
      console.log("Get video with ", settings.width, "x", settings.height, " fps=", settings.frameRate, " aspect=", settings.aspectRatio);
      cameraAspectRation = settings.aspectRatio
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
  debounce.innerHTML = 'Pensez à sourire :)'
  interval = setInterval(() => {
    if (i === 0) {
      video.style.display = 'none'
      secondScreenContainer.style.display = 'block'
      clearInterval(interval)
      debounce.innerText = ''
      Bigcontext.drawImage(video, 0, 0, captureWidth, captureHeight)
      i = 5
      const myRequest = new Request('/photo/', {
        method: 'POST',
        body: canvasToBase64()
      })
      fetch(myRequest).then(async function (response) {
        if (!response.ok) {
          throw new Error('Upload failed with HTTP ' + response.status)
        }
        currentPhotoUUID = await response.text()
        if (use_qr_code) {
          form.style.display = 'none'
          qrcodeImg.src = '/qrcode/' + currentPhotoUUID + '/'
          qrcodeBackgroundImg.src = '/qrcode-background/' + currentPhotoUUID + '/'
          imgResult.src = '/img-result/' + currentPhotoUUID + '/'
          document.getElementById('snapWindow').addEventListener('click', function () {
            window.location.reload()
          })
          setInterval(() => {
            if (iDebounceEnd === 0) {
              window.location.reload()
            } else {
              const secText = iDebounceEnd <= 1 ? 'seconde' : 'secondes'
              debounceEnd.innerHTML =
                "Cette page s'auto-détruira dans " +
                iDebounceEnd +
                ' ' +
                secText +
                ".<br />Vous pouvez également appuyer sur le buzzer si vous avez fini. <br />Merci d'avoir utilisé ce photobooth :)"
              iDebounceEnd = iDebounceEnd - 1
            }
          }, 1000)
        } else {
          qrcodeImg.style.display = 'none'
          qrcodeBackgroundImg.style.display = 'none'
        }
      }).catch(err => {
        // Don't leave the kiosk stuck on an empty screen: tell the user and
        // reset the page so the next person can try again.
        console.error(err)
        secondScreenContainer.style.display = 'none'
        debounce.innerText = 'Oups, la photo n\'a pas pu être enregistrée. Veuillez réessayer.'
        setTimeout(() => {
          window.location.reload()
        }, 5000)
      })
    } else {
      debounce.innerText = i + '...'
      i = i - 1
    }
  }, 1000)
}

// if settings.USE_QR_CODE is False

email.addEventListener('input', function () {
  error.innerText = ''
})

document.getElementById('submit').addEventListener('click', function (e) {
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
    if (!response.ok) {
      throw new Error('Email request failed with HTTP ' + response.status)
    }
    secondScreenContainer.style.display = 'none'
    success.style.display = 'block'
    setTimeout(() => {
      window.location.reload()
    }, 5000)
  }).catch(err => {
    console.error(err)
    error.innerText = "L'envoi du mail a échoué, veuillez réessayer"
  })
})

function canvasToBase64() {
  return Bigcanvas.toDataURL('image/jpeg', 0.98)
}

function validateEmail(email) {
  var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
  return re.test(email)
}
