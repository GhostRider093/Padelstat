import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Camera } from 'expo-camera';
import { Gyroscope } from 'expo-sensors';
import { evaluateAngle } from '../services/angleService';
import { speak } from '../services/voiceFeedback';
import { detectCourtFromFrameBase64 } from '../services/opencvService';
import FramingOverlay from '../components/FramingOverlay';
import AngleIndicator from '../components/AngleIndicator';

export default function FramingAssistScreen() {
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
      const angleDeg = Math.abs(x * 57.3);
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
        const pic = await cameraRef.current.takePictureAsync({ base64: true, skipProcessing: true, quality: 0.1 });
        const detected = await detectCourtFromFrameBase64(pic.base64);
        setTerrainDetected(detected);
      } catch {}
    }, 500);
    return () => clearInterval(interval);
  }, []);

  if (hasPermission === null) return <Text style={styles.txt}>Permission caméra…</Text>;
  if (hasPermission === false) return <Text style={styles.txt}>Permission caméra manquante</Text>;

  const ideal = angleInIdealRange(pitch);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Assistant de cadrage</Text>
      <AngleIndicator angle={pitch} ideal={24} />
      <Text style={styles.info}>Terrain détecté : {terrainDetected ? 'Oui' : 'Non'}</Text>

      <View style={{ flex: 1 }}>
        <Camera ref={cameraRef} style={styles.camera} ratio="16:9" />
        <FramingOverlay ideal={ideal} />
      </View>

      <Text style={styles.feedback}>Ajuste jusqu'à 24° ± 5° puis démarre le match.</Text>
    </View>
  );
}

function angleInIdealRange(angle) {
  return angle >= 19 && angle <= 29; // tolérance ±5° autour de 24
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, backgroundColor: '#000' },
  title: { color: '#fff', fontSize: 20, fontWeight: 'bold', marginBottom: 8 },
  info: { color: '#ccc', marginBottom: 8 },
  camera: { flex: 1, borderRadius: 8, overflow: 'hidden' },
  feedback: { marginTop: 8, color: '#9ca3af' },
  txt: { color: '#fff', padding: 20 }
});
