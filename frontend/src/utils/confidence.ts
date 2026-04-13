export function confidenceLabel(score: number) {
  if (score >= 0.8) return 'High confidence'
  if (score >= 0.65) return 'Medium confidence'
  return 'Low confidence'
}

