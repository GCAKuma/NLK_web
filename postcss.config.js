// Tailwind's CLI compiles the @tailwind layers itself; autoprefixer is applied
// afterwards from here so vendor prefixes are added for older mobile browsers.
module.exports = {
  plugins: {
    autoprefixer: {},
  },
};
