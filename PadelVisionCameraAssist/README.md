# PadelVision Camera Assist (Expo)

Assistant de cadrage pour filmer des matchs de padel avec un smartphone.

## Fonctionnalités
- Aperçu caméra (Expo Camera)
- Lecture gyroscope (Expo Sensors) et calcul de pitch
- Feedback vocal en temps réel (Expo Speech)
- Détection terrain (MVP, branchement OpenCV prévu)

## Prérequis
- Node.js + npm
- Expo CLI via `npx`
- Pour OpenCV: Expo Dev Client (build natif)

## Installation
```pwsh
cd "e:\projet\padel stat\PadelVisionCameraAssist"
# Installer dépendances
npm install
```

## Lancer en dev (sans OpenCV natif)
```pwsh
npx expo start
```

## Activer OpenCV (Dev Client)
```pwsh
npx expo install expo-dev-client
npx expo run:android
# puis
npx expo start --dev-client
```

## Arborescence
```
PadelVisionCameraAssist/
  App.js
  package.json
  components/
    CameraAssistScreen.js
    AngleIndicator.js
    DetectionOverlay.js
  services/
    angleService.js
    opencvService.js
    voiceFeedback.js
  utils/
    math.js
  .vscode/
    prompts.md
```

## Notes
- La capture de frame via `takePictureAsync({ base64: true })` est un MVP.
- Pour une détection fiable (Canny + HoughLinesP), connecter `react-native-opencv4` avec Dev Client.
- Adapter la fréquence des capteurs et la qualité pour économiser la batterie.
