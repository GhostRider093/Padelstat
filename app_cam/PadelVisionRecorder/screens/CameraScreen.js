import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, useWindowDimensions } from 'react-native';
import { Camera } from 'expo-camera/legacy';
import * as FileSystem from 'expo-file-system';
import * as MediaLibrary from 'expo-media-library';
import { Ionicons } from '@expo/vector-icons';
import { speak, stop as stopVoice } from '../services/voiceFeedback';
const SEGMENT_DURATION_SECONDS = 20 * 60; // 20 minutes
const REMINDER_MOMENTS = [10, 20]; // seconds
export default function CameraScreen({ navigation, route }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [hasMediaPermission, setHasMediaPermission] = useState(null);
  const [recording, setRecording] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [zoom, setZoom] = useState(0);
  const [segmentCount, setSegmentCount] = useState(0);
  const cameraRef = useRef(null);
  const reminderTimers = useRef([]);
  const shouldContinueRef = useRef(false);
  const segmentsRef = useRef([]);
  const finalizedRef = useRef(false);
  const { width, height } = useWindowDimensions();
  const isLandscape = width > height;
  useEffect(() => {
    (async () => {
      const cam = await Camera.requestCameraPermissionsAsync();
      const mic = await Camera.requestMicrophonePermissionsAsync();
      const media = await MediaLibrary.requestPermissionsAsync();
      setHasPermission(cam.status === 'granted' && mic.status === 'granted');
      setHasMediaPermission(media.status === 'granted');
    })();
  }, []);
  useEffect(() => {
    const autoStart = route?.params?.autoStart;
    if (autoStart && cameraReady && !recording) {
      setTimeout(() => {
        startRecording();
      }, 800);
    }
  }, [route?.params, cameraReady]);
  const clearReminders = () => {
    reminderTimers.current.forEach(clearTimeout);
    reminderTimers.current = [];
  };
  const scheduleReminders = () => {
    clearReminders();
    REMINDER_MOMENTS.forEach((seconds) => {
      const timer = setTimeout(() => speak('Enregistrement toujours en cours'), seconds * 1000);
      reminderTimers.current.push(timer);
    });
  };
  const startRecording = async () => {
    if (!cameraRef.current || recording) return;
    stopVoice();
    setZoom(0); // force ultra wide
    setRecording(true);
    shouldContinueRef.current = true;
    segmentsRef.current = [];
    setSegmentCount(0);
    finalizedRef.current = false;
    speak('Enregistrement en cours');
    scheduleReminders();
    recordNextSegment();
  };
  const recordNextSegment = async () => {
    if (!shouldContinueRef.current || !cameraRef.current) return;
    try {
      const video = await cameraRef.current.recordAsync({
        quality: Camera.Constants.VideoQuality['1080p'],
        maxDuration: SEGMENT_DURATION_SECONDS,
        mute: false,
      });
      if (!video?.uri) {
        if (!shouldContinueRef.current) {
          finalizeRecording();
        }
        return;
      }
      const fileUri = FileSystem.documentDirectory + `segment_${Date.now()}.mp4`;
      await FileSystem.moveAsync({ from: video.uri, to: fileUri });
      segmentsRef.current.push(fileUri);
      setSegmentCount(segmentsRef.current.length);
      clearReminders();
      if (hasMediaPermission) {
        try {
          await MediaLibrary.saveToLibraryAsync(fileUri);
        } catch (err) {
          console.log('Erreur sauvegarde galerie segment:', err);
        }
      }
      if (shouldContinueRef.current) {
        scheduleReminders();
        setTimeout(() => recordNextSegment(), 500);
      } else {
        finalizeRecording();
      }
    } catch (err) {
      if (shouldContinueRef.current) {
        console.log('Erreur record segment:', err);
      }
      finalizeRecording(err);
    }
  };
  const finalizeRecording = (error) => {
    if (finalizedRef.current) return;
    finalizedRef.current = true;
    shouldContinueRef.current = false;
    clearReminders();
    setRecording(false);
    stopVoice();
    if (error) {
      speak("Enregistrement interrompu");
      return;
    }
    speak('Enregistrement terminé');
    navigation.navigate('UploadScreen', { segments: [...segmentsRef.current] });
  };
  const stopRecording = () => {
    if (!cameraRef.current || !recording) return;
    shouldContinueRef.current = false;
    clearReminders();
    cameraRef.current.stopRecording();
  };
  useEffect(() => {
    return () => {
      clearReminders();
      shouldContinueRef.current = false;
    };
  }, []);
  if (hasPermission === false) return <Text>Permission caméra refusée</Text>;
  if (hasMediaPermission === false) return <Text>Permission galerie refusée</Text>;
  return (
    <View style={styles.container}>
      <Camera
        style={styles.camera}
        type={Camera.Constants.Type.back}
        onCameraReady={() => setCameraReady(true)}
        ref={cameraRef}
        ratio="16:9"
        zoom={zoom}
        whiteBalance={Camera.Constants.WhiteBalance.auto}
        useCamera2Api
      />
      <View
        style={[
          styles.infoBanner,
          isLandscape ? { top: 20, left: 20 } : { top: 60, alignSelf: 'center' },
        ]}
      >
        <Text style={styles.infoText}>Grand angle verrouille (0.6x)</Text>
        <Text style={styles.infoSubText}>Segments enregistrés : {segmentCount}</Text>
      </View>
      <View
        style={[
          styles.controls,
          isLandscape
            ? {
                bottom: 0,
                top: 0,
                right: 0,
                width: 110,
                height: '100%',
                justifyContent: 'center',
                backgroundColor: 'rgba(0,0,0,0.3)',
              }
            : {
                bottom: 40,
                width: '100%',
                alignItems: 'center',
              },
        ]}
      >
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
      <TouchableOpacity
        style={[
          styles.framingBtn,
          isLandscape ? { top: 20, right: 140 } : { top: 40, right: 20 },
        ]}
        onPress={() => navigation.navigate('FramingAssistScreen')}
      >
        <Text style={styles.framingText}>Assistant cadrage</Text>
      </TouchableOpacity>
    </View>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1 },
  controls: { position: 'absolute', alignItems: 'center' },
  recordBtn: { backgroundColor: '#00000080', padding: 10, borderRadius: 50 },
  stopBtn: { backgroundColor: '#ff3333', padding: 20, borderRadius: 50 },
  framingBtn: { position: 'absolute', backgroundColor: '#333', padding: 10, borderRadius: 10 },
  framingText: { color: '#fff', fontWeight: 'bold' },
  infoBanner: {
    position: 'absolute',
    paddingVertical: 8,
    paddingHorizontal: 14,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 12,
  },
  infoText: { color: '#f3f4f6', fontWeight: 'bold' },
  infoSubText: { color: '#d1d5db', marginTop: 2, fontSize: 12 },
});
