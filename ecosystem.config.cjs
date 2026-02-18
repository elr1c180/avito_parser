const path = require("path");
const root = path.resolve(__dirname);
// На сервере используем Python из venv (на Windows: venv\\Scripts\\python.exe)
const venvPython = path.join(root, "venv", "bin", "python");

module.exports = {
  apps: [
    {
      name: "avito-admin",
      script: venvPython,
      args: "-m gunicorn config.wsgi:application --bind 0.0.0.0:8000",
      cwd: root,
      interpreter: "none",
      env: { DJANGO_SETTINGS_MODULE: "config.settings" },
    },
    {
      name: "avito-bot",
      script: "bot.py",
      interpreter: venvPython,
      cwd: root,
    },
  ],
};
