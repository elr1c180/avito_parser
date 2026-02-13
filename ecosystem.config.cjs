module.exports = {
  apps: [
    {
      name: "avito-admin",
      script: "python",
      args: "-m gunicorn config.wsgi:application --bind 0.0.0.0:8000",
      cwd: "./",
      interpreter: "none",
      env: { DJANGO_SETTINGS_MODULE: "config.settings" },
    },
    {
      name: "avito-bot",
      script: "bot.py",
      interpreter: "python",
      cwd: "./",
    },
  ],
};
