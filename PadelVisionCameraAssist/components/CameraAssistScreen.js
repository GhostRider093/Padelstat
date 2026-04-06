import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Camera } from 'expo-camera';
import { Gyroscope } from 'expo-sensors';
import { evaluateAngle } from '../services/angleService';
import { speak } from '../services/voiceFeedback';
import { detectCourtFromFrameBase64 } from '../services/opencvService';

export default function CameraAssist() {
  const [hasPermission, setHasPermission] = useState(null);
  const [pitch, setPitch] = useState(0);
  const [terrainDetected, setTerrainDetected] = useState(false);
  const cameraRef = useRef(null);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();

    Gyroscope.setUpdateInterval(400);
    const sub = Gyroscope.addListener(({ x }) => {
      const angleDeg = Math.abs(x * 57.3); // rad -> deg
      setPitch(angleDeg);
      const guidance = evaluateAngle(angleDeg);
      if (guidance) speak(guidance);
    });
    return () => sub && sub.remove();
  }, []);

  useEffect(() => {
    const interval = setInterval(async () => {
      if (!cameraRef.current) return;
      try {
        const pic = await cameraRef.current.takePictureAsync({
          base64: true,
          skipProcessing: true,
          quality: 0.1,
        });
        const detected = await detectCourtFromFrameBase64(pic.base64);
        setTerrainDetected(detected);
      } catch (e) {
        // silently ignore in MVP
      }
    }, 500);
    return () => clearInterval(interval);
  }, []);

  if (hasPermission === null) return <Text style={styles.txt}>Permission caméra…</Text>;
  if (hasPermission === false) return <Text style={styles.txt}>Permission caméra manquante</Text>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Assistant de cadrage PadelVision</Text>

      <View style={styles.infoRow}>
        <Text style={styles.info}>Inclinaison actuelle : {pitch.toFixed(1)}°</Text>
        <Text style={styles.info}>Inclinaison idéale : 24° ± 5°</Text>
      </View>

      <View style={styles.infoRow}>
        <Text style={styles.info}>Terrain détecté : {terrainDetected ? 'Oui' : 'Non'}</Text>
      </View>

      <Camera
        ref={cameraRef}
        style={styles.camera}
        onCameraReady={() => console.log('Camera OK')}
      />

      <Text style={styles.feedback}>Conseil vocal actif: ajuste jusqu’à 24° ± 5°</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#000' },
  title: { color: '#fff', fontSize: 20, fontWeight: 'bold', marginBottom: 8 },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between' },
  info: { color: '#ccc', marginVertical: 4 },
  camera: { flex: 1, marginTop: 10, borderRadius: 10, overflow: 'hidden' },
  feedback: { marginTop: 8, color: '#9ca3af' },
  txt: { color: '#fff', padding: 20 },
});
