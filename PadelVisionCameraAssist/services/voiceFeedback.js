import * as Speech from 'expo-speech';

export function speak(text) {
  if (!text) return;
  try {
    Speech.speak(text, { language: 'fr-FR', pitch: 1.0, rate: 1.0 });
  } catch {}
}
