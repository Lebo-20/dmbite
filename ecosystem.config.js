module.exports = {
  apps: [
    {
      name: "dramabite-bot",
      script: "python3",
      args: "main.py",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "production",
      }
    }
  ]
};
