export function evaluateAngle(angleDeg) {
  if (angleDeg < 18) return 'Incline un peu plus vers le bas.';
  if (angleDeg > 32) return 'Relève légèrement la caméra.';
  if (angleDeg >= 22 && angleDeg <= 28) return 'Position idéale !';
  return null;
}
