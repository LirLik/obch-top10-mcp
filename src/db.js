import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis;

export const prisma = globalForPrisma.__obchTop10Prisma
  ?? new PrismaClient({
    log: process.env.PRISMA_LOG === '1' ? ['error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.__obchTop10Prisma = prisma;
}

export async function checkDatabase() {
  await prisma.$queryRaw`SELECT 1`;
}
