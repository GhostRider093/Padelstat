// MVP: placeholder simple sans OpenCV natif.
// Pour production: utiliser react-native-opencv4 avec Expo Dev Client
// et implémenter Canny + HoughLinesP.
export async function detectCourtFromFrameBase64(base64Image) {
  if (!base64Image) return false;
  // TODO: brancher OpenCV réel (edges, lignes horizontales/verticales)
  return true;
}
