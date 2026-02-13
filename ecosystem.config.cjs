const path = require("path");
module.exports = {
  apps: [
    {
      name: "avito-admin",
      script: "python3",
      args: "-m gunicorn config.wsgi:application --bind 0.0.0.0:8000",
      cwd: path.resolve(__dirname),
      interpreter: "none",
      env: { DJANGO_SETTINGS_MODULE: "config.settings" },
    },
    {
      name: "avito-bot",
      script: "bot.py",
      interpreter: "python3",
      cwd: path.resolve(__dirname),
    },
  ],
};
