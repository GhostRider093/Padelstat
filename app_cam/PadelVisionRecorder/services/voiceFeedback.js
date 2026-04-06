import * as Speech from "expo-speech";

let lastSpeakTime = 0;
let cooldown = 1500; // délai anti-spam
let speaking = false;

// 🔇 Stop immédiatement la voix
export function stop() {
  Speech.stop();
  speaking = false;
}

// 🔊 Parler avec gestion anti-spam + priorité
export function speak(text, lowPriority = false) {
  const now = Date.now();

  // Anti-spam pour les messages répétitifs
  if (lowPriority) {
    if (now - lastSpeakTime < cooldown) return;
  }

  // Stop si déjà en train de parler (évite les superpositions)
  if (speaking && !lowPriority) {
    Speech.stop();
  }

  speaking = true;

  Speech.speak(text, {
    rate: 0.95,
    pitch: 1.0,
    language: "fr-FR",
    onDone: () => {
      speaking = false;
    },
  });

  lastSpeakTime = now;
}
