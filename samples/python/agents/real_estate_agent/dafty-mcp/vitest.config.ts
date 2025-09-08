import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Specify the root directory for tests
    dir: 'src',
    // You can also use 'include' to specify glob patterns for test files
    // include: ['src/**/*.test.ts'],
    // globals: true, // if you want to use vitest globals without importing
  },
});