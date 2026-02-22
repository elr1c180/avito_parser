const path = require("path");
const root = path.resolve(__dirname);

module.exports = {
  apps: [
    {
      name: "avito-admin",
      script: "python3",
      args: "-m gunicorn config.wsgi:application --bind 0.0.0.0:8000",
      cwd: root,
      interpreter: "none",
      env: { DJANGO_SETTINGS_MODULE: "config.settings" },
    },
    {
      name: "avito-bot",
      script: "bot.py",
      interpreter: "python3",
      cwd: root,
    },
  ],
};
