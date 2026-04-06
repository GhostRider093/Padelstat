import cv from "react-native-opencv4";

// ⚠️ Important : Ce fichier ne doit contenir *que* de la logique de vision.
// Il retourne simplement la hauteur Y moyenne de la grille détectée.
// Renvoie null si rien n'est détecté.

export async function detectGridPosition(base64Image) {
  try {
    // 1️⃣ Décodage de l'image en Mat OpenCV
    const mat = cv.imdecode(base64Image);

    if (!mat || mat.empty()) {
      console.log("OpenCV: image vide");
      return null;
    }

    // 2️⃣ Conversion en niveaux de gris
    const gray = new cv.Mat();
    cv.cvtColor(mat, gray, cv.COLOR_RGBA2GRAY);

    // 3️⃣ Filtrage (optionnel mais améliore la stabilité)
    const blurred = new cv.Mat();
    cv.GaussianBlur(gray, blurred, { width: 5, height: 5 }, 0);

    // 4️⃣ Détection de contours
    const edges = new cv.Mat();
    cv.Canny(blurred, edges, 60, 130);

    // 5️⃣ Détection de segments de lignes
    const lines = new cv.Mat();
    cv.HoughLinesP(
      edges,
      lines,
      1,
      Math.PI / 180,
      45,   // seuil
      40,   // longueur min
      10    // écart max
    );

    if (lines.rows === 0) {
      return null;
    }

    // 6️⃣ Garder uniquement les lignes *verticales*
    let yValues = [];
    for (let i = 0; i < lines.rows; i++) {
      const [x1, y1, x2, y2] = lines.data32S.slice(i * 4, i * 4 + 4);

      const dx = Math.abs(x2 - x1);
      const dy = Math.abs(y2 - y1);

      // Sélectionne les lignes verticales (grille)
      if (dx < 12 && dy > 25) {
        const avgY = (y1 + y2) / 2;
        yValues.push(avgY);
      }
    }

    if (yValues.length === 0) {
      return null;
    }

    // 7️⃣ Calcul de la hauteur moyenne Y de la grille
    const avg = yValues.reduce((a, b) => a + b, 0) / yValues.length;

    // Clean
    mat.delete();
    gray.delete();
    blurred.delete();
    edges.delete();
    lines.delete();

    return avg;
  } catch (err) {
    console.log("Erreur OpenCV detectGridPosition:", err);
    return null;
  }
}
