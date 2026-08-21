export function egp(minor: number) {
  return `${(minor / 100).toLocaleString("ar-EG", {
    maximumFractionDigits: 2,
  })} ج.م`;
}
