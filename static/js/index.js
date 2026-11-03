'use strict'

/*
 * Photobooth kiosk.
 *
 * The page is a small state machine; the current state is stored in
 * body[data-state] and the CSS shows the matching screen:
 *
 *   starting -> idle -> countdown -> uploading -> result -> idle
 *                 ^                      |
 *                 +------- failed <------+
 *   starting/any -> camera-error -> (retry) -> idle
 *
 * The camera stream stays open for the whole lifetime of the page, so going
 * back to the idle screen is instant.
 */

const COUNTDOWN_SECONDS = 5
const RESULT_SECONDS = 45
// Ignore buzzer presses right after the result shows up, so an impatient
// double press does not skip the QR codes.
const RESULT_CLICK_GRACE_MS = 3000
const FAILED_SECONDS = 5
const CAMERA_RETRY_MS = 5000
const PUBLISH_POLL_MS = 1000
const PUBLISH_TIMEOUT_MS = 60000
// Photos are cropped to 16:9, the aspect ratio the frame is designed for.
const CAPTURE_ASPECT_RATIO = 16 / 9
const CAPTURE_IDEAL_WIDTH = 3840
const CAPTURE_IDEAL_HEIGHT = 2160
const JPEG_QUALITY = 0.92

const TEXT = {
  idle: 'Appuyez sur le buzzer pour prendre une photo',
  smile: 'Pensez à sourire :)',
  cameraError: "Impossible d'accéder à la caméra",
  cameraRetry: 'Nouvel essai dans quelques secondes…',
  failed: "Oups, la photo n'a pas pu être enregistrée.",
  failedHint: 'Veuillez réessayer.',
}

const el = {
  preview: document.getElementById('preview'),
  message: document.getElementById('message'),
  hint: document.getElementById('hint'),
  flash: document.getElementById('flash'),
  capture: document.getElementById('capture'),
  photo: document.getElementById('photo'),
  download: document.getElementById('download'),
  qrcode: document.getElementById('qrcode'),
  qrcodeBackground: document.getElementById('qrcode-background'),
  countdownEnd: document.getElementById('countdown-end'),
}

let state = 'starting'
// Incremented each time we go back to idle. Async callbacks (fetch, timers)
// started for a previous visitor compare it to their own value and give up.
let session = 0
let timers = []
let resultClickableAt = 0

function setState(newState) {
  state = newState
  document.body.dataset.state = newState
}

function showMessage(message, hint = '') {
  el.message.textContent = message
  el.hint.textContent = hint
}

// setTimeout that is cancelled when the session ends.
function later(callback, delayMs) {
  timers.push(setTimeout(callback, delayMs))
}

function wait(delayMs) {
  return new Promise(resolve => later(resolve, delayMs))
}

function clearTimers() {
  timers.forEach(clearTimeout)
  timers = []
}

/* Camera */

async function startCamera() {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('getUserMedia is not available (the page must be served over HTTPS or from localhost)')
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: CAPTURE_IDEAL_WIDTH }, height: { ideal: CAPTURE_IDEAL_HEIGHT } },
      audio: false,
    })
    const track = stream.getVideoTracks()[0]
    const settings = track.getSettings()
    console.log('Camera is', track.label)
    console.log('Got video', settings.width + 'x' + settings.height, 'fps=' + settings.frameRate)
    track.addEventListener('ended', () => cameraFailed(new Error('Camera disconnected')))

    el.preview.srcObject = stream
    await el.preview.play()
    goIdle()
  } catch (err) {
    cameraFailed(err)
  }
}

function cameraFailed(err) {
  console.error(err)
  clearTimers()
  session += 1
  setState('camera-error')
  showMessage(TEXT.cameraError, TEXT.cameraRetry)
  setTimeout(startCamera, CAMERA_RETRY_MS)
}

/* States */

function goIdle() {
  clearTimers()
  session += 1

  el.photo.classList.remove('loaded')
  el.photo.removeAttribute('src')
  el.qrcode.removeAttribute('src')
  el.qrcodeBackground.removeAttribute('src')
  el.download.dataset.status = 'uploading'
  el.countdownEnd.textContent = ''

  setState('idle')
  showMessage(TEXT.idle)
}

async function startCountdown() {
  const mySession = session
  setState('countdown')
  for (let remaining = COUNTDOWN_SECONDS; remaining > 0; remaining--) {
    showMessage(String(remaining), TEXT.smile)
    await wait(1000)
    if (mySession !== session) return
  }
  takePhoto(mySession)
}

function takePhoto(mySession) {
  drawCapture()
  flash()
  setState('uploading')

  el.capture.toBlob(async blob => {
    if (mySession !== session) return
    try {
      const photoUUID = await uploadPhoto(blob)
      if (mySession !== session) return
      showResult(photoUUID, mySession)
    } catch (err) {
      if (mySession !== session) return
      console.error(err)
      showFailure()
    }
  }, 'image/jpeg', JPEG_QUALITY)
}

// Copy the current video frame to the canvas, at the camera native
// resolution, center-cropped to the frame aspect ratio. The canvas doubles as
// the freeze frame shown while the photo is uploaded.
function drawCapture() {
  const video = el.preview
  const canvas = el.capture
  let sourceWidth = video.videoWidth
  let sourceHeight = video.videoHeight
  let sourceX = 0
  let sourceY = 0

  if (sourceWidth / sourceHeight > CAPTURE_ASPECT_RATIO) {
    sourceWidth = Math.round(sourceHeight * CAPTURE_ASPECT_RATIO)
    sourceX = Math.round((video.videoWidth - sourceWidth) / 2)
  } else {
    sourceHeight = Math.round(sourceWidth / CAPTURE_ASPECT_RATIO)
    sourceY = Math.round((video.videoHeight - sourceHeight) / 2)
  }

  canvas.width = sourceWidth
  canvas.height = sourceHeight
  canvas.getContext('2d').drawImage(
    video, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, sourceWidth, sourceHeight,
  )
}

function flash() {
  el.flash.classList.remove('active')
  // Force a reflow so the animation restarts even if it is still running.
  void el.flash.offsetWidth
  el.flash.classList.add('active')
}

async function uploadPhoto(blob) {
  if (!blob) {
    throw new Error('Could not encode the photo')
  }
  const response = await fetch('/photo/', {
    method: 'POST',
    headers: { 'Content-Type': 'image/jpeg' },
    body: blob,
  })
  if (!response.ok) {
    throw new Error('Upload failed with HTTP ' + response.status)
  }
  return (await response.text()).trim()
}

function showResult(photoUUID, mySession) {
  setState('result')
  el.download.dataset.status = 'pending'
  resultClickableAt = Date.now() + RESULT_CLICK_GRACE_MS

  el.photo.onload = () => el.photo.classList.add('loaded')
  el.photo.src = '/img-result/' + photoUUID + '/'

  waitForPublication(photoUUID, mySession)
  countdownToIdle(mySession)
}

// The QR codes point to the download server, which only has the photo once
// the rsync task is done: don't show them before that.
async function waitForPublication(photoUUID, mySession) {
  const deadline = Date.now() + PUBLISH_TIMEOUT_MS
  while (Date.now() < deadline) {
    try {
      const response = await fetch('/status/' + photoUUID + '/')
      if (mySession !== session) return
      if (response.ok && (await response.json()).published) {
        if (mySession !== session) return
        el.qrcode.src = '/qrcode/' + photoUUID + '/'
        el.qrcodeBackground.src = '/qrcode-background/' + photoUUID + '/'
        el.download.dataset.status = 'ready'
        return
      }
    } catch (err) {
      console.error(err)
    }
    await wait(PUBLISH_POLL_MS)
    if (mySession !== session) return
  }
  el.download.dataset.status = 'unavailable'
}

async function countdownToIdle(mySession) {
  for (let remaining = RESULT_SECONDS; remaining > 0; remaining--) {
    const unit = remaining > 1 ? 'secondes' : 'seconde'
    el.countdownEnd.textContent =
      "Cette page s'auto-détruira dans " + remaining + ' ' + unit +
      '. Appuyez sur le buzzer quand vous avez fini. Merci et bon Capitole du Libre :)'
    await wait(1000)
    if (mySession !== session) return
  }
  goIdle()
}

async function showFailure() {
  const mySession = session
  setState('failed')
  showMessage(TEXT.failed, TEXT.failedHint)
  await wait(FAILED_SECONDS * 1000)
  if (mySession !== session) return
  goIdle()
}

/* Buzzer: a mouse click, or a key for buzzers that emulate a keyboard. */

function onBuzzer() {
  if (state === 'idle') {
    startCountdown()
  } else if (state === 'result' && Date.now() >= resultClickableAt) {
    goIdle()
  }
}

document.addEventListener('click', onBuzzer)
document.addEventListener('keydown', event => {
  if (!event.repeat) {
    onBuzzer()
  }
})

startCamera()
