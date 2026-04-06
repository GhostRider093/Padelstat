import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function AngleIndicator({ angle, ideal = 24 }) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.text}>Angle actuel : {angle.toFixed(1)}°</Text>
      <Text style={styles.sub}>Angle idéal : {ideal}° ± 5°</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { padding: 8 },
  text: { color: '#fff' },
  sub: { color: '#9ca3af' },
});
