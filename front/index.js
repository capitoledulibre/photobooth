let video = document.getElementById('video')
let canvas = document.getElementById('canvas')
let context = canvas.getContext('2d')
let debounce = document.getElementById('debounce')
let email = document.getElementById('inputEmail')
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
      console.log(error)
      alert('Can not access to camera :/')
    })
}

// Trigger photo take
document.getElementById('snap').addEventListener('click', function() {
  debounce.innerHTML = 'Pensez à sourir :)'
  interval=setInterval(() => {
    if(i===0) {
      clearInterval(interval)
      debounce.innerText=''
      context.drawImage(video,0,0,640,480)
      image = canvasToBase64()
      i=5
    } else {
      debounce.innerText=i+'...'
      i=i-1
    }
  }, 1000)
})

document.getElementById('submit').addEventListener('click', function(e) {
  e.preventDefault()
  let error = ''
  if (!email.value || email.value === '') {
    error += 'Veuillez insérer une adresse mail valide \n'
  }
  if (!image) {
    error += 'Veuillez prendre une photo'
  }
  if(error) {
    alert(error)
  } else {
    console.log('send photo and email to backend')
    email.value = ''
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
    alert('Vous devriez recevoir votre photo dans quelques instants :)')
  }
})

function canvasToBase64() {
  return canvas.toDataURL('image/png')
}
