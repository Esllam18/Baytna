export function egp(minor: number): string {
  const amount = minor / 100;
  return `${Number.isInteger(amount) ? amount.toFixed(0) : amount.toFixed(2)} ج`;
}
export function compactPhone(phone: string): string { return phone.replace(/\s+/g, ""); }
