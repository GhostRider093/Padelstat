import React from 'react';
import { View, StyleSheet } from 'react-native';

// Affiche une bande cible (30-50px) et un marqueur horizontal à gridY
export default function FramingOverlay({ ideal, gridY }) {
  return (
    <View style={[styles.overlay, ideal ? styles.ok : styles.warn]}>
      {/* Bande cible 30–50 px du haut */}
      <View style={styles.targetBand} />
      {/* Marqueur de la grille détectée */}
      {typeof gridY === 'number' && (
        <View style={[styles.gridLine, { top: Math.max(0, gridY) }]} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    borderWidth: 2,
  },
  ok: { borderColor: '#22c55e' },
  warn: { borderColor: '#f59e0b' },
  targetBand: {
    position: 'absolute',
    top: 30, // px depuis le haut
    left: 0,
    right: 0,
    height: 20, // 30→50 px bande
    backgroundColor: '#22c55e55',
  },
  gridLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: '#3b82f6',
  },
});
