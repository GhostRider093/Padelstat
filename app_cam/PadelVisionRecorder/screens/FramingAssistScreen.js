import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Image, useWindowDimensions, PanResponder, Alert } from 'react-native';
import { Camera } from 'expo-camera/legacy';
import { DeviceMotion } from 'expo-sensors';
import { speak, stop as stopVoice } from '../services/voiceFeedback';
import { Ionicons } from '@expo/vector-icons';
const SENSITIVITY = 15; // Pixels per degree of pitch difference (approx)
const ALIGN_TOLERANCE = 1; // Degrees - Plus strict pour éviter démarrage prématuré
export default function FramingAssistScreen({ navigation }) {
  const { width, height } = useWindowDimensions();
  // Steps: 'capture' -> 'place' -> 'align'
  const [step, setStep] = useState('capture');
  const [hasPermission, setHasPermission] = useState(null);
  const [cameraReady, setCameraReady] = useState(false);
  // Data
  const [referencePhotoUri, setReferencePhotoUri] = useState(null);
  const [referencePitch, setReferencePitch] = useState(0);
  const [referenceLineY, setReferenceLineY] = useState(height * 0.3); // Default 30%
  // Live Data
  const [currentPitch, setCurrentPitch] = useState(0);
  const [isAligned, setIsAligned] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [pitchDiff, setPitchDiff] = useState(0);
  const [invertPitch, setInvertPitch] = useState(false);
  const cameraRef = useRef(null);
  const countdownRef = useRef(null);
  const lastGuidanceTime = useRef(0);
  // --- Permissions ---
  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);
  // --- Sensors ---
  useEffect(() => {
    DeviceMotion.setUpdateInterval(100);
    const subscription = DeviceMotion.addListener((motion) => {
      if (motion && motion.rotation) {
        // Beta is rotation around X axis (Pitch)
        // Convert radians to degrees
        const pitchDegrees = motion.rotation.beta * (180 / Math.PI);
        setCurrentPitch(pitchDegrees);
      }
    });
    return () => subscription.remove();
  }, []);
  // --- Guidance Logic (Only in Align step) ---
  useEffect(() => {
    if (step !== 'align' || countdown !== null) return;
    const diff = (invertPitch ? -1 : 1) * (currentPitch - referencePitch);
    const absDiff = Math.abs(diff);
    const now = Date.now();
    
    setPitchDiff(absDiff);
    
    // Check alignment
    if (absDiff < ALIGN_TOLERANCE) {
      if (!isAligned) {
        setIsAligned(true);
        speak("Parfait ! Alignement détecté. Ne bougez plus.");
        startCountdown();
      }
    } else {
      if (isAligned) {
        setIsAligned(false);
        stopCountdown();
        speak("Alignement perdu, repositionnez la caméra.");
      }
      // Audio guidance every 2 seconds
      if (now - lastGuidanceTime.current > 2000) {
        lastGuidanceTime.current = now;
          if (diff > ALIGN_TOLERANCE) {
           speak("Relevez la caméra");
          } else if (diff < -ALIGN_TOLERANCE) {
           speak("Baissez la caméra");
        }
      }
    }
  }, [currentPitch, referencePitch, step, isAligned, countdown]);
  const startCountdown = () => {
    setCountdown(10);
    let count = 10;
    speak("Alignement parfait ! Démarrage dans 10 secondes.");
    countdownRef.current = setInterval(() => {
      count--;
      setCountdown(count);
      if (count === 5) {
        speak("5 secondes");
      } else if (count === 3) {
        speak("3 secondes");
      } else if (count === 1) {
        speak("1 seconde");
      } else if (count <= 0) {
        clearInterval(countdownRef.current);
        speak("Enregistrement en cours");
        navigation.replace("CameraScreen", { autoStart: true });
      }
    }, 1000);
  };
  const stopCountdown = () => {
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    setCountdown(null);
  };
  // --- Actions ---
  const takeReferencePhoto = async () => {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePictureAsync({ quality: 0.5, skipProcessing: true });
        setReferencePhotoUri(photo.uri);
        setReferencePitch(currentPitch); // Capture the pitch at this moment
        setStep('place');
        speak("Placez la ligne rouge sur le haut du filet.");
      } catch (e) {
        console.error(e);
        Alert.alert("Erreur", "Impossible de prendre la photo");
      }
    }
  };
  const confirmPlacement = () => {
    setStep('align');
    speak("Alignez la ligne verte sur la ligne rouge.");
  };
  // --- PanResponder for Line Placement ---
  // We create it once, but we need it to access state setters.
  // Since we use functional updates setReferenceLineY(prev => ...), it's fine.
  // But we need to attach it to a View.
  // We'll define the PanResponder configuration directly in the render for simplicity 
  // or use a useRef that doesn't depend on closure variables if possible.
  // Actually, creating it in render is fine for this simple case, 
  // or use useMemo.
  // Let's use the inline creation in the JSX as I wrote in the plan.
  if (hasPermission === null) return <View />;
  if (hasPermission === false) return <Text>Pas d'accès caméra</Text>;
  return (
    <View style={styles.container}>
      {/* STEP 1: CAPTURE */}
      {step === 'capture' && (
        <View style={styles.fullScreen}>
          <Camera 
            ref={cameraRef} 
            style={styles.camera}
            onCameraReady={() => setCameraReady(true)}
          >
            <View style={styles.overlay}>
                <Text style={styles.instructionText}>Cadrez le filet et prenez une photo de référence</Text>
                <TouchableOpacity style={styles.captureBtn} onPress={takeReferencePhoto}>
                    <View style={styles.captureBtnInner} />
                </TouchableOpacity>
            </View>
          </Camera>
        </View>
      )}
      {/* STEP 2: PLACE LINE */}
      {step === 'place' && referencePhotoUri && (
        <View style={styles.fullScreen}>
          <Image source={{ uri: referencePhotoUri }} style={styles.previewImage} />
          {/* Draggable Line Area */}
          <View 
            style={styles.touchArea}
            {...PanResponder.create({
                onStartShouldSetPanResponder: () => true,
                onPanResponderMove: (evt, gestureState) => {
                    // gestureState.moveY is the absolute Y position of the touch
                    setReferenceLineY(gestureState.moveY);
                }
            }).panHandlers}
          >
             <View style={[styles.refLine, { top: referenceLineY, borderColor: 'red' }]} />
             <Text style={[styles.lineLabel, { top: referenceLineY - 25 }]}>Glissez pour placer sur le filet</Text>
          </View>
          <View style={styles.bottomControls}>
             <TouchableOpacity style={styles.confirmBtn} onPress={confirmPlacement}>
                 <Text style={styles.btnText}>Valider</Text>
             </TouchableOpacity>
             <TouchableOpacity style={styles.retryBtn} onPress={() => setStep('capture')}>
                 <Text style={styles.btnText}>Refaire</Text>
             </TouchableOpacity>
          </View>
        </View>
      )}
      {/* STEP 3: ALIGN */}
      {step === 'align' && (
        <View style={styles.fullScreen}>
          <Camera 
            ref={cameraRef} 
            style={styles.camera}
          />
          {/* Overlay Reference Photo (Transparent) */}
          <Image 
            source={{ uri: referencePhotoUri }} 
            style={[styles.previewImage, { opacity: 0.3, position: 'absolute' }]} 
          />
          {/* Reference Line (Fixed) */}
          <View style={[styles.refLine, { top: referenceLineY, borderColor: 'red', borderStyle: 'solid' }]} />
          {/* Live Line (Moving) */}
          {/* Green Line Y = RefY - (diff * SENSITIVITY) */}
          <View 
            style={[
                styles.refLine, 
                { 
                    top: referenceLineY - (((invertPitch ? -1 : 1) * (currentPitch - referencePitch)) * SENSITIVITY),
                    borderColor: isAligned ? '#00FF00' : 'yellow',
                    borderWidth: 4
                }
            ]} 
          />

          {/* Controls */}
          <View style={{ position: 'absolute', bottom: 20, left: 20, right: 20, flexDirection: 'row', justifyContent: 'space-between' }}>
            <TouchableOpacity 
              onPress={() => setInvertPitch((v) => !v)}
              style={{ backgroundColor: '#444', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8 }}
            >
              <Text style={{ color: '#fff', fontWeight: 'bold' }}>{invertPitch ? 'Direction: Inversée' : 'Direction: Normale'}</Text>
            </TouchableOpacity>
            {isAligned && countdown !== null && (
              <View style={{ backgroundColor: 'rgba(0,0,0,0.5)', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8 }}>
                <Text style={{ color: '#0f0', fontWeight: 'bold' }}>Démarrage dans {countdown}</Text>
              </View>
            )}
          </View>
          <View style={styles.infoPanel}>
             <Text style={styles.infoText}>
                 {isAligned 
                   ? `ALIGNÉ ! Démarrage dans ${countdown}s` 
                   : "Alignez la ligne jaune sur la rouge"}
             </Text>
             <Text style={styles.debugText}>
                 Écart: {pitchDiff.toFixed(1)}° (Tolérance: {ALIGN_TOLERANCE}°)
             </Text>
             <Text style={styles.debugText}>
                 Pitch: {currentPitch.toFixed(1)}° (Ref: {referencePitch.toFixed(1)}°)
             </Text>
          </View>
        </View>
      )}
    </View>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'black' },
  fullScreen: { flex: 1, width: '100%', height: '100%' },
  camera: { flex: 1 },
  previewImage: { width: '100%', height: '100%', resizeMode: 'cover' },
  overlay: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 50 },
  instructionText: { color: 'white', fontSize: 16, marginBottom: 20, textAlign: 'center', backgroundColor: 'rgba(0,0,0,0.5)', padding: 10, borderRadius: 5 },
  captureBtn: { width: 70, height: 70, borderRadius: 35, backgroundColor: 'white', justifyContent: 'center', alignItems: 'center' },
  captureBtnInner: { width: 60, height: 60, borderRadius: 30, backgroundColor: 'white', borderWidth: 2, borderColor: 'black' },
  touchArea: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 },
  refLine: { position: 'absolute', left: 0, right: 0, borderBottomWidth: 2, width: '100%' },
  lineLabel: { position: 'absolute', right: 10, color: 'white', fontWeight: 'bold', textShadowColor: 'black', textShadowRadius: 5 },
  bottomControls: { position: 'absolute', bottom: 30, flexDirection: 'row', width: '100%', justifyContent: 'space-around' },
  confirmBtn: { backgroundColor: '#28a745', paddingVertical: 15, paddingHorizontal: 40, borderRadius: 30 },
  retryBtn: { backgroundColor: '#dc3545', paddingVertical: 15, paddingHorizontal: 40, borderRadius: 30 },
  btnText: { color: 'white', fontWeight: 'bold', fontSize: 16 },
  infoPanel: { position: 'absolute', top: 50, alignSelf: 'center', backgroundColor: 'rgba(0,0,0,0.6)', padding: 15, borderRadius: 10 },
  infoText: { color: 'white', fontSize: 18, fontWeight: 'bold', textAlign: 'center' },
  debugText: { color: '#ccc', fontSize: 12, textAlign: 'center', marginTop: 5 }
});
