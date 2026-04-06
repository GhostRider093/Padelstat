import React from 'react';
import { View, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function VideoControls({ recording, onStart, onStop }) {
  return (
    <View style={styles.controls}>
      {recording ? (
        <TouchableOpacity style={styles.stopBtn} onPress={onStop}>
          <Ionicons name="stop" size={40} color="#fff" />
        </TouchableOpacity>
      ) : (
        <TouchableOpacity style={styles.recordBtn} onPress={onStart}>
          <Ionicons name="radio-button-on" size={80} color="red" />
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  controls: { position: 'absolute', bottom: 40, width: '100%', alignItems: 'center' },
  recordBtn: { backgroundColor: '#00000080', padding: 10, borderRadius: 50 },
  stopBtn: { backgroundColor: '#ff3333', padding: 20, borderRadius: 50 }
});
