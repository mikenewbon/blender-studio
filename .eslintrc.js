module.exports = {
  env: {
    browser: true,
    es6: true
  },
  extends: ["airbnb-base", "prettier"],
  plugins: ["prettier"],
  parserOptions: {
    ecmaVersion: 2018
  },
  rules: {
    "prettier/prettier": ["error"],
    "no-underscore-dangle": "off",
    "no-implicit-globals": ["error", {lexicalBindings: true}],
    "no-else-return": "off",
    "max-classes-per-file": "off",
    "no-shadow": "off",
    "no-use-before-define": ["error", {"classes": false}]
  }
};
