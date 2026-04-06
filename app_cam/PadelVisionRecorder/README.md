# PadelVision Recorder (Expo)

Application d'enregistrement vidéo pour matchs de padel, avec assistant de cadrage et upload backend.

## Modules
- expo, react, react-native
- expo-camera, expo-av, expo-sensors, expo-file-system
- expo-speech
- axios
- react-native-opencv4 (via Expo Dev Client)
- navigation: @react-navigation/native, @react-navigation/native-stack

## Installation
```pwsh
cd "e:\projet\padel stat\app_cam\PadelVisionRecorder"
npm install
```

## Lancer en dev
```pwsh
npx expo start
```

## Dev Client (pour OpenCV)
```pwsh
npx expo install expo-dev-client
npx expo run:android
npx expo start --dev-client
```

## Structure
```
PadelVisionRecorder/
  App.js
  package.json
  screens/
    HomeScreen.js
    CameraScreen.js
    FramingAssistScreen.js
    UploadScreen.js
  components/
    CameraPreview.js
    AngleIndicator.js
    FramingOverlay.js
    VideoControls.js
  services/
    angleService.js
    opencvService.js
    uploadService.js
    videoService.js
  utils/
    math.js
    constants.js
  .vscode/
    padelvision.prompt
```
