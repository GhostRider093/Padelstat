import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Camera } from 'expo-camera';

export default function CameraPreview({ cameraRef }) {
  return (
    <View style={styles.wrap}>
      <Camera ref={cameraRef} style={styles.camera} ratio="16:9" />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  camera: { flex: 1 }
});
