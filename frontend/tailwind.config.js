const { light, dark } = require("@charcoal-ui/theme");
const { createTailwindConfig } = require("@charcoal-ui/tailwind-config");
/**
 * @type {import('tailwindcss/tailwind-config').TailwindConfig}
 */
module.exports = {
  darkMode: true,
  content: ["./src/**/*.tsx", "./src/**/*.html"],
  presets: [
    createTailwindConfig({
      version: "v3",
      theme: {
        ":root": light,
      },
    }),
  ],
  theme: {
    extend: {
      colors: {
        primary: "#93A3FF",
        "primary-hover": "#A7B4FF",
        "primary-press": "#BCC6FF",
        "primary-disabled": "#93A3FF4D",
        secondary: "#63E6FF",
        "secondary-hover": "#84EEFF",
        "secondary-press": "#A4F3FF",
        "secondary-disabled": "#63E6FF4D",
        base: "#111A3A",
        "text-primary": "#D9E4FF",
      },
      fontFamily: {
        M_PLUS_2: ["var(--font-m-plus-2)"],
        Montserrat: ["var(--font-montserrat)"],
      },
    },
  },
  plugins: [require("@tailwindcss/line-clamp")],
};
