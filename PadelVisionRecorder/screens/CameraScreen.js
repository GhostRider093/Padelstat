import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Camera } from 'expo-camera';
import * as FileSystem from 'expo-file-system';
import { Ionicons } from '@expo/vector-icons';

export default function CameraScreen({ navigation }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [recording, setRecording] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const cameraRef = useRef(null);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  const startRecording = async () => {
    if (!cameraRef.current) return;
    try {
      setRecording(true);
      const video = await cameraRef.current.recordAsync({
        quality: '1080p',
        maxDuration: 7200,
        // stabilizationMode: Camera.Constants.VideoStabilization.cinematic,
      });
      const fileUri = FileSystem.documentDirectory + `match_${Date.now()}.mp4`;
      await FileSystem.moveAsync({ from: video.uri, to: fileUri });
      navigation.navigate('UploadScreen', { videoUri: fileUri });
    } catch (e) {
      console.log('Erreur record:', e);
      setRecording(false);
    }
  };

  const stopRecording = () => {
    if (!cameraRef.current) return;
    setRecording(false);
    cameraRef.current.stopRecording();
  };

  if (hasPermission === false) return <Text>Permission caméra refusée</Text>;

  return (
    <View style={styles.container}>
      <Camera
        style={styles.camera}
        type={Camera.Constants.Type.back}
        onCameraReady={() => setCameraReady(true)}
        ref={cameraRef}
        ratio="16:9"
        zoom={0}
      />

      <View style={styles.controls}>
        {recording ? (
          <TouchableOpacity style={styles.stopBtn} onPress={stopRecording}>
            <Ionicons name="stop" size={40} color="#fff" />
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.recordBtn} onPress={startRecording} disabled={!cameraReady}>
            <Ionicons name="radio-button-on" size={80} color="red" />
          </TouchableOpacity>
        )}
      </View>

      <TouchableOpacity style={styles.framingBtn} onPress={() => navigation.navigate('FramingAssistScreen')}>
        <Text style={styles.framingText}>Assistant de cadrage 📐</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1 },
  controls: { position: 'absolute', bottom: 40, width: '100%', alignItems: 'center' },
  recordBtn: { backgroundColor: '#00000080', padding: 10, borderRadius: 50 },
  stopBtn: { backgroundColor: '#ff3333', padding: 20, borderRadius: 50 },
  framingBtn: { position: 'absolute', top: 40, right: 20, backgroundColor: '#333', padding: 10, borderRadius: 10 },
  framingText: { color: '#fff', fontWeight: 'bold' }
});
