export const colors = {
  orange: "#FF7A00",
  orangeDark: "#B94F00",
  orangeSoft: "#FFF0E2",
  orangePale: "#FFF3E7",
  green: "#66A80F",
  greenDark: "#3D6710",
  greenSoft: "#EDF7E7",
  ink: "#1E1B18",
  muted: "#6E635B",
  border: "#EADFD4",
  surface: "#FFFFFF",
  canvas: "#FFFAF5",
  soft: "#F7F1EC",
  danger: "#B42318",
  dangerSoft: "#FEE4E2",
} as const;

export const spacing = { xs: 6, sm: 10, md: 14, lg: 18, xl: 24, xxl: 32 } as const;
export const radius = { sm: 12, md: 16, card: 20, lg: 24, pill: 999 } as const;
export const shadow = {
  shadowColor: "#462814",
  shadowOffset: { width: 0, height: 8 },
  shadowOpacity: 0.08,
  shadowRadius: 18,
  elevation: 3,
} as const;
