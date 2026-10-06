/** Natural comparison of requirement codes like FR-1.1, FR-10.2, NFR-COST-1. */
export function compareRequirementCode(
  a: string | null | undefined,
  b: string | null | undefined,
): number {
  const left = a ?? "";
  const right = b ?? "";
  if (!left && !right) return 0;
  if (!left) return 1; // requirements without a code go last
  if (!right) return -1;
  const aParts = left.match(/(\d+|\D+)/g) ?? [];
  const bParts = right.match(/(\d+|\D+)/g) ?? [];
  const length = Math.max(aParts.length, bParts.length);
  for (let i = 0; i < length; i += 1) {
    const aPart = aParts[i];
    const bPart = bParts[i];
    if (aPart === undefined) return -1;
    if (bPart === undefined) return 1;
    const aNumeric = /^\d+$/.test(aPart);
    const bNumeric = /^\d+$/.test(bPart);
    if (aNumeric && bNumeric) {
      const diff = Number(aPart) - Number(bPart);
      if (diff !== 0) return diff;
    } else {
      const diff = aPart.localeCompare(bPart);
      if (diff !== 0) return diff;
    }
  }
  return 0;
}
