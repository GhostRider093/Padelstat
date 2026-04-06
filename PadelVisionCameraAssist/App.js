import React from 'react';
import { SafeAreaView } from 'react-native';
import CameraAssist from './components/CameraAssistScreen';

export default function App() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#000' }}>
      <CameraAssist />
    </SafeAreaView>
  );
}
