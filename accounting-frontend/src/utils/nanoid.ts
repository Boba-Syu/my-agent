/** 简易 nanoid：生成 8 位随机 ID */
export function nanoid(): string {
  return Math.random().toString(36).slice(2, 10)
}
