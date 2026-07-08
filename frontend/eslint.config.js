import js from '@eslint/js';
import reactPlugin from 'eslint-plugin-react';
import globals from 'globals';

// eslint-plugin-react-hooks v7 has circular refs in configs that cause
// ESLint to hang. Import only rules + meta to break the cycle.
const hooksPkg = (await import('eslint-plugin-react-hooks')).default;
const hooksPlugin = {
  rules: hooksPkg.rules,
  meta: hooksPkg.meta,
};

export default [
  js.configs.recommended,

  // React recommended flat config
  reactPlugin.configs.flat.recommended,

  // React hooks — minimal plugin to avoid circular ref hang
  {
    plugins: {
      'react-hooks': hooksPlugin,
    },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },

  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
    },
    rules: {
      'no-unused-vars': 'warn',
      'no-console': 'warn',
      // React 19 JSX transform
      'react/jsx-uses-react': 'off',
      'react/react-in-jsx-scope': 'off',
    },
    settings: {
      react: { version: '19.0' },
    },
  },

  {
    ignores: ['dist/', 'node_modules/', '**/__tests__/'],
  },
];
