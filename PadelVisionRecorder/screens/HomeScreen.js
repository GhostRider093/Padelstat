import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

export default function HomeScreen({ navigation }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>PadelVision Recorder</Text>
      <TouchableOpacity style={styles.btn} onPress={() => navigation.navigate('CameraScreen')}>
        <Text style={styles.btnText}>🎥 Enregistrer un match</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.btn} onPress={() => navigation.navigate('FramingAssistScreen')}>
        <Text style={styles.btnText}>📐 Assistant de cadrage</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center' },
  title: { color: '#fff', fontSize: 22, fontWeight: 'bold', marginBottom: 24 },
  btn: { backgroundColor: '#333', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10, marginVertical: 8 },
  btnText: { color: '#fff', fontWeight: 'bold' }
});
